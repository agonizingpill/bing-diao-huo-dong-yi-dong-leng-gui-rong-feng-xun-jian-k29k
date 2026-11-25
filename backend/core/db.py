from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine, inspect, text

from core.config import DATABASE_URL

metadata = MetaData()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

@contextmanager
def transaction():
    with engine.begin() as conn:
        yield conn

def ensure_columns():
    with engine.begin() as conn:
        columns = {column['name'] for column in inspect(conn).get_columns('seam_maps')}
        if 'version' not in columns:
            conn.execute(text(
                "ALTER TABLE seam_maps ADD COLUMN version VARCHAR(64) NOT NULL DEFAULT 'KNN-K4'"))
