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
    names, fname, lname = [], [], []

    andres.update_data()
    andres.bday_df.to_csv('beta_bdays.csv')
    if len(fname) != 0:
        latest = andres.bday_df.loc[andres.bday_df['Birthdate'] == datetime.date.today().strftime("%Y-%m-%d")]
    else:
        latest2 = andres.bday_df.loc[andres.bday_df['Birthdate'] == andres.bday_df.iloc[1, 4]]
    fname = latest['FirstName'].tolist()
    lname = latest['LastName'].tolist()
    for x in range(len(fname)):
        names.append(f"{fname[x]} {lname[x]}")
    return names

def update():
    get_latest()


def update():


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    update()

@bot.command()
async def upcoming(ctx):
    await ctx.send(f"Hello")


bot.run(TOKEN)
