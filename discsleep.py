import discord
import time
import os
from discord.ext import commands, tasks
import pandas as pd

bot = commands.Bot(command_prefix='*')

@bot.event
async def on_ready():
    bot.diction = {'TimeElapsed': []}
    printtime.start()
    write.start()
    print('Online')

@tasks.loop(seconds=5)
async def printtime():
    if not hasattr(bot, 'time1'):
        bot.time1 = time.time()
    else:
        time2 = time.time()
        bot.diction['TimeElapsed'].append(time2 - bot.time1)
        print(f"Time elasped since last call of change_nicknames(): {time2 - bot.time1}\n")
        print(printtime.current_loop)
        bot.time1 = time2

@tasks.loop(hours=1)
async def printtime2():
    if not hasattr(bot, 'time1'):
        bot.time1 = time.time()
    else:
        time2 = time.time()
        bot.diction['TimeElapsed'].append(time2 - bot.time1)
        print(f"Time elasped since last call of change_nicknames(): {time2 - bot.time1}\n")
        print(printtime.current_loop)
        bot.time1 = time2

@bot.command()
async def checker(ctx):
    print(repr(write.get_task()))

@tasks.loop(seconds=100)
async def write():
    time_data = pd.DataFrame(bot.diction)
    time_data['Difference'] = time_data['TimeElapsed'].apply(lambda x: x - 5)
    time_data.to_csv('time_data.csv')

bot.run('NzI4MDU4MDQ5ODk3NDMxMTMy.Xv03CQ.fdnY69h3tZ1CCMbPvKKC9VwitHU')
