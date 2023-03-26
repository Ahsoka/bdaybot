import discord
import os


from . import config
from .bot import Bdaybot
from dotenv import load_dotenv
from .logs import setUpLogger

load_dotenv(override=True)

the_bot = Bdaybot(
    # debug_guilds=[713095060652163113],
    debug_guilds=[810742455745773579] if config.testing else None,
    intents=discord.Intents(guilds=True, members=True)
)
logger_names = [
    'bdaybot.data',
    'bdaybot.cogs.automated',
    'bdaybot.cogs.commands',
    'bdaybot.cogs.housekeeping',
    'bdaybot.cogs.meme',
    'bdaybot.cogs.help',
    'bdaybot.bot'
]
for logger_name in logger_names:
    setUpLogger(
        logger_name,
        files=not config.testing,
        fmt='[%(levelname)s] %(name)s: %(asctime)s - [%(funcName)s()] %(message)s'
    )

the_bot.run(os.environ['testing_token'] if config.testing else os.environ['Bday_Token'])
