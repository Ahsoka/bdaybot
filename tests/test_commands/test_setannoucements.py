import re
import pytest
import random
import asyncio
from bdaybot.tables import Guild

@pytest.mark.asyncio
async def test_setann(bot, session, channel, timeout):
    #invalid ann id
    invalid = "<#001>"
    await channel.send(f'test.setannouncements {invalid}')
    message = await bot.wait_for('message',
                                 timeout=timeout,
                                 check=lambda message: channel.guild.me in message.mentions)
    assert 'not a valid TextChannel' in message.content, \
            f'Message content: {message.content}'
    #voice channel
    invalid ="<#713095061180776501>"
    await channel.send(f'test.setannouncements {invalid}')
    message = await bot.wait_for('message',
                                 timeout=timeout,
                                 check=lambda message: channel.guild.me in message.mentions)
    assert 'not a valid TextChannel' in message.content,   \
            f'Message content: {message.content}'
    #set announcements
    # TODO: Change channel.mention to a different channel
    await channel.send(f'test.setannouncements {channel.mention}')
    await bot.wait_for('message',
                       timeout=timeout,
                       check=lambda message: re.search(r'<#\d+>', message.content))
    guild =  await session.get(Guild, channel.guild.id)
    assert channel.id == guild.announcements_id, \
            f'SQLAnnouncments ID: {guild.announcements_id}'
    #reset
    guild.announcements_id = None
    await session.commit()
    #set blank annoucnements
    await channel.send(f'test.setannouncements')
    await bot.wait_for('message',
                       timeout=timeout,
                       check=lambda message: re.search(r'<#\d+>', message.content))
    guild =  await session.get(Guild, channel.guild.id)
    assert channel.id == guild.announcements_id, \
            f'SQLAnnouncments ID: {guild.announcements_id}'
