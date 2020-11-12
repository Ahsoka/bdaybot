import pathlib
import sys
two_levels_up = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(two_levels_up))

import os
import time
import atexit
import random
import unittest
import argparse
import logging
import asyncio
import warnings
import sqlite3, psycopg2
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
    @classmethod
    def speak(cls, message, wait=False):
        task = cls.bot.loop.create_task(cls.send_message(message))
        if wait:
            while not task.done(): pass
        return task

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
        cls.postgres_db = psycopg2.connect(dbname='botsdb',
                                           host=os.environ['host'],
                                           user=os.environ['dbuser'],
                                           password=os.environ['password'])
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

        cls.command_prefix = 'test'
        cls.bot = bdaybot(command_prefix=cls.command_prefix + '.')
        cls.executor = ThreadPoolExecutor()
        bot_thread = cls.executor.submit(cls.run_bot, cls.bot, token=os.environ['testing_token'])
        warnings.simplefilter('ignore', category=DeprecationWarning)
        cls.speak(f"**{'-'*5} Starting Unit Tests! {'-'*5}**")

    @classmethod
    async def send_message(cls, message):
        await cls.bot.wait_until_ready()
        # cls.bot._skip_check = lambda id1, id2: False
        await cls.bot.get_guild(BDAY_SERVER_ID) \
                     .get_channel(TESTING_CHANNEL_ID) \
                     .send(message)

    @classmethod
    def get_latest_message(cls):
        async def fetch_latest_message(cls):
            await cls.bot.wait_until_ready()
            return cls.bot.get_guild(BDAY_SERVER_ID) \
                          .get_channel(TESTING_CHANNEL_ID) \
                          .last_message

        fetch_message_task = cls.bot.loop.create_task(fetch_latest_message(cls))
        result = None
        while result is None:
            while not fetch_message_task.done(): pass
            result = fetch_message_task.result()
        return result

    def test_wish(self):
        pass

    def test_setID(self):
        # Test that the bot does not accept invalid IDs
        invalid_id = 1_000_000
        self.speak(f'{self.command_prefix}.setID {invalid_id}')
        time.sleep(4)
        self.assertIn('not a valid ID', self.get_latest_message().content)

        # Test that the bot accepts valid IDs
        cursor = self.postgres_db.cursor()
        cursor.execute('SELECT stuid FROM student_data')
        all_valid_ids = list(map(lambda tup: tup[0], cursor.fetchall()))
        valid_id = random.choice(all_valid_ids); all_valid_ids.remove(valid_id)
        self.speak(f'{self.command_prefix}.setID {valid_id}')
        time.sleep(4)
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM discord_users WHERE student_id=?', (valid_id,))
        self.assertTupleEqual((self.bot.user.id, valid_id), cursor.fetchone())

        # Test that the bot rejects IDs already in use
        another_valid_id = random.choice(all_valid_ids)
        with self.conn:
            cursor.execute("INSERT INTO discord_users VALUES(?, ?)", (1, another_valid_id))
        self.speak(f'{self.command_prefix}.setID {another_valid_id}')
        time.sleep(4)
        self.assertIn('is already in use. Please use another ID.',
                      self.get_latest_message().content)

    def test_getID(self):
        pass

    @classmethod
    def tearDownClass(cls):
        cls.speak(f'{cls.command_prefix}.quit')
        atexit._clear()
        cls.conn.close()
        cls.postgres_db.close()

if __name__ == '__main__':
    sys.argv[1:] = command_line.unittest_args
    try:
        unittest.main(exit=False)
    except RuntimeError:
        print('RuntimeError ¯\_(ツ)_/¯')
