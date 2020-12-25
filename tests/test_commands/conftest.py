import pytest

@pytest.fixture(scope='package')
async def bot(bot):
    bot.add_cog(bot.commands_cog)
    yield bot
    bot.remove_cog('CommandsCog')
