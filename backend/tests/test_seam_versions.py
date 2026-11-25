import json
import os
import sys
from pathlib import Path

os.environ['DATABASE_URL'] = 'sqlite:////tmp/seam-version-tests.db'
os.environ['REDIS_URL'] = 'redis://localhost'
os.environ['JWT_SECRET'] = 'test-secret'
os.environ['SEED_DEMO'] = 'true'

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fakeredis
import pytest

import core.queueing as queueing

queueing.broker = fakeredis.FakeRedis(decode_responses=True)

from fastapi.testclient import TestClient

from core.app import app
from core.db import engine
from core.queueing import QUEUE
from domain.learning import calculate

DB_FILE = Path('/tmp/seam-version-tests.db')


@pytest.fixture()
def client():
    engine.dispose()
    DB_FILE.unlink(missing_ok=True)
    queueing.broker.flushall()
    with TestClient(app) as test_client:
        yield test_client


def login(client, role):
    response = client.post('/auth/login', json={'email': f'{role}@demo.test',
                                                'password': 'DemoC0de!2026'})
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['token']}


def drain():
    while True:
        raw = queueing.broker.lpop(QUEUE)
        if raw is None:
            return
        job = json.loads(raw)
        status = {'owner': job['owner'], 'input': job['input']}
        try:
            status.update(status='ready', result=calculate(job['input']))
        except ValueError as exc:
            status.update(status='rejected', detail=str(exc))
        queueing.broker.set(f'compute:{job["token"]}', json.dumps(status, allow_nan=False), ex=86400)


def enable_knn_k8(client, operator, reviewer):
    assert client.post('/seam_maps/draft-version', headers=operator,
                       json={'code': 'KNN-K8', 'neighbors': 8}).status_code == 200
    token = client.post('/seam_maps/run-trial', headers=operator,
                        json={'version': 'KNN-K8'}).json()['token']
    drain()
    response = client.post('/seam_maps/record-trial', headers=reviewer,
                           json={'code': 'TRY-8', 'token': token})
    assert response.status_code == 200
    assert client.post('/seam_maps/enable-version', headers=reviewer,
                       json={'code': 'KNN-K8'}).status_code == 200


def test_seed_exposes_version_per_order(client):
    viewer = login(client, 'viewer')
    rows = client.get('/seam_maps', headers=viewer).json()
    assert rows[0]['version'] == 'KNN-K4'
    versions = client.get('/seam_maps/versions', headers=viewer).json()
    assert versions == [{'code': 'KNN-K4', 'neighbors': 4, 'state': '现役'}]
    rechecks = client.get('/seam_maps/rechecks', headers=viewer).json()
    assert {row['sample'] for row in rechecks} == {'ICE-R01', 'ICE-R02'}


