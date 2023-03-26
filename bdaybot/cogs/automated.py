import heapq
import asyncio
import discord
import logging
import datetime
import itertools
import functools

from typing import List
from sqlalchemy import select
from ..snailmail import sendmail
from ..tables import Guild, StudentData
from discord.ext import commands, tasks
from ..amazon.order import order_product
from .. import values, config, sessionmaker
from ..utils import ping_devs, EmojiURLs, devs

logger = logging.getLogger(__name__)

cushion_delay = 0.1

class AutomatedTasksCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.new_day = True

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.send_bdays.is_running():
            # NOTE: Using functools.partial or functools.partialmethod on a method
            # does not register that method as a valid coroutine function as
            # determined by the inspect.iscoroutinefunction function.
            # This might be worth making an issue about on https://bugs.python.org/
            # Reference: https://bugs.python.org/issue33261
            self.send_bdays._before_loop = functools.partial(
                self.wait_to_run, loop_name='send_bdays'
            )
            self.send_bdays.start()
            logger.info("Successfully started the 'send_bdays()' task.")

        if config.ASIN and not self.order_from_amazon.is_running():
            self.order_from_amazon._before_loop = functools.partial(
                self.wait_to_run, loop_name='order_from_amazon'
            )
            self.order_from_amazon.start()
            logger.info("Successfully started the 'order_from_amazon()' task.")

        if config.print_envelope and not self.snailmail.is_running():
            self.snailmail._before_loop = functools.partial(
                self.wait_to_run, loop_name='snailmail'
            )
            self.snailmail.start()
            logger.info("Successfully started the 'snailmail()' task.")

        if not self.send_DM_message.is_running():
            self.send_DM_message._before_loop = functools.partial(
                self.wait_to_run, loop_name='send_DM_message'
            )
            self.send_DM_message.start()
            logger.info("Successfully started the 'send_DM_message()' task.")

        if not self.change_nicknames.is_running():
            self.change_nicknames.start()
            logger.info("Successfully started the 'change_nicknames()' task.")

        if not self.change_roles.is_running():
            self.change_roles.before_loop(self.change_roles_wait_to_run)
            self.change_roles.start()
            logger.info("Successfully started the 'change_roles()' task.")

        if not self.update_cycler.is_running():
            self.update_cycler.before_loop(self.update_cycler_wait_to_run)
            self.update_cycler.start()
            logger.info("Successfully started the 'update_cycler()' task.")

    async def wait_to_run(self, self_again = None, loop_name: str = 'unknown'):
        time_until_midnight = (
            datetime.datetime.today() + datetime.timedelta(days=1)
        ).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        logger.info(
            f"The {loop_name} coroutine is delayed for {time_until_midnight.total_seconds()} "
            "seconds to ensure it will run at midnight."
        )
        await asyncio.sleep(time_until_midnight.total_seconds() + cushion_delay)

    @tasks.loop(hours=24)
    async def send_bdays(self):
        if values.bday_today:
            session = sessionmaker()
            for guild in self.bot.guilds:
                sql_guild = await session.get(Guild, guild.id)
                if sql_guild is None:
                    # TODO: Call function in housekeeping
                    continue
                channel = guild.get_channel(sql_guild.announcements_id)
                if channel is None:
                    logger_message = f"The bot failed to find the announcements channel in {guild}."
                    if config.DM_owner:
                        await guild.owner.send(
                            "While trying to send the birthday message, "
                            f"I failed to find the announcements channel in **{guild}**. "
                            f"Please use `/set announcements` to set the announcements "
                            "channel so I can send a birthday message!"
                        )
                        logger_message += f" A message has been sent to {guild.owner}."
                    logger.warning(logger_message)
                    continue

                for stuid, series in values.today_df.iterrows():
                    # TODO: Add some different styles for the bday message
                    full_name = f"***__{series['FirstName']} {series['LastName']}__***"
                    student = await session.get(StudentData, stuid)
                    mention = f' {student.discord_user.mention}' if student.discord_user else ''
                    age = datetime.datetime.today().year - series['Birthyear']
                    if age in range(14, 101):
                        age_portion = f'\nCongratulations on turning _**{age}**_ 🎂 🎉'
                    else:
                        age_portion = ' 🎂 🎉'

                    embed = discord.Embed(
                        description=f"Happy Birthday to {full_name}{mention}🎈 🎊{age_portion}"
                    ).set_author(
                        name='Happy Birthday! 🎉',
                        icon_url=await EmojiURLs.partying_face
                    )
                    await channel.send(embed=embed)
            await session.close()
        logger.info(f"The 'send_bdays()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info(
            f"The next iteration is scheduled for "
            + format(self.send_bdays.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')
            + "."
        )

    @send_bdays.error
    async def handle_send_bdays_error(self, error: Exception):
        logger.warning("The following error occured with the send_bdays task:", exc_info=error)
        if not self.send_bdays.is_running():
            logger.debug('Attempting to restart the send_bdays task.')
            self.send_bdays.restart()
            if not self.send_bdays.is_running():
                logger.critical('Failed to restart the send_bdays task.')
                await ping_devs(error, 'send_bdays', bot=self.bot)

    @tasks.loop(hours=24)
    async def order_from_amazon(self):
        if values.bday_today:
            for stuid, bday_person in values.today_df.iterrows():
                if bday_person['AddrLine1']:
                    order_product(
                        ASIN=config.ASIN,
                        FULLNAME=bday_person['FirstName'] + ' ' + bday_person['LastName'],
                        ADDRESS_LINE_ONE=bday_person['AddrLine1'],
                        ADDRESS_LINE_TWO=bday_person['AddrLine2'],
                        CITY=bday_person['City'],
                        STATE=bday_person['State'],
                        ZIPCODE=str(int(bday_person['Zipcode'])),
                        place_order=config.place_order
                    )
                    if config.place_order:
                        logger.info(
                            f"The bot successfully sent candy to {bday_person['AddrLine1']} "
                            f"for {bday_person['FirstName'] + ' ' + bday_person['LastName']} "
                            "via Amazon!"
                        )
                        for name, discord_id in devs.items():
                            if getattr(config, name.lower()):
                                dev = await self.bot.get_user(discord_id)
                                await dev.send(
                                    f"The bot successfully sent candy to **{bday_person['AddrLine1']}** "
                                    f"for __{bday_person['FirstName'] + ' ' + bday_person['LastName']}__ "
                                    "via Amazon! ✨"
                                )
                    else:
                        logger.info(
                            "The bot successfully accessed Amazon, however it did not order "
                            "candy since this was disabled."
                        )

    @order_from_amazon.error
    async def handle_order_from_amazon_error(self, error: Exception):
        logger.error(f'The following error occured with the order_from_amazon command: {error!r}')
        await ping_devs(error, 'order_from_amazon', bot=self.bot)

    @tasks.loop(hours=24)
    async def snailmail(self):
        if values.bday_today:
            session = sessionmaker()
            for stuid, bday_person in values.today_df.iterrows():
                if bday_person['AddrLine1']:
                    sendmail(
                        FULLNAME=bday_person['FirstName'] + ' ' + bday_person['LastName'],
                        ADDRESS_LINE_ONE=bday_person['AddrLine1'],
                        ADDRESS_LINE_TWO=bday_person['AddrLine2'],
                        CITY=bday_person['City'],
                        STATE=bday_person['State'],
                        ZIPCODE=str(int(bday_person['Zipcode'])),
                        PERSON=await session.get(StudentData, 123456)
                    )
            await session.close()

    @tasks.loop(hours=24)
    async def send_DM_message(self):
        if values.bday_today:
            session = sessionmaker()
            for stuid, series in values.today_df.iterrows():
                student = await session.get(StudentData, stuid)
                if student.discord_user is not None:
                    user = await self.bot.get_user(student.discord_user.discord_user_id)
                    try:
                        await user.send(
                            f"Happy birthday from me, {self.bot.user.mention}, "
                            "and all the developers of the bdaybot! Hope you have an awesome birthday!"
                        )
                        logger.info(f"A happy birthday DM message was sent to {user}.")
                    except discord.Forbidden:
                        logger.debug(
                            "The bdaybot failed to send a happy birthday DM message to "
                            f"{user} because the bot and {user} do not have any mutual servers."
                        )
            await session.close()

    @tasks.loop(seconds=5)
    async def change_nicknames(self):
        if len(values.today_df) > 1 or self.new_day:
            self.new_day = False
            async with sessionmaker.begin() as session:
                for guild in self.bot.guilds:
                    guild: discord.Guild = guild
                    sql_guild = await session.get(Guild, guild.id)
                    logger_message = f"The bot unsuccessfully changed its nickname in '{guild}'."
                    error = None
                    if guild.me.guild_permissions.change_nickname:
                        # logger_message = f"The bot changed its nickname in {guild}"
                        logger_message = None
                        await guild.me.edit(nick=next(sql_guild.today_names_cycle))
                    elif config.DM_owner and sql_guild.nickname_notice and guild.owner:
                        try:
                            await guild.owner.send(
                                f"Currently I cannot change my nickname in {guild}. "
                                "Please give me the `change nickname` permission so I can work properly."
                            )
                            sql_guild.nickname_notice = False
                            logger_message += (
                                " A DM message requesting to change its "
                                f"permissions was sent to {guild.owner}."
                            )
                        except discord.HTTPException as error:
                            pass
                    if logger_message:
                        logger.warning(logger_message, exc_info=error)

    @change_nicknames.error
    async def handle_change_nicknames_error(self, error: Exception):
        logger.error(f'The following error occured with the change_nicknames loop:', exc_info=error)
        await ping_devs(error, 'change_nicknames', bot=self.bot)

    async def update_cyclers(self):
        async with sessionmaker.begin() as session:
            sql_guilds = (await session.execute(select(Guild))).scalars().all()
            new_cycler = itertools.cycle(values.today_df['FirstName'] + ' ' + values.today_df['LastName'])
            for guild in sql_guilds:
                guild.today_names_cycle = new_cycler

    async def update_cycler_wait_to_run(self, *args):
        await self.update_cyclers()
        await self.wait_to_run(loop_name='update_cycler')

    @tasks.loop(hours=24)
    async def update_cycler(self):
        self.new_day = True
        await self.update_cyclers()
        logger.info(f"The 'update_cycler()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info((
            "The next iteration is scheduled for "
            f"{format(self.update_cycler.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}."
        ))

    async def update_roles(self, guilds: List[discord.Guild] = None):
        if guilds is None:
            guilds = self.bot.guilds
        elif isinstance(guilds, discord.Guild):
            guilds = [guilds]
        async with sessionmaker.begin() as sess:
            for guild in guilds:
                guild: discord.Guild = guild
                if guild.me.guild_permissions.manage_roles:
                    sql_guild = await sess.get(Guild, guild.id)

                    if values.bday_today:
                        role_name, color = (
                            "🎉 Happy Birthday",
                            discord.Color.from_rgb(255, 0, 0)
                        )
                    else:
                        role_name, color = (
                            f"Upcoming Bday-{format(values.today_df.iloc[0]['Birthdate'], '%a %b %d')}",
                            discord.Color.from_rgb(162, 217, 145)
                        )

                    bday_role = None
                    if sql_guild.role_id is not None:
                        try:
                            bday_role = guild.get_role(sql_guild.role_id)
                            if bday_role is None:
                                bday_role = await guild.create_role(
                                    name=role_name,
                                    hoist=True,
                                    color=color,
                                    reason=f'Creating {role_name} role'
                                )
                                sql_guild.role_id = bday_role.id
                            elif bday_role.name != role_name or bday_role.color != color:
                                await bday_role.edit(name=role_name, color=color)
                            await guild.me.add_roles(bday_role)
                        except (discord.NotFound, commands.RoleNotFound):
                            bday_role = None
                        except discord.Forbidden:
                            error = None
                            logger_message = (
                                f"The bot unsucessfully edited its role in '{guild}' "
                                "due to the fact the bot's highest role was not above the "
                                f"'{bday_role}' role."
                            )

                            highest_role, second_highest = heapq.nlargest(2, guild.me.roles)
                            role_of_interest = highest_role
                            if highest_role == bday_role:
                                role_of_interest = second_highest

                            if config.DM_owner and guild.owner:
                                try:
                                    await guild.owner.send(
                                        f"I cannot currently edit my role in **{guild}**. "
                                        f"Please move the **{role_of_interest}** role to above "
                                        f"the **{bday_role}** role."
                                    )
                                    logger_message += (
                                        " A DM message requesting to change "
                                        f"its permissions was sent to {guild.owner}."
                                    )
                                except discord.HTTPException as error:
                                    pass

                            logger.warning(logger_message, exc_info=error)

                            return

                    counter = itertools.count(bday_role.position)
                    no_error = True
                    while no_error:
                        position = next(counter)
                        try:
                            await bday_role.edit(
                                position=position,
                                hoist=True,
                                reason=f'Moving the {role_name} role above other roles'
                            )
                        except discord.errors.HTTPException:
                            no_error = False

                    logger.info(f"The bot's role was changed to '{bday_role.name}' in '{guild}'.")
                else:
                    logger_message = (
                        f"The bot unsuccessfully edited its role in '{guild}' "
                        "due the the fact the bot was the required missing permissions."
                    )
                    error = None
                    if config.DM_owner and guild.owner:
                        try:
                            await guild.owner.send(
                                f"I cannot currently edit my role in **{guild}**. "
                                "Please give me the `manage roles` permission so I can work properly."
                            )
                            logger_message += (
                                " A DM message requesting to change its "
                                f"permissions was sent to {guild.owner}."
                            )
                        except discord.HTTPException as error:
                            pass

                    logger.warning(logger_message, exc_info=error)

    async def change_roles_wait_to_run(self, *args):
        try:
            await self.update_roles()
        except Exception as error:
            await self.handle_change_roles_error(error)
        await self.wait_to_run(loop_name='change_roles')

    @tasks.loop(hours=24)
    async def change_roles(self):
        await self.update_roles()
        logger.info(f"The 'change_roles()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info(
            f"The next iteration is scheduled for "
            f"{format(self.change_roles.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}."
        )

    @change_roles.error
    async def handle_change_roles_error(self, error: Exception):
        logger.error(f'The following error occured with the change_roles loop:', exc_info=error)
        await ping_devs(error, 'change_roles', bot=self.bot)

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
