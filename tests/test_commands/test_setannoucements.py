import pytest
import random
import asyncio
from bdaybot.tables import Guild

@pytest.mark.asyncio
async def test_setann(bot, session, channel, delay):
    #invalid ann id
    invalid = "<#001>"
    await channel.send(f'test.setannouncements {invalid}')
    await asyncio.sleep(delay)
    message = (await channel.history(limit=1).flatten())[0]
    assert 'not a valid TextChannel' in message.content, \
            f'Message content: {message.content}'
    #voice channel
    invalid ="<#713095061180776501>"
    await channel.send(f'test.setannouncements {invalid}')
    await asyncio.sleep(delay)
    message = (await channel.history(limit=1).flatten())[0]
    assert 'not a valid TextChannel' in message.content,   \
            f'Message content: {message.content}'
    #set announcements
    await channel.send(f'test.setannouncements {channel.mention}')
    await asyncio.sleep(delay)
    guild =  await session.get(Guild, channel.guild.id)
    assert channel.id == guild.announcements_id, \
            f'SQLAnnouncments ID: {guild.announcements_id}'
    #reset
    guild.announcements_id = None
    await session.commit()
    #set blank annoucnements
    await channel.send(f'test.setannouncements')
    await asyncio.sleep(delay)
    guild =  await session.get(Guild, channel.guild.id)
    assert channel.id == guild.announcements_id, \
            f'SQLAnnouncments ID: {guild.announcements_id}'
