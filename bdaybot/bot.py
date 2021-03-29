import discord
import logging
from .help import HelpCommand
from discord.ext import commands
from Levenshtein import distance
from sqlalchemy.exc import IntegrityError
from .tables import Base, StudentData, Guild
from sqlalchemy.ext.asyncio import AsyncSession
from . import engine, postgres_engine, config, sessionmaker
from .utils import EmojiURLs, maybe_mention, format_iterable
from .cogs import AutomatedTasksCog, CommandsCog, CosmicHouseKeepingCog, EasterEggsCog

logger = logging.getLogger(__name__)

class bdaybot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parsed_command_prefix = self.command_prefix[0] if isinstance(self.command_prefix, (list, tuple)) \
                                     else self.command_prefix

        self.help_command = HelpCommand()

        self.housekeeping_cog = CosmicHouseKeepingCog(self)
        self.automation_cog = AutomatedTasksCog(self)
        self.commands_cog = CommandsCog()
        self.easter_egg_cog = EasterEggsCog()

        if kwargs.get('housekeeping', True):
            self.add_cog(self.housekeeping_cog)
        if kwargs.get('automation', True):
            self.add_cog(self.automation_cog)
        if kwargs.get('commands', True):
            self.add_cog(self.commands_cog)
        if kwargs.get('easter_egg', True):
            self.add_cog(self.easter_egg_cog)

        EmojiURLs.bot = self

    async def start(self, *args, **kwargs):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all,
                                tables=map(lambda iterr: iterr[1],
                                           filter(lambda tup: 'student_data' not in tup[0],
                                                  Base.metadata.tables.items())))

        if config.testing:
            async with sessionmaker.begin() as session:
                session.add(Guild(guild_id=713095060652163113,
                                    role_id=791804070398132225))
                session.add(Guild(guild_id=675806001231822863,
                                    role_id=791186971078033428))

        await super().start(*args, **kwargs)

    async def get_user(self, user_id):
        if user_id is None:
            return None
        user = super().get_user(user_id)
        if user:
            return user
        try:
            return await self.fetch_user(user_id)
        except (discord.NotFound, discord.HTTPException):
            return None

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            command_plus_prefix, *_ = ctx.message.content.split()
            await ctx.send(f"{maybe_mention(ctx)}`{command_plus_prefix}` is not a valid command.")
            logger.debug(f"{ctx.author} tried to invoke the invalid command '{command_plus_prefix}'.")
            if 'CommandsCog' in self.cogs:
                command_names = ['help']
                for command in self.cogs['CommandsCog'].get_commands():
                    command_names.append(command.name)
                    for alias in command.aliases:
                        command_names.append(alias)
                parsed = command_plus_prefix.removeprefix(ctx.prefix) if hasattr(str, 'removeprefix') \
                         else command_plus_prefix[len(ctx.prefix):]
                possibly_meant = [name for name in command_names \
                                  if len(name) >= 8 and distance(parsed.lower(), name.lower()) <= 2 \
                                     or len(name) < 8 and distance(parsed.lower(), name.lower()) < 2]
                if possibly_meant:
                    await ctx.send(f'Did you mean '
                                   + format_iterable(possibly_meant,
                                                     conjunction='or',
                                                     apos=False,
                                                     get_str=lambda iterr, index: f'`{ctx.prefix}{iterr[index]}`')
                                   + '?')
