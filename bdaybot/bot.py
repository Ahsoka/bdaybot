import discord
import logging

from .utils import EmojiURLs
from .tables import Base, Guild
from . import engine, config, sessionmaker
from .cogs import AutomatedTasksCog, CommandsCog, CosmicHouseKeepingCog, EasterEggsCog, HelpCommandCog

logger = logging.getLogger(__name__)

class Bdaybot(discord.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.housekeeping_cog = CosmicHouseKeepingCog(self)
        self.automation_cog = AutomatedTasksCog(self)
        self.commands_cog = CommandsCog()
        self.easter_egg_cog = EasterEggsCog()
        self.help_cog = HelpCommandCog(self)

        if kwargs.get('housekeeping', True):
            self.add_cog(self.housekeeping_cog)
        if kwargs.get('automation', True):
            self.add_cog(self.automation_cog)
        if kwargs.get('commands', True):
            self.add_cog(self.commands_cog)
        if kwargs.get('easter_egg', True):
            self.add_cog(self.easter_egg_cog)
        if kwargs.get('help', True):
            self.add_cog(self.help_cog)

        EmojiURLs.bot = self

    async def start(self, *args, **kwargs):
        async with engine.begin() as conn:
            await conn.run_sync(
                Base.metadata.create_all,
                tables=map(
                    lambda iterr: iterr[1],
                    filter(lambda tup: 'student_data' not in tup[0], Base.metadata.tables.items())
                )
            )

        if config.testing:
            async with sessionmaker.begin() as session:
                session.add(Guild(
                    guild_id=713095060652163113,
                    role_id=791804070398132225
                ))
                session.add(Guild(
                    guild_id=675806001231822863,
                    role_id=791186971078033428
                ))
                session.add(
                    Guild(
                        guild_id=810742455745773579,
                        role_id=960091320410578984
                    )
                )

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
