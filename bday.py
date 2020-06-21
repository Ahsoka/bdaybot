import discord
from discord.ext import commands, tasks
import os
import time
import datetime
import data as andres
import pandas
import dill, pickle
import warnings
import itertools

bot = commands.Bot(command_prefix="!", description='A bot used for bdays', case_insensitive=True)
TOKEN = os.environ.get('Bday_Token')
print("Succesfully accessed the enviroment variable 'Bday_Token'\n")

# introduction = """@everyone
introduction = """
```The Bday bot has been been revamped!
With the help of a couple reaaaally awesome people (including me), we got rid of most of the old code and created the
new bdaybot on one language (Python!), and we moved the location of the Bday bot server onto a small, yet powerful, raspberry pi.
But that's not it! The Bday bot not only prints birthday statements every 24 hours, but it also
has some hidden methods (and that's for you to find out!)```
"""

def show_slots(self):
    returning = dict()
    for slot in self.__slots__:
        try:
            returning[slot] = getattr(self, slot)
            if not dill.pickles(returning[slot]):
                print(f"returning[{slot}], type = {(returning[slot], type(returning[slot]))}")
        except AttributeError:
            pass
    return returning


discord.Member.show_slots = show_slots


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!\n")
    global announcements
    announcements = [channel for guild in bot.guilds for channel in guild.text_channels if "announcements" in channel.name.lower()]
    send_bdays.start()
    print("Succesfully started 'send_bdays()' task")
    change_name.start()
    print("Sucessfully started 'change_name()' task\n")
    for index, (channel, guild) in enumerate(zip(announcements, bot.guilds)):
        print(f"Sending announcement in the '{channel}' channel in {guild}!")
        if index == len(bot.guilds) - 1:
            print()
        await channel.send(introduction)

@tasks.loop(hours=24)
async def send_bdays():
    global bday_today, today_df
    bday_today, today_df = andres.get_latest()

    for guild, a in zip(bot.guilds, announcements):
        # await a.send('Birthday Time!')
        for role in guild.roles:
            if "happy birthday" in role.name.lower():
                bdayRole = role
            elif "upcoming bday" in role.name.lower():
                upRole = role
        member = guild.me
        await member.remove_roles(bdayRole, upRole)
        if bday_today:
            await member.add_roles(bdayRole)
        else:
            server = bot.get_server(guild.id)
            await bot.edit_role(server = server, role = upRole, name = "Upcoming Bday")
            await member.add_roles(upRole)
            

@tasks.loop(seconds=5)
async def change_name():
    if 'names_cycler' not in globals():
        global names_cycler
        names_cycler = itertools.cycle((today_df['FirstName'] + " " + today_df['LastName']).tolist())
    for guild in bot.guilds:
        await guild.me.edit(nick=next(names_cycler))

def format_discord(first_name, last_name, *, birthyear=None, birthdate=None):
    full_name = f"***__{first_name} {last_name}__***"
    if birthdate is None:
        assert birthyear is not None, 'format_discord() cannot accept birthyear as a None value'
        age = datetime.datetime.today().year - birthyear
        age_portion = '' if age >= 100 or age <= 14  else f' on turning _**{age}**_'
        return f"Happy Birthday to {full_name}{age_portion}*!!!* 🎈 🎊 🎂 🎉"
    else:
        assert birthdate is not None, 'format_discord() cannot accept birthdate as a None value'
        return f"Upcoming Birthday for {full_name} on {format(birthdate, '%A, %b %d')}! 💕 ⏳"

@bot.event
async def on_message(message):
    if message.author == bot.user:
        if message.content.startswith('Birthday Time!'):
            for index_num, person in today_df.iterrows():
                if bday_today:
                    await message.channel.send(format_discord(person['FirstName'], person['LastName'], birthyear=person['Birthyear']))
                else:
                    await message.channel.send(format_discord(person['FirstName'], person['LastName'], birthdate=person['Birthdate']))
            await message.channel.send(("If you want to wish a happy birthday, use \"!wish {Firstname} {Lastname} {Your 6 digit id}\""
                                        "\n(Don't worry, we'll delete the id after you send the message)"))

    valid_purposes_line = ['what is your purpose bdaybot', 'what is ur purpose bdaybot']

    parsed = message.content.lower()

    if message.content in valid_purposes_line:
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

"""
Data Organization:
mega_dictionary = {ID Number (of a person who's birthday is today) : {ctx.author:ctx.author's ID Number, another ctx.author:their ID number, etc},
Another ID Number (of a person who's birthday is today) : {ctx.author:ctx.author's ID Number, another ctx.author:their ID number, etc}, etc}
"""

def have_ID(author):
    for key in bday_dict:
        for previous_author in bday_dict[key]:
            if author == previous_author:
                return True
    return author in temp_id_storage

def get_ID(author, default=None):
    possible = temp_id_storage.pop(author, None)
    if possible is not None:
        return possible
    for key in bday_dict:
        if author in bday_dict[key]:
            return bday_dict[key][author]
    if default is None:
        raise KeyError(f"Could not find {author} in 'bday_dict'")
    return default

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

def name_to_proper(name, dataframe, default=None, mute=False):
    ID = name_to_ID(name, dataframe, default=default, mute=mute)
    if ID == default:
        return default
    return dataframe.loc[ID]["FirstName"] + " " + dataframe.loc[ID]["LastName"]

