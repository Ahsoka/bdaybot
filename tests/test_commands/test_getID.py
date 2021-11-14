import re
import pytest
import random
import asyncio

from sqlalchemy import delete, select
from bdaybot.tables import DiscordUser

@pytest.mark.asyncio
async def test_getID(bot, session, channel, valid_ids, timeout):
    # Test the situation when there is no ID set
    await channel.send('test.getID')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: channel.guild.me in message.mentions
    )
    assert f"{bot.user.mention} You do not currently have a registered ID. Use `test.setID` to set your ID" \
        == latest_message.content, f'Message content: {latest_message.content}'

    # Test the situation with a preset ID
    valid_id = random.choice(valid_ids)
    new_user = DiscordUser(discord_user_id=bot.user.id, student_id=valid_id)
    session.add(new_user)
    await session.commit()
    await channel.send('test.getID')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: re.search(r'\*\*\d{6}\*\*', message.content)
    )
    assert f"Your ID is **{valid_id}**.  If this is a mistake use `test.setID` to change it." \
        == latest_message.content, f'Message content: {latest_message.content}'
