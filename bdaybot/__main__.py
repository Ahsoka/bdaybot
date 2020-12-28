import os
from . import config
from dotenv import load_dotenv
from .bot import bdaybot
from .logs import setUpLogger

load_dotenv()

config.andres = True

the_bot = bdaybot(command_prefix='test.' if config.testing else ('b.', '+'),
                  case_insensitive=True)
logger_names = [
    'bdaybot.data',
    'bdaybot.cogs.automated',
    'bdaybot.cogs.commands',
    'bdaybot.cogs.housekeeping',
    'bdaybot.cogs.meme',
    'bdaybot.help',
    'bdaybot.bot'
]
for logger_name in logger_names:
    setUpLogger(logger_name,
                files=not config.testing,
                fmt='[%(levelname)s] %(name)s: %(asctime)s - [%(funcName)s()] %(message)s')


the_bot.run(os.environ['testing_token'] if config.testing else os.environ['Bday_Token'])
