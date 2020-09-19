import discord
from discord.ext import commands
import logs
import warnings
import requests
import datetime
import itertools
import pandas
import psycopg2
import pickle
import data as andres
from argparser import args

dev_discord_ping = {'Andres':388899325885022211, 'Elliot':349319578419068940, 'Ryan':262676325846876161}

logger = logs.createLogger(__name__, fmt='[%(levelname)s] %(name)s.py: %(asctime)s - [%(funcName)s()] %(message)s')

connection = psycopg2.connect(dbname='botsdb')

cursor = connection.cursor()

# Makes SQL queries shorter and more obvious
def SQL(*args, autocommit=False, first_item=False, **kwargs):
    advance = kwargs.pop('next', False)
    if autocommit:
        with connection:
            cursor.execute(*args, **kwargs)
            return
    else:
        cursor.execute(*args, **kwargs)
    if first_item or advance:
        returning = cursor.fetchone()
        if returning is None:
            raise StopIteration
        return returning[0] if first_item else returning

    return cursor.fetchall()

class emoji_urls:
    # TODO: Check the links everytime the variables are accessed or
    # even better periodically as opposed to the current implementation where
    # they are only checked once on start up

    # TODO: If possible use the built-in urllib library instead of
    # requests. Since requests is used so infrequently its probably
    # best to just use the builtin version.
    confetti_ball = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/microsoft/209/confetti-ball_1f38a.png"
    partying_face = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png"
    wrapped_gift = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/wrapped-gift_1f381.png"
    numbers = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/twitter/248/input-numbers_1f522.png"
    loudspeaker = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/microsoft/209/public-address-loudspeaker_1f4e2.png"
    calendar = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/microsoft/209/calendar_1f4c5.png"

    links = [confetti_ball, partying_face, wrapped_gift, numbers, loudspeaker, calendar]

    broken_links = []
    for website in links:
        try:
            requeststat = requests.get(website).status_code
            if requeststat == 404 or requeststat == 403:
                broken_links.append(website)
        except:
            broken_links.append(website)
    try:
        if len(broken_links) != 0:
            raise ConnectionRefusedError(f'Failed to run bot because there are broken links in emoji_urls: {broken_links}')
    except ConnectionRefusedError as error:
        logger.critical(f"The following links are broken in emoji_urls: {broken_links}")
        raise error

