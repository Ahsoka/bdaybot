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
        self.added = True
        super().__init__(*args, **kwargs)
        self.add_cog(simple_cog(self))
    async def on_ready(self):
        self.change_status.start()
        self.change_role.start()
        print('Bot is ready')

    @tasks.loop(seconds=10)
    async def change_status(self):
        print('Changing status :)')
        await client.change_presence(activity=discord.Game(next(self.status)))
        if not hasattr(self, 'time1'):
            self.time1 = time.time()
        else:
            time2 = time.time()
            print(f'Time elasped: {time2 - self.time1}')
            self.time1 = time2
        # try:
        #     print(f'change_role() raised the following exception {self.change_role.get_task().exception()}')
        # except InvalidStateError:
        #     print('change_roles() is still running :)')

    @tasks.loop(seconds=10)
    # @commands.bot_has_permissions(manage_roles=True)
    async def change_role(self):
        # print("Change roles is being called!")
        starship = self.get_guild(675806001231822863)
        me = starship.get_member(722961456311697510)
        assert starship is not None, "change_role() used an invalid ID when accessing starship"
        if not hasattr(self, 'cycle_starship'):
            self.starship_roles = [role for role in starship.roles if 'role' not in role.name]
            # self.cycle_starship = itertools.cycle(self.starship_roles)

        print("Made it this far :)")

        roles = self.starship_roles.copy()[1:]
        print(f"roles={roles}")
        # roles = me.roles.copy()

        try:
            roles.remove(starship.get_role(675950234421166100))
        except ValueError:
            pass
        print(f"self.added={self.added}")
        self.added = not self.added
        if self.added:
            print('removed roles!')
            await me.remove_roles(*roles)
        else:
            print('added roles!')
            await me.add_roles(*roles)



client = simple(command_prefix=command_prefixs)
client.run(os.environ.get('testing_token'))
