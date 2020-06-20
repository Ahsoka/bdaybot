import discord
from discord.ext import commands, tasks
import os
import time
import datetime
import data as andres
import pandas
import numpy
from itertools import cycle

bot = commands.Bot(command_prefix="!", description='A bot used for bdays', case_insensitive=True)
TOKEN = os.environ.get('Bday_Token')

introduction = """@everyone
```The Bday bot has been been revamped!
With the help of a couple reaaaally awesome people (including me), we got rid of most of the old code and created the
new bdaybot on one language (Python!), and we moved the location ofthe Bday bot server onto a small, yet powerful, raspberry pi.
But that's not it! The Bday bot not only prints birthday statements every 24 hours, but it also
has some hidden methods (and that's for you to find out!)```
"""

def get_latest():
    # returns a list of the latest birthay(s)
    andres.update_data()
    andres.bday_df.to_csv('beta_bdays.csv')
    if len(andres.bday_df.loc[andres.bday_df['Birthdate'] == datetime.date.today().replace(minute = 0, second = 0, microsecond = 0, hour = 0)]) != 0:
        latest = andres.bday_df.loc[andres.bday_df['Birthdate'] == datetime.date.today().replace(minute = 0, second = 0, microsecond = 0, hour = 0)]
    else:
        latest = andres.bday_df.loc[andres.bday_df['Birthdate'] == andres.bday_df.iloc[0, 4]]
    return latest['Fullname'].tolist()

def update():
    get_latest()


def update():


@bot.event
async def on_ready():
    global announcements
    announcements = [channel for guild in bot.guilds for channel in guild.text_channels if "announcements" in channel.name.lower()]
    # print_bday.start()
    send_bdays.start()
    change_name.start()
    print(f"""{bot.user} has connected to Discord!""")
    for a in announcements:
        await a.send(introduction)

@tasks.loop(hours = 24)
async def send_bdays():
    global bday_today, today_df, wishlist
    bday_today, today_df = andres.get_latest()
    wishlist = []
    assert len(bot.guilds) == len(announcements), "announcements is not the same length as the bot.guilds"
    for guild, a in zip(bot.guilds, announcements):
        await a.send('Birthday Time!')
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
            await member.add_roles(upRole)

@tasks.loop(seconds=5)
async def change_name():
    if 'names_cycler' not in globals():
        global names_cycler
        names_cycler = cycle((today_df['FirstName'] + " " + today_df['LastName']).tolist())
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
            await message.channel.send("If you want to wish a happy birthday, use `!wish`")

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

@bot.command
async def wish(ctx, message):
    print(ctx, type(ctx))
    print(message, type(message))
    # fullname_list = (today_df['FirstName'] + " " + today_df['LastName']).tolist()
    # for fullname in fullname_list:
    #     if message.content.channel.startswith(fullname):
    #         pass
    #     else:
    #         await message.channel.send("Either you spelled the name wrong, or its not even this person's birthay, idk my code is bad")
    await bot.channel.send(message)
    

@bot.command()
async def echo(ctx, *, content:str):
    await ctx.send(content)

bot.run(TOKEN)
