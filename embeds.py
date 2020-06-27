import discord
from discord.ext import commands
import os
import datetime

# ryanid
id = 262676325846876161
# andresid
# id = 388899325885022211
# dylansid
# id = 274912077985087489

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

    aintroembed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")
    aintroembed.set_author(name="Introducing Bdaybot!", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")

def helpembed():
    global ahelpembed
    body = """
    All commands:
    ```!wish
    !showwish
    !getID
    !setID
    !upcoming```

    For help on how to use a command use ```!help !{nameofcommand}```
    e.g : ```!help wish```
    """
    ahelpembed = discord.Embed(title="",
        colour=discord.Colour(0xffffff), url="https://discordapp.com",
        description=body)

    aintroembed.set_author(name="Bdaybot's commands:", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")

def wishembed(bdaykid):
    global awishembed
    body = f"""
    ***Congratulations! You wished __{bdaykid}__ a happy birthday!***
    """
    awishembed = discord.Embed(title="",
        colour=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com",
        description=body)
    awishembed.set_author(name="Bdaybot🎁🎁🎁", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/wrapped-gift_1f381.png")

# def showwishembed()

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
    colour=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com",
    description=body)

    ahelpwish.set_author(name="!wish command", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/wrapped-gift_1f381.png")

def birthdayembed(discorduser, irlname, age):
    global abirthday
    body = f"""
    Congratulations to ***__{irlname}__*** ({discorduser.mention}) on turning ***__{age}__*** !
    """
    abirthday = discord.Embed(title="",
    colour=discord.Colour(0xe86eff), url="https://discordapp.com",
    description=body)

    abirthday.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")
    abirthday.set_author(name=f"Happy Birthday to {irlname}!!!", icon_url=discorduser.avatar_url_as(format=None, static_format='webp', size=1024))

def helpgetidembed():
    global ahelpgetid
    body = f"""
    Use ```!help getid``` to get your id (check if it's correct!) from a private message from the Bdaybot.
    """
    ahelpgetid = discord.Embed(title="",
    colour=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com",
    description=body)

def helpsetidembed():
    global asetgetid
    body = """
    Use ```!help setid``` to set or reset your id.
    e.g ```!help setid {your id}``` ```!help setid 123456```
    """
    ahelpsetid = discord.Embed(title="",
    colour=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com",
    description=body)

def helpshowwish(listofwishers):
    global ashowwish
    

@bot.command()
async def showintro(ctx):
    introembed()
    await bot.get_user(id).send(embed=aintroembed)

@bot.command()
async def showhelp(ctx):
    helpembed()
    await bot.get_user(id).send(embed=ahelpembed)

@bot.command()
async def showwish(ctx):
    wishembed("bday kid")
    await bot.get_user(dylanid).send("<@388899325885022211>", embed=awishembed)

@bot.command()
async def showshowwish(ctx):
    wishembed("wisher", "bday kid")
    await bot.get_user(dylanid).send("<@388899325885022211>", embed=awishembed)

@bot.command()
async def showhelpwish(ctx):
    helpwish()
    await bot.get_user(id).send(embed=ahelpwish)

@bot.command()
async def showbirthday(ctx):
    birthdayembed(ctx.author, 'Ryan Lee', 17)
    await bot.get_user(id).send(embed=abirthday)

@bot.command()
async def showhelpgetid(ctx):
    helpgetidembed()
    await bot.get_user(id).send(embed=ahelpgetid)

@bot.command()
async def showhelpsetid(ctx):
    helpsetidembed()
    await bot.get_user(id).send(embed=ahelpsetid)

|
