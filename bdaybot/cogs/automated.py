import asyncio
import discord
import logging
import datetime
import itertools
from discord.ext import commands, tasks
from ..utils import fake_ctx, ping_devs
from ..order_from_amazon import order_product
from sqlalchemy.ext.asyncio import AsyncSession
from .. import values, config, engine, postgres_engine
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from ..tables import Guild as guilds, DiscordUser as discord_users, StudentData as student_data

logger = logging.getLogger(__name__)

cushion_delay = 5

class AutomatedTasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = AsyncSession(bind=engine, binds={student_data: postgres_engine})

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.send_bdays.is_running():
            self.send_bdays.before_loop(self.wait_to_run)
            self.send_bdays.start()
            logger.info("Succesfully started the 'send_bdays()' task.")

        if config.ASIN and not self.order_from_amazon.is_running():
            self.order_from_amazon.before_loop(self.wait_to_run)
            self.order_from_amazon.start()
            logger.info("Succesfully started the 'order_from_amazon()' task.")

        if not self.send_DM_message.is_running():
            self.send_DM_message.before_loop(self.wait_to_run)
            self.send_DM_message.start()
            logger.info("Succesfully started the 'send_DM_message()' task.")

        if not self.change_nicknames.is_running():
            self.change_nicknames.start()
            logger.info("Succesfully started the 'change_nicknames()' task.")

        if not self.change_roles.is_running():
            self.change_roles.start()
            logger.info("Succesfully started the 'change_roles()' task.")

        if not self.update_cycler.is_running():
            self.update_cycler.start()
            logger.info("Succesfully started the 'update_cycler()' task.")

    async def wait_to_run(self, *args):
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)) \
                              .replace(hour=0, minute=0, second=0, microsecond=0) \
                              - datetime.datetime.today()
        logger.info(f"The send_bdays coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.")
        await asyncio.sleep(time_until_midnight.total_seconds() + cushion_delay)

    @tasks.loop(hours=24)
    async def send_bdays(self):
        self.new_day = True
        if values.bday_today:
            for guild in self.bot.guilds:
                sql_guild = await self.session.run_sync(lambda session: session.get(guilds, guild.id))
                if sql_guild is None:
                    # TODO: Call function in housekeeping
                    continue
                channel = guild.get_channel(sql_guild.announcements_id)
                if channel is None:
                    logger_message = f"The bot failed to find the announcements channel in {guild}."
                    if config.DM_owner:
                        await guild.owner.send(("While trying to send the birthday message, "
                                                f"I failed to find the announcements channel in **{guild}**. "
                                                f"Please use `{self.bot.parsed_command_prefix}setannouncements` "
                                                "to set the announcements channel so I can send a birthday message!"))
                        logger_message += f" A message has been sent to {guild.owner}."
                    logger.warning(logger_message)
                    continue

                for stuid, series in values.today_df.iterrows():
                    # TODO: Add some different styles for the bday message
                    full_name = f"***__{series['FirstName']} {series['LastName']}__*** "
                    student = await self.session.run_sync(lambda session: session.get(student_data, stuid))
                    user = None if student.discord_user is None else student.discord_user.mention
                    mention = '' if user is None else f' {user.mention}'
                    age = datetime.datetime.today().year - series['Birthyear']
                    age_portion = ' 🎂 🎉' if age >= 100 or age <= 14 \
                                  else f'\nCongratulations on turning _**{age}**_ 🎂 🎉'
                    embed = discord.Embed(description=f"Happy Birthday to {full_name}{mention}🎈 🎊{age_portion}") \
                            .set_author(name='Happy Birthday! 🎉') # TODO: Add icon url!
                    await channel.send(embed=embed)

        logger.info(f"The 'send_bdays()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info(f"The next iteration is scheduled for {format(self.send_bdays.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}.")

    @tasks.loop(hours=24)
    async def order_from_amazon(self):
        if values.bday_today:
            for stuid, bday_person in values.today_df.iterrows():
                if bday_person['AddrLine1']:
                    order_product(ASIN=config.ASIN,
                                  FULLNAME=bday_person['FirstName'] + ' ' + bday_person['LastName'],
                                  ADDRESS_LINE_ONE=bday_person['AddrLine1'],
                                  ADDRESS_LINE_TWO=bday_person['AddrLine2'],
                                  CITY=bday_person['City'],
                                  STATE=bday_person['State'],
                                  ZIPCODE=str(int(bday_person['Zipcode'])),
                                  place_order=config.place_order)

    @tasks.loop(hours=24)
    async def send_DM_message(self):
        if values.bday_today:
            for stuid, series in values.today_df.iterrows():
                student = await self.session.run_sync(lambda session: session.get(student_data, stuid))
                if student.discord_user is not None:
                    user = await self.bot.get_user(student.discord_user.discord_user_id)
                    await user.send((f"Happy birthday from me, {self.bot.user.mention}, "
                                      "and all the developers of the bdaybot! Hope you have an awesome birthday!"))

    @tasks.loop(seconds=5)
    async def change_nicknames(self):
        if len(values.today_df) > 1 or self.change_nicknames.current_loop == 0:
            for guild in self.bot.guilds:
                await self.bot.invoke(fake_ctx(self.bot, 'update_nickname', guild))

    @commands.command(hidden=True)
    @commands.bot_has_permissions(change_nickname=True)
    async def update_nickname(self, ctx):
        if not hasattr(ctx, 'author'):
            guild = await self.session.run_sync(lambda session: session.get(guilds, ctx.guild.id))
            await ctx.guild.me.edit(nick=next(guild.today_names_cycle))
            await self.session.commit()

    @update_nickname.error
    async def handle_update_nickname_error(self, ctx, error):
        if not hasattr(ctx, 'author'):
            if isinstance(error, NoResultFound):
                # TODO: Add logging and dev messaging
                return
            elif isinstance(error, MultipleResultsFound):
                # TODO: Add logging and dev messaging
                return

            guild = await self.session.run_sync(lambda session: session.get(guilds, ctx.guild.id))
            if isinstance(error, commands.BotMissingPermissions) and guild.nickname_notice:
                logger_message = f"The bot unsucessfully changed its nickname in '{ctx.guild}'. "
                if config.DM_owner:
                    await ctx.guild.owner.send((f"Currently I cannot change my nickname in {ctx.guild}. "
                                                 "Please give me the `change nickname` permission so I can work properly."))
                    logger_message += f"A DM message requesting to change it's permissions was sent to {ctx.guild.owner}."
                logger.warning(logger_message)
                guild.nickname_notice = False
                await self.session.commit()
            else:
                logger.warning(f"Ignoring {error!r}")

    @tasks.loop(hours=24)
    async def update_cycler(self):
        async def update_cycler():
            sql_guilds = await self.session.run_sync(lambda session: session.query(guilds).all())
            new_cycler = itertools.cycle(values.today_df['FirstName'] + ' ' + values.today_df['LastName'])
            for guild in sql_guilds:
                guild.today_names_cycle = new_cycler
            await self.session.commit()
            logger.info(f"The 'update_cycler()' coroutine was run.")
        await update_cycler()
        if self.update_cycler.current_loop == 0:
            time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)) \
                                  .replace(hour=0, minute=0, second=0, microsecond=0) \
                                  - datetime.datetime.today()
            logger.info(f"The update_cycler coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.")
            await asyncio.sleep(time_until_midnight.total_seconds())
            await update_cycler()
        else:
            # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
            # In the code below it is now converted to the local time zone automatically
            logger.info(f"The next iteration is scheduled for {format(self.update_cycler.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}.")

    @tasks.loop(hours=24)
    async def change_roles(self):
        async def change_roles():
            for guild in self.bot.guilds:
                await self.bot.invoke(fake_ctx(self.bot, 'update_role', guild))
            logger.info(f"The 'change_roles()' coroutine was run.")
        await change_roles()
        if self.change_roles.current_loop == 0:
            time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)) \
                                  .replace(hour=0, minute=0, second=0, microsecond=0) \
                                  - datetime.datetime.today()
            logger.info(f"The change_roles coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.")
            await asyncio.sleep(time_until_midnight.total_seconds() + cushion_delay)
            await change_roles()
        else:
            # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
            # In the code below it is now converted to the local time zone automatically
            logger.info(f"The next iteration is scheduled for {format(self.change_roles.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}.")

    @commands.command(hidden=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def update_role(self, ctx):
        if not hasattr(ctx, 'author'):
            if values.bday_today:
                role_name, color = "🎉 Happy Birthday", discord.Color.from_rgb(255, 0, 0)
            else:
                role_name, color = (f"Upcoming Bday-{format(values.today_df.iloc[0]['Birthdate'], '%a %b %d')}",
                                    discord.Color.from_rgb(162, 217, 145))
            guild = await self.session.run_sync(lambda session: session.get(guilds, ctx.guild.id))
            if guild.role_id is not None:
                try:
                    bday_role = ctx.guild.get_role(guild.role_id)
                    await bday_role.edit(name=role_name, color=color)
                except (discord.NotFound, commands.RoleNotFound):
                    bday_role = None
            else:
                bday_role = None

            if bday_role is None:
                bday_role = await ctx.guild \
                                     .create_role(name=role_name,
                                                  hoist=True,
                                                  color=color,
                                                  reason='Creating Happy Birthday/Upcoming Birthday role')
                guild.role_id = bday_role.id
                await self.session.commit()

            await ctx.guild.me.add_roles(bday_role)

            counter = itertools.count(bday_role.position)
            no_error = True
            while no_error:
                position = next(counter)
                try:
                    await bday_role.edit(position=position,
                                         hoist=True,
                                         reason='Moving role above other roles')
                except discord.errors.HTTPException:
                    no_error = False

            logger.info(f"The bot's role was changed to '{bday_role.name}' in '{ctx.guild}'.")

    @update_role.error
    async def handle_update_role_error(self, ctx, error):
        if not hasattr(ctx, 'author'):
            if isinstance(error, commands.BotMissingPermissions):
                logger_message = (f"The bot unsucessfully edited its role in '{ctx.guild}' "
                                   "due the the fact the bot was the required missing permissions.")
                if config.DM_owner:
                    await ctx.guild.owner.send((f"I cannot currently edit my role in **{ctx.guild}**. "
                                                 "Please give me the `manage roles` permission so I can work properly"))
                    logger_message += f" A DM message requesting to change its permissions was sent to {ctx.guild.owner}."
                logger.warning(logger_message)
            elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden):
                # TODO: Have the bot fix this problem on its own if possible
                guild = await self.session.run_sync(lambda session: session.get(guilds, ctx.guild.id))
                current_role = ctx.guild.get_role(guild.role_id)
                most_likely = [role for role in ctx.guild.me.roles
                                if role.id != current_role_id and
                                "Upcoming Bday-" not in role.name and
                                "🎉 Happy Birthday" != role.name]
                logger_message = (f"The bot unsucessfully edited its role in '{ctx.guild}' "
                                  f"due to the fact the bot's highest role was not above the '{current_role}' role.")
                if config.DM_owner:
                    await ctx.guild.owner.send(f"I cannot currently edit my role in **{ctx.guild}**. "
                                               f"Please move the **{most_likely[-1]}** role to above the **{current_role}** role.")
                    logger_message += f" A DM message requesting to change its permissions was sent to {ctx.guild.owner}."
                logger.warning(logger_message)
            else:
                logger.error(f'The following error occured with the update_role command: {error!r}')
                await ping_devs(error, self.update_role, ctx=ctx)

    def cog_unload(self):
        if self.send_bdays.is_running():
            self.send_bdays.stop()
            logger.info("The 'send_bdays()' task was gracefully ended.")

        if self.order_from_amazon.is_running():
            self.order_from_amazon.stop()
            logger.info("The 'order_from_amazon()' task was gracefully ended.")

        if self.send_DM_message.is_running():
            self.send_DM_message.stop()
            logger.info("The 'send_DM_message()' task was gracefully ended.")

        if self.change_nicknames.is_running():
            self.change_nicknames.stop()
            logger.info("The 'change_nicknames()' task was gracefully ended.")

        if self.change_roles.is_running():
            self.change_roles.stop()
            logger.info("The 'change_roles()' task was gracefully ended.")

        if self.update_cycler.is_running():
            self.update_cycler.stop()
            logger.info("The 'update_cycler()' task was gracefully ended.")
