from sqlalchemy import select

from core.queueing import submit, result
from core.records import get, insert, need, scan, update
from domain.cold_cells_model import cold_cells
from domain.thaw_samples_model import thaw_samples
from domain.seam_maps_model import seam_maps, seam_versions, seam_rechecks, seam_trials
from domain.cell_swaps_model import cell_swaps

ACTIVE, TRIAL, RETIRED = '现役', '试算', '停用'
PENDING, ENABLED, REDONE, STALE = '待启用', '已启用', '已重算', '已失效'
FALLBACK_VERSION = 'KNN-K4'


def active_version(conn, lock=False):
    query = select(seam_versions).where(seam_versions.c.state == ACTIVE)
    if lock:
        query = query.with_for_update()
    row = conn.execute(query).mappings().first()
    need(row is not None, '缺少现役评分版本')
    return dict(row)


def score_seam(conn, user, data):
    source=get(conn,thaw_samples,data.sample)
    need(not source['empty_test'],'空载测试不评估冰雕融缝')
    pool=[r for r in scan(conn,thaw_samples) if r['cell']==source['cell'] and
        not r['empty_test'] and r['code']!=data.sample]
    need(len(pool)>=20,'此柜格带载基线不足二十条')
    version=active_version(conn)
    return submit(user,{'source':source,'pool':pool,
        'neighbors':version['neighbors'],'version':version['code']})


def record_seam(conn, user, data):
    run=result(user,data.token)
    need(run['input'].get('kind','score')=='score','对照试算凭据请走试算登记')
    metrics=run['result']
    return insert(conn,seam_maps,code=data.code,sample=run['input']['source']['code'],
       density=metrics['density'],threshold=metrics['threshold'],token=data.token,
       version=run['input'].get('version') or FALLBACK_VERSION,
       decision='建议换格' if metrics['density']<metrics['threshold'] else '同档可留')


def record_recheck(conn, user, data):
    sample=get(conn,thaw_samples,data.sample)
    need(not sample['empty_test'],'空载测试不参与带载复检')
    taken=conn.execute(select(seam_rechecks).where(seam_rechecks.c.sample==data.sample)).first()
    need(taken is None,'该实测已有带载复检结论')
    return insert(conn,seam_rechecks,code=data.code,sample=data.sample,verdict=data.verdict)


def draft_version(conn, user, data):
    return insert(conn,seam_versions,code=data.code,neighbors=data.neighbors,state=TRIAL)


def run_trial(conn, user, data):
    version=get(conn,seam_versions,data.version)
    need(version['state']==TRIAL,'仅试算版本可发起对照')
    base=active_version(conn)
    samples={row['code']:row for row in scan(conn,thaw_samples)}
    batch=[]
    for recheck in scan(conn,seam_rechecks):
        sample=samples[recheck['sample']]
        if not sample['empty_test']:
            batch.append({'sample':sample,'verdict':recheck['verdict']})
    need(batch,'没有带复检结论的带载样本')
    pieces={item['sample']['piece'] for item in batch}
    pools={}
    for cell in sorted({item['sample']['cell'] for item in batch}):
        pool=[row for row in samples.values() if row['cell']==cell and
            not row['empty_test'] and row['piece'] not in pieces]
        need(len(pool)>=20,f'排除参加复检对照的冰雕后，{cell} 参考基线不足二十条')
        pools[cell]=pool
    return submit(user,{'kind':'trial','batch':batch,'pools':pools,
        'version':{'code':version['code'],'neighbors':version['neighbors']},
        'base':{'code':base['code'],'neighbors':base['neighbors']}})


def record_trial(conn, user, data):
    run=result(user,data.token)
    need(run['input'].get('kind')=='trial','该凭据不是对照试算')
    version=get(conn,seam_versions,run['input']['version']['code'])
    need(version['state']==TRIAL,'版本已切换，试算结果需重新发起')
    metrics=run['result']
    conn.execute(seam_trials.update().where(seam_trials.c.version==run['input']['version']['code'],
        seam_trials.c.state==PENDING).values(state=REDONE))
    return insert(conn,seam_trials,code=data.code,version=run['input']['version']['code'],
       base_version=run['input']['base']['code'],samples=metrics['samples'],
       miss_current=metrics['miss_current'],miss_trial=metrics['miss_trial'],
       false_current=metrics['false_current'],false_trial=metrics['false_trial'],
       token=data.token,state=PENDING)


def enable_version(conn, user, data):
    draft=get(conn,seam_versions,data.code,lock=True)
    need(draft['state']==TRIAL,'仅试算版本可启用')
    active=active_version(conn,lock=True)
    trial=conn.execute(select(seam_trials).where(seam_trials.c.version==data.code,
        seam_trials.c.state==PENDING)).mappings().first()
    need(trial is not None,'该版本没有待启用的试算对照')
    need(trial['base_version']==active['code'],'试算对照基于旧版，不能覆盖刚启用的版本')
    need(trial['miss_trial']<=trial['miss_current'] and
         trial['false_trial']<trial['false_current'],
         '试算版漏报不增加且误报减少才可启用')
    update(conn,seam_versions,active['code'],state=RETIRED)
    update(conn,seam_trials,trial['code'],state=ENABLED)
    conn.execute(seam_trials.update().where(seam_trials.c.state==PENDING).values(state=STALE))
    return update(conn,seam_versions,data.code,state=ACTIVE)
