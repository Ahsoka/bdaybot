import discord
from discord.ext import commands, tasks
import itertools
import os
import time
import random

command_prefixs = ['.', '!']
# client = commands.Bot(command_prefix=command_prefixs)
# client.add_cog(simple_cog(client))

class simple_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx, *args):
        if 'uh-oh' in args:
            raise RuntimeError('Oh-no!')
        print("test was triggered")
        self.apple = random.choice(['apple', 'manzana', '苹果'])
        print(f"self.apple was set to {self.apple}")
        await ctx.send(" ".join(args))

    @test.error
    async def error_test(self, ctx, error):
        await ctx.send(f"Succesfully excepted error ➡ {error}")

class simple(commands.Bot):
    status = itertools.cycle(['Status 1', 'Status 2'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_cog(simple_cog(self))
    async def on_ready(self):
        self.change_status.start()
        print('Bot is ready')

    @tasks.loop(seconds=10)
    async def change_status(self):
        print('Changing status :)')
        await client.change_presence(activity=discord.Game(next(self.status)))
        if 'time1' not in globals():
            global time1
            time1 = time.time()
        else:
            time2 = time.time()
            print(f'Time elasped: {time2 - time1}')
            time1 = time2



client = simple(command_prefix=command_prefixs)
client.run(os.environ.get('testing_token'))
