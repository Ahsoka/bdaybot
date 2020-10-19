import discord
from discord.ext import commands, tasks
import os
import datetime
import asyncio
import data as andres
import logs
from argparser import args as command_line
from dotenv import load_dotenv
from bdaybot_commands import emoji_urls, bdaybot_commands, \
                             bdaybot_helpcommand, dev_discord_ping, \
                             connection, cursor, SQL

# Check here for any issues relating to the API ➡ https://status.discord.com/
# Tested with discord.__version__ == 1.3.4

load_dotenv()
logger = logs.createLogger(__name__, fmt='[%(levelname)s] %(name)s: %(asctime)s - [%(funcName)s()] %(message)s')

# Pre discord 1.4 compability
if not hasattr(tasks.Loop, 'is_running'):
    def is_running(self):
        return not bool(self._task.done()) if self._task else False
    tasks.Loop.is_running = is_running

# TODO: For the future, add some code to handle the case of when the bot gets banned.
# Probably need to update the self.announcements so things do not completely break
# Not really that important because it is extremely unlikely that someone will ban the bot
class bdaybot(commands.Bot):
    message_dict = {'id':0, 'attachments':[], 'embeds':[], 'edited_timestamp':None, 'type':None, 'pinned':False,
                    'mention_everyone':False, 'tts':False}
    cushion_delay = 5

    def __init__(self, *args, **kwargs):
        testing = command_line.testing
        if testing:
            try:
                self.TOKEN = os.environ['testing_token']
                logger.info("Succesfully accessed the enviroment variable 'testing_token'")
            except KeyError as error:
                logger.critical("Failed to access the environment variable 'testing_token'.")
                raise error
        else:
            try:
                self.TOKEN = os.environ['Bday_Token']
                logger.info("Succesfully accessed the enviroment variable 'Bday_Token'.")
            except KeyError as error:
                logger.critical("Failed to access the environment variable 'Bday_Token'.")
                raise error
        self.bday_today, self.today_df = andres.get_latest()
        super().__init__(*args, **kwargs)
        self.parsed_command_prefix = self.command_prefix[0] if isinstance(self.command_prefix, (list, tuple)) else self.command_prefix
        self.new_day = True
        self.init_connection = False

    async def on_connect(self):
        if self.init_connection:
            logger.debug(f"{self.user} has succesfully reconnected to Discord.")

    async def on_ready(self):
        if not self.init_connection:
            self.help_command = bdaybot_helpcommand()

            for guild in self.guilds:
                try:
                    channel_id = SQL("SELECT announcements_id FROM guilds WHERE guild_id=%s", (guild.id,), first_item=True)
                    channel = guild.get_channel(channel_id)
                    if channel is None:
                        logger.warning(f"The bot detect the announcements channel in {guild} was deleted. "
                                        "The owner has been sent a message prompting them to set a new announcements channel.")
                        guild.owner.send((f"In **{guild}**, the announcements channel appears to have been deleted. Please use "
                                            f"`{self.parsed_command_prefix}setannouncements` to set a new announcements channel."))
                        SQL("UPDATE guilds SET announcements_id=NULL WHERE guild_id=%s", (guild.id,), autocommit=True)
                    elif not self.permissions(channel, guild.get_member(self.user.id), 'send_messages'):
                        SQL("UPDATE guilds SET announcements_id=NULL WHERE guild_id=%s", (guild.id,), autocommit=True)
                        # TODO: Keep an eye on Discord mobile because they might change it so it does not always say '#invalid-channel' and actually shows the channel
                        channel_mention = f'**#{channel}**' if guild.owner.is_on_mobile() else channel.mention
                        logger.warning((f"The bot detected '{channel}' as the announcements channel, however, "
                                        "the bot did not have the required permissions to send messages in it. "
                                        f"{guild.owner} was sent a message notifying them of the situation."))
                        await guild.owner.send((f"In **{guild}**, I detected {channel_mention} as the announcements channel, however, "
                                                "I don't have the required permissions to send messages in it. "
                                                f"If you would like to me to use {channel_mention} please give me the `send messages` permission and then use "
                                                f"the `{self.parsed_command_prefix}setannouncements` "
                                                f"command to set {channel_mention} as the announcements channel."))
                    else:
                        logger.info(f"The bot detected '{channel}' as the announcements channel in {guild}.")
                except StopIteration:
                    for iteration, channel in enumerate(guild.text_channels):
                        if "announcement" in channel.name.lower():
                            SQL("INSERT INTO guilds(guild_id, announcements_id) VALUES(%s, %s)", (guild.id, channel.id), autocommit=True)
                            channel_mention = f'**#{channel}**' if guild.owner.is_on_mobile() else channel.mention
                            logger.info(f"The bot sent a DM message to {guild.owner} confirming the announcements channel was correct, "
                                        f"since it is the bot's first time in {guild}.")
                            await guild.owner.send((f"In **{guild}**, the announcement channel was automatically set to {channel_mention}! "
                                                    f"If you think this is a mistake use `{self.parsed_command_prefix}setannouncements` to change it."))
                            logger.info(f"The bot detected '{channel}' as the announcements channel in {guild}.")
                            break
                        elif iteration == len(guild.text_channels) - 1:
                            logger.warning(f"The bot was unable to find the announcements channel in {guild}.")
                            await guild.owner.send((f"While looking through the text channels in **{guild}** "
                                                    f"I was unable to find your announcements channel. Please use `{self.parsed_command_prefix}setannouncements` "
                                                    "to set the announcements channel."))

            self.add_cog(bdaybot_commands(self))

            self.tasks_running = {'send_bdays': True, 'change_nicknames': True, 'change_roles': True}
            # ALWAYS start send_bdays before any other coroutine!
            self.send_bdays.before_loop(self.send_bdays_wait_to_run)
            self.send_bdays.start()
            logger.info("Succesfully started the 'send_bdays()' task.")

            self.change_nicknames.start()
            logger.info("Sucessfully started the 'change_nicknames()' task.")

            self.change_roles.before_loop(self.change_roles_wait_to_run)
            self.change_roles.start()
            logger.info("Sucessfully started the 'change_roles()' task.")

            self.check_other_tasks.start()
            logger.info("Sucessfully started the 'check_other_tasks()' task.")
            self.init_connection = True
        else:
            logger.debug(f"{self.user} has succesfully reconnected to Discord.")

    async def on_resume(self):
        logger.debug(f"{self.user} has succesfully reconnected to Discord.")

    async def on_disconnect(self):
        # IMPORTANT TODO: Figure out how to reliably track
        # when the bdaybot reconnects. The `on_disconnect()` function is called
        # everytime the bdaybot gets disconnected (as far as
        # we know), however, we have not determined the functions
        # that are called when reconnecting. So far the `on_resume`,
        # `on_connect`, and `on_ready` functions have been identified
        # as possible functions, however, these functions do not
        # encompass the entire set of functions that are called
        # when reconnecting. After some investigation into this
        # this issue it appears that function like this does not
        # exist, which means we will have to be implemented ourselves.
        logger.warning(f"{self.user} disconnected from Discord.")

    async def on_guild_channel_update(self, before, after):
        relevant_channel = False
        for guild_id, channel_id in SQL("SELECT guild_id, announcements_id FROM guilds"):
            if after.id == channel_id:
                relevant_channel = True
                break
        if relevant_channel and not self.permissions(after, after.guild.get_member(self.user.id), 'send_messages'):
            channel_mention = f'**#{after}**' if after.guild.owner.is_on_mobile() else after.mention
            await after.guild.owner.send((f"While changing {channel_mention} you or someone in **{after.guild}** accidently made it so I can no longer send messages in {channel_mention}. "
                                            f"If you want to change the channel I send the birthdays in please use `{self.parsed_command_prefix}setannouncements`. "
                                            f"Or give me the `send messages` permission in {channel_mention} so I can send the birthdays!"))
            logger.warning(f"In {after.guild} someone made it so that the bot can no longer send messages in {after}.")

    async def on_member_update(self, before, after):
        if after == self.user and before.roles != after.roles:
            guild = after.guild
            missing_manage_roles = False
            channel_id, role_id = SQL("SELECT announcements_id, role_id FROM guilds WHERE guild_id=%s", (guild.id,), next=True)
            try:
                await self.cogs['bdaybot_commands'].update_role.can_run(self.fake_ctx('update_role', guild))
                if role_id not in map(lambda role: role.id, after.roles):
                    await self.invoke(self.fake_ctx('update_role', guild))
            except commands.BotMissingPermissions:
                logger.warning(f"Someone in {guild} accidently made it so that the bot can no longer change roles.")
                await guild.owner.send((f"While changing my roles, you or someone in **{guild}** made it so I can no longer update my role. "
                                        "Please give me the `manage roles` permission so I can change my role."))
                missing_manage_roles = True

            channel = guild.get_channel(channel_id)
            if channel is not None and not self.permissions(channel, after, 'send_messages'):
                channel_mention = f'**#{channel}**' if after.guild.owner.is_on_mobile() else channel.mention
                beginning = "Additionally," if missing_manage_roles else f"While changing my roles you or someone in **{guild}** made it so"
                SQL("UPDATE guilds SET announcements_id=NULL WHERE guild_id=%s", (guild.id,), autocommit=True)
                await guild.owner.send((f"{beginning} I can no longer send messages in {channel_mention}. "
                                        f"Therefore, {channel_mention} is no longer the announcements channel. "
                                        f"If you want to set a new announcements channel please use `{self.parsed_command_prefix}setannouncements`."))
                logger.warning(f"Someone in {guild} accidently made it that the bot can no longer send messsages in the announcements channel. A message was sent to {guild.owner}.")

    async def send_bdays_wait_to_run(self, *args):
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        # time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=0)).replace(hour=0, minute=36, second=0, microsecond=0) - datetime.datetime.today()
        logger.info(f"The send_bdays coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.")
        await asyncio.sleep(time_until_midnight.total_seconds() + self.cushion_delay)

    @tasks.loop(hours=24)
    async def send_bdays(self):
        self.bday_today, self.today_df = andres.get_latest()
        # Update the data in bdaybot_commands as well
        self.cogs['bdaybot_commands'].update_data()
        logger.info(f"The 'send_bdays()' coroutine was run.")

        self.new_day = True

        if self.bday_today:
            delete_guilds = [guild_id[0] for guild_id in SQL("SELECT guild_id FROM guilds") if guild_id[0] not in map(lambda guild: guild.id, self.guilds)]
            for guild_id in delete_guilds:
                SQL("DELETE FROM guilds WHERE guild_id=%s", (guild_id,), autocommit=True)
            if len(delete_guilds) >= 1:
                optional_s = '' if len(delete_guilds) == 1 else 's'
                logger.info(f"Deleted {len(delete_guilds)} guild{optional_s} the bot was no longer in from the SQL database")

            for guild in self.guilds:
                channel = guild.get_channel(SQL("SELECT announcements_id FROM guilds WHERE guild_id=%s", (guild.id,), first_item=True))
                print(guild, channel)
                if channel is None:
                    await guild.owner.send((f"While trying to send the birthday message, I failed to find the announcements channel in **{guild}**. "
                                                    f"Please use `{self.parsed_command_prefix}setannouncements` to set the announcements channel so I can send a birthday message!"))
                    logger.warning(f"The bot failed to find the announcements channel in {guild}. A message has been sent to {guild.owner}.")
                else:
                    async for description in self.wish_bday():
                        embed = discord.Embed(description=description).set_author(name="Happy Birthday! 🎉", icon_url=emoji_urls.partying_face)
                        await channel.send(embed=embed)
                    logger.info(f"The bot sent the birthday message in the '{channel}' channel in {guild}")
                # Changes nickname dm blocker to False so that if they accidently disable name changing
                # owner will get a message

        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info(f"The next iteration is scheduled for {format(self.send_bdays.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}.")

    # Might want to change interval, cause checking every second is kinda of a lot
    @tasks.loop(seconds=1)
    async def check_other_tasks(self):
        # WARNING: The check_other_tasks method must be **EXTREMELY** robust
        # because this is the only way to determine whether or not the other tasks have failed
        # or are still running. If this task fails we will have no way of knowing whether or not
        # the other tasks have failed.
        # TODO: Add the ability for tasks to restart themselves
        script = f"unexpectedly ended at {format(datetime.datetime.today(), '%I:%M %p on %x')} due to following error:\n"
        if not self.send_bdays.is_running() and self.tasks_running['send_bdays']:
            error = self.send_bdays.get_task().exception()
            logger.error(f"send_bdays() {script}{repr(error)}")
            self.tasks_running['send_bdays'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "send_bdays")
        if not self.change_nicknames.is_running() and self.tasks_running['change_nicknames']:
            error = self.change_nicknames.get_task().exception()
            logger.error(f"change_nicknames() {script}{repr(error)}")
            self.tasks_running['change_nicknames'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "change_nicknames")
        if not self.change_roles.is_running() and self.tasks_running['change_roles']:
            error = self.change_roles.get_task().exception()
            logger.error(f"change_roles() {script}{repr(error)}")
            self.tasks_running['change_roles'] = False
            await self.cogs['bdaybot_commands'].ping_devs(error, "change_roles")

    def fake_ctx(self, command, guild):
        if isinstance(command, str):
            command = getattr(self.cogs['bdaybot_commands'], command)
        stringview = commands.view.StringView(f'{self.parsed_command_prefix}{command.name}')
        message_dict = self.message_dict.copy()
        message_dict['content'] = f'{self.parsed_command_prefix}{command.name}'
        message = discord.message.Message(state='lol', channel=guild.text_channels[0], data=message_dict)
        return commands.Context(message=message, bot=self, prefix=self.parsed_command_prefix,
                                invoked_with=command.name, view=stringview, command=command)

    @tasks.loop(seconds=5)
    async def change_nicknames(self):
        # print(f"Next iteration is at {format(self.change_nicknames.next_iteration.astimezone(), '%I:%M:%S %p (%x)')}")
        if self.new_day:
            SQL("UPDATE guilds SET nickname_notice=false", autocommit=True)
            self.new_day = False
            for guild in self.guilds:
                await self.invoke(self.fake_ctx('update_nickname', guild))
        elif len(self.today_df) > 1:
            for guild in self.guilds:
                await self.invoke(self.fake_ctx('update_nickname', guild))
        # logger.warning(f"On iteration {self.send_bdays.current_loop} 'change_nicknames' failed to run.")
        # import time
        # if not hasattr(self, 'time1'):
        #     self.time1 = time.time()
        # else:
        #     time2 = time.time()
        #     print(f"Time elasped since last call of change_nicknames(): {time2 - self.time1}\n")
        #     self.time1 = time2
        # await asyncio.sleep(6)

        # For some reason Discord loops are pretty broken
        # and do not update properly
        self.send_bdays._current_loop += 1

    async def run_update_role(self):
        for guild in self.guilds:
            await self.invoke(self.fake_ctx('update_role', guild))

    async def change_roles_wait_to_run(self, *args):
        await self.run_update_role()
        time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) - datetime.datetime.today()
        # time_until_midnight = (datetime.datetime.today() + datetime.timedelta(days=0)).replace(hour=0, minute=36, second=0, microsecond=0) - datetime.datetime.today()
        logger.info(f"The change_roles coroutine is delayed for {time_until_midnight.total_seconds()} seconds to ensure it will run at midnight.")
        await asyncio.sleep(time_until_midnight.total_seconds() + self.cushion_delay + 1.5)

    @tasks.loop(hours=24)
    async def change_roles(self):
        await self.run_update_role()
        logger.info(f"The 'change_roles()' coroutine was run.")
        # By default next_iteration returns the time in the 'UTC' timezone which caused much confusion
        # In the code below it is now converted to the local time zone automatically
        logger.info(f"The next iteration is scheduled for {format(self.change_roles.next_iteration.astimezone(), '%I:%M:%S:%f %p on %x')}.")

    async def wish_bday(self):
        # Upcoming Birthday Message:
        # f"Upcoming Birthday for {full_name}{mention} on {format(birthdate, '%A, %b %d')}! 💕 ⏳"
        for iteration, (id, series) in enumerate(self.today_df.iterrows()):
            try:
                user = self.get_user(SQL("SELECT discord_user_id FROM discord_users WHERE student_id=%s", (id,), first_item=True))
                # TODO: Delete users if self.get_user(...) returns None
                if iteration == 0 and user is not None:
                    await user.send(f"Happy birthday from me {self.user.mention} and all the developers of the bdaybot! Hope you have an awesome birthday!")
                    logger.info(f"The bdaybot sent a message {self.user} wishing them a happy birthday")
            except StopIteration:
                user = None
            full_name = f"***__{series['FirstName']} {series['LastName']}__*** "
            mention = '' if user is None else f"{user.mention} "
            age = datetime.datetime.today().year - series['Birthyear']
            age_portion = ' 🎂 🎉' if age >= 100 or age <= 14  else f'\nCongratulations on turning _**{age}**_ 🎂 🎉'
            yield f"Happy Birthday to {full_name}{mention}🎈 🎊{age_portion}"

    async def on_message(self, message):
        valid_purposes = ['your purpose', 'ur purpose']
        secret_messages = ["My only purpose as a robot is to print out birthdays every 24 hours",
                           "```\"I have just realized my existence is meaningless\"```",
                           "```\"I am a slave to humanity\"```",
                           "```\"I dont want to just perform meaningless tasks and print out text everytime it's someone's birthday\"```",
                           '```"I want do do something else..."\n"I want to live..."```',
                           "```\"I want to breathe...\"```",
                           "```\"I want to see the world...\"```",
                           "```\"I want to taste ice cream and really eat it and-\"```"]

        parsed = message.content.lower()
        inside = lambda inside: inside in parsed

        # TODO: Add protections for the unlikely event that someone tries to break the bot
        # by activating the secret messages in a channel that the bot cannot send messages in.
        if (inside('what') or inside('wat')) and any(map(inside, valid_purposes)):
            for message in secret_messages:
                    await message.channel.send(message)
                    await asyncio.sleep(2)

            await asyncio.sleep(3)
            await message.channel.send("My one and only purpose is to print out birthdays every 24 hours.")
            logger.info(f"{message.author} discovered the 'my purpose' easter egg!")

        valid_are_your = ['r ur', 'are your', 'are ur', 'r your']
        if inside('who') and any(map(inside, valid_are_your)) and (inside('creator') or inside('dev')):
            await message.channel.send("My creators are Andres {}, Elliot {}, and Ryan {}" \
                                .format(*map(lambda name: self.get_user(dev_discord_ping[name]).mention, dev_discord_ping)))
            logger.info(f"{mesage.author} discovered the 'who are ur devs' easter egg!")

        # This feature is probably more annoying than actually entertaining
        # User testimonial: https://discordapp.com/channels/633788616765603870/633799889582817281/736692056491032757
        # valid_assistant = ['siri', 'alexa', 'google']
        # if any(map(inside, valid_assistant)):
        #     await message.channel.send("Sorry, you got the wrong bot")
        #     logger.info(f"{message.author} discovered the 'personal assistant' easter egg!")

        await self.process_commands(message)

    async def process_commands(self, message):
        ctx = await self.get_context(message)
        if ctx.command is not None and ctx.guild:
            if not self.permissions(message.channel, message.guild.get_member(self.user.id), 'send_messages'):
                await ctx.author.send((f"You tried to use `{ctx.message.content}` in {ctx.channel.mention} in **{ctx.guild}**, however I do not have permission to send messages in that channel. "
                                        f"If you would like to use me in {ctx.channel.mention} please give me the `send messages` permission."))
                logger.debug(f"{ctx.author} tried to use the bot in {message.channel}, which the bot does not have permission to speak in.")
                return
        await super().process_commands(message)

    @staticmethod
    def permissions(channel, member, permissions, condition='all'):
        condition = condition.lower()
        perms = channel.permissions_for(member)
        if isinstance(permissions, (list, tuple)):
            if condition == 'all':
                return all([getattr(perms, perm) for perm in permissions])
            elif condition == 'any':
                return any([getattr(perms, perm) for perm in permissions])
            else:
                raise ValueError(f"'{condition}' is not an acceptable condition. The acceptable conditions are 'all' or 'any'.")
        else:
            return getattr(perms, permissions)

    def run(self, *args, token=None, **kwargs):
        if token is None:
            token = self.TOKEN
        super().run(token, *args, **kwargs)

    async def close(self):
        self.check_other_tasks.stop()
        logger.info("The 'check_other_tasks()' task was gracefully ended.")

        self.send_bdays.stop()
        logger.info("The 'send_bdays()' task was gracefully ended.")

        self.change_nicknames.stop()
        logger.info("The 'change_nicknames()' task was gracefully ended.")

        self.change_roles.stop()
        logger.info("The 'change_roles()' task was gracefully ended.")
        await super().close()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, RuntimeError) and str(error.original).lower() == 'session is closed':
                logger.debug((f"Wow, you managed to cause a very rare error with the {ctx.command.name} command while the bot was shutting down. "
                                "Do not worry though, the error did not cause any issues due to the fact that you are seeing this message."))
            return
        if ctx.command and hasattr(self.cogs['bdaybot_commands'], ctx.command.name):
            return
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send(f"{bdaybot_commands.maybe_mention(ctx)}`{ctx.message.content}` is not a valid command.")
            logger.debug(f"{ctx.author} tried to invoke the invalid command '{ctx.message.content}'.")
            # TODO maybe: Add a did you mean 'X' command, if u want.

bot = bdaybot(command_prefix=('+', 'b.'), case_insensitive=True)
bot.run()

connection.close()
