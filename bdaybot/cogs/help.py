from discord.commands import Option
from .commands import CommandsCog
from discord.ext import commands
from discord import SlashCommand
from ..utils import EmojiURLs
from ..data import values

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
                    'get wishes',
                    'help'
                ],
                required=False
            )
        ]
    )
    async def help(self, ctx: discord.ApplicationContext, name: str = None):
        if name is None:
            logger.info(f"{ctx.author} accessed the general help command.")
            await ctx.respond(embed=await self.general_help(ctx))
        elif name == 'help':
            logger.info(f"{ctx.author} discovered the Mental Illness easter egg!")
            await ctx.respond(
                "It sounds like your having a personal problem there, please seek a therapist for real help."
            )
        else:
            logger.info(f"{ctx.author} accessed the help command for the {name} command.")
            await ctx.respond(embed=await self.specific_help(ctx, name))

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

    async def specific_help(self, ctx: discord.ApplicationContext, name: str) -> discord.Embed:
        description = io.StringIO()
        command = self.name_to_command(name)
        if name == 'wish':
            try:
                await command.can_run(ctx)
            except commands.NoPrivateMessage:
                description.write('**UNAVAILABLE IN DM MESSAGES**\n\n')
            description.write(
                "The wish command allows you to wish someone a happy birthday!\n\n"
                "If there are multiple people's birthday today you must specify who you want to wish a happy birthday.\n"
                "\ne.g. If you want wish Jaiden a happy birthday, use `/wish Jaiden 694208`"
                "The `/wish` command is not available on days when it is no one's birthday"
            )
            description.write("." if values.bday_today else " (like today).")

            command_embed = discord.Embed(
                description=description.getvalue()
            ).set_author(
                name="Wish Command",
                icon_url=await EmojiURLs.wrapped_gift
            ).set_footer(
                text="Names are not case sensitive and full names are also acceptable."
            )
        elif name == 'get id':
            description.write(
                "The get id command allows you to determine the student ID that corresponds with your Discord account. "
                "An ID is useful because it allows you to use other commands.\n\n"
                "To use the get id command use `/get id`"
                "\n\nWhen you activate the get id command I will provide it to you in a message only you can see.\n\n"
                "If you do not currently have an ID registered I will let you know in this message.\n\n"
                "You can use the `/set id` command to register your ID."
            )
            command_embed = discord.Embed(
                description=description.getvalue()
            ).set_author(name="Get ID Command", icon_url=await EmojiURLs.numbers)
        elif name == 'set id':
            description.write(
                "The set id command allows you to set the CVHS student ID that will correspond with your Discord account. "
                "Setting an ID is useful because it allows you to use other commands.\n\n"
                "To use the setID command use `/set id " "{6-digit student ID}`\n"
                "\nThe student ID you input is validated against a database of legitimate student IDs, "
                "so make sure you use your real one.\n"
            )
            command_embed = discord.Embed(
                description=description.getvalue()
            ).set_author(name="Set ID Command", icon_url=await EmojiURLs.numbers)
        elif name == 'set announcements':
            try:
                await command.can_run(ctx)
            except commands.NoPrivateMessage:
                description.write("**UNAVAILABLE IN DM MESSAGES**\n\n")
            description.write(
                "The set announcements command allows you to set the text channel which I will announce the birthdays in.\n\n"
                "There are two ways to use the `/set announcements` command:\n"
                "▶ Type `/set announcements` in the text channel you want to be the announcements channel\n"
                "▶ Type `/set announcements " "{text channel}` to set a certain channel to the announcements channel. "
            )
            if ctx.guild:
                description.write(f"e.g. `/setannouncements` {ctx.channel.mention}")
            description.write("\n\nYou must have the administrator permission in order to use `/set announcements`")
            command_embed = discord.Embed(
                description=description.getvalue()
            ).set_author(
                name="Set Announcements Command",
                icon_url=await EmojiURLs.loudspeaker
            )
        elif name == 'get announcements':
            try:
                await command.can_run(ctx)
            except commands.NoPrivateMessage:
                description.write('**UNAVAILABLE IN DM MESSAGES**\n\n')
            description.write(
                "The /get announcements command shows you the current channel I use to announce whose birthday it is.\n\n"
                "By default the announcements channel is the text channel titled 'announcements'.\n\n"
                "If you would to change the announcements channel use `/set announcements`"
            )
            command_embed = discord.Embed(
                description=description.getvalue()
            ).set_author(
                name="Get Announcements Command",
                icon_url=await EmojiURLs.loudspeaker
            )
        elif name == 'upcoming':
            try:
                await command.can_run(ctx)
            except commands.NoPrivateMessage:
                description.write('**UNAVAILABLE IN DM MESSAGES**\n\n')
            description.write(
                "The upcoming command shows you the upcoming birthdays.\n\n"
                "By default it will show you the next 5 upcoming birthdays. "
                "However, you can choose the number of birthday you would like, by using this format "
                "`/upcoming " "{number}`" " e.g. To see the next 3 birthdays use `/upcoming 3`\n"
                "\nValid numbers are between 1 and 10."
            )
            command_embed = discord.Embed(
                description=description.getvalue()
            ).set_author(
                name="Upcoming Command",
                icon_url=await EmojiURLs.calendar
            )
        elif name == 'get wishes':
            description.write(
                "The get wishes command shows you all the wishes someone has received.\n\n"
                "By default the command shows you all the wishes you have received. \n\n"
                f"However, you can see the wishes of someone else like this: `/get wishes` {ctx.author.mention}"
            )
            command_embed = discord.Embed(
                description=description.getvalue()
            ).set_author(
                name="Get Wishes Command",
                icon_url=await EmojiURLs.party_popper
            )

        return command_embed

    def name_to_command(self, name: str) -> SlashCommand:
        for command in self.bot.commands_cog.walk_commands():
            command: SlashCommand
            if command.qualified_name == name:
                return command
        raise discord.NotFound(f"Slash command {name!r} not found.")

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
