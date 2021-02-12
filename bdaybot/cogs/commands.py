import pandas
import logging
import discord
import datetime
from sqlalchemy import or_
from discord.ext import commands
from sqlalchemy.exc import IntegrityError
from .. import values, engine, postgres_engine
from sqlalchemy.ext.asyncio import AsyncSession
from ..tables import DiscordUser, StudentData, Guild, Wish
from ..utils import get_bday_names, apostrophe, maybe_mention, ping_devs, EmojiURLs, format_iterable

logger = logging.getLogger(__name__)

class CommandsCog(commands.Cog):
    def __init__(self):
        self.session = AsyncSession(bind=engine, binds={StudentData: postgres_engine})

    @commands.command()
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def wish(self, ctx, *message):
        # TODO: Make it so you cannot wish yourself a happy birthday
        wish_embed = discord.Embed()
        try:
            input_id = int(message[-1])
            message = message[:-1]
            await ctx.message.delete()
            wish_embed.set_footer(text="[Original wish message deleted because it contained your ID]")
        except (IndexError, ValueError):
            input_id = None

        if values.bday_today:
            discord_user = await self.session.get(DiscordUser, ctx.author.id)
            if discord_user is None:
                if input_id is None:
                    wish_embed.description = "You are first-time wisher. You must include your 6-digit student ID at the end of the wish command to send a wish."
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    logger.debug(f"{ctx.author} unsucessfully used the wish command because they forgot to put their student ID.")
                    return
                student_user = await self.session.get(StudentData, input_id)
                if student_user is None:
                    wish_embed.description = "Your ID is invalid, please use a valid 6-digit ID"
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    logger.debug(f"{ctx.author} unsucessfully used the wish command because they included an invalid ID.")
                    return
                discord_user = DiscordUser(discord_user_id=ctx.author.id, student_data=student_user)
                self.session.add(discord_user)
                await self.session.commit()
            elif input_id is not None:
                await ctx.send((f"{ctx.author.mention} Once you've submitted your ID once, "
                                "you do not need to submitted it again to send wishes!"))

            if input_id is not None:
                if discord_user.student_data.stuid != input_id:
                    wish_embed.description = ("The ID you submitted does not match the ID you submitted previously.\n"
                                              "Please use the same ID you have used in the past or don't use an ID at all")
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    logger.debug(f"{ctx.author} unsucessfully used the with command because they used a different ID than their previously stored ID.")
                    return
                elif input_id not in values.bday_df.index:
                    await ctx.send((f"Yay! {ctx.author.mention} Your ID is valid, however, "
                                    "you are not in the bdaybot's birthday database.\n"
                                    "Add yourself to database here ⬇\n"
                                    "**http://drneato.com/Bday/Bday2.php**"))

            today_df = values.today_df
            if len(message) == 0 and len(today_df) > 1:
                wish_embed.description = (f"Today is {get_bday_names()} birthday\n"
                                           "You must specify who you want wish a happy birthday!")
                await ctx.send(ctx.author.mention, embed=wish_embed)
                logger.debug(f"{ctx.author} unsucessfully used the wish command because they failed to include who they wanted to wish.")
                return
            elif len(message) == 0:
                wishee_id = today_df.index.values[0]
            elif len(message) >= 1:
                # Can use first name, last name, or first and last name together to wish someone
                # Also firstname and lastname as one word ex: 'ahsokatano'
                comparing = map(lambda string: string.capitalize(), message)
                columns = ['FirstName', 'LastName']
                if len(message) == 1:
                    today_df['FullNameLower'] = today_df['FirstName'].str.lower() + today_df['LastName'].str.lower()
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
                        discrim = or_(StudentData.firstname == firstname.capitalize(),
                                      StudentData.lastname == firstname.capitalize(),
                                      StudentData.firstname == secondname.capitalize(),
                                      StudentData.lastname == secondname.capitalize())
                    fail_wishee = await self.session.run_sync(lambda session: session.query(StudentData) \
                                                                                     .filter(discrim).first())
                    if fail_wishee is None:
                        wish_embed.description = f"'{name}' is not a name in the birthday database!"
                        logger.debug(f"{ctx.author} unsucessfully used the wish command because tried to wish someone whose birthday is not today.")
                    else:
                        wish_embed.description = (f"Today is not **{fail_wishee.firstname} "
                                                  f"{fail_wishee.lastname}{apostrophe(fail_wishee.lastname)}** birthday.\n"
                                                  f"It is {get_bday_names()} birthday today. Wish them a happy birthday!")
                        logger.debug(f"{ctx.author} unsuccessfully used the wish command because they used a name that is not in the birthday database.")
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    return

                wishee_id = today_df[is_in.any(axis='columns')].index.values[0]

            wishee = await self.session.get(StudentData, int(wishee_id))
            assert wishee is not None, "Some how wishee is None"

            try:
                wish = Wish(year=datetime.datetime.today().year, wishee=wishee, discord_user=discord_user)
                self.session.add(wish)
                await self.session.commit()
                wish_embed.description = (f"Congrats {discord_user.student_data.firstname}! 🎈 ✨ 🎉\n"
                                          f"You wished ***__{wish.wishee.fullname}__*** a happy birthday!")
                logger.info(f"{ctx.author} successfully wished {wish.wishee.fullname} a happy birthday!")
            except IntegrityError:
                await self.session.rollback()
                wish_embed.description = (f"You cannot wish **{wish.wishee.fullname}** a happy birthday more than once!"
                                           "\nTry wishing someone else a happy birthday!")
                logger.debug(f"{ctx.author} tried to wish {wish.wishee.fullname} a happy birthday even though they already wished them before.")
            await ctx.send(ctx.author.mention, embed=wish_embed)
        else:
            wish_embed.description = (f"You cannot use the `{ctx.prefix}wish` command if it is no one's birthday today.\n"
                                      f"However, it will be **{get_bday_names()}** birthday on "
                                      f"**{format(values.today_df.iloc[0]['Birthdate'], '%A, %B %d')}**")
            await ctx.send(ctx.author.mention, embed=wish_embed)
            logger.debug(f"{ctx.author} tried to use the wish command on day when it was no one's birthday.")

    @wish.error
    async def handle_wish_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            logger.debug(f"{ctx.author} tried to use the wish command in a DM")
            await ctx.send(f"The `{ctx.prefix}wish` command is not currently available in DMs. Please try using it in a server with me.")
        elif isinstance(error, commands.BotMissingPermissions):
            logger.warning(f"The wish command was used in {ctx.guild} without the 'manage_messages' permission by {ctx.author}")
            await ctx.send((f"The `{ctx.prefix}wish` command is currently unavailable because I do not have the `manage messages` permission.\n"
                            f"If you would like to use the `{ctx.prefix}wish` command please, give me the `manage messages` permission."))
        else:
            logger.error(f'The following error occured with the wish command: {error!r}')
            await ctx.send(f"{ctx.author.mention} Congratulations, you managed to break the wish command.")
            await ping_devs(error, self.wish, ctx=ctx)

    @commands.command()
    async def getID(self, ctx, *message):
        discord_user = await self.session.get(DiscordUser, ctx.author.id)
        if discord_user is None:
            await ctx.send(f"{maybe_mention(ctx)}You do not currently have a registered ID. Use `{ctx.prefix}setID` to set your ID")
            logger.debug(f"{ctx.author} tried to access their ID even though they do not have one.")
        else:
            await ctx.author.send(f"Your ID is **{discord_user.student_id}**.  If this is a mistake use `{ctx.prefix}setID` to change it.")
            logger.info(f"{ctx.author} succesfully used the getID command.")

    def dm_allowed_bot_has_guild_permissions(**perms):
        invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
        if invalid:
            raise TypeError('Invalid permission(s): %s' % (', '.join(invalid)))

        def predicate(ctx):
            if ctx.guild:
                permissions = ctx.me.guild_permissions
                missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]
                if not missing:
                    return True
                raise commands.BotMissingPermissions(missing)
            return True

        return commands.check(predicate)

    @commands.command()
    @dm_allowed_bot_has_guild_permissions(manage_messages=True)
    async def setID(self, ctx, new_id: int):
        # TODO: Unlikely, however, if someone CHANGES their ID (from one that has been set in the past)
        # to another ID we should also transfer any of their wishes with the new id
        if ctx.guild:
            await ctx.message.delete()
        student = await self.session.get(StudentData, new_id)
        if student is None:
            await ctx.author.send(f"**{new_id}** is not a valid ID. Please use a valid 6-digit ID.")
            logger.debug(f"{ctx.author} tried to set their ID to an invalid ID.")
            return

        exists = False
        discord_user = await self.session.get(DiscordUser, ctx.author.id)
        if discord_user is None:
            discord_user = DiscordUser(discord_user_id=ctx.author.id, student_data=student)
            self.session.add(discord_user)
        else:
            old_id = discord_user.student_id
            discord_user.student_data = student
            exists = True

        try:
            await self.session.commit()
            if exists:
                logger.info(f"{ctx.author} successfully updated their ID from {old_id} to {new_id}.")
            else:
                logger.info(f"{ctx.author} successfully set their ID to {new_id}.")
            await ctx.author.send(f"Your ID has now been set to **{new_id}**!")
        except IntegrityError:
            await self.session.rollback()
            await ctx.author.send(f"**{new_id}** is already in use. Please use another ID.")
            logger.debug(f"{ctx.author} tried to set their ID to an ID already in use.")

    @setID.error
    async def handle_setID_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"{maybe_mention(ctx)}You must give me a new ID to replace your old one with")
            logger.debug(f"{ctx.author} unsucessfully used the setID command because they did not include an ID.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send((f"{maybe_mention(ctx)}"
                            f"**{' '.join(ctx.message.content.split()[1:])}** is not a valid number."))
            logger.debug(f"{ctx.author} tried to set their ID to a non-numeric value.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send((f"The `{ctx.prefix}setID` command is currently unavailable because I do not have the `manage messages` permission.\n"
                            f"If you would like to use the `{ctx.prefix}setID` command please, give me the `manage messages` permission."))
            logger.warning(f"The setID command was used in {ctx.guild} without the 'manage_messages' permission by {ctx.author}")
        else:
            logger.error(f'The following error occured with the setID command: {error!r}')
            await ctx.send(f"{maybe_mention(ctx)}Congrats, you managed to break the `{ctx.prefix}setID` command.")
            await ping_devs(error, self.setID, ctx=ctx)

    @commands.command(aliases=['up'])
    @commands.guild_only()
    async def upcoming(self, ctx, num=5):
        if num <= 0:
            await ctx.send(f"{ctx.author.mention} **{num}** is less than 1. Please use a number that is not less than 1.")
            logger.debug(f"{ctx.author} tried to use the upcoming command with a number less than 1.")
            return
        upcoming_embed = discord.Embed().set_author(name=f"Upcoming Birthday{'s' if num != 1 else ''}", icon_url=await EmojiURLs.calendar)
        upcoming_df = values.bday_df.drop(values.today_df.index) if values.bday_today else values.bday_df
        # INFO: The maximum without erroring out is 76
        max_num = 10
        if num > max_num:
            upcoming_embed.set_footer(text=f"The input value exceeded {max_num}. Automatically showing the top {max_num} results.")
            num = max_num

        upcoming_bdays = []
        for stuid, row in upcoming_df.iloc[:num].iterrows():
            discord_user = await self.session.run_sync(lambda session: session.query(DiscordUser) \
                                                       .filter(DiscordUser.student_id == stuid) \
                                                       .one_or_none())
            mention = '' if discord_user is None else discord_user.mention
            upcoming_bdays.append([f"{(row['FirstName'] + ' ' + row['LastName'])} {mention}",
                                   format(row['Birthdate'], '%b %d'),
                                   f"{row['Timedelta'].days} day{'s' if row['Timedelta'].days != 1 else ''}"])
        upcoming_embed.add_field(name='Name', value='\n'.join(map(lambda iterr: iterr[0], upcoming_bdays))) \
                      .add_field(name='Birthday', value='\n'.join(map(lambda iterr: iterr[1], upcoming_bdays))) \
                      .add_field(name='Upcoming In', value='\n'.join(map(lambda iterr: iterr[2], upcoming_bdays)))

        # Commented out line below is to mention the user when they use upcoming
        # await ctx.send(f"{ctx.author.mention}", embed=upcoming_embed)
        await ctx.send(embed=upcoming_embed)
        logger.info(f"{ctx.author} succesfully used the upcoming command!")

    @upcoming.error
    async def handle_upcoming_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"{ctx.author.mention} **{' '.join(ctx.message.content.split()[1:])}** is not a valid integer.")
            logger.debug(f"{ctx.author} tried to use an non-integer value.")
        elif isinstance(error, commands.NoPrivateMessage):
            logger.debug(f"{ctx.author} tried to use the upcoming command in a DM.")
            await ctx.send(f"The `{ctx.prefix}upcoming` command is currently unavailable in DMs. Please try using it in a server with me.")
        else:
            logger.error(f'The following error occured with the upcoming command: {error!r}')
            await ctx.send(f"{ctx.author.mention} Congrats! You managed to break the `{ctx.prefix}upcoming` command.")
            await ping_devs(error, self.upcoming, ctx)

    @commands.command(aliases=['setann'])
    @commands.has_guild_permissions(administrator=True)
    async def setannouncements(self, ctx, channel=commands.TextChannelConverter()):
        if not isinstance(channel, discord.TextChannel):
            channel = ctx.channel
        guild = await self.session.get(Guild, ctx.guild.id)
        guild.announcements_id = channel.id
        await self.session.commit()
        await ctx.send(f"The new announcements channel is now {channel.mention}!")

    @setannouncements.error
    async def handle_setannouncements_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send((f"{ctx.author.mention} You do not have the required permissions to set the announcements channel. "
                            "You must have a role that has the 'admin' permission."))
            logger.debug(f"{ctx.author} failed to set the announcements channel due to the lack of appropriate permissions.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f"The `{ctx.prefix}setannouncements` command is unavailable in DMs. Please try using it in a server with me.")
            logger.debug(f"{ctx.author} tried to used the setannouncements command in a DM.")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send(f"{ctx.author.mention} '{ctx.message.content.split()[1:]}' is not a valid TextChannel")
        else:
            logger.error(f'The following error occured with the setannouncements command: {error!r}')
            await ctx.send(f"{ctx.author.mention} Congrats! You managed to break the `{ctx.prefix}setannouncements` command!")
            await ping_devs(error, self.setannouncements, ctx=ctx)

    @commands.command(aliases=['getann'])
    @commands.guild_only()
    async def getannouncements(self, ctx, *args):
        guild = await self.session.get(Guild, ctx.guild.id)
        if guild.announcements_id is None:
            await ctx.send((f"{ctx.author.mention} There is not currently an announcements channel set. "
                            f"Use `{ctx.prefix}setann` to set an announcements channel."))
        else:
            await ctx.send((f"{ctx.author.mention} The current announcements channel is {guild.mention_ann}. "
                            f"If you like to change the announcements channel use `{ctx.prefix}setann`."))

    @getannouncements.error
    async def handle_getannouncements_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f"The `{ctx.prefix}getannouncements` command is unavailable in DMs. Please try using it in server with me.")
            logger.debug(f"{ctx.author} tried to use the getannouncements command in a DM.")
        else:
            logger.error(f'The following error occured with the getannouncements command: {error!r}')
            await ctx.send(f"{ctx.author.mention} Congrats! You managed to break the `{ctx.prefix}getannouncements` command!")
            await ping_devs(error, self.getannouncements, ctx=ctx)

    @commands.command()
    @commands.guild_only()
    async def wishes(self, ctx, person=commands.MemberConverter()):
        if not isinstance(person, discord.Member):
            person = ctx.author
        discord_user = await self.session.get(DiscordUser, person.id)
        embed = discord.Embed().set_author(name=f"{person}'s Wishes Received!", icon_url=person.avatar_url)
        if discord_user:
            wishes_received = discord_user.student_data.wishes_received
            embed.description = (f"{person.mention} currently has {len(wishes_received)} wish"
                                 f"{'es' if len(wishes_received) != 1 else ''}{'.' if len(wishes_received) < 5 else '!'}")
            if wishes_received:
                wishers_dict = {}
                more_than_one = False
                for wish in wishes_received:
                    if wish.discord_user not in wishers_dict:
                        wishers_dict[wish.discord_user] = [wish]
                    else:
                        more_than_one = True
                        wishers_dict[wish.discord_user].append(wish)
                embed.add_field(name='Wishers', value='\n'.join(map(lambda discord_user: discord_user.mention, wishers_dict)))
                embed.add_field(name=f"Year{'s' if more_than_one else ''}", \
                                value='\n'.join(map(lambda wishes: format_iterable(wishes, get_str=lambda ref, index: ref[index].year, apos=False, conjunction=None),
                                                    wishers_dict.values())))
                if discord_user in map(lambda wish: wish.discord_user, wishes_received):
                    embed.set_footer(text=f'Hey {person} wished himself/herself! 🤔')
        else:
            embed.description = f"{person.mention} currently has 0 wishes."
            embed.set_footer(text=f"{person} is not currently in the database 🙁")
        await ctx.send(embed=embed)

    @wishes.error
    async def handle_wishes_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f"The `{ctx.prefix}wishes` command is unavailable in DMs. Please try using it in server with me.")
            logger.debug(f"{ctx.author} tried to use the wishes command in a DM.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"'{ctx.message.content.split()[1:]}' is not a valid user.")
            logger.debug(f"{ctx.author} inputted an invalid user.")
        else:
            logger.error(f'The following error occured with the wishes command: {error!r}')
            await ctx.send(f"{ctx.author.mention} Congrats! You managed to break the `{ctx.prefix}wishes` command!")
            await ping_devs(error, self.wishes, ctx=ctx)
