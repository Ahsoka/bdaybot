import argparse

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from bdaybot.tables import Base
from bdaybot import postgres_URL

parser = argparse.ArgumentParser()

parser.add_argument('-b', '--backup', default='sqlite:///backup.db')

config = parser.parse_args()

sqlite_engine = create_engine(config.backup)
postgres_engine = create_engine(postgres_URL.set(drivername='postgresql+psycopg2'))

with sqlite_engine.begin() as conn:
    Base.metadata.create_all(conn)

with sqlite_engine.begin() as sqlite, postgres_engine.connect() as postgres:
    for table in Base.metadata.sorted_tables:
        params = [dict(row) for row in postgres.execute(select(table.c))]
        sqlite.execute(table.insert(), params)
