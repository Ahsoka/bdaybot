import click
import asyncio
import aiohttp
import discord
import inspect
import logging
import datetime
import functools # NOTE: Do not remove this, see EmojiURLs class
import traceback

from discord.ext import commands

class mention_int(int):
    @property
    def mention(self):
        return f'<@{self}>'

devs = {
    'Andres': mention_int(388899325885022211),
    'Elliot': mention_int(349319578419068940),
    'Ryan': mention_int(262676325846876161),
    'Peter': mention_int(250776640681017345),
    'Deelan': mention_int(274912077985087489)
}

def fake_ctx(bot, command, guild):
    # Used to call commands
    # from within the bot itself
    if isinstance(command, str):
        command = bot.get_command(command)
    if not isinstance(command, commands.Command):
        raise ValueError(f'command must be either a str or Command type, not {type(command)}')
    stringview = commands.view.StringView(f'{bot.parsed_command_prefix}{command.name}')
    message_dict = {
        'id': 0,
        'attachments': [],
        'embeds': [],
        'edited_timestamp': None,
        'type': None,
        'pinned': False,
        'mention_everyone': False,
        'tts': False
    }
    message_dict['content'] = f'{bot.parsed_command_prefix}{command.name}'
    message = discord.message.Message(state='lol', channel=guild.text_channels[0], data=message_dict)
    return commands.Context(
        message=message,
        bot=bot,
        prefix=bot.parsed_command_prefix,
        invoked_with=command.name,
        view=stringview,
        command=command
    )

def apostrophe(name):
    return "'" if name[-1] == "s" else "'s"

def format_iterable(
    iterable,
    apos=True,
    separator=',',
    conjunction='and',
    get_str=lambda ref, index: ref[index]
):
    if not hasattr(iterable, '__len__'):
        iterable = list(iterable)

    if len(iterable) == 1:
        result = get_str(iterable, 0)
        return f"{result}{apostrophe(result) if apos else ''}"
    elif len(iterable) == 2:
        result1 = get_str(iterable, 0)
        result2 = get_str(iterable, 1)
        if conjunction:
            return f"{result1} {conjunction} {result2}{apostrophe(result2) if apos else ''}"
        return f"{result1}{separator} {result2}{apostrophe(result2) if apos else ''}"

    returning = ''
    for counter in range(len(iterable)):
        result = get_str(iterable, counter)
        if conjunction:
            returning += f"{conjunction} {result}{apostrophe(result) if apos else ''}" if counter == len(iterable) - 1 \
                         else f'{result}{separator} '
        else:
            returning += str(result) if counter == len(iterable) - 1 else f'{result}{separator} '
    return returning

def get_bday_names(apos=True):
    # DEBUG: DO NOT move this import!
    # It is here to avoid circular import issues.
    from . import values
    def df_get_str(iterable, index):
        return iterable.iloc[index]['FirstName'] + ' ' + iterable.iloc[index]['LastName']
    return format_iterable(
        values.today_df,
        apos=apos,
        get_str=df_get_str
    )

def maybe_mention(ctx):
    return f'{ctx.author.mention} ' if ctx.guild else ''

def find_ann_channel(guild):
    bday_channels = list(filter(lambda channel: 'bday' in channel.name.lower(), guild.text_channels))
    ann_channels = list(filter(lambda channel: 'announcement' in channel.name.lower(), guild.text_channels))
    if bday_channels:
        return bday_channels[0]
    elif ann_channels:
        return ann_channels[0]
    return None

def permissions(channel, member, permissions, condition='all'):
    if channel is None:
        return True
    condition = condition.lower()
    perms = channel.permissions_for(member)
    if isinstance(permissions, (list, tuple)):
        if condition == 'all':
            return all([getattr(perms, perm) for perm in permissions])
        elif condition == 'any':
            return any([getattr(perms, perm) for perm in permissions])
        else:
            raise ValueError((
                f"'{condition}' is not an acceptable condition. "
                "The acceptable conditions are 'all' or 'any'."
            ))
    else:
        return getattr(perms, permissions)

