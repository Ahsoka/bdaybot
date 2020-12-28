import pytest
import random
import asyncio
from bdaybot.tables import DiscordUser

@pytest.mark.asyncio
async def test_getID(bot, session, channel, valid_ids, delay):
    # Test the situation when there is no ID set
    await channel.send('test.getID')
    await asyncio.sleep(delay)
    latest_message = (await channel.history(limit=1).flatten())[0]
    assert f"{bot.user.mention} You do not currently have a registered ID. Use `test.setID` to set your ID" \
           == latest_message.content, \
           f'Message content: {latest_message.content}'

    # Test the situation with a preset ID
    valid_id = random.choice(valid_ids)
    new_user = DiscordUser(discord_user_id=bot.user.id, student_id=valid_id)
    session.add(new_user)
    await session.commit()
    await channel.send('test.getID')
    await asyncio.sleep(delay)
    latest_message = (await channel.history(limit=1).flatten())[0]
    assert f"Your ID is **{valid_id}**.  If this is a mistake use `test.setID` to change it." \
           == latest_message.content, \
           f'Message content: {latest_message.content}'

    # Delete all data in DiscordUsers
    # before moving onto the next test
    await session.run_sync(lambda sess: sess.query(DiscordUser).delete())
