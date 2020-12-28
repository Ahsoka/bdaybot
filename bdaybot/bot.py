import discord
import logging
from .help import HelpCommand
from discord.ext import commands
from sqlalchemy.exc import IntegrityError
from .utils import EmojiURLs, maybe_mention
from . import engine, postgres_engine, config
from .tables import Base, StudentData, Guild
from sqlalchemy.ext.asyncio import AsyncSession
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

        self.session = AsyncSession(bind=engine, binds={StudentData: postgres_engine})

        EmojiURLs.bot = self

    async def start(self, *args, **kwargs):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all,
                                tables=map(lambda iterr: iterr[1],
                                           filter(lambda tup: 'student_data' not in tup[0],
                                                  Base.metadata.tables.items())))
        if config.testing:
            self.session.add(Guild(guild_id=713095060652163113,
                                   role_id=791804070398132225))
            self.session.add(Guild(guild_id=675806001231822863,
                                   role_id=791186971078033428))
            try:
                await self.session.commit()
            except IntegrityError:
                await self.session.rollback()

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
            await ctx.send(f"{maybe_mention(ctx)}`{ctx.message.content}` is not a valid command.")
            logger.debug(f"{ctx.author} tried to invoke the invalid command '{ctx.message.content}'.")
            # TODO maybe: Add a did you mean 'X' command, if u want.
