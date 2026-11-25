from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, JSON, String, Table

from core.db import metadata


seam_versions = Table('seam_versions', metadata,
    Column('code', String(64), primary_key=True),
    Column('neighbors', Integer, nullable=False),
    Column('state', String(16), nullable=False),
    CheckConstraint('neighbors >= 1'),
)

seam_maps = Table('seam_maps', metadata,
    Column('code', String(64), primary_key=True),
    Column('sample', String(160), ForeignKey('thaw_samples.code'), nullable=False),
    Column('density', Float, nullable=False),
    Column('threshold', Float, nullable=False),
    Column('decision', String(160), nullable=False),
    Column('token', String(64), nullable=False, unique=True),
    Column('version', String(64), ForeignKey('seam_versions.code'), nullable=False,
           server_default='KNN-K4'),
)

seam_rechecks = Table('seam_rechecks', metadata,
    Column('code', String(64), primary_key=True),
    Column('sample', String(160), ForeignKey('thaw_samples.code'), nullable=False, unique=True),
    Column('verdict', String(160), nullable=False),
)

seam_trials = Table('seam_trials', metadata,
    Column('code', String(64), primary_key=True),
    Column('version', String(64), ForeignKey('seam_versions.code'), nullable=False),
    Column('base_version', String(64), nullable=False),
    Column('samples', Integer, nullable=False),
    Column('miss_current', Integer, nullable=False),
    Column('miss_trial', Integer, nullable=False),
    Column('false_current', Integer, nullable=False),
    Column('false_trial', Integer, nullable=False),
    Column('token', String(64), nullable=False, unique=True),
    Column('state', String(16), nullable=False),
)
