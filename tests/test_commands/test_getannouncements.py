import pytest
import asyncio
from bdaybot.tables import Guild

@pytest.mark.asyncio
async def test_getann(bot, session, channel, delay):
    # Test with situation with no announcements channel
    # Delete preset announcements channel
    guild = await session.get(Guild, channel.guild.id)
    guild.announcements_id = None
    await session.commit()
    await channel.send(f'test.getannouncements')
    await asyncio.sleep(delay)
    latest_message = (await channel.history(limit=1).flatten())[0]
    assert (f"{bot.user.mention} There is not currently an announcements channel set. "
            f"Use `test.setann` to set an announcements channel.") \
            == latest_message.content, \
            f'Message content: {latest_message.content}'
    # Same test with alias
    await channel.send(f'test.getann')
    await asyncio.sleep(delay)
    latest_message = (await channel.history(limit=1).flatten())[0]
    assert (f"{bot.user.mention} There is not currently an announcements channel set. "
            f"Use `test.setann` to set an announcements channel.") \
            == latest_message.content, \
            f'Message content: {latest_message.content}'

    # Test with situation with preset announcements channel
    guild.announcements_id = channel.id
    await session.commit()
    await channel.send(f'test.getannouncements')
    await asyncio.sleep(delay)
    latest_message = (await channel.history(limit=1).flatten())[0]
    assert (f"{bot.user.mention} The current announcements channel is {guild.mention_ann}. "
            f"If you like to change the announcements channel use `test.setann`.") \
            == latest_message.content, \
            f'Message content: {latest_message.content}'
    # Same test with alias
    await channel.send(f'test.getann')
    await asyncio.sleep(delay)
    latest_message = (await channel.history(limit=1).flatten())[0]
    assert (f"{bot.user.mention} The current announcements channel is {guild.mention_ann}. "
            f"If you like to change the announcements channel use `test.setann`.") \
            == latest_message.content, \
            f'Message content: {latest_message.content}'
