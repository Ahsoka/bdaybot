import pathlib
import sys
two_levels_up = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(two_levels_up))

import os
import time
import atexit
import pandas
import random
import discord
import datetime
import unittest
import argparse
import logging
import warnings
import sqlite3, psycopg2
from concurrent.futures import ThreadPoolExecutor
raise unittest.SkipTest()
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


from bday import bdaybot, andres
from create_database import (create_discord_users_table,
                             create_guilds_table,
                             create_wishes_table)

bday_df = andres.bday_df

BDAY_SERVER_ID = 713095060652163113
STARSHIP_SERVER_ID = 675806001231822863

BDAY_SERVER_ROLE_ID = 767587634796429374
STARSHIP_SERVER_ROLE_ID = 767552973948583966

BDAY_SERVER_ANNOUNCEMENTS_ID = 713096191507693681
STARSHIP_SERVER_ANNOUNCEMENTS_ID = 675806642696093759

TESTING_CHANNEL_ID = 769671372963971072

class TestBdaybot(unittest.TestCase):
    @classmethod
    def speak(cls, message, wait=True):
        task = cls.bot.loop.create_task(cls.send_message(message))
        if wait:
            while not task.done(): pass
            return task.result()
        return task

    @staticmethod
    def run_bot(bot, token):
        db_conn = sqlite3.connect("file::memory:?cache=shared",
                                  detect_types=sqlite3.PARSE_DECLTYPES,
                                  check_same_thread=False,
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
    async def send_message(cls, message):
        await cls.bot.wait_until_ready()
        # cls.bot._skip_check = lambda id1, id2: False
        return await cls.bot.get_guild(BDAY_SERVER_ID) \
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

    @classmethod
    def delete_message(cls, message):
        async def delete(message):
            await message.delete()
        task = cls.bot.loop.create_task(delete(message))
        while not task.done(): pass
        if task.exception() is not None:
            raise task.exception()

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
            cursor.execute('\n'.join(create_wishes_table.splitlines()[:-3])[:-1] + ')')
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

    def setUp(self):
        cursor = self.postgres_db.cursor()
        cursor.execute('SELECT stuid FROM student_data')
        self.all_valid_ids = list(map(lambda tup: tup[0], cursor.fetchall()))

    def test_wish(self):
        test_df = pandas.DataFrame({
            'FirstName': ['Captain', 'Commander', 'Ahsoka'],
            'LastName': ['Rex', 'Cody', 'Tano'],
            'Birthdate': (datetime.date.today(),) * 3,
            'Timedelta': (datetime.timedelta(),) * 3
        })
        wishee = 'Ahsoka'
        wishee_fullname = 'Ahsoka Tano'
        wishee_id = 2
        # print(test_df)

        # Test the situation when there is no birthday
        self.bot.bday_today = False
        self.bot.today_df = test_df
        self.bot.cogs['bdaybot_commands'].update_data()
        self.speak(f"{self.command_prefix}.wish", wait=True)
        time.sleep(1)
        self.assertIn(f"You cannot use the `{self.command_prefix}.wish`",
                      self.get_latest_message().embeds[0].description)

        # Test the situation when the user does not include their ID
        self.bot.bday_today = True
        self.bot.cogs['bdaybot_commands'].update_data()
        self.speak(f"{self.command_prefix}.wish", wait=True)
        time.sleep(1)
        self.assertIn("You are first-time wisher.",
                      self.get_latest_message().embeds[0].description)

        # Test the situation when the user submits an invalid ID
        invalid_id = 1_000_000
        message = self.speak(f"{self.command_prefix}.wish {invalid_id}", wait=True)
        time.sleep(1)
        # Make sure the message was deleted
        with self.assertRaises(discord.NotFound):
            self.delete_message(message)
        self.assertIn("Your ID is invalid",
                      self.get_latest_message().embeds[0].description)

        # Test the situation when the user submits a valid ID (that is in the birthday database)
        # but does not specify who they want to wish a happy
        # birthday, when it is multiple people's birthday
        valid_id = random.choice(bday_df.index)
        message = self.speak(f"{self.command_prefix}.wish {valid_id}")
        time.sleep(1)
        # Make sure the message was deleted
        with self.assertRaises(discord.NotFound):
            self.delete_message(message)
        # Make sure the user was added to the `discord_users` table
        cursor = self.conn.cursor()
        cursor.execute("SELECT student_id FROM discord_users WHERE discord_user_id=?",
                       (self.bot.user.id,))
        self.assertEqual(valid_id, cursor.fetchone()[0])
        # Make sure the proper message is sent back
        self.assertIn('You must specify who you want wish a happy birthday!',
                      self.get_latest_message().embeds[0].description)

        # Test the situation when the user submits a different valid ID (that is in the birthday database)
        # than the one they previously submitted
        # Make sure that another_valid_id != valid_id
        another_valid_id = valid_id
        while another_valid_id == valid_id:
            another_valid_id = random.choice(bday_df.index)

        message = self.speak(f"{self.command_prefix}.wish {another_valid_id}")
        time.sleep(1)
        # Make sure the message was deleted
        with self.assertRaises(discord.NotFound):
            self.delete_message(message)
        self.assertIn('The ID you submitted does not match the ID you submitted previously',
                      self.get_latest_message().embeds[0].description)

        # Test the situation when the user wishes someone
        # with a first name with a previously set ID
        self.speak(f'{self.command_prefix}.wish {wishee}', wait=True)
        time.sleep(1)
        self.assertIn(f"You wished ***__{wishee_fullname}__*** a happy birthday!",
                      self.get_latest_message().embeds[0].description)
        # Make sure that the correct SQL table is made
        cursor = self.conn.cursor()
        # Make sure the bot is added to the wishes table (with the correct year)
        cursor.execute("SELECT * FROM wishes WHERE discord_user_id=?", (self.bot.user.id,))
        self.assertTupleEqual((self.bot.user.id, datetime.date.today().year, wishee_id),
                              cursor.fetchone())

        # Test the situation when a second user wishes someone
        # with a full name with a previously set ID
        # DEBUG: We will mimic the second user by the deleting all the
        # data in the 'wishes' table.
        with self.conn:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM wishes')
        self.speak(f'{self.command_prefix}.wish {wishee_fullname}')
        time.sleep(1)
        cursor.execute('SELECT * FROM wishes WHERE discord_user_id=?', (self.bot.user.id,))
        self.assertTupleEqual((self.bot.user.id, datetime.date.today().year, wishee_id),
                              cursor.fetchone())
        self.assertIn(f"You wished ***__{wishee_fullname}__*** a happy birthday!",
                      self.get_latest_message().embeds[0].description)

        # Test the situation when the user tries to wish
        # the same person twice
        self.speak(f'{self.command_prefix}.wish {wishee}')
        time.sleep(1)
        self.assertIn("Try wishing someone else a happy birthday!",
                      self.get_latest_message().embeds[0].description)

        # TODO:
        # Test the situation when a user submits with
        # a previously set ID submits their ID again

    def test_setID(self):
        # Test that the bot does not accept invalid IDs
        invalid_id = 1_000_000
        message = self.speak(f'{self.command_prefix}.setID {invalid_id}', wait=True)
        time.sleep(1)
        # Make sure the message was deleted
        with self.assertRaises(discord.NotFound):
            self.delete_message(message)
        self.assertIn('not a valid ID', self.get_latest_message().content)

        # Test that the bot accepts valid IDs
        valid_id = random.choice(self.all_valid_ids); self.all_valid_ids.remove(valid_id)
        message = self.speak(f'{self.command_prefix}.setID {valid_id}', wait=True)
        time.sleep(1)
        # Make sure the message was deleted
        with self.assertRaises(discord.NotFound):
            self.delete_message(message)
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM discord_users WHERE student_id=?', (valid_id,))
        self.assertTupleEqual((self.bot.user.id, valid_id), cursor.fetchone())

        # Test that the bot rejects IDs already in use
        another_valid_id = random.choice(self.all_valid_ids)
        with self.conn:
            cursor.execute("INSERT INTO discord_users VALUES(?, ?)", (1, another_valid_id))
        message = self.speak(f'{self.command_prefix}.setID {another_valid_id}', wait=True)
        time.sleep(1)
        # Make sure the message was deleted
        with self.assertRaises(discord.NotFound):
            self.delete_message(message)
        self.assertIn('is already in use. Please use another ID.',
                      self.get_latest_message().content)

    def test_getID(self):
        # Test the situation when there is no ID set
        self.speak(f'{self.command_prefix}.getID', wait=True)
        time.sleep(1)
        self.assertIn("You do not currently have a registered ID.",
                   self.get_latest_message().content)

        # Test the situation with a preset ID
        with self.conn:
            valid_id = random.choice(self.all_valid_ids)
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO discord_users VALUES(?, ?)", (self.bot.user.id, valid_id))
        self.speak(f'{self.command_prefix}.getID', wait=True)
        time.sleep(1)
        self.assertIn(str(valid_id), self.get_latest_message().content)

    def test_getannouncements(self):
        self.speak(f'{self.command_prefix}.getannouncements', wait=True)
        time.sleep(1)
        cursor = self.conn.cursor()
        cursor.execute('SELECT announcements_id FROM guilds WHERE guild_id=?', [BDAY_SERVER_ID])
        self.assertIn(str(cursor.fetchone()[0]), self.get_latest_message().content)

    def test_setannouncments(self):
        #invalid ann id
        invalid = "<#001>"
        self.speak(f'{self.command_prefix}.setannouncements {invalid}', wait=True)
        time.sleep(1)
        self.assertIn('I know your tricks', self.get_latest_message().content)
        #voice channel
        invalid ="<#713095061180776501>"
        self.speak(f'{self.command_prefix}.setannouncements {invalid}', wait=True)
        time.sleep(1)
        self.assertIn('Holy cow', self.get_latest_message().content)
        #set announcements
        self.speak(f'{self.command_prefix}.setannouncements <#{TESTING_CHANNEL_ID}>', wait=True)
        time.sleep(1)
        cursor =  self.conn.cursor()
        cursor.execute('SELECT announcements_id FROM guilds WHERE guild_id=?',[BDAY_SERVER_ID])
        self.assertEqual(TESTING_CHANNEL_ID, cursor.fetchone()[0])
        #reset
        self.speak(f'{self.command_prefix}.setannouncements <#{BDAY_SERVER_ANNOUNCEMENTS_ID}>', wait=True)
        time.sleep(1)
        #set blank annoucnements
        self.speak(f'{self.command_prefix}.setannouncements', wait=True)
        time.sleep(1)
        cursor.execute('SELECT announcements_id FROM guilds WHERE guild_id=?',[BDAY_SERVER_ID])
        self.assertEqual(TESTING_CHANNEL_ID, cursor.fetchone()[0])

    def tearDown(self):
        with self.conn:
            cursor = self.conn.cursor()
            # This loop is try to execute
            # the given SQL query a maximum
            # of 10 times before raising an error
            # This loop is needed because the table
            # might be 'locked' because another
            # connection is using it.
            for iterr in range(10):
                try:
                    # Delete all the data from the discord_users table
                    # but not the table itself
                    cursor.execute("DELETE FROM discord_users")
                    break
                except sqlite3.OperationalError as error:
                    if 'database table is locked' != str(error) or iterr == 9:
                        raise

    @classmethod
    def tearDownClass(cls):
        cls.speak(f'{cls.command_prefix}.quit', wait=True)
        atexit._clear()
        cls.conn.close()
        cls.postgres_db.close()

if __name__ == '__main__':
    sys.argv[1:] = command_line.unittest_args
    try:
        unittest.main(exit=False)
    except RuntimeError:
        print('RuntimeError ¯\_(ツ)_/¯')
