import discord
from discord.ext import commands
import os
import time
import schedule
import data
import pandas

bot = commands.Bot(command_prefix = "!", description = description)
# Use enviroment variables to access the Discord token so it's not visible in the code
TOKEN = os.environ.get('Bday_Token')
assert TOKEN is not None, ("The Discord token could not be found in environment variables.\n"
                        "See this video on how add the url to the environment variables (name the enviroment variable 'bday_data_URL' without quotes): "
                        f"{data.windows_vid_url}" if 'nt' in os.name else f"{data.unix_vid_url}")

def update():


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    update()

@bot.command()
async def upcoming(ctx):
    await ctx.send(f"Hello")


bot.run(TOKEN)
