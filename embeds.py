import discord
from discord.ext import commands
import os
import datetime

myid = 262676325846876161
andresid = 388899325885022211

bot = commands.Bot(command_prefix='!')

def introembed():
    introduction = """
    ```The Bday bot has been been revamped!

With the help of a couple reaaaally awesome people (including me), we got rid of most of the old code and created the
new bdaybot on one language (Python!), and we moved the location of the Bday bot server onto a small, yet powerful, raspberry pi.

But that's not it! The Bday bot not only prints birthday statements every 24 hours, but it also
has a bunch of other methods (!wish, !showwish, ...)```
    """
    global aintroembed
    aintroembed = discord.Embed(title="",
        colour=discord.Colour(0xe86eff), url="https://discordapp.com",
        description=introduction)

    aintroembed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/face-with-party-horn-and-party-hat_1f973.png")
    aintroembed.set_author(name="Introducing Bdaybot!", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/face-with-party-horn-and-party-hat_1f973.png")

def helpembed():
    global ahelpembed
    body = """
    ```!wish
    !showwish
    !getID
    !setID```

    for how info on a command use ```!help !{nameofcommand}```
    e.g : ```!help wish```
    """
    ahelpembed = discord.Embed(title="",
        colour=discord.Colour(0xffffff), url="https://discordapp.com",
        description=body)

    aintroembed.set_author(name="Bdaybot's commands:", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/face-with-party-horn-and-party-hat_1f973.png")

def wishembed(author, bdaykid):
    global awishembed
    body = f"""
    ***__{author}__ has wished __{bdaykid}__ a happy birthday!***
    """
    awishembed = discord.Embed(title="",
        colour=discord.Colour(0xe86eff), url="https://discordapp.com",
        description=body)
    awishembed.set_author(name="Bdaybot", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/face-with-party-horn-and-party-hat_1f973.png")

def helpwish():
    global ahelpwish
    body = """
    This command is unavailable when it is noone's birthday today.

    When it is one person's birthday today, use ```!wish``` to wish that person
    a happy birthday

    when it is multiple people's birthday today use ```!wish {name of person's birthday}```
    e.g, if it is ***Ryan Lee's*** birthday, use  ```!wish Ryan Lee``` or ```!wish Ryan``` or
    ```!wish ryan``` or ```!wish lee```
    """
    ahelpwish = discord.Embed(title="",
    colour=discord.Colour(0xffffff), url="https://discordapp.com",
    description=body)
    ahelpwish.setauthor(name="!wish command", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/face-with-party-horn-and-party-hat_1f973.png")

def birthdayembed(discorduser, irlname, age):
    global abirthday
    body = f"""
    Congratulations to {irlname} on turning {age}!
    """
    abirthday = discord.Embed(title="",
    colour=discord.Colour(0xe86eff), url="https://discordapp.com",
    description=body)

    embed.set_image(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/face-with-party-horn-and-party-hat_1f973.png")
    ahelpwish.setauthor(name="!wish command", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/apple/237/face-with-party-horn-and-party-hat_1f973.png")
    aintroembed.set_thumbnail(url=discorduser.avatar_url_as(*, format=None, static_format='webp', size=1024))
    aintroembed.set_author(name=f"Happy Birthday to {discorduser.mention}!!!", icon_url=discorduser.avatar_url_as(*, format=None, static_format='webp', size=1024))


embed = discord.Embed(title="title ~~(did you know you can have markdown here too?)~~", colour=discord.Colour(0x9a3c7d), url="https://discordapp.com", description="this supports [named links](https://discordapp.com) on top of the previously shown subset of markdown. ```\nyes, even code blocks```", timestamp=datetime.datetime.utcfromtimestamp(1593111022))

embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
embed.set_author(name="author name", url="https://discordapp.com", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")

embed.add_field(name="🤔", value="some of these properties have certain limits...")
embed.add_field(name="😱", value="try exceeding some of them!")
embed.add_field(name="🙄", value="an informative error should show up, and this view will remain as-is until all issues are fixed")
embed.add_field(name="<:thonkang:219069250692841473>", value="these last two", inline=True)
embed.add_field(name="<:thonkang:219069250692841473>", value="are inline fields", inline=True)

await bot.say(content="this `supports` __a__ **subset** *of* ~~markdown~~ 😃 ```js\nfunction foo(bar) {\n  console.log(bar);\n}\n\nfoo(1);```", embed=embed)

@bot.command()
async def showintro(ctx):
    introembed()
    await bot.get_user(andresid).send(embed=aintroembed)

@bot.command()
async def showhelp(ctx):
    helpembed()
    await bot.get_user(andresid).send(embed=ahelpembed)

@bot.command()
async def showwish(ctx):
    wishembed("wisher", "bday kid")
    await bot.get_user(andresid).send(embed=awishembed)

@bot.command()
async def showhelpwish(ctx):
    helpwish()
    await bot.get_user(andresid).send(embed=ahelpwish)

@bot.command()
async def showbirthday(ctx):
    birthdayembed()
    await bot.get_user(andresid).send(embed=abirthday())

# @bot.command()
# async def showbirthday(ctx):
#     birthdayembed()
#     await bot.get_user(andresid).send(embed=ahelpwish)

@bot.event
async def on_ready():
    print('Online!')

bot.run(os.environ['testing_token'])
