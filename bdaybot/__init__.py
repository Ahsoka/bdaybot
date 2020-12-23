import os
from .data import values
from dotenv import load_dotenv
from .argparser import parser
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

config = parser.parse_args()

engine = create_async_engine(config.database)

postgres_URL = URL('postgresql',
                   database=os.environ['database'],
                   username=os.environ['dbuser'],
                   password=os.environ['password'],
                   host=os.environ['host'])
if not config.testing:
    engine = create_async_engine(postgres_URL)
    config.DM_owner = True

postgres_engine = create_async_engine(postgres_URL) if engine.name != 'postgresql' else engine
