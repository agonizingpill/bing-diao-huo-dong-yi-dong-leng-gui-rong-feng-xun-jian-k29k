from fastapi import APIRouter, Depends

from core.auth import actor, allow
from core.audit import record
from core.db import transaction
from core.records import scan
from domain import seam_maps_service as service
from domain.seam_maps_model import seam_maps, seam_versions, seam_rechecks, seam_trials
from domain.seam_maps_schemas import (ScoreSeam, RecordSeam, RecordRecheck, DraftVersion,
                                      RunTrial, RecordTrial, EnableVersion)

router = APIRouter()

@router.get('/seam_maps')
def list_seam_maps(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, seam_maps)


@router.get('/seam_maps/versions')
def list_seam_versions(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, seam_versions)


@router.get('/seam_maps/rechecks')
def list_seam_rechecks(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, seam_rechecks)


@router.get('/seam_maps/trials')
def list_seam_trials(user=Depends(actor)):
    with transaction() as conn:
        return scan(conn, seam_trials)


@router.post('/seam_maps/score-seam')
def score_seam(data: ScoreSeam, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.score_seam(conn, user, data)
        record(conn, user, 'seam_maps.score_seam')
        return output


@router.post('/seam_maps/record-seam')
def record_seam(data: RecordSeam, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.record_seam(conn, user, data)
        record(conn, user, 'seam_maps.record_seam')
        return output


@router.post('/seam_maps/record-recheck')
def record_recheck(data: RecordRecheck, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.record_recheck(conn, user, data)
        record(conn, user, 'seam_maps.record_recheck')
        return output


@router.post('/seam_maps/draft-version')
def draft_version(data: DraftVersion, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.draft_version(conn, user, data)
        record(conn, user, 'seam_maps.draft_version')
        return output


@router.post('/seam_maps/run-trial')
def run_trial(data: RunTrial, user=Depends(actor)):
    allow(user, ('operator', 'reviewer'))
    with transaction() as conn:
        output = service.run_trial(conn, user, data)
        record(conn, user, 'seam_maps.run_trial')
        return output


@router.post('/seam_maps/record-trial')
def record_trial(data: RecordTrial, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.record_trial(conn, user, data)
        record(conn, user, 'seam_maps.record_trial')
        return output


@router.post('/seam_maps/enable-version')
def enable_version(data: EnableVersion, user=Depends(actor)):
    allow(user, ('reviewer',))
    with transaction() as conn:
        output = service.enable_version(conn, user, data)
        record(conn, user, 'seam_maps.enable_version')
        return output
