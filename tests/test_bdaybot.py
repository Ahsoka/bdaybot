import pathlib
import sys
two_levels_up = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(two_levels_up))

import discord
from discord.ext import commands, tasks
import unittest
import argparse
import logging
import asyncio
import sqlite3
import os
import time
from concurrent.futures import ThreadPoolExecutor

parser = argparse.ArgumentParser(description="Use this to set unit-test settings")
parser.add_argument('-ul', '--unmute-logger', action='store_true', dest='mute_logger',
                    help="Use this to unmute the logger.")
parser.add_argument('unittest_args', nargs='*')

command_line = parser.parse_args()

# Automatically convert 0 or 1 to bool
sqlite3.register_converter("BOOLEAN", lambda val: bool(int(val)))

if not command_line.mute_logger:
    class MuteLogger:
        def filter(self, record): return False

    # This is to mute the loggers
    logging.getLogger('data').addFilter(MuteLogger())
    logging.getLogger('bdaybot_commands').addFilter(MuteLogger())
    logging.getLogger('bday').addFilter(MuteLogger())


from bday import bdaybot
from create_database import create_discord_users_table, create_guilds_table

BDAY_SERVER_ID = 713095060652163113
STARSHIP_SERVER_ID = 675806001231822863

BDAY_SERVER_ROLE_ID = 767587634796429374
STARSHIP_SERVER_ROLE_ID = 767552973948583966

BDAY_SERVER_ANNOUNCEMENTS_ID = 713096191507693681
STARSHIP_SERVER_ANNOUNCEMENTS_ID = 675806642696093759

TESTING_CHANNEL_ID = 769671372963971072

class TestBdaybot(unittest.TestCase):
    speak = classmethod(lambda cls, message: cls.bot.loop.create_task(cls.send_message(message)))

    @staticmethod
    def run_bot(bot, token):
        db_conn = sqlite3.connect("file::memory:?cache=shared",
                                  detect_types=sqlite3.PARSE_DECLTYPES,
                                  uri=True)
        # DEBUG: **MUST** include this line in order to use
        # FOREIGN KEYS, by default they are **DISABLED**
        db_conn.execute("PRAGMA foreign_keys = 1")
        async def process_commands(self, message):
            self._skip_check = lambda id1, id2: False
            ctx = await self.get_context(message)
            await self.invoke(ctx)
        # Monkey patch the process_commands method to allow
        # bots to invoke commands
        bdaybot.process_commands = process_commands
        bot.run(db_conn, token=token)
        db_conn.close()

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect("file::memory:?cache=shared",
                                   detect_types=sqlite3.PARSE_DECLTYPES,
                                   uri=True)
        cls.conn.execute("PRAGMA foreign_keys = 1")
        cursor = cls.conn.cursor()
        with cls.conn:
            cursor.execute('\n'.join(create_discord_users_table.splitlines()[:-2])[:-1] + ')')
            cursor.execute(create_guilds_table)
            for server_name in ['BDAY', 'STARSHIP']:
                cursor.execute("INSERT INTO guilds(guild_id, announcements_id, role_id) VALUES(?, ?, ?)",
                              (eval(f'{server_name}_SERVER_ID'),
                               eval(f'{server_name}_SERVER_ANNOUNCEMENTS_ID'),
                               eval(f'{server_name}_SERVER_ROLE_ID')))

        cls.command_prefix = 'test.'
        cls.bot = bdaybot(command_prefix=cls.command_prefix)
        cls.executor = ThreadPoolExecutor()
        bot_thread = cls.executor.submit(cls.run_bot, cls.bot, token=os.environ['testing_token'])
        cls.speak('-'*5 +  'Starting Unit Tests!' + '-'*5)

    @classmethod
    async def send_message(cls, message):
        await cls.bot.wait_until_ready()
        # cls.bot._skip_check = lambda id1, id2: False
        await cls.bot.get_guild(BDAY_SERVER_ID) \
                     .get_channel(TESTING_CHANNEL_ID) \
                     .send(message)

    def test_wish(self):
        pass

    def test_setID(self):
        pass

    def test_getID(self):
        pass

    @classmethod
    def tearDownClass(cls):
        cls.speak('test.quit')
        cls.executor.shutdown()
        cls.conn.close()

if __name__ == '__main__':
    sys.argv[1:] = command_line.unittest_args
    unittest.main()
