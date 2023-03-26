from discord.commands import Option
from .commands import CommandsCog
from discord.ext import commands
from discord import SlashCommand
from ..utils import EmojiURLs

import discord
import logging
import random
import io

logger = logging.getLogger(__name__)


class HelpCommandCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        description="Use this command to see info about all my commands.",
        options=[
            Option(
                str,
                name='command',
                description="Name of command you want more info about.",
                choices=[
                    'get announcements',
                    'get id',
                    'set announcements',
                    'set id',
                    'upcoming',
                    'wish',
                    'get wishes'
                ],
                required=False
            )
        ]
    )
    async def help(self, ctx: discord.ApplicationContext, name: str = None):
        logger.info(f"{ctx.author} accessed the help command.")
        if name is None:
            await ctx.respond(embed=await self.general_help(ctx))

    async def general_help(self, ctx: discord.ApplicationContext) -> discord.Embed:
        runnable = await self.runnable_commands(ctx)
        description = io.StringIO(
            "All" if ctx.guild and len(runnable) == self.num_of_commands else "Available"
        )
        description.write(" Commands:\n```\n")
        for loc, command in enumerate(runnable):
            end = '\n' if loc != len(runnable) - 1 else '```'
            description.write(f"/{command.qualified_name}{end}")
        description.write(
            (
                f"\nFor help on how to use a command use `/help {{nameofcommand}}`"
                f"\ne.g. `/help {random.choice(runnable).qualified_name}`"
            )
        )

        help_embed = discord.Embed(
            description=description.getvalue()
            ).set_author(
                name="Bdaybot's commands:",
                icon_url=await EmojiURLs.partying_face
            )

        if not ctx.guild:
            help_embed.set_footer(text=(
                f"Not all available commands are shown above.\n"
                f"Use /help in server with me to see all the available commands!"
            ))
        elif len(runnable) < self.num_of_commands():
            help_embed.set_footer(text=(
                "Not all available commands are shown above because I do not have certain permissions.\n"
                "Please give me all the required permissions so you can use all my commands!"
            ))

        return help_embed

    async def runnable_commands(self, ctx: discord.ApplicationContext) -> list[SlashCommand]:
        runnable = []
        for command in self.bot.commands_cog.walk_commands():
            command: SlashCommand
            try:
                await command.can_run(ctx)
                runnable.append(command)
            except discord.DiscordException:
                pass
        return runnable

    def num_of_commands(self) -> int:
        return len([command for command in self.bot.commands_cog.walk_commands()])
