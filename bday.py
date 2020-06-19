import discord
from discord.ext import commands, tasks
import os
import time
import datetime
# import schedule
import data as andres
import pandas
import numpy
# from concurrent.futures import ThreadPoolExecutor
from itertools import cycle

# multi = ThreadPoolExecutor()


bot = commands.Bot( command_prefix="!", description='A bot used for bdays', case_insensitive=True)
TOKEN = os.environ.get('Bday_Token')

introduction = """
```The Bday bot has been been revamped!
With the help of a couple reaaaally awesome people (including me), we got rid of most of the old code and created the
new bdaybot on one language (Python), and we moved the location ofthe Bday bot server onto a small, yet powerful, raspberry pi.
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
    # print_bday.start()
    send_bdays.start()
    change_name.start()
    print(f"""{bot.user} has connected to Discord!""")
    # await channel.send(introduction)

@tasks.loop(hours = 24)
async def send_bdays():
    for guild in bot.guilds:
        await guild.text_channels[2].send('Birthday Time!')

@tasks.loop(minutes = 5)
async def change_name():
    await bot.change_presence(activity=discord.Game('jack'))

def format_discord(first_name, last_name, *, birthyear=None, birthdate=None):
    if birthdate is None:
        assert birthyear is not None, 'format_discord() cannot accept birthyear as a None value'
        age = datetime.datetime.today().year - birthyear
        age_portion = '' if age >= 100 or age <= 14  else f' on turning _**{age}**_'
        return f"Happy Birthday to _**{first_name + last_name}**_{age_portion}*!!!* 🎈🎊🎂🎉"
    else:
        assert birthdate is not None, 'format_discord() cannot accept birthdate as a None value'
        return f"Upcoming Birthday for _**{first_name + last_name}**_ on {birthdate.format("%A, %b, %d")}! 💕⏳"

@bot.event
async def on_message(message):
    if message.author == bot.user:
        if message.content.startswith('Birthday Time!'):
            andres.update_data()
            top_person = andres.bday_df.iloc[0]
            if top_person['Timedelta'] == datetime.timedelta():
                for index_num, person in andres.bday_df[andres.bday_df['Timedelta'] == datetime.timedelta()].iterrows():
                    await message.channel.send(format_discord(person['FirstName'], person['LastName'], birthyear=person['Birthyear']))
            else:
                other_ppl_df = andres.bday_df[andres.bday_df['Timedelta'] == top_person['Timedelta']]
                for index_num, person in other_ppl_df.iterrows():
                    await message.channel.send(format_discord(person['FirstName'], person['LastName'], birthdate=person['Birthdate']))

    if message.content.startswith('What is your purpose bdaybot') | message.content.startswith('What is ur purpose bdaybot') | message.content.startswith('what is ur purpose bdaybot') | message.content.startswith('what is your purpose bdaybot'):
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

        if message.content.channel.startswith('Hey Alexa') | message.content.channel.startswith('Hey alexa'):
            time.sleep(1)
            await message.channel.send("Sorry, you got the wrong bot")

# andres.bday_df = pandas.read_csv('beta_bdays.csv', index_col = 'StuID')
# andres.bday_df['Birthdate'], andres.bday_df['Timedelta'] = pandas.to_datetime(andres.bday_df['Birthdate']), pandas.to_timedelta(andres.bday_df['Timedelta'])
# print(andres.bday_df)
# print(andres.bday_df.columns)
# with ThreadPoolExecutor() as something:
#     something.submit(type(bot).run, bot, TOKEN)
#     updated = False
#     while True:
#         # make sure to update under and overtime
#         undertime = datetime.datetime.today().replace(hour=20, minute=0, second=0, microsecond=0)
#         overtime = datetime.datetime.today().replace(hour=23, minute=0, second=0, microsecond=0)
#         # print('okboomer')
#         if (datetime.datetime.now() >= undertime and datetime.datetime.now() <= overtime) and not updated:
#             andres.get_latest()
#             channel = discord.utils.get(server.channels, name="|announcements", type="ChannelType.text")
#             channel.send('hello')
#             updated = True
#             print('yee')
#         elif (datetime.datetime.now() > overtime or datetime.datetime.now() < undertime):
#             # print('this didnt work loser')
#             updated = False
bot.run(TOKEN)
