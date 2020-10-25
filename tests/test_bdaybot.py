import pathlib
import sys
two_levels_up = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(two_levels_up))

import unittest
import argparse
import logging
import asyncio
import sqlite3
import os
from concurrent.futures import ThreadPoolExecutor
from create_database import create_guilds_table, create_discord_users_table

parser = argparse.ArgumentParser(description="Use this to set unit-test settings")

parser.add_argument('-db', '--database', default=':memory:',
                    help="Use this to set the SQLite3 database location. (default: %(default)s)")

command_line = parser.parse_args()

class TestBdaybot(unittest.TestCase):
    BDAY_SERVER_ID = 713095060652163113
    STARSHIP_SERVER_ID = 675806001231822863

    BDAY_SERVER_ROLE_ID = 767587634796429374
    STARSHIP_SERVER_ROLE_ID = 767552973948583966

    TESTING_CHANNEL_ID = 769671372963971072

    @classmethod
    async def send_message(cls, message):
        await cls.bdaybot.get_guild(cls.BDAY_SERVER_ID) \
                         .get_channel(cls.TESTING_CHANNEL_ID) \
                         .send(message)

    speak = classmethod(lambda cls, message: asyncio.run(cls.send_message(message)))

    @classmethod
    def setUpClass(cls):
        cls.connection = sqlite3.connect(command_line.database, detect_types=sqlite3.PARSE_DECLTYPES)
        # Automatically convert 0 or 1 to bool
        sqlite3.register_converter("BOOLEAN", lambda val: bool(int(val)))
        # DEBUG: **MUST** include this line in order to use
        # FOREIGN KEYS, by default they are **DISABLED**
        cls.connection.execute("PRAGMA foreign_keys = 1")
        cursor = cls.connection.cursor()
        with cls.connection:
            cursor.execute('\n'.join(create_discord_users_table.splitlines()[:-2])[:-1] + ')')
            cursor.execute(create_guilds_table)
            for server_name in ['BDAY', 'STARSHIP']:
                cursor.execute("INSERT INTO guilds(guild_id, role_id) VALUES(?, ?)",
                              (getattr(cls, f'{server_name}_SERVER_ID'),
                               getattr(cls, f'{server_name}_SERVER_ROLE_ID')))

        class MuteLogger:
            def filter(self, record): return False
        # This is to mute the loggers
        logging.getLogger('data').addFilter(MuteLogger())
        logging.getLogger('bdaybot_commands').addFilter(MuteLogger())
        logging.getLogger('bday').addFilter(MuteLogger())

        with ThreadPoolExecutor() as executor:
            from bday import bdaybot
            cls.bdaybot = bdaybot(cls.connection, command_prefix=('b.',))
            executor.submit(bdaybot.run, cls.bdaybot, token=os.environ['testing_token'])

        cls.speak(f"{'-' * 5} **Beginning Unit Test** {'-' * 5}")

if __name__ == '__main__':
    unittest.main()
