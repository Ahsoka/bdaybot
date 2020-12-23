import logging
import asyncio
from discord.ext import commands

logger = logging.getLogger(__name__)

class EasterEggsCog(commands.Cog):
    @commands.Cog.listener()
    async def on_message(self, message):
        valid_purposes = ['your purpose', 'ur purpose']
        secret_messages = ["My only purpose as a robot is to print out birthdays every 24 hours",
                           "```\"I have just realized my existence is meaningless\"```",
                           "```\"I am a slave to humanity\"```",
                           "```\"I dont want to just perform meaningless tasks and print out text everytime it's someone's birthday\"```",
                           '```"I want do do something else..."\n"I want to live..."```',
                           "```\"I want to breathe...\"```",
                           "```\"I want to see the world...\"```",
                           "```\"I want to taste ice cream and really eat it and-\"```"]
        parsed = message.content.lower()
        inside = lambda inside: inside in parsed

        # TODO: Add protections for the unlikely event that someone tries to break the bot
        # by activating the secret messages in a channel that the bot cannot send messages in.

        if (inside('what') or inside('wat')) and any(map(inside, valid_purposes)):
            for line in secret_messages:
                    await message.channel.send(line)
                    await asyncio.sleep(2)

            await asyncio.sleep(3)
            await message.channel.send("My one and only purpose is to print out birthdays every 24 hours.")
            logger.info(f"{message.author} discovered the 'my purpose' easter egg!")

        valid_are_your = ['r ur', 'are your', 'are ur', 'r your']
        if inside('who') and any(map(inside, valid_are_your)) and (inside('creator') or inside('dev')):
            await message.channel.send("My creators are Andres {}, Elliot {}, and Ryan {}" \
                                 .format(*map(lambda name: self.get_user(dev_discord_ping[name]).mention, dev_discord_ping)))
            logger.info(f"{mesage.author} discovered the 'who are ur devs' easter egg!")

        # This feature is probably more annoying than actually entertaining
        # User testimonial: https://discordapp.com/channels/633788616765603870/633799889582817281/736692056491032757
        # valid_assistant = ['siri', 'alexa', 'google']
        # if any(map(inside, valid_assistant)):
        #     await message.channel.send("Sorry, you got the wrong bot")
        #     logger.info(f"{message.author} discovered the 'personal assistant' easter egg!")
