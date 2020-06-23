import discord
from discord.ext import commands, tasks
import os
import datetime
import data as andres
import pandas
import pickle
import warnings
import itertools
import time
import asyncio

dev_discord_ping = {'Andres':'<@388899325885022211>', 'Elliot':'<@349319578419068940>', 'Ryan':'<@262676325846876161>'}

class bdaybot_commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parsed_command_prefix = self.bot.parsed_command_prefix
        self.bday_today, self.today_df = self.bot.bday_today, self.bot.today_df
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

    def get_ID(self, author, default=None):
        try:
            possible = self.temp_id_storage.pop(author.id)
            self.update_pickle('temp_id_storage', source='get_ID()')
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

    def update_pickle(self, updating, source=None):
        valid_updating = ['bday_dict', 'temp_id_storage']
        assert updating in valid_updating, ("update_pickle() received a invalid value for updating, "
                                            f"the acceptable values for updating are '{valid_updating[0]}' and {valid_updating[1]}")
        with open(f'{updating}.pickle', mode='wb') as file:
            pickle.dump(getattr(self, updating), file)
        extra_info = '' if source is None else f" [{source}]"
        print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')} '{updating}.pickle' was sucessfully saved to.{extra_info}\n")

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
            print(f"{ctx.author} used the wish command in a DM on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}")
            await ctx.send(f"The `{self.parsed_command_prefix}wish` command is not currently available in DMs. Please try using it in a server with me.")
        elif isinstance(error, commands.errors.BotMissingPermissions):
            print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')}, the wish command was used in {ctx.guild} without the 'manage_messages' permission by {ctx.author}\n")
            await ctx.send((f"The `{self.parsed_command_prefix}wish` command is currently unavailable because I do not have the `manage messages` permission.\n"
                            f"If you would like to use the `{self.parsed_command_prefix}wish` command please, give me the `manage messages` permission."))
        else:
            print(f"{ctx.author} caused the following error in {ctx.guild}, on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}:\n{error}\n")
            await ctx.send((f"{ctx.author.mention} Congratulations, you managed to break the wish command. "
                            f"{dev_discord_ping['Andres']}, {dev_discord_ping['Elliot']}, or {dev_discord_ping['Ryan']} fix this!"))

    @commands.command()
    async def getID(self, ctx, *message):
        try:
            ID = self.get_ID(ctx.author)
        except KeyError:
            # Might want to edit this so that it does not tell ppl to use setID if it does not have the required permission
            await ctx.send(f"{ctx.author.mention} You do not currently have a registered ID. Use `{self.parsed_command_prefix}setID` to set your ID")
            return
        await ctx.author.send(f"Your ID is {ID}.  If this is a mistake, use `{self.parsed_command_prefix}setID` to change it.")

    # @commands.command()
    # async def setID(self, ctx, *messages):
    #     for message in messages:
    #         try:
    #             ID = int(message)
    #             break
    #         except ValueError:
    #             pass
    #     if len(messages) > 1:
    #         await ctx.author.send(f"You gave me multiple arguments, I am using {ID} as your new ID, if you made a mistake use `{self.parsed_command_prefix}setID` again")



