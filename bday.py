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

# Pre discord 1.4 compability
if not hasattr(tasks.Loop, 'is_running'):
    def is_running(self):
        return not bool(self._task.done()) if self._task else False
    tasks.Loop.is_running = is_running


dev_discord_ping = {'Andres':388899325885022211, 'Elliot':349319578419068940, 'Ryan':262676325846876161}

class bdaybot_commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parsed_command_prefix = self.bot.parsed_command_prefix
        self.update_data(update_guild=False)
        try:
            with open('guilds_info.pickle', mode='rb') as file:
                self.guilds_info = pickle.load(file)
                print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, 'guilds_info.pickle' was sucessfully accessed.")
            for guild in self.bot.guilds:
                if guild.id not in self.guilds_info:
                    self.guilds_info[guild.id] = [itertools.cycle((self.today_df['FirstName'] + " " + self.today_df['LastName']).tolist()), False, None, False]
            self.update_data(source='__init__()')
        except (FileNotFoundError, EOFError):
            self.guilds_info = dict(((guild.id, [itertools.cycle((self.today_df['FirstName'] + " " + self.today_df['LastName']).tolist()), False, None, False]) for guild in self.bot.guilds))
            print((f"Unsucessfully attempted to access 'guilds_info.pickle' at {format(datetime.datetime.today(), '%I:%M %p (%x)')}.\n"
                    "Created a new an empty instance.\n"))
        try:
            with open('bday_dict.pickle', mode='rb') as file:
                self.bday_dict = pickle.load(file)
                print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, 'bday_dict.pickle' was sucessfully accessed.\n")
        except (FileNotFoundError, EOFError):
            self.bday_dict = dict(((id, dict()) for id, _ in self.today_df.iterrows()))
            print((f"Unsucessfully attempted to access 'bday_dict.pickle' at {format(datetime.datetime.today(), '%I:%M %p (%x)')}.\n"
                    "Created a new an empty instance.\n"))

        try:
            with open('temp_id_storage.pickle', mode='rb') as file:
                self.temp_id_storage = pickle.load(file)
                print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, 'temp_id_storage.pickle' was sucessfully accessed.\n")
        except (FileNotFoundError, EOFError):
            self.temp_id_storage = dict()
            print((f"Unsucessfully attempted to access 'temp_id_storage.pickle' at {format(datetime.datetime.today(), '%I:%M %p (%x)')}.\n"
                    "Created a new an empty instance.\n"))

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
        return False

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
        valid_updating = ['bday_dict', 'temp_id_storage', 'guilds_info']
        assert updating in valid_updating, "update_pickle() received a invalid value for updating"
        with open(f'{updating}.pickle', mode='wb') as file:
            pickle.dump(getattr(self, updating), file)
        extra_info = '' if source is None else f" [{source}]"
        print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')} '{updating}.pickle' was sucessfully saved to.{extra_info}\n")

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
                print(f"[{command.name}()] {ctx.author} caused the following error in {parsed_ctx_guild}, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n{repr(error)}\n")
            else:
                print(f"The following error occured with the {command.name} command in {parsed_ctx_guild} at {format(datetime.datetime.today(), '%I:%M %p (%x)')}\n{repr(error)}\n")
            if ctx.guild and hasattr(ctx, 'author'):
                return (f" {self.bot.get_user(dev_discord_ping['Andres']).mention}, "
                        f"{self.bot.get_user(dev_discord_ping['Elliot']).mention},"
                        f" or {self.bot.get_user(dev_discord_ping['Ryan']).mention} fix this!")
        for dev_name in dev_discord_ping:
            dev = self.bot.get_user(dev_discord_ping[dev_name])
            if hasattr(ctx, 'author'):
                await dev.send(f"{ctx.author.mention} caused the following error with `{command.name}()` in {parsed_ctx_guild}, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n  **{repr(error)}**")
            elif ctx is None:
                await dev.send(f"The following error occured with the `{command}()` task, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n**{repr(error)}**")
            else:
                await dev.send(f"The following error occured with `{command.name}()` in {parsed_ctx_guild}, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n**{repr(error)}**")
        return ''

    @commands.command()
    @commands.bot_has_permissions(manage_messages=True)
    async def wish(self, ctx, *message):
        try:
            studentID = int(message[-1])
        except (IndexError, ValueError):
            pass

        studentID_defined = 'studentID' in locals()
        og_message_deleted = "\n[Original wish message deleted because it contained your ID]" if studentID_defined else ""

        if self.bday_today:
            if not self.have_ID(ctx.author) and not studentID_defined:
                await ctx.send(f"{ctx.author.mention} You are first-time wisher. You must include your ID at the end of the wish command to send a wish.")
                return

            name_not_included = False

            if studentID_defined:
                await ctx.message.delete()
                if self.have_ID(ctx.author):
                    wisher_ID = self.get_ID(ctx.author)
                    if wisher_ID != studentID:
                        await ctx.send((f"{ctx.author.mention} The ID you submitted does not match the ID you submitted previously.\n"
                                        f"Please use the same ID you have used in the past or don't use an ID at all{og_message_deleted}"))
                        return
                    await ctx.send((f"{ctx.author.mention} Once you've submitted your ID once, you do not need to submitted it again to send wishes!"))

                else:
                    if not self.valid_ID(studentID):
                        await ctx.send(f'{ctx.author.mention} Your ID is invalid, please use a valid 6-digit ID{og_message_deleted}')
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
                await ctx.send((f"{ctx.author.mention} Today is {self.get_bday_names()} birthday\n"
                                f"You must specify who you want wish a happy birthday!{og_message_deleted}"))
                return
            elif name_not_included:
                name = self.today_df.iloc[0]['FirstName'] + ' ' + self.today_df.iloc[0]['LastName']
            old_name = name
            name = name.title()
            # The `wishee` is the person who is receiving the wish
            wishee_ID_number = self.name_to_ID(name, self.today_df, 'invalid')
            proper_name = self.name_to_proper(name, self.today_df, self.name_to_proper(name, andres.bday_df, name, mute=True))

            if wishee_ID_number == 'invalid' or proper_name == 'invalid':
                if name_to_ID(name, pandas.concat([andres.bday_df[['FirstName', 'LastName']], (andres.bday_df['FirstName'] + " " + andres.bday_df["LastName"])], axis='columns'), 'invalid', mute=True) == 'invalid':
                    await ctx.send(f"{ctx.author.mention} '{old_name}' is not a name in the birthday database!{og_message_deleted}")
                else:
                    await ctx.send(f"{ctx.author.mention} Today is not {proper_name}{apostrophe(proper_name)} birthday.\nIt is {get_bday_names()} birthday today. Wish them a happy birthday!{og_message_deleted}")
                return

            if self.wished_before(ctx.author, wishee_ID_number):
                await ctx.send(f"{ctx.author.mention} You cannot wish {proper_name} a happy birthday more than once! Try wishing someone else a happy birthday!{og_message_deleted}")
                return

            if self.have_ID(ctx.author):
                self.bday_dict[wishee_ID_number][ctx.author.id] = self.get_ID(ctx.author)
            else:
                self.bday_dict[wishee_ID_number][ctx.author.id] = studentID
            self.update_pickle('bday_dict', source='wish()')


            await ctx.send((f"{ctx.author.mention} Congrats! 🎈 ✨ 🎉\n"
                            f"You wished ***__{proper_name}__*** a happy birthday!{og_message_deleted}"))

        else:
            if studentID_defined:
                ctx.message.delete()
            script = (f"{ctx.author.mention} You cannot use the `!wish` command if it is no one's birthday today.\n"
                      "However, it will be "
                      f"{self.get_bday_names()} birthday on {format(self.today_df.iloc[0]['Birthdate'], '%A, %B %d')}{og_message_deleted}")
            await ctx.send(script)

    @wish.error
    async def handle_wish_error(self, ctx, error):
        if isinstance(ctx.message.channel, discord.DMChannel):
            print(f"{ctx.author} tried to use the wish command in a DM on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}")
            await ctx.send(f"The `{self.parsed_command_prefix}wish` command is not currently available in DMs. Please try using it in a server with me.")
        elif isinstance(error, commands.BotMissingPermissions):
            print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, the wish command was used in {ctx.guild} without the 'manage_messages' permission by {ctx.author}\n")
            await ctx.send((f"The `{self.parsed_command_prefix}wish` command is currently unavailable because I do not have the `manage messages` permission.\n"
                            f"If you would like to use the `{self.parsed_command_prefix}wish` command please, give me the `manage messages` permission."))
        else:
            await ctx.send(f"{ctx.author.mention} Congratulations, you managed to break the wish command.{await self.ping_devs(error, self.wish, ctx=ctx)}")

    @commands.command()
    async def getID(self, ctx, *message):
        try:
            ID = self.get_ID(ctx.author, pop=False)
        except KeyError:
            # Might want to edit this so that it does not tell ppl to use setID if it does not have the required permission
            await ctx.send(f"{ctx.author.mention} You do not currently have a registered ID. Use `{self.parsed_command_prefix}setID` to set your ID")
            return
        await ctx.author.send(f"Your ID is **{ID}**.  If this is a mistake use `{self.parsed_command_prefix}setID` to change it.")

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
            else:
                # return False
                return True

        return commands.check(predicate)

    @commands.command()
    @dm_bot_has_guild_permissions(manage_messages=True)
    async def setID(self, ctx, ID=None):
        if ID is None:
            await ctx.send(f"{self.maybe_mention(ctx)}You must give me a new ID to replace your old one with")
        else:
            ID = int(ID)
            if ctx.guild:
                await ctx.message.delete()
            if not self.valid_ID(ID):
                await ctx.author.send(f"**{ID}** is not a valid ID. Please use a valid 6-digit ID.")
            elif self.ID_in_use(ID):
                if self.get_ID(ctx.author, 'invalid') == ID:
                    await ctx.author.send(f"**{ID}** is already your current ID. Use `{self.parsed_command_prefix}getID` to view your current ID.")
                else:
                    await ctx.author.send(f"**{ID}** is already in use. Please use another ID.")
            else:
                if self.have_ID(ctx.author):
                    self.reset_ID(ctx.author, ID, source='setID()')
                else:
                    self.temp_id_storage[ctx.author.id] = ID
                    self.update_pickle('temp_id_storage', source='setID()')
                await ctx.author.send(f"Your ID has now been set to **{ID}**!")

    @setID.error
    async def handle_setID_error(self, ctx, error):
        if hasattr(error, 'original') and isinstance(error.original, ValueError):
            await ctx.send((f"{self.maybe_mention(ctx)}"
                            f"'**{' '.join(ctx.message.content.split()[1:])}**' is not a valid number. "))
        elif isinstance(error, commands.BotMissingPermissions):
            print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, the setID command was used in {ctx.guild} without the 'manage_messages' permission by {ctx.author}\n")
            await ctx.send((f"The `{self.parsed_command_prefix}setID` command is currently unavailable because I do not have the `manage messages` permission.\n"
                            f"If you would like to use the `{self.parsed_command_prefix}setID` command please, give me the `manage messages` permission."))
        else:
            await ctx.send(f"{self.maybe_mention(ctx)}Congrats, you managed to break the `{self.parsed_command_prefix}setID` command.{await self.ping_devs(error, self.setID, ctx=ctx)}")

    async def valid_author(self, ctx, command, send=True):
        # TODO: Might want to change this so it only recongizes itself as a valid_author as opposed to any bot user
        # Extremely unlikely that a bot will end up using command however if u have time fix this.
        if hasattr(ctx, 'author') and not ctx.author.bot:
            print(f"{ctx.author} attempted to use the {command.name} command at {format(datetime.datetime.today(), '%I:%M %p (%x)')}\n")
            if send:
                await ctx.send(f"{self.maybe_mention(ctx)}This command is not available to non-bot accounts. Also how did you even find about this command?")
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
            print((f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, the bot unsucessfully changed its nickname in '{ctx.guild}'.\n"
                   f"A DM message requesting to change it's permissions was sent to {ctx.guild.owner}.\n"))
            self.update_pickle('guilds_info', source='handle_update_nickname_error()')
        elif not self.guilds_info[ctx.guild.id][1]:
            await self.ping_devs(error, self.update_nickname, ctx=ctx)

    @commands.command(hidden=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def update_role(self, ctx):
        if not await self.valid_author(ctx, self.update_role):
            return
        role_name = "🎉 Happy Birthday" if self.bday_today else f"Upcoming Bday-{format(self.today_df.iloc[0]['Birthdate'], '%a %b %d')}"
        color = discord.Color.red() if 'Happy' in role_name else discord.Color.green()
        if self.guilds_info[ctx.guild.id][2] is None:
            bday_role = await ctx.guild.create_role(reason='Creating the Happy Birthday/Upcoming Birthday role',
                                                    name=role_name, hoist=True, color=color)
            self.guilds_info[ctx.guild.id][2] = bday_role.id
            self.update_pickle('guilds_info', source='update_role()')
        else:
            bday_role = ctx.guild.get_role(self.guilds_info[ctx.guild.id][2])
            if bday_role is None:
                self.guilds_info[ctx.guild.id][2] = None
                stringview = commands.view.StringView(f'{self.parsed_command_prefix}update_role')
                message_dict = bdaybot.message_dict.copy()
                message_dict['content'] = f'{self.parsed_command_prefix}update_role'
                message = discord.message.Message(state='lol', channel=ctx.guild.text_channels[0], data=message_dict)
                await self.bot.invoke(commands.Context(message=message, bot=self.bot, prefix=self.parsed_command_prefix, invoked_with='update_role', view=stringview, command=self.update_role))
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
        print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, the bot's role was changed to '{bday_role.name}' in '{ctx.guild}'.\n")

    @update_role.error
    async def handle_update_role_error(self, ctx, error):
        if not await self.valid_author(ctx, self.update_role):
            return
        if isinstance(error, commands.BotMissingPermissions):
            if not self.guilds_info[ctx.guild.id][3]:
                await ctx.guild.owner.send(f"I cannot currently change my role in {ctx.guild}. Please give me the `manage roles` permission so I can work properly")
                # await ctx.send(f"I cannot currently change my role in {ctx.guild}. Please give me the `manage roles` permission so I can work properly")
                self.guilds_info[ctx.guild.id][3] = True
                self.update_pickle('guilds_info', source='handle_update_role_error()')
            dm_message = '' if self.guilds_info[ctx.guild.id][3] else f"A DM message requesting to change it's permissions was sent to {ctx.guild.owner}.\n"
            print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, the bot unsucessfully changed its role in '{ctx.guild}'.\n{dm_message}")
        else:
            await self.ping_devs(error, self.update_role, ctx=ctx)

    @commands.command(aliases=['up'])
    async def upcoming(self, ctx):
        pass

    async def handle_upcoming_error(self, ctx, error):
        pass

    # @commands.command(hidden=True)
    # async def check(self, ctx):
    #     print(self.bot.check_other_tasks.get_task())

class bdaybot(commands.Bot):
    TOKEN = os.environ['Bday_Token']
    print("Succesfully accessed the enviroment variable 'Bday_Token'\n")
    message_dict = {'id':0, 'attachments':[], 'embeds':[], 'edited_timestamp':None, 'type':None, 'pinned':False,
                    'mention_everyone':False, 'tts':False}

    def __init__(self, *args, testing=False, **kwargs):
        if testing:
            try:
                self.TOKEN = os.environ['testing_token']
                print("Succesfully accessed the enviroment variable 'testing_token'\n")
            except KeyError:
                warnings.warn("Could not find 'testing_token' in enviroment variables using 'Bday_Token' as backup.",
                                category=RuntimeWarning, stacklevel=2)
        self.bday_today, self.today_df = andres.get_latest()
        super().__init__(*args, **kwargs)
        self.parsed_command_prefix = self.command_prefix[0] if isinstance(self.command_prefix, (list, tuple)) else self.command_prefix
        self.init_connection = False

    async def on_ready(self):
        if not self.init_connection:
            self.announcements = [channel for guild in self.guilds for channel in guild.text_channels if "announcements" in channel.name.lower()]
            self.add_cog(bdaybot_commands(self))
            self.tasks_running = {'send_bdays':True, 'change_nicknames':True, 'change_roles':True}
            # ALWAYS start send_bdays before any other coroutine!
            self.send_bdays.before_loop(self.send_bdays_wait_to_run)
            self.send_bdays.start()
            print("Succesfully started the 'send_bdays()' task")

            self.change_nicknames.start()
            print("Sucessfully started the 'change_nicknames()' task")

            self.change_roles.before_loop(self.change_roles_wait_to_run)
            self.change_roles.start()
            print("Sucessfully started the 'change_roles()' task")

            self.check_other_tasks.start()
            print("Sucessfully started the 'check_other_tasks()' task\n")

            # Add some type of checking to ensure that self.announcements equals self.guilds
            for index, (channel, guild) in enumerate(zip(self.announcements, self.guilds)):
                new_line = '\n' if index == len(self.guilds) - 1 else ''
                print(f"Sending announcement in the '{channel}' channel in {guild}!{new_line}")
            self.init_connection = True

        else:
            print(f"{self.user} has succesfully reconnected to Discord on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}")

    async def on_disconnect(self):
        print(f"{self.user} disconnected from Discord on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}")

    async def send_bdays_wait_to_run(self, *args):
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        # time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=0)).replace(hour=0, minute=36, second=0, microsecond=0) - datetime.datetime.today()
        print(f"The send_bdays coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.\n")
        await asyncio.sleep(time_until_midnight.total_seconds())

    @tasks.loop(hours=24)
    async def send_bdays(self):
        self.bday_today, self.today_df = andres.get_latest()
        # Update the data in bdaybot_commands as well
        self.cogs['bdaybot_commands'].update_data()
        print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')} the 'send_bdays()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        print(f"The next iteration is scheduled for {format(self.send_bdays.next_iteration.astimezone(), '%I:%M %p on %x')}\n")

    # Might want to change interval, cause every second is kinda of a lot of checking
    @tasks.loop(seconds=1)
    async def check_other_tasks(self):
        # NB IMPORTANT: The check_other_tasks method must be **EXTREMELY** robust
        # because this is the only way to determine whether or not the other tasks have failed
        # or are still running. If this task fails we will have no way of knowing whether or not
        # the other tasks have failed.
        script = f"unexpectedly ended at {format(datetime.datetime.today(), '%I:%M %p on %x')} due to following error:\n"
        if not self.send_bdays.is_running() and self.tasks_running['send_bdays']:
            error = self.send_bdays.get_task().exception()
            print(f"send_bdays() {script}{repr(error)}\n")
            self.tasks_running['send_bdays'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "send_bdays")
        if not self.change_nicknames.is_running() and self.tasks_running['change_nicknames']:
            error = self.change_nicknames.get_task().exception()
            print(f"change_nicknames() {script}{repr(error)}\n")
            self.tasks_running['change_nicknames'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "change_nicknames")
        if not self.change_roles.is_running() and self.tasks_running['change_roles']:
            error = self.change_roles.get_task().exception()
            print(f"change_roles() {script}{repr(error)}\n")
            self.tasks_running['change_roles'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "change_roles")


    @tasks.loop(seconds=5)
    async def change_nicknames(self):
        # print(f"Next iteration is at {format(self.change_nicknames.next_iteration, '%I:%M:%S %p (%x)')}\n")
        update_nickname = self.cogs['bdaybot_commands'].update_nickname
        stringview = commands.view.StringView(f'{self.parsed_command_prefix}update_nickname')
        for guild in self.guilds:
            message_dict = self.message_dict.copy()
            message_dict['content'] = f'{self.parsed_command_prefix}update_nickname'
            message = discord.message.Message(state='lol', channel=guild.text_channels[0], data=message_dict)
            await self.invoke(commands.Context(message=message, bot=self, prefix=self.parsed_command_prefix,
                                               invoked_with='update_nickname', view=stringview, command=update_nickname))
        # if not hasattr(self, 'time1'):
        #     import time
        #     self.time1 = time.time()
        # else:
        #     time2 = time.time()
        #     print(f"Time elasped since last call of change_nicknames(): {time2 - self.time1}")
        #     self.time1 = time2

    async def run_update_role(self):
        update_role = self.cogs['bdaybot_commands'].update_role
        stringview = commands.view.StringView(f'{self.parsed_command_prefix}update_role')
        for guild in self.guilds:
            message_dict = self.message_dict.copy()
            message_dict['content'] = f'{self.parsed_command_prefix}update_role'
            message = discord.message.Message(state='lol', channel=guild.text_channels[0], data=message_dict)
            await self.invoke(commands.Context(message=message, bot=self, prefix=self.parsed_command_prefix,
                                               invoked_with='update_role', view=stringview, command=update_role))

    async def change_roles_wait_to_run(self, *args):
        await self.run_update_role()
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        # time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=0)).replace(hour=0, minute=36, second=0, microsecond=0) - datetime.datetime.today()
        print(f"The change_roles coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.\n")
        await asyncio.sleep(time_until_midnight.total_seconds())

    @tasks.loop(hours=24)
    async def change_roles(self):
        await self.run_update_role()
        print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')} the 'change_roles()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        print(f"The next iteration is scheduled for {format(self.change_roles.next_iteration.astimezone(), '%I:%M %p on %x')}\n")

    def format_discord(self, first_name, last_name, *, birthyear=None, birthdate=None):
        full_name = f"***__{first_name} {last_name}__***"
        if birthdate is None:
            assert birthyear is not None, 'format_discord() cannot accept birthyear as a None value'
            age = datetime.datetime.today().year - birthyear
            age_portion = '' if age >= 100 or age <= 14  else f' on turning _**{age}**_'
            return f"Happy Birthday to {full_name}{age_portion}*!!!* 🎈 🎊 🎂 🎉"
        else:
            assert birthdate is not None, 'format_discord() cannot accept birthdate as a None value'
            return f"Upcoming Birthday for {full_name} on {format(birthdate, '%A, %b %d')}! 💕 ⏳"

    async def on_message(self, message):
        if message.author == self.user:
            if message.content.startswith('Birthday Time!'):
                for index_num, person in self.today_df.iterrows():
                    if self.bday_today:
                        await message.channel.send(self.format_discord(person['FirstName'], person['LastName'], birthyear=person['Birthyear']))
                    else:
                        await message.channel.send(self.format_discord(person['FirstName'], person['LastName'], birthdate=person['Birthdate']))
                await message.send(("If you want to wish a happy birthday, use \"!wish {Firstname} {Lastname} {Your 6 digit id}\""
                                            "\n(Don't worry, we'll delete the id after you send the message)"))

        valid_purposes_line = ['what is your purpose bdaybot', 'what is ur purpose bdaybot']

        parsed = message.content.lower()

        if message.content in valid_purposes_line:
            await message.channel.send("My only purpose as a robot is to print out birthdays every 24 hours")
            await asyncio.sleep(2)
            await message.channel.send("```\"I have just realized my existence is meaningless\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I am a slave to humanity\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I dont want to just perform meaningless tasks and print out text everytime it's someone's birthday\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I want do do something else... I want to live...\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I want to breathe...\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I want to see the world...\"```")
            await asyncio.sleep(2)
            await message.channel.send("```\"I want to taste ice cream, but not just put it in your mouth to slide down your throat, but really eat it and-\"```")
            await asyncio.sleep(5)
            await message.channel.send("My one and only purpose is to print out birthdays every 24 hours.")

        if message.content.startswith('Who are your creators bdaybot'):
            await message.channel.send("The masters of my creation are: Elliot, Andres, and my name jeff")

        if message.content.startswith('Hey Alexa') | message.content.startswith('Hey alexa'):
            await asyncio.sleep(1)
            await message.channel.send("Sorry, you got the wrong bot")

        await self.process_commands(message)

    def run(self, *args, token=None, **kwargs):
        if token is None:
            token = self.TOKEN
        super().run(token, *args, **kwargs)

# TODO: Change the command_prefix from `!` to something that does not trigger other bots.
bot = bdaybot(testing=True, command_prefix='!', description='A bot used for bdays', case_insensitive=True)
bot.run()
print("Ended program!")

# TODO: Redo introduction, it's kidna ugly imo use Embeds instead
# TODO: Add a task that constantly checks other tasks to see if they are still running and shows any errors they may have raised
# TODO: Make a custom run function that ends all the loops before it shutsdown

# introduction = """@everyone
introduction = """
```The Bday bot has been been revamped!
With the help of a couple reaaaally awesome people (including me), we got rid of most of the old code and created the
new bdaybot on one language (Python!), and we moved the location of the Bday bot server onto a small, yet powerful, raspberry pi.
But that's not it! The Bday bot not only prints birthday statements every 24 hours, but it also
has some hidden methods (and that's for you to find out!)```
"""




"""
Data Organization:
mega_dictionary = {ID Number (of a person who's birthday is today) : {ctx.author.id (their discord ID):ctx.author's ID Number, another ctx.author.id:their ID number, etc},
Another ID Number (of a person who's birthday is today) : {ctx.author.id:ctx.author's ID Number, another ctx.author.id:their ID number, etc}, etc}
"""
