import discord
import logging
from discord.ext import commands
from .cogs.commands import CommandsCog
from . import values
from .utils import maybe_mention, ping_devs, EmojiURLs

logger = logging.getLogger(__name__)

class HelpCommand(commands.HelpCommand):
    num_of_commands = len(CommandsCog().get_commands()) + 1
    async def send_bot_help(self, mapping):
        # TODO: Let ppl accessing the help command know that certain command are unavailable due to certain permissions be unavailable
        ctx = self.context
        filtered_commands = await self.filter_commands(
                            [command for key, commands in mapping.items() for command in commands])
        description = ("All" if ctx.guild and len(filtered_commands) == self.num_of_commands else "Available") + " Commands:\n```\n"

        for loc, command in enumerate(filtered_commands):
            end = '\n' if loc != len(filtered_commands) - 1 else '```'
            description += f"{ctx.prefix}{command.name}{end}"
        description += "\n" + f"For help on how to use a command use `{ctx.prefix}help " + "{nameofcommand}`\ne.g. " + f"`{ctx.prefix}help getID`"
        help_embed = discord.Embed(description=description).set_author(name="Bdaybot's commands:", icon_url=await EmojiURLs.partying_face)
        if not ctx.guild:
            help_embed.set_footer(text=f"Not all available commands are shown above.\nUse {ctx.prefix}help in server with me to see all the available commands!")
        elif len(filtered_commands) < self.num_of_commands:
            help_embed.set_footer(text=f"Not all available commands are shown above because I do not have certain permissions.\nPlease give me all the required permissions so you can use all my commands!")

        await ctx.send(embed=help_embed)
        logger.info(f"{ctx.author} accessed the help command.")

    async def send_command_help(self, command):
        ctx = self.context
        if command.name == 'wish':
            description = ''
            try:
                await command.can_run(ctx)
            except commands.BotMissingPermissions:
                description = "**CURRENTLY UNAVAILABLE BECAUSE I DO NOT HAVE THE MANAGE MESSAGES PERMISSION**\n\n"
            except commands.NoPrivateMessage:
                description = '**UNAVAILABLE IN DM MESSAGES**\n\n'
            description += ("The wish command allows you to wish someone a happy birthday!\n\n"
                            f"There are several ways to use the `{ctx.prefix}wish` command:\n"
                            f"▶ If you are using the `{ctx.prefix}wish` command for the first time you must include your\n"
                            "6-digit ID number as the last argument of the command.\n"
                            f"▶ If you are using the `{ctx.prefix}wish` command again you do not need to submit your ID number again.\n"
                            "▶ If there are multiple people's birthday today you must specify who you want to wish a happy birthday.\n"
                            f"\ne.g. If you want wish Jaiden a happy birthday, use `{ctx.prefix}wish Jaiden 694208`"
                            "\nThe ID you submit is checked against a list of valid IDs so use your real ID.\n"
                            "\n**Your message containing your ID is deleted to keep your ID confidental.**\n\n"
                            f"The `{ctx.prefix}wish` command is not available on days when it is no one's birthday")

            description += "." if values.bday_today else " (like today)."

            command_embed = discord.Embed(description=description).set_author(name="Wish Command", icon_url=await EmojiURLs.wrapped_gift) \
                            .set_footer(text="Names are not case sensitive and full names are also acceptable.")
        elif command.name == 'getID':
            description =  ("The getID command allows you to determine the ID that corresponds with your Discord account. "
                            "An ID is useful because it allows you to use other commands.\n\n"
                            f"To use the getID command use `{ctx.prefix}getID`"
                            "\n\nWhen you activate the getID command I will DM you your currently registered ID.\n\n"
                            "If you do not currently have an ID registered I will let you know in the DM message.\n\n"
                            f"You can use the `{ctx.prefix}setID` command to register your ID.")
            command_embed = discord.Embed(description=description).set_author(name="getID Command", icon_url=await EmojiURLs.numbers)
        elif command.name == 'setID':
            description = ''
            try:
                await command.can_run(ctx)
            except commands.BotMissingPermissions:
                description = "**CURRENTLY UNAVAILABLE BECAUSE I DO NOT HAVE THE MANAGE MESSAGES PERMISSION**\n\n"
            description += ("The setID command allows you to set the ID that corresponds with your Discord account. "
                            "And ID is useful because it allows you to use other commands.\n\n"
                            f"To use the setID command use `{ctx.prefix}setID " "{6-digit student ID}`\n"
                            "\nThe student ID you input is validated against a database of legitimate student IDs, "
                            "so make sure you use your real one.\n"
                            "\nIf you are using this command in a server, your message will be deleted to keep your ID confidental.")
            command_embed = discord.Embed(description=description).set_author(name="setID Command", icon_url=await EmojiURLs.numbers)
        elif command.name == 'setannouncements':
            description = ''
            try:
                await command.can_run(ctx)
            except commands.MissingPermissions:
                description = "**YOU DO NOT HAVE THE REQUIRED PERMISSIONS TO USE THIS COMMAND**\n\n"
            except commands.NoPrivateMessage:
                description = "**UNAVAILABLE IN DM MESSAGES**\n\n"
            description += ("The setannouncements command allows you to set the text channel which I will announce the birthdays in.\n\n"
                            f"There are two ways to use the `{ctx.prefix}setannouncements` command:\n"
                            f"▶ Type `{ctx.prefix}setannouncements` in the text channel you want to be the announcements channel\n"
                            f"▶ Type `{ctx.prefix}setannouncements " "{text channel}` to set a certain channel to the announcements channel. ") \
                            + (f"e.g. `{ctx.prefix}setannouncements` {ctx.channel.mention}" if ctx.guild else '') \
                            + ("\n\nYou must have the administrator permission in order to use " f"`{ctx.prefix}setannouncements`")
            command_embed = discord.Embed(description=description).set_author(name="Setannouncements Command", icon_url=await EmojiURLs.loudspeaker) \
                            .set_footer(text=f"{ctx.prefix}setann is an alias")
        elif command.name == 'getannouncements':
            description = ''
            try:
                await command.can_run(ctx)
            except commands.NoPrivateMessage:
                description = '**UNAVAILABLE IN DM MESSAGES**\n\n'
            description += ("The getannouncements command shows you the current channel I use to announce whose birthday it is.\n\n"
                            "By default the announcements channel is the text channel titled 'announcements'.\n\n"
                            f"If you would to change the announcements channel use `{ctx.prefix}setannouncements`")
            command_embed = discord.Embed(description=description).set_author(name="Getannouncements Command", icon_url=await EmojiURLs.loudspeaker) \
                            .set_footer(text=f"{ctx.prefix}getann is an alias")
        elif command.name == 'upcoming':
            description = ''
            try:
                await command.can_run(ctx)
            except commands.NoPrivateMessage:
                description = '**UNAVAILABLE IN DM MESSAGES**\n\n'
            description += ("The upcoming command shows you the upcoming birthdays.\n\n"
                            "By default it will show you the next 5 upcoming birthdays. "
                            "However, you can choose the number of birthday you would like, by using this format "
                            f"`{ctx.prefix}upcoming " "{number}`" f" e.g. To see the next 3 birthdays use `{ctx.prefix}upcoming 3`\n"
                            "\nValid numbers are between 1 and 10.  If you use a number larger than 10 only the first 10 upcoming birthdays will be shown.")
            command_embed = discord.Embed(description=description).set_author(name="Upcoming Command", icon_url=await EmojiURLs.calendar) \
                            .set_footer(text=f"{ctx.prefix}up is an alias")
        elif command.name == 'help':
            await ctx.send("It sounds like your having a personal problem there, please seek a therapist for real help.")
            logger.info(f"{ctx.author} discovered the Mental Illness easter egg!")
            return
        logger.info(f"{ctx.author} accessed the help command for the {command.name} command.")
        await ctx.send(embed=command_embed)

    async def command_not_found(self, invalid_command):
        ctx = self.context
        if invalid_command == '@invalid' and ctx.guild:
            return f"{ctx.author.mention} I know your tricks. Stop trying to abuse me!"
        return f"{maybe_mention(ctx)}{super().command_not_found(invalid_command)}"

    async def on_help_command_error(self, ctx, error):
        self.name = 'help'
        logger.error(f'The following error occured with the help command: {error!r}')
        await ctx.send(f"{maybe_mention(ctx)}Congrats you broke the help command!")
        await ping_devs(error, self, ctx=ctx)