class bdaybot_commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parsed_command_prefix = self.bot.parsed_command_prefix
        self.update_data()

    @staticmethod
    def apostrophe(name):
        return "'" if name[-1] == "s" else "'s"

    def get_bday_names(self, apos=True):
        if len(self.today_df) == 1:
            fullname0 = self.today_df.iloc[0]['FirstName'] + ' ' + self.today_df.iloc[0]['LastName']
            return f"{fullname0}{self.apostrophe(fullname0) if apos else ''}"

        if len(self.today_df) == 2:
            fullname0 = self.today_df.iloc[0]['FirstName'] + ' ' + self.today_df.iloc[0]['LastName']
            fullname1 = self.today_df.iloc[1]['FirstName'] + ' ' + self.today_df.iloc[1]['LastName']
            return f"{fullname0} and {fullname1}{self.apostrophe(fullname1) if apos else ''}"

        script = ''
        for counter, (_, series) in enumerate(self.today_df.iterrows()):
            fullname = series['FirstName'] + " " + series['LastName']
            # The line below is the specific part that is broken!
            script += f'and {fullname}{self.apostrophe(fullname) if apos else ""}' if counter == len(self.today_df) - 1 else fullname + ", "
        return script

    def update_data(self):
        self.bday_today, self.today_df = self.bot.bday_today, self.bot.today_df
        # TODO: Removed .to_list(), should still work but should test to make sure
        cycler = itertools.cycle(self.today_df['FirstName'] + " " + self.today_df['LastName'])
        SQL("UPDATE guilds SET today_names_cycle=%s", (pickle.dumps(cycler),), autocommit=True)

    async def ping_devs(self, error, command, ctx=None):
        if ctx is not None:
            parsed_ctx_guild = ctx.guild if ctx.guild else 'a DM message'
            if hasattr(ctx, 'author'):
                logger.error(f"[{command.name}] {ctx.author} caused the following error in {parsed_ctx_guild}:\n{repr(error)}")
            elif not isinstance(error, commands.CommandInvokeError):
                logger.error(f"The following error occured with the {command.name} command in {parsed_ctx_guild}\n{repr(error)}")
        for iteration, dev_name in enumerate(dev_discord_ping):
            dev = self.bot.get_user(dev_discord_ping[dev_name])
            ok_log = (iteration == len(dev_discord_ping) - 1)
            try:
                if hasattr(ctx, 'author'):
                    await dev.send(f"{ctx.author.mention} caused the following error with `{command.name}` in **{parsed_ctx_guild}**, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n**{repr(error)}**")
                    await dev.send(f"The message that caused the error is the following:\n**{ctx.message.content}**")
                    if ok_log:
                        logger.error(f"{ctx.author} said '{ctx.message.content}' which caused the following error with {command.name} in {parsed_ctx_guild}. Error message: {repr(error)}")
                elif ctx is None:
                    await dev.send(f"The following error occured with the `{command}` task, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n**{repr(error)}**")
                else:
                    await dev.send(f"The following error occured with `{command.name}` in **{parsed_ctx_guild}**, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n**{repr(error)}**")
                    if ok_log:
                        logger.error(f"The following error occured with {command.name} in {parsed_ctx_guild}. Error message: {repr(error)}")
            except RuntimeError as error:
                logger.critical(f"The following error occurred unexpectedly while trying to ping {dev_name}\n{repr(error)}")
                if str(error).lower() == 'session is closed':
                    break
        if ctx and ctx.guild and hasattr(ctx, 'author'):
            return (f" {self.bot.get_user(dev_discord_ping['Andres']).mention}, "
                    f"{self.bot.get_user(dev_discord_ping['Elliot']).mention},"
                    f" or {self.bot.get_user(dev_discord_ping['Ryan']).mention} fix this!")
        return ''

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

        if self.bday_today:
            try:
                discord_id, student_id = SQL("SELECT * FROM discord_users WHERE discord_user_id=%s", (ctx.author.id,), next=True)
                first_name = SQL("SELECT FirstName FROM student_data WHERE StuID=%s", (student_id,), first_item=True)
            except StopIteration:
                discord_id = None
                if input_id is None:
                    wish_embed.description = "You are first-time wisher. You must include your 6-digit student ID at the end of the wish command to send a wish."
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    logger.debug(f"{ctx.author} unsucessfully used the wish command because they forgot to put their student ID.")
                    return
                try:
                    student_id, first_name = SQL("SELECT StuID, FirstName FROM student_data WHERE StuID=%s", (input_id,), next=True)
                except StopIteration:
                    wish_embed.description = "Your ID is invalid, please use a valid 6-digit ID"
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    logger.debug(f"{ctx.author} unsucessfully used the wish command because they included an invalid ID.")
                    return

            if input_id is not None and student_id != input_id:
                wish_embed.description = ("The ID you submitted does not match the ID you submitted previously.\n"
                                            f"Please use the same ID you have used in the past or don't use an ID at all")
                await ctx.send(ctx.author.mention, embed=wish_embed)
                logger.debug(f"{ctx.author} unsucessfully used the with command because they used a different ID than their previously stored ID.")
                return

            if input_id is not None and discord_id is not None:
                await ctx.send(f"{ctx.author.mention} Once you've submitted your ID once, you do not need to submitted it again to send wishes!")
            elif input_id is not None:
                discord_id = ctx.author.id
                SQL("INSERT INTO discord_users VALUES(%s, %s)", (discord_id, input_id), autocommit=True)

            if input_id is not None and input_id not in andres.bday_df.index:
                await ctx.send((f"Yay! {ctx.author.mention} Your ID is valid, however, you are not in the bdaybot's birthday database.\n"
                                "Add yourself to database here ⬇\n"
                                "**http://drneato.com/Bday/Bday2.php**"))

            name_not_included = False

            if len(message) == 0 and len(self.today_df) > 1:
                wish_embed.description = (f"Today is {self.get_bday_names()} birthday\n"
                                            "You must specify who you want wish a happy birthday!")
                await ctx.send(ctx.author.mention, embed=wish_embed)
                logger.debug(f"{ctx.author} unsucessfully used the wish command because they failed to include who they wanted to wish.")
                return
            elif len(message) == 0:
                name = self.today_df.iloc[0]['FirstName'] + ' ' + self.today_df.iloc[0]['LastName']
            elif len(message) >= 1:
                name = " ".join(message)
                # Can use first name, last name, or first and last name together to wish someone
                fullname_df = pandas.concat([self.today_df[['FirstName', 'LastName']],
                                            (self.today_df['FirstName'] + " " + self.today_df['LastName'])], axis='columns')
                is_in = fullname_df.isin([name.title()])
                if not is_in.any(axis=None):
                    try:
                        beginning_sql_query = "SELECT FirstName, LastName FROM student_data "
                        split_name = name.title().split()
                        if len(message) == 1:
                            invalid_first, invalid_last = SQL(beginning_sql_query + "WHERE FirstName=%s OR LastName=%s", (split_name[0],)*2, next=True)
                        else:
                            invalid_first, invalid_last = SQL(beginning_sql_query + "WHERE (FirstName=%s OR LastName=%s) AND (FirstName=%s OR LastName=%s)",
                                                            ([split_name[0]]*2 + [split_name[1]]*2), next=True)
                        wish_embed.description = (f"Today is not **{invalid_first} {invalid_last}{self.apostrophe(invalid_last)}** birthday.\n"
                                                f"It is {self.get_bday_names()} birthday today. Wish them a happy birthday!")
                        await ctx.send(ctx.author.mention, embed=wish_embed)
                        logger.debug(f"{ctx.author} unsucessfully used the wish command because tried to wish someone whose birthday is not today.")
                    except StopIteration:
                        wish_embed.description = f"'{name}' is not a name in the birthday database!"
                        await ctx.send(ctx.author.mention, embed=wish_embed)
                        logger.debug(f"{ctx.author} unsucessfully used the wish command because they used a name that is not in the birthday database.")
                    return

            wishee_id, wishee_series = next(fullname_df[is_in.any(axis='columns')].iterrows())
            proper_name = wishee_series['FirstName'] + " " + wishee_series['LastName']

            table_name = f"id_{wishee_id}"
            try:
                # Generally this line below is **BAD** pratice due to the possibility
                # of an SQL injection attack, however, since the input we are receiving is
                # sanitized and can only result in an integer then it is IMPOSSIBLE to do
                # an SQL injection attack with this input method
                create_id_table = """CREATE TABLE {}(
                                    discord_user_id BIGINT,
                                    year INT,
                                    PRIMARY KEY(discord_user_id, year),
                                    FOREIGN KEY(discord_user_id) REFERENCES discord_users(discord_user_id)
                                    ON DELETE CASCADE
                                    )""".format(table_name)
                SQL(create_id_table, autocommit=True)
            except psycopg2.errors.DuplicateTable:
                connection.rollback()

            try:
                # Same warning applies to this line as above
                # This is generally bad practice, however, it is okay here
                # because of the sanitized input
                SQL("INSERT INTO {} VALUES(%s, %s)".format(table_name),
                    (ctx.author.id, datetime.date.today().year), autocommit=True)
            except psycopg2.errors.UniqueViolation:
                connection.rollback()
                wish_embed.description = f"You cannot wish **{proper_name}** a happy birthday more than once!\nTry wishing someone else a happy birthday!"
                await ctx.send(ctx.author.mention, embed=wish_embed)
                logger.debug(f"{ctx.author} tried to wish {proper_name} a happy birthday even though they already wished them before.")
                return

            wish_embed.description = (f"Congrats {first_name}! 🎈 ✨ 🎉\n"
                                        f"You wished ***__{proper_name}__*** a happy birthday!")
            await ctx.send(ctx.author.mention, embed=wish_embed)
            logger.info(f"{ctx.author} succesfully wished {proper_name} a happy birthday!")

        else:
            wish_embed.description = (f"You cannot use the `{ctx.prefix}wish` command if it is no one's birthday today.\n"
                                        "However, it will be "
                                        f"**{self.get_bday_names()}** birthday on {format(self.today_df.iloc[0]['Birthdate'], '%A, %B %d')}")
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
            await ctx.send(f"{ctx.author.mention} Congratulations, you managed to break the wish command.{await self.ping_devs(error, self.wish, ctx=ctx)}")

    @commands.command()
    async def getID(self, ctx, *message):
        try:
            id = SQL("SELECT student_id FROM discord_users WHERE discord_user_id=%s", (ctx.author.id,), first_item=True)
            await ctx.author.send(f"Your ID is **{id}**.  If this is a mistake use `{ctx.prefix}setID` to change it.")
            logger.info(f"{ctx.author} succesfully used the getID command.")
        except StopIteration:
             # Might want to edit this so that it does not tell ppl to use setID if it does not have the required permission
             await ctx.send(f"{self.maybe_mention(ctx)}You do not currently have a registered ID. Use `{ctx.prefix}setID` to set your ID")
             logger.debug(f"{ctx.author} tried to access their ID even though they do not have one.")

    @staticmethod
    def maybe_mention(ctx):
        return f'{ctx.author.mention} ' if ctx.guild else ''

    def dm_bot_has_guild_permissions(**perms):
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
    @dm_bot_has_guild_permissions(manage_messages=True)
    async def setID(self, ctx, id: int):
        # TODO: Unlikely, however, if someone CHANGES their ID (from one that has been set in the past)
        # to another ID we should also transfer any of their wishes with the new id
        if ctx.guild:
            await ctx.message.delete()
        try:
            SQL("SELECT * FROM student_data WHERE StuID=%s", (id,), first_item=True)
        except StopIteration:
            await ctx.author.send(f"**{id}** is not a valid ID. Please use a valid 6-digit ID.")
            logger.debug(f"{ctx.author} tried to set their ID to an invalid ID.")
            return
        try:
            current_id = SQL("SELECT student_id FROM discord_users WHERE discord_user_id=%s", (ctx.author.id,), first_item=True)
            if current_id == id:
                await ctx.author.send(f"**{id}** is already your current ID. Use `{ctx.prefix}getID` to view your current ID.")
                logger.debug(f"{ctx.author} tried to set their ID to the ID they already have.")
                return
        except StopIteration:
            current_id = None

        SQL("DELETE FROM discord_users WHERE discord_user_id=%s", (ctx.author.id,), autocommit=True)
        try:
            SQL("INSERT INTO discord_users VALUES(%s, %s)", (ctx.author.id, id), autocommit=True)
            await ctx.author.send(f"Your ID has now been set to **{id}**!")
            if current_id is not None:
                logger.info(f"{ctx.author} succesfully updated their ID from {current_id} to {id}.")
            else:
                logger.info(f"{ctx.author} succesfully set their ID to {id}.")
        except psycopg2.errors.UniqueViolation:
            connection.rollback()
            await ctx.author.send(f"**{id}** is already in use. Please use another ID.")
            logger.debug(f"{ctx.author} tried to set their ID to an ID already in use.")

    @setID.error
    async def handle_setID_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"{self.maybe_mention(ctx)}You must give me a new ID to replace your old one with")
            logger.debug(f"{ctx.author} unsucessfully used the setID command because they did not include an ID.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send((f"{self.maybe_mention(ctx)}"
                            f"**{' '.join(ctx.message.content.split()[1:])}** is not a valid number."))
            logger.debug(f"{ctx.author} tried to set their ID to a non-numeric value.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send((f"The `{ctx.prefix}setID` command is currently unavailable because I do not have the `manage messages` permission.\n"
                            f"If you would like to use the `{ctx.prefix}setID` command please, give me the `manage messages` permission."))
            logger.warning(f"The setID command was used in {ctx.guild} without the 'manage_messages' permission by {ctx.author}")
        else:
            await ctx.send(f"{self.maybe_mention(ctx)}Congrats, you managed to break the `{ctx.prefix}setID` command.{await self.ping_devs(error, self.setID, ctx=ctx)}")

    async def valid_author(self, ctx, command, send=True, devs=False):
        # TODO: Might want to change this so it only recongizes itself as a valid_author as opposed to any bot user
        # Extremely unlikely that a bot will end up using the hidden commands however if u have time fix this.
        if hasattr(ctx, 'author') and not ctx.author.bot:
            if devs:
                for dev_name in dev_discord_ping:
                    if ctx.author.id == dev_discord_ping[dev_name]:
                        return True
            logger.warning(f"{ctx.author} attempted to use the {command.name} command.")
            if send:
                available = "only available to bdaybot developers" if devs else "not available to non-bot accounts"
                await ctx.send(f"{self.maybe_mention(ctx)}This command is {available}. Also how did you even find about this command? Was it the source code?")
            return False
        return True

    @commands.command(hidden=True)
    @commands.bot_has_permissions(change_nickname=True)
    async def update_nickname(self, ctx):
        if not await self.valid_author(ctx, self.update_nickname):
            return
        cycler = pickle.loads(SQL("SELECT today_names_cycle FROM guilds WHERE guild_id=%s", (ctx.guild.id,), first_item=True))
        new_name = next(cycler)
        SQL("UPDATE guilds SET today_names_cycle=%s WHERE guild_id=%s", (pickle.dumps(cycler), ctx.guild.id), autocommit=True)
        await ctx.guild.me.edit(nick=new_name)

    @update_nickname.error
    async def handle_update_nickname_error(self, ctx, error):
        if not await self.valid_author(ctx, self.update_nickname):
            return
        nickname_notice = SQL("SELECT nickname_notice FROM guilds WHERE guild_id=%s",
                                (ctx.guild.id,), first_item=True)
        if isinstance(error, commands.BotMissingPermissions) and nickname_notice:
            await ctx.guild.owner.send(f"Currently I cannot change my nickname in {ctx.guild}. Please give me the `change nickname` permission so I can work properly.")
            SQL("UPDATE guilds SET nickname_notice=%s WHERE guilds_id=%s", (False, ctx.guild.id), autocommit=True)
            logger.warning(f"The bot unsucessfully changed its nickname in '{ctx.guild}'. A DM message requesting to change it's permissions was sent to {ctx.guild.owner}.")
        else:
            logger.warning(f"Ignoring {error!r}")

    @commands.command(hidden=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def update_role(self, ctx):
        if not await self.valid_author(ctx, self.update_role):
            return
        # Old colors in the comment below
        # color = discord.Color.red() if self.bday_today else discord.Color.green()
        role_name, color = ("🎉 Happy Birthday", discord.Color.from_rgb(255, 0, 0)) if self.bday_today \
                            else (f"Upcoming Bday-{format(self.today_df.iloc[0]['Birthdate'], '%a %b %d')}",
                                    discord.Color.from_rgb(162, 217, 145))

        role_id = SQL("SELECT role_id FROM guilds WHERE guild_id=%s", (ctx.guild.id,), first_item=True)
        if role_id is None:
            bday_role = await ctx.guild.create_role(reason='Creating the Happy Birthday/Upcoming Birthday role',
                                                    name=role_name, hoist=True, color=color)
            SQL("UPDATE guilds SET role_id=%s WHERE guild_id=%s", (bday_role.id, ctx.guild.id), autocommit=True)
        else:
            bday_role = ctx.guild.get_role(role_id)
            if bday_role is None:
                SQL("UPDATE guilds SET role_id=NULL WHERE guild_id=%s", (ctx.guild.id,), autocommit=True)
                await self.bot.invoke(self.bot.fake_ctx('update_role', ctx.guild))
                return

            await bday_role.edit(name=role_name, color=color)

        await ctx.guild.me.add_roles(bday_role)

        counter = itertools.count(bday_role.position)
        no_error = True
        while no_error:
            position = next(counter)
            try:
                await bday_role.edit(position=position)
            except discord.errors.HTTPException:
                no_error = False
        logger.info(f"The bot's role was changed to '{bday_role.name}' in '{ctx.guild}'.")

    @update_role.error
    async def handle_update_role_error(self, ctx, error):
        if not await self.valid_author(ctx, self.update_role):
            return
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.guild.owner.send(f"I cannot currently edit my role in **{ctx.guild}**. Please give me the `manage roles` permission so I can work properly")
            logger.warning(f"The bot unsucessfully edited its role in '{ctx.guild}' due the the fact the bot was the required missing permissions. "
                            f"A DM message requesting to change its permissions was sent to {ctx.guild.owner}.")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
            # TODO: Have the bot fix this problem on its own if possible
            current_role_id = SQL("SELECT role_id FROM guilds WHERE guild_id=%s", (ctx.guild.id,), first_item=True)
            current_role = ctx.guild.get_role(current_role_id)
            most_likely = [role for role in ctx.guild.me.roles
                            if role.id != current_role_id and
                            "Upcoming Bday-" not in role.name and
                            "🎉 Happy Birthday" != role.name]
            await ctx.guild.owner.send(f"I cannot currently edit my role in **{ctx.guild}**. "
                                        f"Please move the **{most_likely[-1]}** role to above the **{current_role}** role.")
            logger.warning(f"The bot unsucessfully edited its role in '{ctx.guild}' due to the fact the bot's highest role was not above the '{current_role}' role. "
                            f"A DM message requesting to change its permissions was sent to {ctx.guild.owner}.")
        else:
            await self.ping_devs(error, self.update_role, ctx=ctx)

    @commands.command(hidden=True)
    async def quit(self, ctx, *messages):
        if not await self.valid_author(ctx, self.quit, devs=True):
            return
        await ctx.author.send("Shutting down the bdaybot!")
        logger.info(f"{ctx.author} accessed the quit commmand!")
        await self.bot.loop.stop()

    @commands.command(aliases=['up'])
    @commands.guild_only()
    async def upcoming(self, ctx, num=5):
        if num <= 0:
            await ctx.send(f"{ctx.author.mention} **{num}** is less than 1. Please use a number that is not less than 1.")
            logger.debug(f"{ctx.author} tried to use the upcoming command with a number less than 1.")
            return
        upcoming_embed = discord.Embed().set_author(name=f"Upcoming Birthday{'s' if num != 1 else ''}", icon_url=emoji_urls.calendar)
        upcoming_df = andres.bday_df.drop(self.today_df.index) if self.bday_today else andres.bday_df
        if num > 8:
            upcoming_embed.set_footer(text=f"The input value exceeded 8. Automatically showing the top 8 results.")
            num = 8

        for id, row in upcoming_df.iloc[:num].iterrows():
            try:
                id = SQL("SELECT discord_user_id FROM discord_users WHERE student_id=%s", (id,), first_item=True)
                mention = self.bot.get_user(id).mention
            except StopIteration:
                mention = ''
            upcoming_embed.add_field(name='Name', value=f"{(row['FirstName'] + ' ' + row['LastName'])}{mention}") \
            .add_field(name='Birthday', value=format(row['Birthdate'], '%b %d')) \
            .add_field(name='Upcoming In', value=f"{row['Timedelta'].days} day{'s' if row['Timedelta'].days != 1 else ''}")

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
            await ctx.send(f"{ctx.author.mention} Congrats! You managed to break the `{ctx.prefix}upcoming` command. {await self.ping_devs(error, self.upcoming, ctx)}")

    @commands.command(aliases=['setann'])
    @commands.has_guild_permissions(administrator=True)
    async def setannouncements(self, ctx, channel=None):
        try:
            channel_id = ctx.channel.id if channel is None else int(channel.strip('<#>'))
            channel = ctx.guild.get_channel(channel_id)
            if channel is None:
                await ctx.send(f"{ctx.author.mention} I know your tricks, why are you trying to set a non-existent channel as the announcements channel?")
                logger.info(f"{ctx.author} discovered one of the easter eggs in the setannouncements command!")
            elif not isinstance(channel, discord.TextChannel):
                await ctx.send((f"{ctx.author.mention} Holy cow, you must know how to read Python 🐍 code really, really well. "
                                "And you know how Discord works in-depth too! "
                                "You are really trying to screw with me, huh? Well done! 👍🏽"))
                logger.info(f"{ctx.author} discovered the voice channel easter egg!")
            elif not self.bot.permissions(channel, ctx.guild.get_member(self.bot.user.id), 'send_messages'):
                await ctx.send(f"{ctx.author.mention} I cannot use {channel.mention} as the new announcements channel because I do not have the `send messages` permission in that channel.")
                logger.info(f"In {ctx.guild}, {ctx.author} tried to set the announcements channel to a channel the bot could not speak in.")
            else:
                SQL("UPDATE guilds SET announcements_id=%s WHERE guild_id=%s", (channel_id, ctx.guild.id), autocommit=True)
                await ctx.send(f"The new announcements channel is now {channel.mention}!")
                logger.info(f"{ctx.author} successfully set the announcements channel to {channel}!")
        except ValueError:
            await ctx.send(f"{ctx.author.mention} '{channel}' is not a valid channel name.")

    @setannouncements.error
    async def handle_setannouncements_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send((f"{ctx.author.mention} You do not have the required permissions to set the announcements channel. "
                            "You must have a role that has the 'admin' permission."))
            logger.debug(f"{ctx.author} failed to set the announcements channel due to the lack of appropriate permissions.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f"The `{ctx.prefix}setannouncements` command is unavailable in DMs. Please try using it in a server with me.")
            logger.debug(f"{ctx.author} tried to used the setannouncements command in a DM.")
        else:
            await ctx.send(f"{ctx.author.mention} Congrats! You managed to break the `{ctx.prefix}setannouncements` command! {await self.ping_devs(error, self.setannouncements, ctx=ctx)}")

    @commands.command(aliases=['getann'])
    @commands.guild_only()
    async def getannouncements(self, ctx):
        try:
            id = SQL("SELECT announcements_id FROM guilds WHERE guild_id=%s", (ctx.guild.id,), first_item=True)
            await ctx.send((f"{ctx.author.mention} The current announcements channel is {ctx.guild.get_channel(id).mention}. "
                            f"If you like to change the announcements channel use `{ctx.prefix}setannouncements`"))
            logger.info(f"{ctx.author} successfully accessed the setannouncements command.")
        except StopIteration:
            await ctx.send((f"{ctx.author.mention} There is not currently an announcements channel set. "
                            f"Use `{ctx.prefix}setannouncements` to set an announcements channel."))
            logger.debug(f"{ctx.author} accessed the getannouncements command in {ctx.guild} which does not have an announcements channel.")

    @getannouncements.error
    async def handle_getannouncements_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send(f"The `{ctx.prefix}getannouncements` command is unavailable in DMs. Please try using it in server with me.")
            logger.debug(f"{ctx.author} tried to use the getannouncements command in a DM.")
        else:
            await ctx.send(f"{ctx.author.mention} Congrats! You managed to break the `{ctx.prefix}getannouncements` command! {await self.ping_devs(error, self.getannouncements, ctx=ctx)}")

    # @commands.command(hidden=True)
    # async def check(self, ctx):
    #     print(self.bot.check_other_tasks.get_task())

class bdaybot_helpcommand(commands.HelpCommand):
    # TODO: Add error handling to the help command
    num_of_commands = 7
    async def send_bot_help(self, mapping):
        # TODO: Let ppl accessing the help command know that certain command are unavailable due to certain permissions be unavailable
        ctx = self.context
        self.bday_today, self.today_df = ctx.bot.bday_today, ctx.bot.today_df
        filtered_commands = await self.filter_commands(
                            [command for key, commands in mapping.items() for command in commands])
        description = ("All" if ctx.guild and len(filtered_commands) == self.num_of_commands else "Available") + " Commands:\n```\n"

        for loc, command in enumerate(filtered_commands):
            end = '\n' if loc != len(filtered_commands) - 1 else '```'
            description += f"{ctx.prefix}{command.name}{end}"
        description += "\n" + f"For help on how to use a command use `{ctx.prefix}help " + "{nameofcommand}`\ne.g. " + f"`{ctx.prefix}help getID`"
        help_embed = discord.Embed(description=description).set_author(name="Bdaybot's commands:", icon_url=emoji_urls.partying_face)
        if not ctx.guild:
            help_embed.set_footer(text=f"Not all available commands are shown above.\nUse {ctx.prefix}help in server with me to see all the available commands!")
        elif len(filtered_commands) < self.num_of_commands:
            help_embed.set_footer(text=f"Not all available commands are shown above because I do not have certain permissions.\nPlease give me all the required permissions so you can use all my commands!")

        await ctx.send(embed=help_embed)
        logger.info(f"{ctx.author} accessed the help command.")

    async def send_command_help(self, command):
        ctx = self.context
        self.bday_today, self.today_df = ctx.bot.bday_today, ctx.bot.today_df
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
                            "\nYour message containing your ID is deleted to keep your ID confidental.\n\n"
                            f"The `{ctx.prefix}wish` command is not available on days when it is no one's birthday")

            description += "." if self.bday_today else " (like today)."

            command_embed = discord.Embed(description=description).set_author(name="Wish Command", icon_url=emoji_urls.wrapped_gift) \
                            .set_footer(text="Names are not case sensitive and full names are also acceptable.")
        elif command.name == 'getID':
            description =  ("The getID command allows you to determine the ID that corresponds with your Discord account. "
                            "An ID is useful because it allows you to use other commands.\n\n"
                            f"To use the getID command use `{ctx.prefix}getID`"
                            "\n\nWhen you activate the getID command I will DM you your currently registered ID.\n\n"
                            "If you do not currently have an ID registered I will let you know in the DM message.\n\n"
                            f"You can use the `{ctx.prefix}setID` command to register your ID.")
            command_embed = discord.Embed(description=description).set_author(name="getID Command", icon_url=emoji_urls.numbers)
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
            command_embed = discord.Embed(description=description).set_author(name="setID Command", icon_url=emoji_urls.numbers)
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
            command_embed = discord.Embed(description=description).set_author(name="Setannouncements Command", icon_url=emoji_urls.loudspeaker) \
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
            command_embed = discord.Embed(description=description).set_author(name="Getannouncements Command", icon_url=emoji_urls.loudspeaker) \
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
                            "\nValid numbers are between 1 and 8.  If you use a number larger than 8 only the first 8 upcoming birthdays will be shown.")
            command_embed = discord.Embed(description=description).set_author(name="Upcoming Command", icon_url=emoji_urls.calendar) \
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
        return f"{ctx.bot.cogs['bdaybot_commands'].maybe_mention(ctx)}{super().command_not_found(invalid_command)}"

    async def on_help_command_error(self, ctx, error):
        self.name = 'help'
        bdaybot_cog = ctx.bot.cogs['bdaybot_commands']
        await ctx.send(f"{bdaybot_cog.maybe_mention(ctx)}Congrats you broken the help command!{await bdaybot_cog.ping_devs(error, self, ctx)}")