def test_score_and_record_stamps_active_version(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    token = client.post('/seam_maps/score-seam', headers=operator,
                        json={'sample': 'ICE-S05'}).json()['token']
    drain()
    response = client.post('/seam_maps/record-seam', headers=reviewer,
                           json={'code': 'DENS-101', 'token': token})
    assert response.status_code == 200
    row = [row for row in client.get('/seam_maps', headers=reviewer).json()
           if row['code'] == 'DENS-101'][0]
    assert row['version'] == 'KNN-K4'
    assert row['sample'] == 'ICE-S05'


def test_recheck_rules(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    empty = client.post('/seam_maps/record-recheck', headers=reviewer,
                        json={'code': 'RCK-1', 'sample': 'ICE-S00', 'verdict': '无需换格'})
    assert empty.status_code == 409
    duplicate = client.post('/seam_maps/record-recheck', headers=reviewer,
                            json={'code': 'RCK-2', 'sample': 'ICE-R01', 'verdict': '无需换格'})
    assert duplicate.status_code == 409
    invalid = client.post('/seam_maps/record-recheck', headers=reviewer,
                          json={'code': 'RCK-3', 'sample': 'ICE-S11', 'verdict': '再看看'})
    assert invalid.status_code == 422
    forbidden = client.post('/seam_maps/record-recheck', headers=operator,
                            json={'code': 'RCK-4', 'sample': 'ICE-S11', 'verdict': '无需换格'})
    assert forbidden.status_code == 403
    ok = client.post('/seam_maps/record-recheck', headers=reviewer,
                     json={'code': 'RCK-5', 'sample': 'ICE-S11', 'verdict': '无需换格'})
    assert ok.status_code == 200


def test_trial_quarantines_batch_pieces(client):
    operator = login(client, 'operator')
    client.post('/seam_maps/draft-version', headers=operator,
                json={'code': 'KNN-K8', 'neighbors': 8})
    token = client.post('/seam_maps/run-trial', headers=operator,
                        json={'version': 'KNN-K8'}).json()['token']
    drain()
    job = client.get(f'/compute/{token}', headers=operator).json()
    batch_pieces = {item['sample']['piece'] for item in job['input']['batch']}
    assert batch_pieces == {'ART-R1', 'ART-R2'}
    assert all(item['sample']['empty_test'] is False for item in job['input']['batch'])
    pool = job['input']['pools']['CELL-A']
    assert len(pool) == 30
    assert not {row['piece'] for row in pool} & batch_pieces


def test_trial_metrics_and_enable_switches_new_requests(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    client.post('/seam_maps/draft-version', headers=operator,
                json={'code': 'KNN-K8', 'neighbors': 8})
    first = client.post('/seam_maps/run-trial', headers=operator,
                        json={'version': 'KNN-K8'}).json()['token']
    drain()
    client.post('/seam_maps/record-trial', headers=reviewer,
                json={'code': 'TRY-1', 'token': first})
    second = client.post('/seam_maps/run-trial', headers=operator,
                         json={'version': 'KNN-K8'}).json()['token']
    drain()
    client.post('/seam_maps/record-trial', headers=reviewer,
                json={'code': 'TRY-2', 'token': second})
    trials = {row['code']: row for row in client.get('/seam_maps/trials', headers=reviewer).json()}
    assert trials['TRY-1']['state'] == '已重算'
    assert trials['TRY-2']['state'] == '待启用'
    assert (trials['TRY-2']['miss_current'], trials['TRY-2']['miss_trial']) == (1, 0)
    assert (trials['TRY-2']['false_current'], trials['TRY-2']['false_trial']) == (1, 0)
    assert trials['TRY-2']['samples'] == 2
    assert trials['TRY-2']['base_version'] == 'KNN-K4'

    response = client.post('/seam_maps/enable-version', headers=reviewer,
                           json={'code': 'KNN-K8'})
    assert response.status_code == 200
    versions = {row['code']: row for row in
                client.get('/seam_maps/versions', headers=reviewer).json()}
    assert versions['KNN-K4']['state'] == '停用'
    assert versions['KNN-K8']['state'] == '现役'
    trials = {row['code']: row for row in
              client.get('/seam_maps/trials', headers=reviewer).json()}
    assert trials['TRY-2']['state'] == '已启用'

    token = client.post('/seam_maps/score-seam', headers=operator,
                        json={'sample': 'ICE-S06'}).json()['token']
    drain()
    job = client.get(f'/compute/{token}', headers=operator).json()
    assert job['input']['neighbors'] == 8
    assert job['input']['version'] == 'KNN-K8'


def test_enable_rejects_when_gate_fails(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    client.post('/seam_maps/draft-version', headers=operator,
                json={'code': 'KNN-K4B', 'neighbors': 4})
    token = client.post('/seam_maps/run-trial', headers=operator,
                        json={'version': 'KNN-K4B'}).json()['token']
    drain()
    client.post('/seam_maps/record-trial', headers=reviewer,
                json={'code': 'TRY-4B', 'token': token})
    response = client.post('/seam_maps/enable-version', headers=reviewer,
                           json={'code': 'KNN-K4B'})
    assert response.status_code == 409
    assert '漏报不增加且误报减少' in response.json()['detail']
    versions = {row['code']: row for row in
                client.get('/seam_maps/versions', headers=reviewer).json()}
    assert versions['KNN-K4']['state'] == '现役'
    assert versions['KNN-K4B']['state'] == '试算'


def test_stale_trial_cannot_overwrite_fresh_version(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    client.post('/seam_maps/draft-version', headers=operator,
                json={'code': 'KNN-K6', 'neighbors': 6})
    token = client.post('/seam_maps/run-trial', headers=operator,
                        json={'version': 'KNN-K6'}).json()['token']
    drain()
    client.post('/seam_maps/record-trial', headers=reviewer,
                json={'code': 'TRY-6', 'token': token})
    enable_knn_k8(client, operator, reviewer)
    trials = {row['code']: row for row in
              client.get('/seam_maps/trials', headers=reviewer).json()}
    assert trials['TRY-6']['state'] == '已失效'
    response = client.post('/seam_maps/enable-version', headers=reviewer,
                           json={'code': 'KNN-K6'})
    assert response.status_code == 409
    versions = {row['code']: row for row in
                client.get('/seam_maps/versions', headers=reviewer).json()}
    assert versions['KNN-K8']['state'] == '现役'
    assert versions['KNN-K6']['state'] == '试算'


def test_trial_based_on_retired_version_cannot_enable(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    client.post('/seam_maps/draft-version', headers=operator,
                json={'code': 'KNN-K6', 'neighbors': 6})
    token = client.post('/seam_maps/run-trial', headers=operator,
                        json={'version': 'KNN-K6'}).json()['token']
    drain()
    enable_knn_k8(client, operator, reviewer)
    recorded = client.post('/seam_maps/record-trial', headers=reviewer,
                           json={'code': 'TRY-6', 'token': token})
    assert recorded.status_code == 200
    assert recorded.json()['base_version'] == 'KNN-K4'
    response = client.post('/seam_maps/enable-version', headers=reviewer,
                           json={'code': 'KNN-K6'})
    assert response.status_code == 409
    assert '基于旧版' in response.json()['detail']
    versions = {row['code']: row for row in
                client.get('/seam_maps/versions', headers=reviewer).json()}
    assert versions['KNN-K8']['state'] == '现役'


def test_queued_jobs_keep_original_version(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    queued = client.post('/seam_maps/score-seam', headers=operator,
                         json={'sample': 'ICE-S05'}).json()['token']
    enable_knn_k8(client, operator, reviewer)
    fresh = client.post('/seam_maps/score-seam', headers=operator,
                        json={'sample': 'ICE-S06'}).json()['token']
    drain()
    old_job = client.get(f'/compute/{queued}', headers=operator).json()
    assert old_job['status'] == 'ready'
    assert old_job['input']['neighbors'] == 4
    assert old_job['input']['version'] == 'KNN-K4'
    new_job = client.get(f'/compute/{fresh}', headers=operator).json()
    assert new_job['input']['neighbors'] == 8
    assert new_job['input']['version'] == 'KNN-K8'
    client.post('/seam_maps/record-seam', headers=reviewer,
                json={'code': 'DENS-105', 'token': queued})
    client.post('/seam_maps/record-seam', headers=reviewer,
                json={'code': 'DENS-106', 'token': fresh})
    rows = {row['code']: row for row in client.get('/seam_maps', headers=reviewer).json()}
    assert rows['DENS-105']['version'] == 'KNN-K4'
    assert rows['DENS-106']['version'] == 'KNN-K8'


def test_tokens_stay_in_their_own_lane(client):
    operator = login(client, 'operator')
    reviewer = login(client, 'reviewer')
    score_token = client.post('/seam_maps/score-seam', headers=operator,
                              json={'sample': 'ICE-S05'}).json()['token']
    client.post('/seam_maps/draft-version', headers=operator,
                json={'code': 'KNN-K8', 'neighbors': 8})
    trial_token = client.post('/seam_maps/run-trial', headers=operator,
                              json={'version': 'KNN-K8'}).json()['token']
    drain()
    wrong_lane = client.post('/seam_maps/record-seam', headers=reviewer,
                             json={'code': 'DENS-107', 'token': trial_token})
    assert wrong_lane.status_code == 409
    other_lane = client.post('/seam_maps/record-trial', headers=reviewer,
                             json={'code': 'TRY-X', 'token': score_token})
    assert other_lane.status_code == 409


def test_viewer_is_read_only(client):
    viewer = login(client, 'viewer')
    assert client.get('/seam_maps', headers=viewer).status_code == 200
    assert client.get('/seam_maps/trials', headers=viewer).status_code == 200
    assert client.post('/seam_maps/score-seam', headers=viewer,
                       json={'sample': 'ICE-S05'}).status_code == 403
    assert client.post('/seam_maps/draft-version', headers=viewer,
                       json={'code': 'KNN-K8', 'neighbors': 8}).status_code == 403
    assert client.post('/seam_maps/enable-version', headers=viewer,
                       json={'code': 'KNN-K8'}).status_code == 403
