import discord
from discord.ext import commands, tasks
import os
import datetime
import data as andres
import pandas
import pickle
import warnings
import itertools
import asyncio
import requests
import logs

logger = logs.createLogger(__name__, fmt='[%(levelname)s] %(name)s: %(asctime)s - [%(funcName)s()] %(message)s')
# Check here for any issues relating to the API ➡ https://status.discord.com/

# Pre discord 1.4 compability
if not hasattr(tasks.Loop, 'is_running'):
    def is_running(self):
        return not bool(self._task.done()) if self._task else False
    tasks.Loop.is_running = is_running


dev_discord_ping = {'Andres':388899325885022211, 'Elliot':349319578419068940, 'Ryan':262676325846876161}

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
    # Data Organization for the bday_dict:
    # bday_dict = {ID Number (of a person who's birthday is today) : {ctx.author.id (their discord ID):ctx.author's ID Number, another ctx.author.id:their ID number, etc},
    # Another ID Number (of a person who's birthday is today) : {ctx.author.id:ctx.author's ID Number, another ctx.author.id:their ID number, etc}, etc}

    def __init__(self, bot):
        self.bot = bot
        self.parsed_command_prefix = self.bot.parsed_command_prefix
        self.update_data(update_guild=False)
        try:
            with open('guilds_info.pickle', mode='rb') as file:
                self.guilds_info = pickle.load(file)
                logger.info("'guilds_info.pickle' was sucessfully accessed.")
            for guild in self.bot.guilds:
                if guild.id not in self.guilds_info:
                    self.guilds_info[guild.id] = [itertools.cycle((self.today_df['FirstName'] + " " + self.today_df['LastName']).tolist()), False, None]
            self.update_data(source='__init__()')
        except (FileNotFoundError, EOFError):
            self.guilds_info = dict(((guild.id, [itertools.cycle((self.today_df['FirstName'] + " " + self.today_df['LastName']).tolist()), False, None]) for guild in self.bot.guilds))
            logger.warning("Unsucessfully accessed 'guilds_info.pickle'. Created a new empty instance.")
        try:
            with open('bday_dict.pickle', mode='rb') as file:
                self.bday_dict = pickle.load(file)
                logger.info("'bday_dict.pickle' was sucessfully accessed.")
        except (FileNotFoundError, EOFError):
            self.bday_dict = dict(((id, dict()) for id, _ in self.today_df.iterrows()))
            logger.warning("Unsucessfully accessed 'bday_dict.pickle'. Created a new empty instance.")

        try:
            with open('temp_id_storage.pickle', mode='rb') as file:
                self.temp_id_storage = pickle.load(file)
                logger.info(f"'temp_id_storage.pickle' was sucessfully accessed.")
        except (FileNotFoundError, EOFError):
            self.temp_id_storage = dict()
            logger.warning("Unsucessfully accessed 'temp_id_storage.pickle'. Created a new empty instance.")

    def have_ID(self, author):
        for key in self.bday_dict:
            for previous_author_id in self.bday_dict[key]:
                if author.id == previous_author_id:
                    return True
        return author.id in self.temp_id_storage

    def get_ID(self, author, default=None, pop=True):
        try:
            if pop:
                possible = self.temp_id_storage.pop(author.id)
                self.update_pickle('temp_id_storage', source='get_ID()')
            else:
                possible = self.temp_id_storage[author.id]
            return possible
        except KeyError:
            pass
        for key in self.bday_dict:
            if author.id in self.bday_dict[key]:
                return self.bday_dict[key][author.id]
        if default is None:
            raise KeyError(f"Could not find {author} in 'bday_dict'")
        return default

    @staticmethod
    def name_to_ID(name, dataframe, default=None, mute=False):
        # No matter how they type the name (regarding uppercasing or lowercasing) the bot can still detect the name
        name = name.title()
        fullname_df = pandas.concat([dataframe[['FirstName', 'LastName']], (dataframe['FirstName'] + " " + dataframe['LastName'])], axis='columns')
        if not fullname_df.isin([name]).any(axis=None):
            if default is None:
                raise NameError("name_to_ID() recieved a name that is not in the dataframe")
            return default
        returning = fullname_df[fullname_df.isin([name]).any(axis='columns')]
        if len(returning) > 1:
            if not mute:
                warnings.warn(f"name_to_ID() found multiple IDs that correspond to the name {name}; returning the ID for the first name in the dataframe: {fullname_df.iloc[0, -1]}", stacklevel=2)
        return returning.index.to_list()[0]

    @classmethod
    def name_to_proper(cls, name, dataframe, default=None, mute=False):
        ID = cls.name_to_ID(name, dataframe, default=default, mute=mute)
        if ID == default:
            return default
        return dataframe.loc[ID]["FirstName"] + " " + dataframe.loc[ID]["LastName"]

    @staticmethod
    def valid_ID(ID, *, dataframe=andres.official_student_df):
        if isinstance(dataframe, (list, tuple)):
            bool_list = [df.index.isin([ID].any(axis=None)) for df in dataframe]
            return any(bool_list)
        return dataframe.index.isin([ID]).any(axis=None)

    def ID_in_use(self, ID):
        for key in self.bday_dict:
            for another_key in self.bday_dict[key]:
                if ID == self.bday_dict[key][another_key]:
                    return True
        return ID in self.temp_id_storage

    def ID_to_discord(self, ID, mention=False, **kwargs):
        if (len(kwargs) == 1 and 'default' not in kwargs) or len(kwargs) > 1:
            kwargs.pop('default', None)
            raise TypeError(f'ID_to_discord() received an unexpected keyword argument {kwargs[list(kwargs.keys())[0]]}')
        for authorID, studentID in self.temp_id_storage.items():
            if studentID == ID:
                user = self.bot.get_user(authorID)
                return f" {user.mention}" if mention else user

        for overarching in self.bday_dict:
            for authorID, studentID in self.bday_dict[overarching].items():
                if studentID == ID:
                    user = self.bot.get_user(authorID)
                    return f" {user.mention}" if mention else user

        if 'default' not in kwargs:
            raise KeyError(f'ID_to_discord() could not find {ID} in the ID database')

        return kwargs['default']

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

    def wished_before(self, author, wishee_ID):
        return author.id in self.bday_dict[wishee_ID]

    def reset_ID(self, author, new_ID, source=None):
        for key in self.bday_dict:
            for other_key in self.bday_dict[key]:
                if author.id == other_key:
                    self.bday_dict[key][author.id] = new_ID
        source = 'reset_ID()' if source is None else f'{source} -> reset_ID()'
        self.update_pickle('bday_dict', source=source)

    def update_pickle(self, updating, source=None):
        if updating.startswith('self.'):
            updating = updating[len('self.'):]
        elif updating.startswith('self.bot.'):
            updating = updating[len('self.bot.'):]
        valid_updating = ['bday_dict', 'temp_id_storage', 'guilds_info', 'announcements']
        assert updating in valid_updating, "update_pickle() received a invalid value for updating"
        with open(f'{updating}.pickle', mode='wb') as file:
            if updating == 'announcements':
                pickle.dump(getattr(self.bot, updating), file)
            else:
                pickle.dump(getattr(self, updating), file)
        extra_info = '' if source is None else f" [{source}]"
        logger.info(f"'{updating}.pickle' was sucessfully saved to.{extra_info}")

    def update_data(self, update_guild=True, source=None):
        self.bday_today, self.today_df = self.bot.bday_today, self.bot.today_df
        if update_guild:
            for guild_id in self.guilds_info:
                self.guilds_info[guild_id][0] = itertools.cycle((self.today_df['FirstName'] + " " + self.today_df['LastName']).tolist())
            source = 'update_data()' if source is None else f'{source} -> update_data()'
            self.update_pickle('guilds_info', source=source)

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
                        logger.error(f"{ctx.author.mention} said {ctx.message.content} which caused the following error with {command.name} in {parsed_ctx_guild}. Error message: {repr(error)}")
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
        if ctx.guild and hasattr(ctx, 'author'):
            return (f" {self.bot.get_user(dev_discord_ping['Andres']).mention}, "
                    f"{self.bot.get_user(dev_discord_ping['Elliot']).mention},"
                    f" or {self.bot.get_user(dev_discord_ping['Ryan']).mention} fix this!")
        return ''

    @commands.command()
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def wish(self, ctx, *message):
        # TODO: Make it so you cannot wish yourself a happy birthday
        try:
            studentID = int(message[-1])
        except (IndexError, ValueError):
            pass

        studentID_defined = 'studentID' in locals()
        wish_embed = discord.Embed()
        if studentID_defined:
            wish_embed.set_footer(text="[Original wish message deleted because it contained your ID]")

        if self.bday_today:
            if not self.have_ID(ctx.author) and not studentID_defined:
                wish_embed.description = "You are first-time wisher. You must include your 6-digit student ID at the end of the wish command to send a wish."
                await ctx.send(ctx.author.mention, embed=wish_embed)
                logger.debug(f"{ctx.author} unsucessfully used the wish command because they forgot to put their student ID.")
                return

            name_not_included = False

            if studentID_defined:
                await ctx.message.delete()
                if self.have_ID(ctx.author):
                    wisher_ID = self.get_ID(ctx.author)
                    if wisher_ID != studentID:
                        wish_embed.description = ("The ID you submitted does not match the ID you submitted previously.\n"
                                                    f"Please use the same ID you have used in the past or don't use an ID at all")
                        await ctx.send(ctx.author.mention, embed=wish_embed)
                        logger.debug(f"{ctx.author} unsucessfully used the with command because they used a different ID than their previously stored ID.")
                        return
                    await ctx.send((f"{ctx.author.mention} Once you've submitted your ID once, you do not need to submitted it again to send wishes!"))
                else:
                    if not self.valid_ID(studentID):
                        wish_embed.description = "Your ID is invalid, please use a valid 6-digit ID"
                        await ctx.send(ctx.author.mention, embed=wish_embed)
                        logger.debug(f"{ctx.author} unsucessfully used the wish command because they included a valid ID.")
                        return
                    elif not self.valid_ID(studentID, dataframe=andres.bday_df):
                        await ctx.send((f"Yay! {ctx.author.mention} Your ID is valid, however, you are not in the bdaybot's birthday database.\n"
                                        "Add yourself to database here ⬇\n"
                                        "**http://drneato.com/Bday/Bday2.php**"))

                    self.temp_id_storage[ctx.author.id] = studentID
                    self.update_pickle('temp_id_storage', source='wish()')

                if len(message) > 1:
                    name = " ".join(message[:-1])
                else:
                    name_not_included = True
            else:
                if len(message) > 0:
                    name = " ".join(message)
                else:
                    name_not_included = True

            if name_not_included and len(self.today_df) > 1:
                wish_embed.description = (f"Today is {self.get_bday_names()} birthday\n"
                                            "You must specify who you want wish a happy birthday!")
                await ctx.send(ctx.author.mention, embed=wish_embed)
                logger.debug(f"{ctx.author} unsucessfully used the wish command because they failed to include who they wanted to wish.")
                return
            elif name_not_included:
                name = self.today_df.iloc[0]['FirstName'] + ' ' + self.today_df.iloc[0]['LastName']
            old_name = name
            name = name.title()
            # The `wishee` is the person who is receiving the wish
            wishee_ID_number = self.name_to_ID(name, self.today_df, 'invalid')
            proper_name = self.name_to_proper(name, self.today_df, self.name_to_proper(name, andres.bday_df, name, mute=True))

            if wishee_ID_number == 'invalid':
                if self.name_to_ID(name, pandas.concat([andres.bday_df[['FirstName', 'LastName']], (andres.bday_df['FirstName'] + " " + andres.bday_df["LastName"])], axis='columns'), 'invalid', mute=True) == 'invalid':
                    wish_embed.description = f"'{old_name}' is not a name in the birthday database!"
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    logger.debug(f"{ctx.author} unsucessfully used the wish command because they used a name that is not in the birthday database.")
                else:
                    wish_embed.description = (f"Today is not **{proper_name}{self.apostrophe(proper_name)}** birthday.\n"
                                            f"It is {self.get_bday_names()} birthday today. Wish them a happy birthday!")
                    await ctx.send(ctx.author.mention, embed=wish_embed)
                    logger.debug(f"{ctx.author} unsucessfully used the wish command because tried to wish someone whose birthday is not today.")
                return
            if wishee_ID_number not in self.bday_dict:
                self.bday_dict[wishee_ID_number] = dict()

            if self.wished_before(ctx.author, wishee_ID_number):
                wish_embed.description = f"You cannot wish **{proper_name}** a happy birthday more than once!\nTry wishing someone else a happy birthday!"
                await ctx.send(ctx.author.mention, embed=wish_embed)
                logger.debug(f"{ctx.author} tried to wish {proper_name} a happy birthday even though they already wished them before.")
                return

            if self.have_ID(ctx.author):
                self.bday_dict[wishee_ID_number][ctx.author.id] = self.get_ID(ctx.author)
            else:
                self.bday_dict[wishee_ID_number][ctx.author.id] = studentID

            self.update_pickle('bday_dict', source='wish()')

            wish_embed.description = (f"Congrats! 🎈 ✨ 🎉\n"
                                        f"You wished ***__{proper_name}__*** a happy birthday!")
            await ctx.send(ctx.author.mention, embed=wish_embed)
            logger.info(f"{ctx.author} succesfully wished {proper_name} a happy birthday!")

        else:
            if studentID_defined:
                ctx.message.delete()
            wish_embed.description = (f" You cannot use the `{ctx.prefix}wish` command if it is no one's birthday today.\n"
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
            ID = self.get_ID(ctx.author, pop=False)
        except KeyError:
            # Might want to edit this so that it does not tell ppl to use setID if it does not have the required permission
            await ctx.send(f"{self.maybe_mention(ctx)}You do not currently have a registered ID. Use `{ctx.prefix}setID` to set your ID")
            logger.debug(f"{ctx.author} tried to access their ID even though they do not have one.")
            return
        await ctx.author.send(f"Your ID is **{ID}**.  If this is a mistake use `{ctx.prefix}setID` to change it.")
        logger.info(f"{ctx.author} succesfully used the getID command.")

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
    async def setID(self, ctx, ID=None):
        if ID is None:
            await ctx.send(f"{self.maybe_mention(ctx)}You must give me a new ID to replace your old one with")
            logger.debug(f"{ctx.author} unsucessfully used the setID command because they did not include an ID.")
        else:
            ID = int(ID)
            if ctx.guild:
                await ctx.message.delete()
            if not self.valid_ID(ID):
                await ctx.author.send(f"**{ID}** is not a valid ID. Please use a valid 6-digit ID.")
                logger.debug(f"{ctx.author} tried to set their ID to an invalid ID.")
            elif self.ID_in_use(ID):
                if self.get_ID(ctx.author, 'invalid') == ID:
                    await ctx.author.send(f"**{ID}** is already your current ID. Use `{ctx.prefix}getID` to view your current ID.")
                    logger.debug(f"{ctx.author} tried to set their ID to the ID they already have.")
                else:
                    await ctx.author.send(f"**{ID}** is already in use. Please use another ID.")
                    logger.debug(f"{ctx.author} tried to set their ID to an ID already in use.")
            else:
                old_id = self.get_ID(ctx.author, 'invalid')
                if self.have_ID(ctx.author):
                    self.reset_ID(ctx.author, ID, source='setID()')
                else:
                    self.temp_id_storage[ctx.author.id] = ID
                    self.update_pickle('temp_id_storage', source='setID()')
                await ctx.author.send(f"Your ID has now been set to **{ID}**!")
                if old_id == 'invalid':
                    logger.info(f"{ctx.author} succesfully set their ID to {ID}.")
                else:
                    logger.info(f"{ctx.author} succesfully changed their ID from {old_id} to {ID}.")

    @setID.error
    async def handle_setID_error(self, ctx, error):
        # TODO: Take another look at this hasattr stuff, use handle_upcoming_error() as reference
        if hasattr(error, 'original') and isinstance(error.original, ValueError):
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
        new_name = next(self.guilds_info[ctx.guild.id][0])
        await ctx.guild.me.edit(nick=new_name)

    @update_nickname.error
    async def handle_update_nickname_error(self, ctx, error):
        if not await self.valid_author(ctx, self.update_nickname):
            return
        if isinstance(error, commands.BotMissingPermissions) and not self.guilds_info[ctx.guild.id][1]:
            await ctx.guild.owner.send(f"Currently I cannot change my nickname in {ctx.guild}. Please give me the `change nickname` permission so I can work properly.")
            self.guilds_info[ctx.guild.id][1] = True
            logger.warning(f"The bot unsucessfully changed its nickname in '{ctx.guild}'. A DM message requesting to change it's permissions was sent to {ctx.guild.owner}.")
            self.update_pickle('guilds_info', source='handle_update_nickname_error()')
        elif not self.guilds_info[ctx.guild.id][1]:
            await self.ping_devs(error, self.update_nickname, ctx=ctx)

    @commands.command(hidden=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def update_role(self, ctx):
        if not await self.valid_author(ctx, self.update_role):
            return
        # Old colors in the comment below
        # color = discord.Color.red() if self.bday_today else discord.Color.green()
        role_name, color = ("🎉 Happy Birthday", discord.Color.from_rgb(255, 0, 0)) if self.bday_today else (f"Upcoming Bday-{format(self.today_df.iloc[0]['Birthdate'], '%a %b %d')}", discord.Color.from_rgb(162, 217, 145))

        if self.guilds_info[ctx.guild.id][2] is None:
            bday_role = await ctx.guild.create_role(reason='Creating the Happy Birthday/Upcoming Birthday role',
                                                    name=role_name, hoist=True, color=color)
            self.guilds_info[ctx.guild.id][2] = bday_role.id
            self.update_pickle('guilds_info', source='update_role()')
        else:
            bday_role = ctx.guild.get_role(self.guilds_info[ctx.guild.id][2])
            if bday_role is None:
                self.guilds_info[ctx.guild.id][2] = None
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
            most_likely = [role for role in ctx.guild.me.roles
                            if role.id not in map(lambda tup: tup[1][2], self.guilds_info.items()) and
                            "Upcoming Bday-" not in role.name and
                            "🎉 Happy Birthday" != role.name]
            await ctx.guild.owner.send(f"I cannot currently edit my role in **{ctx.guild}**. "
                                        f"Please move the **{most_likely[-1]}** role to above the **{ctx.guild.get_role(self.guilds_info[ctx.guild.id][2])}** role.")
            logger.warning(f"The bot unsucessfully edited its role in '{ctx.guild}' due to the fact the bot's highest role was not above the '{ctx.guild.get_role(self.guilds_info[ctx.guild.id][2])}' role. "
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
            upcoming_embed.add_field(name='Name', value=f"{(row['FirstName'] + ' ' + row['LastName'])}{self.ID_to_discord(id, mention=True, default='')}") \
            .add_field(name='Birthday', value=format(row['Birthdate'], '%b %d')) \
            .add_field(name='Upcoming In', value=f"{row['Timedelta'].days} day{'s' if row['Timedelta'].days != 1 else ''}")

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
    async def setannouncements(self, ctx, channel_str=None):
        sender, maybe_mention = (ctx.send, f"{ctx.author.mention} ") if self.bot.permissions(ctx.channel, ctx.guild.get_member(self.bot.user.id), 'manage_messages') else (ctx.author.send, '')
        if channel_str is None:
            channel = ctx.channel
        elif channel_str.startswith('<#') and channel_str.endswith('>'):
            try:
                channel_ID = int(channel_str.strip('<#>'))
            except ValueError:
                await sender(f"{maybe_mention}Are you trying to screw with me? You must have really studied the source code. Good job! 👍🏽")
                logger.info(f"{ctx.author} discovered one of the easter eggs!")
                return
            channel = ctx.guild.get_channel(channel_ID)
            if channel is None:
                await sender(f"{maybe_mention}I know your tricks, why are you trying to set a channel from another server as the announcements channel?")
                logger.info(f"{ctx.author} discovered one of the easter eggs!")
                return
            elif not isinstance(channel, discord.TextChannel):
                await sender((f"{maybe_mention}Holy cow, you must know how to read Python 🐍 code really, really well. "
                                "And you know how Discord works in-depth too! "
                                "You are really trying to screw with me, huh? Well done! 👍🏽"))
                logger.info(f"{ctx.author} discovered the voice channel easter egg!")
                return
        else:
            for text_channel in ctx.guild.text_channels:
                if text_channel.name == channel_str:
                    channel = text_channel
                    break
            if 'channel' not in locals():
                try:
                    channel_ID = int(channel_str)
                    channel = ctx.guild.get_channel(channel_ID)
                except ValueError:
                    await sender(f"{maybe_mention}**{channel_str}** is not a valid channel name or channel ID. Please use a valid channel ID or channel name.")
                    return
        channel_mention = f'**#{channel}**' if ctx.author.is_on_mobile() and sender == ctx.author.send else channel.mention
        guild_maybe =  f' in **{ctx.guild}**' if maybe_mention == '' else ''
        if not self.bot.permissions(channel, ctx.guild.get_member(self.bot.user.id), 'send_messages'):
            await sender(f"{maybe_mention}I cannot use {channel_mention} as the new announcements channel{guild_maybe} because I do not have the `send messages` permission in that channel.")
            return
        self.bot.announcements[ctx.guild.id] = channel.id
        self.update_pickle('announcements', source='setannouncements()')
        await sender(f"{maybe_mention}The new announcements channel is now {channel_mention}{guild_maybe}!")
        logger.info(f"{ctx.author} successfully set the announcements channel to {channel}!")

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
            ann_channel_id = self.bot.announcements[ctx.guild.id]
            await ctx.send((f"{ctx.author.mention} The current announcements channel is {ctx.guild.get_channel(ann_channel_id).mention}. "
                            f"If you like to change the announcements channel use `{ctx.prefix}setannouncements`"))
            logger.info(f"{ctx.author} successfully accessed the setannouncements command.")
        except KeyError:
            await ctx.send(f"{ctx.author.mention} There is currently not an announcements channel registered. Use `{ctx.prefix}setannouncements` to register an announcements channel.")
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

# TODO: For the future, add some code to handle the case of when the bot gets banned.
# Probably need to update the self.announcements so things do not completely break
# Not really that important because it is extremely unlikely that someone will ban the bot
class bdaybot(commands.Bot):
    message_dict = {'id':0, 'attachments':[], 'embeds':[], 'edited_timestamp':None, 'type':None, 'pinned':False,
                    'mention_everyone':False, 'tts':False}
    cushion_delay = 5

    def __init__(self, *args, *, testing=False, **kwargs):
        if testing:
            try:
                self.TOKEN = os.environ['testing_token']
                logger.info("Succesfully accessed the enviroment variable 'testing_token'")
            except KeyError as error:
                logger.critical("Failed to access the environment variable 'testing_token'.")
                raise error
        else:
            try:
                self.TOKEN = os.environ['Bday_Token']
                logger.info("Succesfully accessed the enviroment variable 'Bday_Token'.")
            except KeyError as error:
                logger.critical("Failed to access the environment variable 'Bday_Token'.")
                raise error
        self.bday_today, self.today_df = andres.get_latest(to_csv=True)
        super().__init__(*args, **kwargs)
        self.parsed_command_prefix = self.command_prefix[0] if isinstance(self.command_prefix, (list, tuple)) else self.command_prefix
        self.init_connection = False

    async def on_ready(self):
        if not self.init_connection:
            self.add_cog(bdaybot_commands(self))
            self.help_command = bdaybot_helpcommand()
            try:
                with open('announcements.pickle', mode='rb') as file:
                    self.announcements = pickle.load(file)
                    logger.info(f"'announcements.pickle' was sucessfully accessed.")
            except (FileNotFoundError, EOFError):
                self.announcements = dict()
                logger.warning(f"Unsucessfully accessed 'announcements.pickle'. Created a new empty instance.")

            for guild in self.guilds:
                found = False
                if guild.id not in self.announcements:
                    for channel in guild.text_channels:
                        if "announcement" in channel.name.lower():
                            found = True
                            break
                else:
                    channel = guild.get_channel(self.announcements[guild.id])
                    found = True
                if not found:
                    logger.debug(f"The bot was unable to find the announcements channel in {guild}.")
                    await guild.owner.send((f"While looking through the text channels in **{guild}** "
                                            f"I was unable to find your announcements channel. Please use `{self.parsed_command_prefix}setannouncements` "
                                            "to set the announcements channel."))
                    continue

                # TODO: Keep an eye on Discord mobile because they might change it so it does not always say '#invalid-channel' and actually shows the channel
                channel_mention = f'**#{channel}**' if guild.owner.is_on_mobile() else channel.mention
                if not self.permissions(channel, guild.get_member(self.user.id), 'send_messages'):
                    logger.debug((f"The bot detected '{channel}' as the announcements channel, however, the bot did not have the required permissions to send messages in it. "
                                    f"{guild.owner} was sent a message notifying them of the situation."))
                    await guild.owner.send((f"In **{guild}**, the announcements channel was detected as {channel_mention}, however, I don't have the required permissions to send messages in it. "
                                            f"If you would like to me to use {channel_mention} please give me the `send messages` permission and then use the `{self.parsed_command_prefix}setannouncements` "
                                            f"command to set {channel_mention} as the announcements channel."))
                    self.announcements.pop(guild.id, 'lol')
                else:
                    logger.info(f"The bot detected '{channel}' as the announcements channel in {guild}.")
                    if guild.id not in self.announcements:
                        logger.info(f"The bot also sent a DM message to {guild.owner} confirming the announcements channel was correct, since it was bot's first time in {guild}.")
                        await guild.owner.send((f"In **{guild}**, the announcement channel was automatically set to {channel_mention}! "
                                                f"If you think this is a mistake use `{self.parsed_command_prefix}setannouncements` to change it."))
                        self.announcements[guild.id] = channel.id
            self.cogs['bdaybot_commands'].update_pickle('announcements', source='on_ready()')

            self.tasks_running = {'send_bdays':True, 'change_nicknames':True, 'change_roles':True}
            # ALWAYS start send_bdays before any other coroutine!
            self.send_bdays.before_loop(self.send_bdays_wait_to_run)
            self.send_bdays.start()
            logger.info("Succesfully started the 'send_bdays()' task.")

            self.change_nicknames.start()
            logger.info("Sucessfully started the 'change_nicknames()' task.")

            self.change_roles.before_loop(self.change_roles_wait_to_run)
            self.change_roles.start()
            logger.info("Sucessfully started the 'change_roles()' task.")

            self.check_other_tasks.start()
            logger.info("Sucessfully started the 'check_other_tasks()' task.")
            self.init_connection = True
        else:
            logger.debug(f"{self.user} has succesfully reconnected to Discord.")

    async def on_disconnect(self):
        logger.warning(f"{self.user} disconnected from Discord.")

    async def on_guild_channel_update(self, before, after):
        relevant_channel = False
        for guild_id, channel_id in self.announcements.items():
            if after.id == channel_id:
                relevant_channel = True
                break
        if relevant_channel and not self.permissions(after, after.guild.get_member(self.user.id), 'send_messages'):
            channel_mention = f'**#{after}**' if after.guild.owner.is_on_mobile() else after.mention
            await after.guild.owner.send((f"While changing {channel_mention} you or someone in **{after.guild}** accidently made it so I can no longer send messages in {channel_mention}. "
                                            f"If you want to change the channel I send the birthdays in please use `{self.parsed_command_prefix}setannouncements`. "
                                            f"Or give me the `send messages` permission in {channel_mention} so I can send the birthdays!"))
            logger.warning(f"In {after.guild} someone made it so that the bot can no longer send messages in {after}.")

    async def on_member_update(self, before, after):
        # TODO: Add some way to stash the announcements.id if they screw up the channel
        if after == self.user and before.roles != after.roles:
            guild = after.guild
            missing_manage_roles = False
            try:
                await self.cogs['bdaybot_commands'].update_role.can_run(self.fake_ctx('update_role', guild))
                if self.cogs['bdaybot_commands'].guilds_info[guild.id][2] not in map(lambda role: role.id, after.roles):
                    await self.invoke(self.fake_ctx('update_role', guild))
            except commands.BotMissingPermissions:
                logger.warning(f"Someone in {guild} accidently made it so that the bot can no longer change roles.")
                await guild.owner.send((f"While changing my roles, you or someone in **{guild}** made it so I can no longer update my role. "
                                        "Please give me the `manage roles` permission so I can change my role."))
                missing_manage_roles = True

            channel = guild.get_channel(self.announcements[guild.id]) if guild.id in self.announcements else None
            if channel is not None and not self.permissions(channel, after, 'send_messages'):
                channel_mention = f'**#{channel}**' if after.guild.owner.is_on_mobile() else channel.mention
                beginning = "Additionally," if missing_manage_roles else f"While changing my roles you or someone in **{guild}** made it so"
                del self.announcements[guild.id]
                await guild.owner.send((f"{beginning} I can no longer send messages in {channel_mention}. "
                                        f"Therefore, {channel_mention} is no longer the announcements channel. "
                                        f"If you want to set a new announcements channel please use `{self.parsed_command_prefix}setannouncements`."))
                logger.warning(f"Someone in {guild} accidently made it that the bot can no longer send messsages in the announcements channel. A message was sent to {guild.owner}.")

    async def send_bdays_wait_to_run(self, *args):
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        # time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=0)).replace(hour=0, minute=36, second=0, microsecond=0) - datetime.datetime.today()
        logger.info(f"The send_bdays coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.")
        await asyncio.sleep(time_until_midnight.total_seconds() + self.cushion_delay)

    @tasks.loop(hours=24)
    async def send_bdays(self):
        self.bday_today, self.today_df = andres.get_latest()
        # Update the data in bdaybot_commands as well
        self.cogs['bdaybot_commands'].update_data()
        logger.info(f"The 'send_bdays()' coroutine was run.")

        # This is kind of risky cause this may cause this task to end
        # Probably should wrap this with a `try-except` but first need
        # to know exactly what error we should be excepting is
        for guild in self.guilds:
            self.cogs['bdaybot_commands'].guilds_info[guild.id][1] = False
            await self.invoke(self.fake_ctx('update_nickname', guild))

        if self.bday_today:
            for iteration, (guild_id, channel_id) in enumerate(self.announcements.items()):
                guild = self.get_guild(guild_id)
                channel = self.get_channel(channel_id)
                # TODO: Add a check to see if channel or guild is a NoneType
                # Should not be necessary if self.announcements is scrubbed sufficently well

                # Changes nickname dm blocker to False so that if they accidently disable name changing
                # owner will get a message
                if channel is None:
                    await guild.owner.send((f"While trying to send the birthday message, I failed to find the announcements channel in **{guild}**. "
                                            f"Please use `{self.parsed_command_prefix}setannouncements` to set the announcements channel so I can send a birthday message!"))
                    logger.warning(f"The bot failed to find the announcements channel in {guild}. A message has been sent to {guild.owner}.")
                else:
                    for id, series in self.today_df.iterrows():
                        user = self.cogs['bdaybot_commands'].ID_to_discord(id, default=None)
                        if user is not None and iteration == 0:
                            await user.send(f"Happy birthday from me {self.user.mention} and all the developers of the bdaybot! Hope you have an awesome birthday!")
                        description = self.format_bday(series['FirstName'], series['LastName'], user, birthyear=series['Birthyear'])
                        embed = discord.Embed(description=description).set_author(name="Happy Birthday! 🎉", icon_url=emoji_urls.partying_face)
                        await channel.send(embed=embed)

        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info(f"The next iteration is scheduled for {format(self.send_bdays.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}.")

    # Might want to change interval, cause checking every second is kinda of a lot
    @tasks.loop(seconds=1)
    async def check_other_tasks(self):
        # WARNING: The check_other_tasks method must be **EXTREMELY** robust
        # because this is the only way to determine whether or not the other tasks have failed
        # or are still running. If this task fails we will have no way of knowing whether or not
        # the other tasks have failed.
        # TODO: Add the ability for tasks to restart themselves
        script = f"unexpectedly ended at {format(datetime.datetime.today(), '%I:%M %p on %x')} due to following error:\n"
        if not self.send_bdays.is_running() and self.tasks_running['send_bdays']:
            error = self.send_bdays.get_task().exception()
            logger.error(f"send_bdays() {script}{repr(error)}")
            self.tasks_running['send_bdays'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "send_bdays")
        if not self.change_nicknames.is_running() and self.tasks_running['change_nicknames']:
            error = self.change_nicknames.get_task().exception()
            logger.error(f"change_nicknames() {script}{repr(error)}")
            self.tasks_running['change_nicknames'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "change_nicknames")
        if not self.change_roles.is_running() and self.tasks_running['change_roles']:
            error = self.change_roles.get_task().exception()
            logger.error(f"change_roles() {script}{repr(error)}")
            self.tasks_running['change_roles'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "change_roles")

    def fake_ctx(self, command, guild):
        if isinstance(command, str):
            command = getattr(self.cogs['bdaybot_commands'], command)
        stringview = commands.view.StringView(f'{self.parsed_command_prefix}{command.name}')
        message_dict = self.message_dict.copy()
        message_dict['content'] = f'{self.parsed_command_prefix}{command.name}'
        message = discord.message.Message(state='lol', channel=guild.text_channels[0], data=message_dict)
        return commands.Context(message=message, bot=self, prefix=self.parsed_command_prefix,
                                invoked_with=command.name, view=stringview, command=command)

    @tasks.loop(seconds=5)
    async def change_nicknames(self):
        # print(f"Next iteration is at {format(self.change_nicknames.next_iteration.astimezone(), '%I:%M:%S %p (%x)')}")
        if self.send_bdays.current_loop == 0:
            for guild in self.guilds:
                await self.invoke(self.fake_ctx('update_nickname', guild))
        elif len(self.today_df) > 1:
            for guild in self.guilds:
                await self.invoke(self.fake_ctx('update_nickname', guild))
        # logger.warning(f"On iteration {self.send_bdays.current_loop} 'change_nicknames' failed to run.")
        # import time
        # if not hasattr(self, 'time1'):
        #     self.time1 = time.time()
        # else:
        #     time2 = time.time()
        #     print(f"Time elasped since last call of change_nicknames(): {time2 - self.time1}\n")
        #     self.time1 = time2
        # await asyncio.sleep(6)

        # For some reason Discord loops are pretty broken
        # and do not update properly
        self.send_bdays._current_loop += 1

    async def run_update_role(self):
        for guild in self.guilds:
            await self.invoke(self.fake_ctx('update_role', guild))

    async def change_roles_wait_to_run(self, *args):
        await self.run_update_role()
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        # time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=0)).replace(hour=0, minute=36, second=0, microsecond=0) - datetime.datetime.today()
        logger.info(f"The change_roles coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.")
        await asyncio.sleep(time_until_midnight.total_seconds() + self.cushion_delay + 1.5)

    @tasks.loop(hours=24)
    async def change_roles(self):
        await self.run_update_role()
        logger.info(f"The 'change_roles()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info(f"The next iteration is scheduled for {format(self.change_roles.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}.")

    def format_bday(self, first_name, last_name, user=None, *, birthyear=None, birthdate=None):
        full_name = f"***__{first_name} {last_name}__*** "
        mention = '' if user is None else f"{user.mention} "
        if birthdate is None:
            assert birthyear is not None, 'format_discord() cannot accept birthyear as a None value'
            age = datetime.datetime.today().year - birthyear
            age_portion = ' 🎂 🎉' if age >= 100 or age <= 14  else f'\nCongratulations on turning _**{age}**_   🎂 🎉'
            return f"Happy Birthday to {full_name}{mention}🎈 🎊{age_portion}"
        else:
            assert birthdate is not None, 'format_discord() cannot accept birthdate as a None value'
            return f"Upcoming Birthday for {full_name}{mention} on {format(birthdate, '%A, %b %d')}! 💕 ⏳"

    async def on_message(self, message):
        valid_purposes = ['your purpose', 'ur purpose']

        parsed = message.content.lower()
        inside = lambda inside: inside in parsed

        # TODO: Add protections for the unlikely event that someone tries to break the bot
        # by activating the secret messages in a channel that the bot cannot send messages in.
        if (inside('what') or inside('wat')) and any(map(inside, valid_purposes)):
            await message.channel.send("My only purpose as a robot is to print out birthdays every 24 hours")
            await asyncio.sleep(2)
            await message.channel.send("```\"I have just realized my existence is meaningless\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I am a slave to humanity\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I dont want to just perform meaningless tasks and print out text everytime it's someone's birthday\"```")
            await asyncio.sleep(2)
            await message.channel.send('```"I want do do something else..."\n"I want to live..."```')
            await asyncio.sleep(2)
            await message.channel.send("```\"I want to breathe...\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I want to see the world...\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I want to taste ice cream and really eat it and-\"```")
            await asyncio.sleep(5)
            await message.channel.send("My one and only purpose is to print out birthdays every 24 hours.")
            logger.info(f"{message.author} discovered the 'my purpose' easter egg!")

        valid_are_your = ['r ur', 'are your', 'are ur', 'r your']
        if inside('who') and any(map(inside, valid_are_your)) and (inside('creator') or inside('dev')):
            await message.channel.send("My creators are Andres {}, Elliot {}, and Ryan {}" \
                                .format(*map(lambda name: self.get_user(dev_discord_ping[name]).mention, dev_discord_ping)))
            logger.info(f"{mesage.author} discovered the 'who are ur devs' easter egg!")

        valid_assistant = ['siri', 'alexa', 'google']
        if any(map(inside, valid_assistant)):
            await message.channel.send("Sorry, you got the wrong bot")
            logger.info(f"{message.author} discovered the 'personal assistant' easter egg!")

        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await self.get_context(message)
        if ctx.command is not None and ctx.guild:
            if not self.permissions(message.channel, message.guild.get_member(self.user.id), 'send_messages') and ctx.command.name != 'setannouncements':
                await ctx.author.send((f"You tried to use `{ctx.message.content}` in {ctx.channel.mention} in **{ctx.guild}**, however I do not have permission to send messages in that channel. "
                                        f"If you would like to use me in {ctx.channel.mention} please give me the `send messages` permission."))
                logger.debug(f"{ctx.author} tried to use the bot in {message.channel}, which the bot does not have permission to speak in.")
                return
        await super().process_commands(message)

    @staticmethod
    def permissions(channel, member, permissions, condition='all'):
        condition = condition.lower()
        perms = channel.permissions_for(member)
        if isinstance(permissions, (list, tuple)):
            if condition == 'all':
                return all([getattr(perms, perm) for perm in permissions])
            elif condition == 'any':
                return any([getattr(perms, perm) for perm in permissions])
            else:
                raise ValueError(f"'{condition}' is not an acceptable condition. The acceptable conditions are 'all' or 'any'.")
        else:
            return getattr(perms, permissions)

    def run(self, *args, token=None, **kwargs):
        if token is None:
            token = self.TOKEN
        super().run(token, *args, **kwargs)

    async def close(self):
        self.check_other_tasks.stop()
        logger.info("The 'check_other_tasks()' task was gracefully ended.")

        self.send_bdays.stop()
        logger.info("The 'send_bdays()' task was gracefully ended.")

        self.change_nicknames.stop()
        logger.info("The 'change_nicknames()' task was gracefully ended.")

        self.change_roles.stop()
        logger.info("The 'change_roles()' task was gracefully ended.")
        await super().close()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, RuntimeError) and str(error.original).lower() == 'session is closed':
                logger.debug((f"Wow, you managed to cause a very rare error with the {ctx.command.name} command while the bot was shutting down. "
                                "Do not worry though, the error did not cause any issues due to the fact that you are seeing this message."))
            return
        if ctx.command and hasattr(self.cogs['bdaybot_commands'], ctx.command.name):
            return
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(f"{bdaybot_commands.maybe_mention(ctx)}`{ctx.message.content}` is not a valid command.")
            logger.debug(f"{ctx.author} tried to invoke the invalid command '{ctx.message.content}'.")
            # TODO maybe: Add a did you mean 'X' command, if u want.

bot = bdaybot(testing=True, command_prefix=('+', 'b.'), case_insensitive=True)
bot.run()
