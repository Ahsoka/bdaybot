import pytest
import random
import asyncio
import discord
import datetime
import pandas

from bdaybot.tables import DiscordUser, StudentData
from sqlalchemy import select, delete
from bdaybot.tables import Wish
from bdaybot.data import values

@pytest.mark.asyncio
async def test_wish(bot, session, channel, mocker, mock_delete, valid_ids, timeout):
    test_df = pandas.DataFrame({
        'FirstName': ['Captain', 'Commander', 'Ahsoka'],
        'LastName': ['Rex', 'Cody', 'Tano'],
        'Birthdate': (datetime.date.today(),) * 3,
        'Timedelta': (datetime.timedelta(),) * 3
    }, index=random.sample(valid_ids, k=3))
    one_row_in_df = test_df.iloc[:1]
    wishee = 'Ahsoka'
    wishee_series = test_df[test_df["FirstName"] == wishee].iloc[0]
    wishee_fullname = f"{wishee_series['FirstName']} {wishee_series['LastName']}"
    wishee_id = int(test_df.index[test_df["FirstName"] == wishee].values[0])
    student = await session.get(StudentData, wishee_id)

    # Test the situation when there is no birthday
    mocker.patch("bdaybot.data.values.today_df", new_callable=mocker.PropertyMock, return_value=test_df)
    mocker.patch("bdaybot.data.values.bday_today", new_callable=mocker.PropertyMock, return_value=False)
    await channel.send(f"test.wish")
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    assert "You cannot use the `test.wish`" in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    mocker.patch.object(values, "bday_today", return_value=True)

    # Test the situation when the user does not include their ID
    await channel.send(f"test.wish")
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    assert "You are first-time wisher." in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    # Test the situation when the user submits an invalid ID
    invalid_id = 1_000_000
    message = await channel.send(f"test.wish {invalid_id}")
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    # Make sure the message was deleted
    discord.message.delete_message.assert_awaited_with(message)
    assert "Your ID is invalid" in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    # Test the situation when the user submits a valid ID (that is in the birthday database)
    # but does not specify who they want to wish a happy
    # birthday, when it is multiple people's birthday
    valid_id = random.choice(values.bday_df.index)
    message = await channel.send(f"test.wish {valid_id}")
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    # Make sure the message was deleted
    discord.message.delete_message.assert_awaited_with(message)
    # We need to sleep here since the transaction
    # is commited AFTER the message is sent
    await asyncio.sleep(0.5)
    # Make sure the user was added to the `discord_users` table
    the_bot = await session.get(DiscordUser, bot.user.id)
    assert the_bot.student_id == valid_id, \
        f"Bot's ID is {the_bot.student_id} it's supposed to be {valid_id}" if the_bot else \
        "the_bot is None"
    # Make sure the proper message is sent back
    assert "You must specify who you want wish a happy birthday!" in latest_message.embeds[0].description, \
    f'Message content(embed): {latest_message.embeds[0].description}'

    # Test the situation when there is an invalid first and last name and a previously set ID,
    # see https://github.com/Ahsoka/bdaybot/commit/5c026ea981def9def84356e5c9de6033614bd682
    await channel.send(f"test.wish Governor Tarkin")
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    assert 'is not a name in the birthday database!' in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    # Test the situation when the user submits a different valid ID (that is in the birthday database)
    # than the one they previously submitted
    # Make sure that another_valid_id != valid_id
    another_valid_id = valid_id
    while another_valid_id == valid_id:
        another_valid_id = random.choice(values.bday_df.index)

    message = await channel.send(f"test.wish {another_valid_id}")
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    # Make sure the message was deleted
    discord.message.delete_message.assert_awaited_with(message)
    assert 'The ID you submitted does not match the ID you submitted previously' in latest_message.embeds[0].description, \
    f'Message content(embed): {latest_message.embeds[0].description}'

    # Test the situation when the user wishes someone without putting the name when it is multiple people's birthdays with a previously set # ID
    await channel.send(f'test.wish')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    assert f"You must specify" in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    # Test the situation when the user wishes someone
    # with a first name with a previously set ID
    await channel.send(f'test.wish {wishee}')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    assert f"You wished ***__{student.fullname}__*** a happy birthday!" in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'
    # Make sure the bot is added to the wishes table (with the correct year)
    wish = await session.get(Wish, (bot.user.id, datetime.date.today().year, wishee_id))
    assert wish is not None, 'Wish was not added to the database'

    # Test the situation when a second user wishes someone
    # with a full name with a previously set ID
    # DEBUG: We will mimic the second user by the deleting all the
    # data in the 'wishes' table.
    await session.execute(delete(Wish))
    await channel.send(f'test.wish {wishee_fullname}')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    wishlist = (await session.execute(select(Wish))).one()
    assert f"You wished ***__{student.fullname}__*** a happy birthday!" in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    # Test the situation when the user tries to wish
    # the same person twice
    await channel.send(f'test.wish {wishee}')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    assert f"Try wishing someone else a happy birthday!" in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    #Test situation where user wishes without specifying name on one person's birthday with a previously set ID
    await session.execute(delete(Wish))
    mocker.patch("bdaybot.data.values.today_df", new_callable=mocker.PropertyMock, return_value=test_df.loc[test_df['FirstName'] == wishee])
    await channel.send(f'test.wish')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    assert f"You wished ***__{student.fullname}__*** a happy birthday!" in latest_message.embeds[0].description, \
        f'Message content(embed): {latest_message.embeds[0].description}'

    # TODO:
    # Test the situation when a user submits with
    # a previously set ID submits their ID again

    # TODO:
    # Test the situation where a user tries to wish
    # someone who is in the database but there birthday
    # is not today.

    # TODO: Make it so you can run this test multiple times in a row
