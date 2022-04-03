import logging
import discord
import datetime

from discord.ext import commands
from sqlalchemy import select, or_
from discord.commands import Option
from .. import values, sessionmaker
from sqlalchemy.exc import IntegrityError
from ..tables import DiscordUser, StudentData, Guild, Wish
from ..utils import get_bday_names, apostrophe, maybe_mention, ping_devs, EmojiURLs, format_iterable

logger = logging.getLogger(__name__)

class CommandsCog(commands.Cog):
    set_commands = discord.SlashCommandGroup(
        'set',
        "Commands used for telling the bdaybot various information about yourself."
    )
    get_commands = discord.SlashCommandGroup(
        'get',
        'Commands used for retrieving certain information from the bdaybot.'
    )

    @commands.slash_command(
        description="Command used for wishing people a happy birthday.",
        options=[
            Option(
                str,
                name='name',
                description="Name of person who you want to wish a happy birthday to.",
                required=False
            )
        ]
    )
    async def wish(self, ctx: discord.ApplicationContext, name: str = None):
        # TODO: Make it so you cannot wish yourself a happy birthday
        wish_embed = discord.Embed()
        if values.bday_today:
            async with sessionmaker.begin() as session:
                discord_user = await session.get(DiscordUser, ctx.author.id)
                if discord_user is None:
                    wish_embed.description = (
                        "You are first-time wisher. Use the `/set ID` command "
                        "to set your ID so you can use this command."
                    )
                    await ctx.respond(embed=wish_embed)
                    logger.debug(
                        f"{ctx.author} unsuccessfully used the wish command "
                        "because they do not have an associated student ID."
                    )
                    return
                input_id = discord_user.student_id

                today_df = values.today_df.copy()
                if name is None and len(today_df) > 1:
                    wish_embed.description = (
                        f"Today is {get_bday_names()} birthday\n"
                        "You must specify who you want wish a happy birthday!"
                    )
                    await ctx.respond(embed=wish_embed)
                    logger.debug(
                        f"{ctx.author} unsuccessfully used the wish command "
                        "because they failed to include who they wanted to wish."
                    )
                    return
                elif name is None:
                    wishee_id = today_df.index.values[0]
                else:
                    # Can use first name, last name, or first and last name together to wish someone
                    # Also firstname and lastname as one word ex: 'ahsokatano'
                    message = name.split()
                    comparing = map(lambda string: string.capitalize(), message)
                    columns = ['FirstName', 'LastName']
                    if len(message) == 1:
                        today_df['FullNameLower'] = (
                            today_df['FirstName'].str.lower()
                            + today_df['LastName'].str.lower()
                        )
                        comparing = [*comparing, message[0].lower()]
                        columns += ['FullNameLower']
                    is_in = today_df[columns].isin(comparing)
                    if not is_in.any(axis=None):
                        if len(message) == 1:
                            name = message[0]
                            discrim = or_(StudentData.firstname == name.capitalize(),
                                        StudentData.lastname == name.capitalize())
                        else:
                            firstname, secondname, *rest = message
                            if input_id is not None:
                                name = ' '.join(message[:-1])
                            else:
                                name = ' '.join(message)
                            discrim = or_(
                                StudentData.firstname == firstname.capitalize(),
                                StudentData.lastname == firstname.capitalize(),
                                StudentData.firstname == secondname.capitalize(),
                                StudentData.lastname == secondname.capitalize()
                            )
                        fail_wishee = (
                            await session.execute(select(StudentData).filter(discrim))
                        ).scalar()
                        if fail_wishee is None:
                            wish_embed.description = f"'{name}' is not a name in the birthday database!"
                            logger.debug(
                                f"{ctx.author} unsuccessfully used the wish command "
                                "because tried to wish someone whose birthday is not today."
                            )
                        else:
                            wish_embed.description = (
                                f"Today is not **{fail_wishee.firstname} "
                                f"{fail_wishee.lastname}{apostrophe(fail_wishee.lastname)}** "
                                f"birthday.\nIt is {get_bday_names()} birthday today. "
                                "Wish them a happy birthday!"
                            )
                            logger.debug(
                                f"{ctx.author} unsuccessfully used the wish command because "
                                "they used a name that is not in the birthday database."
                            )
                        await ctx.respond(embed=wish_embed)
                        return

                    wishee_id = today_df[is_in.any(axis='columns')].index.values[0]

                wishee = await session.get(StudentData, int(wishee_id))
                assert wishee is not None, "Some how wishee is None"

                wish = await session.get(
                    Wish,
                    (
                        discord_user.discord_user_id,
                        datetime.datetime.today().year,
                        wishee.stuid
                    )
                )
                if wish:
                    wish_embed.description = (
                        f"You cannot wish **{wish.wishee.fullname}** "
                        "a happy birthday more than once!"
                        "\nTry wishing someone else a happy birthday!"
                    )
                    logger.debug(
                        f"{ctx.author} tried to wish {wish.wishee.fullname} "
                        "a happy birthday even though they already wished them before."
                    )
                else:
                    wish = Wish(
                        year=datetime.datetime.today().year,
                        wishee=wishee,
                        discord_user=discord_user
                    )
                    session.add(wish)
                    wish_embed.description = (
                        f"Congrats {discord_user.student_data.firstname}! 🎈 ✨ 🎉\n"
                        f"You wished ***__{wish.wishee.fullname}__*** a happy birthday!"
                    )
                    logger.info(
                        f"{ctx.author} successfully wished "
                        f"{wish.wishee.fullname} a happy birthday!"
                    )
            await ctx.respond(embed=wish_embed)

            if input_id not in values.bday_df.index:
                await ctx.respond(
                    "Hey there I noticed that you are not in the "
                    "bdaybot's birthday database.\n"
                    "Add yourself to database here: ⬇\n"
                    "**http://drneato.com/Bday/Bday2.php**"
                )
        else:
            wish_embed.description = (
                f"You cannot use the `/wish` command if it is no one's birthday today.\n"
                f"However, it will be **{get_bday_names()}** birthday on "
                f"**{format(values.today_df.iloc[0]['Birthdate'], '%A, %B %d')}**"
            )
            await ctx.respond(embed=wish_embed)
            logger.debug(
                f"{ctx.author} tried to use the wish command "
                "on day when it was no one's birthday."
            )

    @get_commands.command(
        name='id',
        description="Use this command to get your currently set ID."
    )
    async def get_id(self, ctx: discord.ApplicationContext):
        async with sessionmaker() as session:
            discord_user = await session.get(DiscordUser, ctx.author.id)
        if discord_user is None:
            await ctx.respond(
                "You do not currently have a registered ID. "
                f"Use `/set id` to set your ID.",
                ephemeral=True
            )
            logger.debug(
                f"{ctx.author} tried to access their ID "
                "even though they do not have one."
            )
        else:
            await ctx.respond(
                f"Your ID is **{discord_user.student_id}**. "
                f"If this is a mistake use `/set id` to change it.",
                ephemeral=True
            )
            logger.info(f"{ctx.author} succesfully used the /get id command.")

    @set_commands.command(
        name='id',
        description="Use this command to tell me your school ID so you can use the other commands. ",
        options=[
            Option(
                int,
                name='id',
                description="Your 6-digit school ID.",
                required=True
            )
        ]
    )
    async def set_id(self, ctx: discord.ApplicationContext, new_id: int):
        # TODO: Unlikely, however, if someone CHANGES their ID (from one that has been set in the past)
        # to another ID we should also transfer any of their wishes with the new id
        try:
            async with sessionmaker.begin() as session:
                if new_id > 2147483647 or new_id < -2147483648:
                    student = None
                else:
                    student = await session.get(StudentData, new_id)
                if student is None:
                    await ctx.respond(
                        f"**{new_id}** is not a valid ID. Please use a valid 6-digit ID.",
                        ephemeral=True
                    )
                    logger.debug(f"{ctx.author} tried to set their ID to an invalid ID.")
                    return

                exists = False
                discord_user = await session.get(DiscordUser, ctx.author.id)
                if discord_user is None:
                    discord_user = DiscordUser(discord_user_id=ctx.author.id, student_data=student)
                    session.add(discord_user)
                else:
                    old_id = discord_user.student_id
                    discord_user.student_id = student.stuid
                    exists = True
            if exists:
                logger.info(f"{ctx.author} successfully updated their ID from {old_id} to {new_id}.")
            else:
                logger.info(f"{ctx.author} successfully set their ID to {new_id}.")
            await ctx.respond(
                f"Your ID has now been set to **{new_id}**!",
                ephemeral=True
            )
        except IntegrityError:
            await ctx.respond(
                f"**{new_id}** is already in use. Please use another ID.",
                ephemeral=True
            )
            logger.debug(f"{ctx.author} tried to set their ID to an ID already in use.")

    @commands.slash_command(
        description="Use this command to see the upcoming birthdays.",
        options=[
            Option(
                int,
                name='number',
                description='How many people will appear per page.',
                required=False,
                default=5,
                min_value=1,
                max_value=10
            )
        ]
    )
    async def upcoming(self, ctx: discord.ApplicationContext, num: int = 5):
        if num <= 0:
            await ctx.respond(
                f"**{num}** is less than 1. Please use a number that is not less than 1."
            )
            logger.debug(
                f"{ctx.author} tried to use the upcoming command with a number less than 1."
            )
            return
        upcoming_embed = discord.Embed().set_author(
            name=f"Upcoming Birthday{'s' if num != 1 else ''}",
            icon_url=await EmojiURLs.calendar
        )
        upcoming_df = values.bday_df.drop(values.today_df.index) if values.bday_today else values.bday_df
        # INFO: The maximum without erroring out is 76
        max_num = 10
        if num > max_num:
            upcoming_embed.set_footer(
                text=(
                    f"The input value exceeded {max_num}. "
                    f"Automatically showing the top {max_num} results."
                )
            )
            num = max_num

        upcoming_bdays = []
        async with sessionmaker() as session:
            for stuid, row in upcoming_df.iloc[:num].iterrows():
                discord_user = (
                    await session.execute(
                        select(DiscordUser).where(DiscordUser.student_id == stuid)
                    )
                ).scalar_one_or_none()
                mention = '' if discord_user is None else discord_user.mention
                upcoming_bdays.append([
                    f"{(row['FirstName'] + ' ' + row['LastName'])} {mention}",
                    format(row['Birthdate'], '%b %d'),
                    f"{row['Timedelta'].days} day{'s' if row['Timedelta'].days != 1 else ''}"
                ])
        upcoming_embed.add_field(
            name='Name',
            value='\n'.join(map(lambda iterr: iterr[0], upcoming_bdays))
        )
        upcoming_embed.add_field(
            name='Birthday',
            value='\n'.join(map(lambda iterr: iterr[1], upcoming_bdays))
        )
        upcoming_embed.add_field(
            name='Upcoming In',
            value='\n'.join(map(lambda iterr: iterr[2], upcoming_bdays))
        )

        await ctx.respond(embed=upcoming_embed)
        logger.info(f"{ctx.author} successfully used the upcoming command!")

    @set_commands.command(
        name='announcements',
        description="Use this command to set the announcements channel in this server.",
        options=[
            Option(
                discord.TextChannel,
                name='channel',
                description=(
                    "Select channel to be the announcements channel, "
                    "if there's no input the current channel is selected."
                ),
                required=False
            )
        ]
    )
    @commands.has_guild_permissions(administrator=True)
    async def set_announcements(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel = None
    ):
        if channel is None:
            channel = ctx.channel
        async with sessionmaker.begin() as session:
            guild = await session.get(Guild, ctx.guild.id)
            guild.announcements_id = channel.id
        await ctx.respond(f"The new announcements channel is now {channel.mention}!")

    @get_commands.command(
        name='announcements',
        description="Use this command to get the current announcements channel."
    )
    @commands.guild_only()
    async def get_announcements(self, ctx: discord.ApplicationContext):
        async with sessionmaker() as session:
            guild = await session.get(Guild, ctx.guild.id)
        if guild.announcements_id is None:
            await ctx.respond(
                f"There is not currently an announcements channel set. "
                f"Use `/set announcements` to set an announcements channel."
            )
        else:
            await ctx.respond(
                f"The current announcements channel is {guild.mention_ann}. "
                f"If you like to change the announcements channel use `/set announcements`."
            )

    @get_commands.command(
        description="Use this command to get the wishes of a certain user.",
        options=[
            Option(
                discord.Member,
                name='user',
                description="The user to get the wishes of.",
                required=True
            )
        ]
    )
    async def wishes(self, ctx: discord.ApplicationContext, person: discord.Member):
        session = sessionmaker()
        discord_user = await session.get(DiscordUser, person.id)
        embed = discord.Embed().set_author(
            name=f"{person}'s Wishes Received!",
            icon_url=person.display_avatar.url
        )
        if discord_user:
            wishes_received = discord_user.student_data.wishes_received
            embed.description = (
                f"{person.mention} currently has {len(wishes_received)} wish"
                f"{'es' if len(wishes_received) != 1 else ''}"
                f"{'.' if len(wishes_received) < 5 else '!'}"
            )
            if wishes_received:
                wishers_dict = {}
                more_than_one = False
                for wish in wishes_received:
                    await session.refresh(wish)
                    if wish.discord_user not in wishers_dict:
                        wishers_dict[wish.discord_user] = [wish]
                    else:
                        more_than_one = True
                        wishers_dict[wish.discord_user].append(wish)
                embed.add_field(
                    name='Wishers',
                    value='\n'.join(
                        map(
                            lambda discord_user: discord_user.mention,
                            wishers_dict
                        )
                    )
                )
                embed.add_field(
                    name=f"Year{'s' if more_than_one else ''}",
                    value='\n'.join(
                        map(
                            lambda wishes: format_iterable(
                                wishes,
                                get_str=lambda ref, index: ref[index].year,
                                apos=False,
                                conjunction=None
                            ),
                            wishers_dict.values()
                        )
                    )
                )
                if discord_user in map(lambda wish: wish.discord_user, wishes_received):
                    embed.set_footer(text=f'Hey {person} wished himself/herself! 🤔')
        else:
            embed.description = f"{person.mention} currently has 0 wishes."
            embed.set_footer(text=f"{person} is not currently in the database 🙁")
        await ctx.respond(embed=embed)
        await session.close()

    @commands.Cog.listener()
    async def on_application_command_error(
        self,
        ctx: discord.ApplicationContext,
        error: discord.ApplicationCommandInvokeError
    ):
        if isinstance(error.original, commands.MissingPermissions):
            logger.info(
                f"{ctx.author} tried to use the /{ctx.command.qualified_name} "
                "even though they don't have permission to do so."
            )
            await ctx.respond("You do not have permission to use this command.")
        elif isinstance(error.original, commands.NoPrivateMessage):
            logger.info(
                f"{ctx.author} tried to use the /{ctx.command.qualified_name} in a DM."
            )
            await ctx.respond("This command is not available in DM messages.")
        else:
            logger.error(
                f'The following error occured with the {ctx.command.qualified_name} command:',
                exc_info=error
            )
            await ctx.respond(
                f"{maybe_mention(ctx)}Congrats, you managed to break the "
                f"`/{ctx.command.qualified_name}` command.",
                ephemeral=True
            )

        await ping_devs(error, ctx.command, ctx=ctx)
