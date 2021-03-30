import re
import os
import click
import pytest
import random
import asyncio
import discord
from sqlalchemy import delete
from bdaybot.tables import DiscordUser


@pytest.mark.asyncio
async def test_setID(bot, session, valid_ids, channel, mock_delete, dashes, timeout):
    # Test that the bot does not accept invalid IDs
    invalid_id = 1_000_000
    message = await channel.send(f'test.setID {invalid_id}')
    latest_message = await bot.wait_for('message',
                                        timeout=timeout,
                                        check=lambda message: re.search(r'\*\*\d{7}\*\*', message.content))
    # Make sure the message is attempted to be deleted
    discord.message.delete_message.assert_awaited_with(message)
    # NOTE: For some reason when using fetch_message it doesn't
    # fetch the latest message
    assert f'**{invalid_id}** is not a valid ID. Please use a valid 6-digit ID.' \
           == latest_message.content, \
           f'Message content: {latest_message.content}'

    # Test that the bot accepts valid IDs
    valid_id = random.choice(valid_ids); valid_ids.remove(valid_id)
    message = await channel.send(f'test.setID {valid_id}')
    latest_message = await bot.wait_for('message',
                                        timeout=timeout,
                                        check=lambda message: re.search(r'\*\*\d{6}\*\*', message.content))
    # Make sure the message is attempted to be deleted
    discord.message.delete_message.assert_awaited_with(message)
    # Check to see if the ID is properly added to the database
    the_bot = await session.get(DiscordUser, bot.user.id)
    assert the_bot, "The bot was not found in the database"
    assert the_bot.student_id == valid_id, \
           f"Bot's ID is {the_bot.student_id} it's supposed to be {valid_id}" if the_bot else \
           "the_bot is None"
    # Check to see if the message sent back is correct
    assert f'Your ID has now been set to **{valid_id}**!' == latest_message.content, \
           f'Message content: {latest_message.content}'

    # Test that the bot rejects IDs already in use
    another_valid_id = random.choice(valid_ids); valid_ids.remove(another_valid_id)
    other_user = DiscordUser(discord_user_id=1, student_id=another_valid_id)
    session.add(other_user)
    await session.commit()
    message = await channel.send(f'test.setID {another_valid_id}')
    latest_message = await bot.wait_for('message',
                                        timeout=timeout,
                                        check=lambda message: re.search(r'\*\*\d{6}\*\*', message.content))
    # Make sure the message is attempted to be deleted
    discord.message.delete_message.assert_awaited_with(message)
    # Check to see if the message sent back is correct
    assert f"**{another_valid_id}** is already in use. Please use another ID." \
           == latest_message.content, \
           f'Message content: {latest_message.content}'

    # Test that the bot updates IDs correctly
    valid_id = random.choice(valid_ids)
    message = await channel.send(f'test.setID {valid_id}')
    latest_message = await bot.wait_for('message',
                                        timeout=timeout,
                                        check=lambda message: re.search(r'\*\*\d{6}\*\*', message.content))
    # Make sure the message is attempted to be deleted
    discord.message.delete_message.assert_awaited_with(message)
    # Check to see if the ID is properly added to the database
    the_bot = await session.get(DiscordUser, bot.user.id)
    assert the_bot.student_id == valid_id, \
           f"Bot's ID is {the_bot.student_id} it's supposed to be {valid_id}" if the_bot else \
           "the_bot is None"
    # Check to see if the message sent back is correct
    assert f'Your ID has now been set to **{valid_id}**!' == latest_message.content, \
           f'Message content: {latest_message.content}'
