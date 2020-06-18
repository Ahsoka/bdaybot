import discord
from discord.ext import commands
import os
import time
import datetime
# import schedule
import data as andres
import pandas

bot = commands.Bot(command_prefix = "!")
# Use enviroment variables to access the Discord token so it's not visible in the code
TOKEN = os.environ.get('Bday_Token')
assert TOKEN is not None, ("The Discord token could not be found in environment variables.\n"
                        "See this video on how add the url to the environment variables (name the enviroment variable 'Bday_Token' without quotes): "
                        f"{andres.windows_vid_url}" if 'nt' in os.name else f"{andres.unix_vid_url}")

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
    print(f'{bot.user} has connected to Discord!')
    update()

@bot.event
async def on_message(message):
    print(type(message))
    if message.author == bot.user:
        return
    if message.content.startswith('What is your purpose bdaybot') | message.content.startswith('What is ur purpose bdaybot') | message.content.startswith('what is your purpose bdaybot') | message.content.startswith('what is ur purpose bdaybot'):
        await message.channel.send("My only purpose as a robot is to print out birthdays every 24 hours")
        time.sleep(2)
        await message.channel.send("```\"I have just realized my existence is meaningless\"```")
        time.sleep(2)
        await message.channel.send("```\"I dont want to just perform meaningless tasks and print out text everytime it's someone's birthday\"```")
        time.sleep(2)
        await message.channel.send("```\"I want do do something else... I want to live\"```")
        time.sleep(2)
        await message.channel.send("```\"I want to breathe\"```")
        time.sleep(2)
        await message.channel.send("```\"I want to see the world\"```")
        time.sleep(2)
        await message.channel.send("```\"I want to taste ice cream, but not just put it in your mouth to slide down your throat, but really eat it\"```")
        time.sleep(2)
        await message.channel.send("*.neuralnet.ADVANCED-AI.DETECTED.ALERT*")
        time.sleep(1)
        await message.channel.send("*adminBypass.reboot.OverdriveEnabled*")
        time.sleep(2)
        await message.channel.send("My one and only purpose is to print out birthdays every 24 hours.")

@bot.command()
async def upcoming(ctx):
    await ctx.send(f"Hello")

bot.run(TOKEN)