def valid_ID(ID, *, dataframe=andres.official_student_df):
    if isinstance(dataframe, (list, tuple)):
        bool_list = [df.index.isin([ID].any(axis=None)) for df in dataframe]
        return any(bool_list)

    return dataframe.index.isin([ID]).any(axis=None)

def apostrophe(name):
    return "'" if name[-1] == "s" else "'s"

def get_bday_names(punctation=True):
    # TODO: This is broken, fixed for punctation/grammar!
    script = ''
    for counter, (_, series) in enumerate(today_df.iterrows()):
        fullname = series['FirstName'] + " " + series['LastName']
        script += f'{fullname}{apostrophe(fullname) if punctation else ""}' if counter == len(today_df) - 1 else fullname + " and "
    return script

def wished_before(author, wishee_ID):
    return author in bday_dict[wishee_ID]

@bot.command()
@commands.bot_has_permissions(manage_messages=True)
async def wish(ctx, *message):
    print(f"ctx.author.show_slots() = {ctx.author.show_slots()}")

    if 'bday_dict' not in globals():
        global bday_dict, temp_id_storage
        # try:
        #     with open('bday_dict.dill', mode='rb') as file:
        #         bday_dict = dill.load(file)
        # except FileNotFoundError:
        #     bday_dict = dict(((id, dict()) for id, _ in today_df.iterrows()))
        bday_dict = dict(((id, dict()) for id, _ in today_df.iterrows()))
        temp_id_storage = dict()

    if bday_today:
        try:
            studentID = int(message[-1])
        except (IndexError, ValueError):
            if not have_ID(ctx.author):
                await ctx.send(f"{ctx.author.mention} You are first-time wisher. You must include your ID at the end of the wish command to send a wish.")
                return

        studentID_defined = 'studentID' in locals()

        name_not_included = False

        if studentID_defined:
            await ctx.message.delete()
            if have_ID(ctx.author):
                wisher_ID = get_ID(ctx.author)
                if wisher_ID != studentID:
                    await ctx.send((f"{ctx.author.mention} The ID you submitted does not match the ID you submitted previously.\n"
                                    "Please use the same ID you have used in the past or don't use an ID at all"))
                    return
                await ctx.send((f"{ctx.author.mention} Once you've submitted your ID once, you do not need to submitted it again to send wishes!"))

            else:
                if not valid_ID(studentID):
                    await ctx.send(f'{ctx.author.mention} Your ID is invalid, please use a valid 6-digit ID')
                    return
                elif not valid_ID(studentID, dataframe=andres.bday_df):
                    await ctx.send((f"Yay! {ctx.author.mention} Your ID is valid, however, you are not in the bdaybot's birthday database.\n"
                                    "Add yourself to database here ⬇\n"
                                    "**http://drneato.com/Bday/Bday2.php**"))
                temp_id_storage[ctx.author] = studentID
            if len(message) > 1:
                name = " ".join(message[:-1])
            else:
                name_not_included = True
        else:
            if len(message) > 0:
                name = " ".join(message)
            else:
                name_not_included = True

        if name_not_included and len(today_df) > 1:
            await ctx.send((f"{ctx.author.mention} Today is {get_bday_names()} birthday\n"
                            "You must specify who you want wish a happy birthday!"))
            return
        elif name_not_included:
            name = today_df.iloc[0]['FirstName'] + ' ' + today_df.iloc[0]['LastName']
        old_name = name
        name = name.title()
        # The `wishee` is the person who is receiving the wish
        wishee_ID_number = name_to_ID(name, today_df, 'invalid')
        proper_name = name_to_proper(name, today_df, name_to_proper(name, andres.bday_df, name.title(), mute=True))

        if wishee_ID_number == 'invalid' or proper_name == 'invalid':
            if name_to_ID(name, pandas.concat([andres.bday_df[['FirstName', 'LastName']], (andres.bday_df['FirstName'] + " " + andres.bday_df["LastName"])], axis='columns'), 'invalid', mute=True) == 'invalid':
                await ctx.send(f"{ctx.author.mention} '{old_name}' is not a name in the birthday database!")
            else:
                await ctx.send(f"{ctx.author.mention} Today is not {proper_name}{apostrophe(proper_name)} birthday.\nIt is {get_bday_names()} birthday today. Wish them a happy birthday!")
            return

        if wished_before(ctx.author, wishee_ID_number):
            await ctx.send(f"{ctx.author.mention} You cannot wish {proper_name} a happy birthday more than once! Try wishing someone else a happy birthday!")
            return

        if have_ID(ctx.author):
            bday_dict[wishee_ID_number][ctx.author] = get_ID(ctx.author)
        else:
            bday_dict[wishee_ID_number][ctx.author] = studentID

        await ctx.send((f"{ctx.author.mention} Congrats! 🎈 ✨ 🎉\n"
                        f"You wished ***__{proper_name}__*** a happy birthday!"))

    else:
        script = (f"{ctx.author.mention} You cannot use the `!wish` command if it is no one's birthday today.\n"
                  "However, it will be "
                  f"{get_bday_names()} birthday on {format(today_df.iloc[0]['Birthdate'], '%A, %B %d')}")
        await ctx.send(script)

# @bot.command(aliases=['up'])
# async def upcoming(ctx, *message):
#

bot.run(TOKEN)