class bdaybot(commands.Bot):
    TOKEN = os.environ['Bday_Token']
    print("Succesfully accessed the enviroment variable 'Bday_Token'\n")

    def __init__(self, *args, testing=False, **kwargs):
        if testing:
            try:
                self.TOKEN = os.environ['testing_token']
            except KeyError:
                warnings.warn("Could not find 'testing_token' in enviroment variables using 'Bday_Token' as backup.",
                                category=RuntimeWarning, stacklevel=2)
        self.bday_today, self.today_df = andres.get_latest()
        self.names_cycler = itertools.cycle((self.today_df['FirstName'] + " " + self.today_df['LastName']).tolist())
        super().__init__(*args, **kwargs)
        self.parsed_command_prefix = self.command_prefix[0] if isinstance(self.command_prefix, (list, tuple)) else self.command_prefix
        self.add_cog(bdaybot_commands(self))
        assert not hasattr(self, 'connected'), "__init__() when setting self.connected another attribute named self.connected was detected"
        self.connected = False
        assert not hasattr(self, 'disconnected'), "__init__() when setting self.disconnected another attribute named self.disconnected was detected"
        self.disconnected = True

    async def on_ready(self):
        if self.disconnected:
            self.disconnected = False

        if not self.connected:
            self.announcements = [channel for guild in self.guilds for channel in guild.text_channels if "announcements" in channel.name.lower()]
            print(f"{self.user} has connected to Discord!\n")
            # ALWAYS start send_bdays before any other coroutine!
            self.send_bdays.before_loop(self.send_bdays_wait_to_run)
            self.send_bdays.start()

            print("Succesfully started 'send_bdays()' task\n")
            self.change_name.start()
            print("Sucessfully started 'change_name()' task\n")

            # Add some type of checking to ensure that self.announcements equals self.guilds
            for index, (channel, guild) in enumerate(zip(self.announcements, self.guilds)):
                print(f"Sending announcement in the '{channel}' channel in {guild}!")
                if index == len(self.guilds) - 1:
                    print()
            self.disconnected = False
            self.connected = True
        else:
            print(f"{self.user} has succesfully reconnected to Discord on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}")

    async def on_disconnect(self):
        self.disconnected = True
        print(f"{self.user} disconnected from Discord on {format(datetime.datetime.today(), '%b %d at %I:%M %p')}")


    async def send_bdays_wait_to_run(self, *args):
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        # time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=0)).replace(hour=0, minute=36, second=0, microsecond=0) - datetime.datetime.today()
        print(f"The send_bdays coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.\n")
        await asyncio.sleep(time_until_midnight.total_seconds())

    @tasks.loop(hours=24)
    async def send_bdays(self):
        self.bday_today, self.today_df = andres.get_latest()
        self.names_cycler = itertools.cycle((self.today_df['FirstName'] + " " + self.today_df['LastName']).tolist())

        print(f"At {format(datetime.datetime.today(), '%I:%M %p (%x)')} the 'send_bdays()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone; which caused much confusion
        # It now converted to the local time zone automatically
        print(f"The next iteration is schedule for {format(send_bdays.next_iteration.astimezone(), '%I:%M %p on %x')}\n")
        # for guild, a in zip(self.guilds, announcements):
        #     # await a.send('Birthday Time!')
        #     for role in guild.roles:
        #         if "happy birthday" in role.name.lower():
        #             bdayRole = role
        #         elif "upcoming bday" in role.name.lower():
        #             upRole = role
        #     member = guild.me
        #     await member.remove_roles(bdayRole, upRole)
        #     if bday_today:
        #         await member.add_roles(bdayRole)
        #     else:
        #         server = self.get_server(guild.id)
        #         await self.edit_role(server=server, role=upRole, name="Upcoming Bday")
        #         await member.add_roles(upRole)

    @tasks.loop(seconds=5)
    async def change_name(self):
        # print(f"Next iteration is at {format(self.change_name.next_iteration, '%I:%M:%S %p (%x)')}\n")
        new_name = next(self.names_cycler)
        for guild in self.guilds:
            await guild.me.edit(nick=new_name)

        # if not hasattr(self, 'time1'):
        #     self.time1 = time.time()
        # else:
        #     time2 = time.time()
        #     print(f"Time elasped since last call of change_name(): {time2 - self.time1}")
        #     self.time1 = time2

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
                await message.channel.send(("If you want to wish a happy birthday, use \"!wish {Firstname} {Lastname} {Your 6 digit id}\""
                                            "\n(Don't worry, we'll delete the id after you send the message)"))

        valid_purposes_line = ['what is your purpose bdaybot', 'what is ur purpose bdaybot']

        parsed = message.content.lower()

        if message.content in valid_purposes_line:
            # TODO: Replace time.sleep with asyncio.sleep
            await message.channel.send("My only purpose as a robot is to print out birthdays every 24 hours")
            time.sleep(2)
            await message.channel.send("```\"I have just realized my existence is meaningless\"```")
            time.sleep(2)
            await message.channel.send("```\"I am a slave to humanity\"```")
            time.sleep(2)
            await message.channel.send("```\"I dont want to just perform meaningless tasks and print out text everytime it's someone's birthday\"```")
            time.sleep(2)
            await message.channel.send("```\"I want do do something else... I want to live...\"```")
            time.sleep(2)
            await message.channel.send("```\"I want to breathe...\"```")
            time.sleep(2)
            await message.channel.send("```\"I want to see the world...\"```")
            time.sleep(2)
            await message.channel.send("```\"I want to taste ice cream, but not just put it in your mouth to slide down your throat, but really eat it and-\"```")
            time.sleep(2)
            await message.channel.send("*.neuralnet.ADVANCED-AI.DETECTED.ALERT*")
            time.sleep(1)
            await message.channel.send("*adminBypass.reboot.OverdriveEnabled*")
            time.sleep(5)
            await message.channel.send("My one and only purpose is to print out birthdays every 24 hours.")

        if message.content.startswith('Who are your creators bdaybot'):
            await message.channel.send("The masters of my creation are: Elliot, Andres, and my name jeff")

        if message.content.startswith('Hey Alexa') | message.content.startswith('Hey alexa'):
            time.sleep(1)
            await message.channel.send("Sorry, you got the wrong bot")
        await bot.process_commands(message)

    def run(self, *args, token=None, **kwargs):
        if token is None:
            token = self.TOKEN
        super().run(token, *args, **kwargs)


bot = bdaybot(testing=True, command_prefix='!', description='A bot used for bdays', case_insensitive=True)
bot.run()

# TODO: Redo introduction, it's kidna ugly imo use Embeds instead
# introduction = """@everyone
introduction = """
```The Bday bot has been been revamped!
With the help of a couple reaaaally awesome people (including me), we got rid of most of the old code and created the
new bdaybot on one language (Python!), and we moved the location of the Bday bot server onto a small, yet powerful, raspberry pi.
But that's not it! The Bday bot not only prints birthday statements every 24 hours, but it also
has some hidden methods (and that's for you to find out!)```
"""

# TODO: Add a task that constantly checks other tasks to see if they are still running and shows any errors they may have raised

"""
Data Organization:
mega_dictionary = {ID Number (of a person who's birthday is today) : {ctx.author.id (their discord ID):ctx.author's ID Number, another ctx.author.id:their ID number, etc},
Another ID Number (of a person who's birthday is today) : {ctx.author.id:ctx.author's ID Number, another ctx.author.id:their ID number, etc}, etc}
"""