async def ping_devs(
    error: Exception,
    command: discord.ApplicationCommand,
    ctx: discord.ApplicationContext = None,
    bot = None
):
    # DEBUG: DO NOT move this import!
    # It is here to avoid circular import issues.
    from . import config
    if ctx is None:
        assert bot is not None, 'bot cannot be None if ctx is None'
    else:
        bot = ctx.bot
        discord_location = ctx.guild if ctx.guild else 'a DM message'
    error_message = traceback.format_exc()
    if error_message == 'NoneType: None\n':
        error_message = repr(error)
    error_length = len(error_message)
    amount_of_messages = error_length//1990
    if not error_length%1990 == 0:
        amount_of_messages = amount_of_messages + 1
    error_messages_array = []
    for c in range(amount_of_messages):
        if c==amount_of_messages-1:
            error_messages_array.append(error_message[c*1990:len(error_message)])
        else:
            error_messages_array.append(error_message[c*1990:(c+1)*1990])
        #(:
    logger = logging.getLogger(inspect.getmodule(inspect.stack()[1].frame).__name__)
    for name, discord_id in devs.items():
        if getattr(config, name.lower()):
            dev = await bot.get_user(discord_id)
            if hasattr(ctx, 'author'):
                await dev.send(
                    f"{ctx.author.mention} caused the following error with "
                    f"`/{command.qualified_name}` in **{discord_location}**, "
                    f"on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}"
                )
            elif ctx is None:
                await dev.send(
                    f"The following error occured with the `{command}` task, on "
                    f"{format(datetime.datetime.today(), '%b %d at %I:%M %p')}:"
                )
            else:
                await dev.send(
                    f"The following error occured with `/{command.qualified_name}` "
                    f"in **{discord_location}**, on "
                    f"{format(datetime.datetime.today(), '%b %d at %I:%M %p')}:"
                )
            for error_content in error_messages_array:
                await dev.send(f"```\n{error_content}```")
            if hasattr(ctx, 'author'):
                await dev.send(f"The following is dictionary of the command interaction:\n**{ctx.interaction.data}**")
            logger.info(f'{dev} was sent a message notifying them of the situation.')


class classproperty:
    # NOTE: The `classproperty` class
    # is NOT my (@Ahsoka's) code. See reference below
    # for original source
    # Reference: https://stackoverflow.com/questions/128573/using-property-on-classmethods/13624858#13624858
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)

class EmojiURLs:
    urls = {
        'confetti_ball': "https://em-content.zobj.net/thumbs/320/microsoft/74/confetti-ball_1f38a.png",
        'partying_face': "https://em-content.zobj.net/thumbs/120/microsoft/153/face-with-party-horn-and-party-hat_1f973.png",
        'wrapped_gift': "https://em-content.zobj.net/thumbs/120/microsoft/74/wrapped-present_1f381.png",
        'numbers': "https://em-content.zobj.net/thumbs/120/twitter/322/abacus_1f9ee.png",
        'loudspeaker': "https://em-content.zobj.net/thumbs/120/microsoft/74/public-address-loudspeaker_1f4e2.png",
        'calendar' : "https://em-content.zobj.net/thumbs/120/microsoft/74/calendar_1f4c5.png",
        'party_popper': "https://em-content.zobj.net/thumbs/120/microsoft/74/party-popper_1f389.png"
    }

    @classmethod
    async def check_url(cls, key, session=None):
        url = cls.urls[key]
        try:
            if session:
                async with session.get(url) as resp:
                    pass
            else:
                async with aiohttp.request('GET', url) as resp:
                    pass
            if resp.content_type != 'image/png':
                raise aiohttp.ContentTypeError(
                    resp.request_info,
                    resp.history,
                    status=resp.status,
                    headers=resp.headers,
                    message=f'Content type for {key!r} was not a png it was {resp.content_type!r}'
                )
            return url
        except (aiohttp.ClientConnectorError, aiohttp.ContentTypeError) as error:
            logger = None
            for stack in inspect.stack():
                module = inspect.getmodule(stack.frame)
                if module and module.__name__ != __name__ and 'bdaybot.' in module.__name__:
                    logger = logging.getLogger(module.__name__)
                    break
            if logger:
                logger.warning(f"The {key} ({url}) url is not working!", exc_info=error)
            if hasattr(cls, 'bot'):
                # DEBUG: DO NOT move this import!
                # It is here to avoid circular import issues.
                from . import config
                for name, discord_id in devs.items():
                    if getattr(config, name.lower()):
                        dev = await cls.bot.get_user(discord_id)
                        await dev.send(f"The `{key}` url ({url}) is not working!")
                        if logger:
                            logger.info(f'{dev} was notified of the situation.')
            return discord.Embed.Empty

    for key in urls:
        async def __func(cls, url_key): return await cls.check_url(url_key)
        # NOTE: Function name gets changed from
        # __func to _EmojiURLs__func in exec function
        exec(f"{key}=classproperty(functools.partial(_EmojiURLs__func, url_key='{key}'))")
        del __func

    @classproperty
    def missing_urls(cls):
        async def get_urls():
            urls_dict = {}
            async with aiohttp.ClientSession() as session:
                results = await asyncio.gather(*map(lambda key: cls.check_url(key, session), cls.urls))
                urls_dict = {click.style(cls.urls[key], fg='yellow'): result for key, result in zip(cls.urls, results)}
            return urls_dict
        loop = asyncio.get_event_loop()
        urls = loop.run_until_complete(get_urls())
        return list(filter(lambda key: isinstance(urls[key], type(discord.Embed.Empty)), urls))
