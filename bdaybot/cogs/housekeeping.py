import logging
import discord

from .. import config
from discord.ext import commands
from .. import sessionmaker, config
from ..tables import StudentData, Guild
from ..utils import find_ann_channel, permissions, fake_ctx

logger = logging.getLogger(__name__)

@property
def mention(self):
    # NOTE: Keep an eye on Discord mobile because they might change it
    # so it does not always say '#invalid-channel' and actually shows the channel
    return f'**#{self}**' if self.guild.owner and self.guild.owner.is_on_mobile() \
           else f'<#{self.id}>'

discord.TextChannel.mention = mention

class CosmicHouseKeepingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.parsed_command_prefix = self.bot.parsed_command_prefix

    @commands.Cog.listener()
    async def on_ready(self):
        session = sessionmaker()
        for guild in self.bot.guilds:
            sql_guild = await session.get(Guild, guild.id)
            if sql_guild is None:
                channel = find_ann_channel(guild)
                if channel is None:
                    sql_guild = Guild(guild_id=guild.id)
                    logger.warning(f"The bot was unable to find the announcements channel in {guild}.")
                    if config.DM_owner:
                        await guild.owner.send((f"While looking through the text channels in **{guild}** "
                                                f"I was unable to find your announcements channel. Please use `{self.parsed_command_prefix}setann` "
                                                "to set the announcements channel."))
                else:
                    sql_guild = Guild(guild_id=guild.id, announcements_id=channel.id)
                    logger.info(f"The bot detected '{channel}' as the announcements channel in {guild}.")
                    if config.DM_owner:
                        await guild.owner.send((f"In **{guild}**, the announcement channel was automatically set to {channel.mention}! "
                                                f"If you think this is a mistake use `{self.parsed_command_prefix}setann` to change it."))
                        logger.info(f"The bot sent a DM message to {guild.owner} confirming the announcements channel was correct, "
                                    f"since it is the bot's first time in {guild}.")
                async with session.begin():
                    session.add(sql_guild)
            else:
                channel = guild.get_channel(sql_guild.announcements_id)
                if channel is None:
                    channel = find_ann_channel(guild)
                    script = f"In **{guild}**, the announcements channel appears to have been deleted"
                    if channel is None:
                        if config.DM_owner:
                            await guild.owner.send(script + (f". Please use `{self.parsed_command_prefix}setann` "
                                                              "to set a new announcements channel."))
                    else:
                        async with session.begin():
                            sql_guild.announcements_id = channel.id
                        if config.DM_owner:
                            await guild.owner.send(script + (f", however, I automatically detected {channel.mention} "
                                                              "as the announcements channel! If you think this is a mistake "
                                                             f"use `{self.parsed_command_prefix}setann` to change it."))
            if not permissions(channel, guild.me, 'send_messages'):
                logger_message = (f"The bot detected '{channel}' as the announcements channel, however, "
                                   "the bot did not have the required permissions to send messages in it.")
                if config.DM_owner:
                    await guild.owner.send((f"In **{guild}**, I detected {channel.mention} as the announcements channel, "
                                             "however, I don't have the required permissions to send messages in it. "
                                            f"If you would like to me to use {channel.mention} please give me the "
                                            f"`send messages` permission and then use the `{self.parsed_command_prefix}setann` "
                                            f"command to set {channel.mention} as the announcements channel."))
                    logger_message += f" {guild.owner} was sent a message notifying them of the situation."
                logger.warning(logger_message)
                async with session.begin():
                    sql_guild.announcements_id = None
        await session.close()

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        session = sessionmaker()
        guild = await session.get(Guild, after.guild.id)
        if guild.announcements_id == before.id and not permissions(after, after.guild.me, 'send_messages'):
            async with session.begin():
                guild.announcements_id = None
            if config.DM_owner:
                await after.guild.owner.send((f"While changing {after.mention} you or someone in **{after.guild}** "
                                              f"accidently made it so I can no longer send messages in {after.mention}. "
                                              f"Please use `{self.bot.parsed_command_prefix}setann` to set another announcements "
                                               "channel."))
        await session.close()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        session = sessionmaker()
        guild = await session.get(Guild, channel.guild.id)
        if channel.id == guild.announcements_id:
            async with session.begin():
                guild.announcements_id = None
            if config.DM_owner:
                await channel.guild.owner.send(("You or someone in the server deleted the channel I announce birthdays in. "
                                               f"Please set a new channel with `{self.bot.parsed_command_prefix}setann`"))
        await session.close()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        session = sessionmaker()
        if after == self.bot.user:
            guild = await session.get(Guild, after.guild.id)
            missing_manage_roles = False
            if before.roles != after.roles and guild.role_id not in map(lambda role: role.id, after.roles):
                try:
                    await self.bot.invoke(fake_ctx(self.bot, 'update_role', after.guild))
                except commands.BotMissingPermissions:
                    logger.warning(f"Someone in {after.guild} accidently made it so that the bot can no longer change roles.")
                    if config.DM_owner:
                        await after.guild.owner.send((f"While changing my roles, you or someone in **{after.guild}** "
                                                       "made it so I can no longer update my role. Please give me the "
                                                       "`manage roles` permission so I can change my role."))

                    missing_manage_roles = True

            if guild.announcements_id:
                channel = after.guild.get_channel(guild.announcements_id)
                if not permissions(channel, after.guild.me, 'send_messages'):
                    beginning = "Additionally," if missing_manage_roles \
                                else f"While changing my roles you or someone in **{after.guild}** made it so"
                    async with session.begin():
                        guild.announcements_id = None
                    logger_message = (f"Someone in {after.guild} accidently made it so that "
                                       "the bot can no longer send messsages in the announcements channel.")
                    if config.DM_owner:
                        await after.guild.owner.send((f"{beginning} I can no longer send messages in {channel.mention}. "
                                                      f"Therefore, {channel.mention} is no longer the announcements channel. "
                                                       "If you want to set a new announcements channel please use "
                                                      f"`{self.parsed_command_prefix}setannouncements`."))
                        logger_message += f" A message was sent to {after.guild.owner}."
                    logger.warning(logger_message)
        await session.close()
