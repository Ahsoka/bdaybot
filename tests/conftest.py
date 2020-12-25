import os
import re
import pytest
import asyncio
import discord
import inspect
import functools
from dotenv import load_dotenv
from bdaybot.bot import bdaybot
from bdaybot.tables import StudentData
from bdaybot import engine, postgres_engine
from sqlalchemy.ext.asyncio import AsyncSession

BDAY_SERVER_ID = 713095060652163113
STARSHIP_SERVER_ID = 675806001231822863
UNIT_TESTING_CHANNEL_ID = 769671372963971072
TESTING_CHANNEL_ID = 787491935517802558

NUMBER_OF_DASHES = 25
UNIT_TEST_NUMBER_OF_DASHES = 10

# DELAY_BETWEEN_MESSAGE = 1 # seconds
DELAY_BETWEEN_MESSAGE = 0.5 # seconds

load_dotenv()

@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.get_event_loop()
    return loop
    # if not loop.is_closed():
    #     loop.close()

def get_channel(bot):
    return bot.get_guild(BDAY_SERVER_ID) \
              .get_channel(UNIT_TESTING_CHANNEL_ID)

@pytest.fixture(scope='session')
async def bot():
    # NOTE: Monkey patch the author command
    # so that we have access to ctx in the author
    # instance
    @property
    def author(self):
        class MemberContext(discord.member.Member):
            __slots__ = 'ctx',

            @classmethod
            def convert_to_member_ctx(cls, member, ctx):
                converted_member = cls(data={'user': member._user._to_minimal_user_json(),
                                             'roles': member._roles,
                                             'id': member.id},
                                       guild=member.guild,
                                       state=member._state)
                converted_member.ctx = ctx
                return converted_member

            async def send(self, *args, **kwargs):
                # NOTE: Use the ctx to send a message in ctx
                # instead of sending to author
                await self.ctx.send(*args, **kwargs)

        member_with_context = MemberContext.convert_to_member_ctx(self.message.author, self)
        return member_with_context
    discord.ext.commands.Context.author = author

    # NOTE: Monkey patch the process_commands method to allow
    # bots to invoke commands
    async def process_commands(self, message):
        self._skip_check = lambda id1, id2: False
        ctx = await self.get_context(message)
        await self.invoke(ctx)
    bdaybot.process_commands = process_commands

    bot = bdaybot(command_prefix='test.',
                  case_insensitive=True,
                  housekeeping=False,
                  automation=False,
                  commands=False,
                  easter_egg=False)
    asyncio.create_task(bot.start(os.environ['testing_token']))
    try:
        await asyncio.wait_for(bot.wait_until_ready(), timeout=30)
    except asyncio.TimeoutError:
        pytest.skip('Bot failed to connect to Discord.')
    # Can't use channel since channel relies on bot :/
    channel = get_channel(bot)
    num = NUMBER_OF_DASHES
    await channel.send('** **')
    await channel.send('**' + '-'*num + ' Starting Unit Tests! ' + '-'*num + '**')
    yield bot
    await channel.send('**' + '-'*num + ' Ending Unit Tests ' + '-'*num + '**')
    await channel.send('** **')
    try:
        await asyncio.wait_for(bot.close(), timeout=5)
    except asyncio.TimeoutError:
        pass



@pytest.fixture(scope='session')
async def session():
    session = AsyncSession(bind=engine, binds={StudentData: postgres_engine})
    yield session
    # Close session and
    # dispose engine so
    # that we can run
    # pytest.main() many
    # times in row
    await session.close()
    await engine.dispose()

@pytest.fixture()
def mock_delete(mocker):
    # IMPORTANT NOTE: For some reason
    # when mocker.patch mock a method
    # (a function in a class) it does
    # not automatically convert the function
    # to a method thus causing the `self`
    # attribute to not be passed in as in argument
    # work to this is seen above
    async def call_delete_message(self):
        await discord.message.delete_message(self)
    discord.Message.delete = call_delete_message

    async def do_nothing(): pass
    # Add discord.message.delete_message as
    # an attribute or else patch won't work
    # properly
    discord.message.delete_message = do_nothing
    mocker.patch('discord.message.delete_message')

@pytest.fixture()
def channel(bot):
    return get_channel(bot)

@pytest.fixture()
async def students(session):
    return await session.run_sync(lambda sess: sess.query(StudentData).all())

@pytest.fixture()
def valid_ids(students):
    return list(map(lambda student: student.stuid, students))

@pytest.fixture(autouse=True)
async def which_test(channel):
    dashes = UNIT_TEST_NUMBER_OF_DASHES
    unit_test_name = re.search(r'(:{2})([a-zA-z]+)_([a-zA-Z]+)', os.environ.get('PYTEST_CURRENT_TEST')).group(3)
    await channel.send('** **')
    await channel.send('-'*dashes + f' Testing __{unit_test_name}__ ' + '-'*dashes)
    yield
    await channel.send('-'*(dashes*2 + len(f' Testing {unit_test_name} ')))
    await channel.send('** **')

@pytest.fixture()
def dashes():
    return UNIT_TEST_NUMBER_OF_DASHES

@pytest.fixture
def delay():
    return DELAY_BETWEEN_MESSAGE
