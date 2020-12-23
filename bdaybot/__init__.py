import os
from .data import values
from .utils import EmojiURLs, format_iterable
from dotenv import load_dotenv
from .argparser import parser
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

config = parser.parse_args()

missing_URLs = EmojiURLs.missing_urls
if missing_URLs:
    class MissingURLs(Exception):
        pass
    raise MissingURLs(f'The following URLs are missing: {format_iterable(missing_URLs, apos=False)}')

engine = create_async_engine(config.database)

postgres_URL = URL('postgresql',
                   database=os.environ['database'],
                   username=os.environ['dbuser'],
                   password=os.environ['password'],
                   host=os.environ['host'])
if not config.testing:
    engine = create_async_engine(postgres_URL)
    config.DM_owner = True

config.andres, config.elliot, config.ryan = (not config.testing,) * 3

postgres_engine = create_async_engine(postgres_URL) if engine.name != 'postgresql' else engine
