import pytest
import random
import asyncio
import discord

@pytest.mark.asyncio
async def test_upcoming(bot, channel, timeout):
    # Test when the user types a number less than 1
    await channel.send('test.upcoming -1')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: channel.guild.me in message.mentions
    )
    assert "**-1** is less than 1. Please use a number" in latest_message.content, \
        f"Message content: {latest_message.content}"
    # Test the standard usage of the upcoming command
    await channel.send('test.upcoming')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    # Check if latest_message has any embeds
    assert latest_message.embeds, f"latest_message does not have any embeds, {latest_message}"
    # Check if latest_message embed has three fields
    assert len(latest_message.embeds[0].fields) == 3, f"Num of field: {len(latest_message.embeds[0].fields)}"
    # Check if the first field name is 'Name'
    assert latest_message.embeds[0].fields[0].name == 'Name', \
        f"first field name: {latest_message.embeds[0].fields[0].name}"
    # Check to see if there are five rows in the 'Name' field
    assert len(latest_message.embeds[0].fields[0].value.splitlines()) == 5, \
        f"Number of rows: {len(latest_message.embeds[0].fields[0].value.splitlines())}"
    # Test the upcoming command with a number between 1 and 10 (inclusive on both sides)
    num_of_rows = random.randint(1, 10)
    await channel.send(f'test.upcoming {num_of_rows}')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    # Check if latest_message has any embeds
    assert latest_message.embeds, "latest_message does not have any embeds"
    # Check if latest_message embed has three fields
    assert len(latest_message.embeds[0].fields) == 3, f"Num of field: {len(latest_message.embeds[0].fields)}"
    # Check if the first field name is 'Name'
    assert latest_message.embeds[0].fields[0].name == 'Name', \
        f"first field name: {latest_message.embeds[0].fields[0].name}"
    # Check to see if there are num_of_rows rows in the 'Name' field
    assert len(latest_message.embeds[0].fields[0].value.splitlines()) == num_of_rows, \
        f"Number of rows: {len(latest_message.embeds[0].fields[0].value.splitlines())}"
    # Test the upcoming command with a number greater than 10
    num_of_rows = 1_000
    await channel.send(f'test.upcoming {num_of_rows}')
    latest_message = await bot.wait_for(
        'message',
        timeout=timeout,
        check=lambda message: message.embeds
    )
    # Check if latest_message has any embeds
    assert latest_message.embeds, "latest_message does not have any embeds"
    # Check if latest_message embed has three fields
    assert len(latest_message.embeds[0].fields) == 3, f"Num of field: {len(latest_message.embeds[0].fields)}"
    # Check if the first field name is 'Name'
    assert latest_message.embeds[0].fields[0].name == 'Name', \
    f"first field name: {latest_message.embeds[0].fields[0].name}"
    # Check to see if there are five rows in the 'Name' field
    assert len(latest_message.embeds[0].fields[0].value.splitlines()) == 10, \
        f"Number of rows: {len(latest_message.embeds[0].fields[0].value.splitlines())}"
    # Check to see if there is a footer
    assert isinstance(
        latest_message.embeds[0].footer,
        discord.embeds.EmbedProxy
    ), f'Type footer: {type(latest_message.footer)}'
    # TODO (maybe): Check the content of the field instead of checking the number of rows
