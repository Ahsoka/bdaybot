import discord
from discord.ext import commands
import os
import datetime
import itertools

# ryanid
# id = 262676325846876161
# andresid
# id = 388899325885022211
# dylansid
# id = 274912077985087489

# bot = commands.Bot(command_prefix='!')

class classproperty:
    def __init__(self, func):
        self.func = func

    def __get__(self, func_self, func_cls):
        return self.func(func_cls)

class bdaybot_embeds:
    introduction_text = """
    ```The Bday bot has been been revamped again!

With the help of a couple reaaaally awesome people (including me), we got rid of most of the old code and created the
new bdaybot on one language (Python!), and we moved the location of the Bday bot server onto a small, yet powerful, raspberry pi.

But that's not it! The Bday bot not only prints birthday statements every 24 hours, but it also
has a bunch of other methods (use ```!help``` to see all the commands)```
    """
    @classproperty
    def introembed_cls(cls):
        aintroembed = discord.Embed(title="", color=discord.Color(0xe86eff), url="https://discordapp.com", description=cls.introduction_text)
        aintroembed.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")
        aintroembed.set_author(name="Introducing Bdaybot!", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")
        return aintroembed


    help_text = """
    All commands:
    ```!wish
    !upcoming
    !showwish
    !getID
    !setID
    !getannouncements
    !setannouncements```

    For help on how to use a command use ```!help !{nameofcommand}```
    e.g : ```!help wish```
    """
    @classproperty
    def helpembed(cls):
        ahelpembed = discord.Embed(title="", color=discord.Color(0xffffff), url="https://discordapp.com", description=cls.help_text)
        ahelpembed.set_author(name="Bdaybot's commands:", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")
        return ahelpembed

    wish_text = """
    {} Congrats! 🎈🌟🎉
    You wished __{}__ a happy birthday!
    """
    @classmethod
    def wishembed(cls, bdaykid, wisher):
        awishembed = discord.Embed(title="", color=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com",
                                   description=cls.wish_text.format(wisher.mention, bdaykid))
        awishembed.set_author(name="Bdaybot🎁🎁🎁", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/wrapped-gift_1f381.png")
        return awishembed

    helpwish_text = """
    This command is unavailable when it is noone's birthday today.

    When it is one person's birthday today, use ```!wish``` to wish that person
    a happy birthday

    when it is multiple people's birthday today use ```!wish {name of person's birthday}```
    e.g, if it is ***Ryan Lee's*** birthday, use  ```!wish Ryan Lee``` or ```!wish Ryan``` or
    ```!wish ryan``` or ```!wish lee```
    """
    @classproperty
    def helpwish(cls):
        ahelpwish = discord.Embed(title="", color=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com",
                                  description=cls.helpwish_text)
        ahelpwish.set_author(name="!wish command", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/wrapped-gift_1f381.png")
        return ahelpwish

    birthdayembed_text = "Congratulations to ***__{}__*** ({}) on turning ***__{}__*** !!!🎈🌟🎉"
    @classmethod
    def birthdayembed(cls, discorduser, irlname, age):
        abirthday = discord.Embed(title="", color=discord.Color(0xe86eff), url="https://discordapp.com", description=cls.birthdayembed_text.format(irlname, discorduser.mention, age))
        abirthday.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")
        abirthday.set_author(name=f"Happy Birthday to {irlname}!!!", icon_url=discorduser.avatar_url_as(format=None, static_format='webp', size=1024))
        return abirthday

    helpgetid_text = "Use `!getid` to get your id (check if it's correct!) from a private message from the Bdaybot."
    @classproperty
    def helpgetidembed(cls):
        ahelpgetid = discord.Embed(title="", colour=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com", description=cls.helpgetid_text)
        return ahelpgetid

    helpsetid_text = """
    Use `!help setid` to set or reset your id.
    e.g `!help setid {your id}` `!help setid 654321`
    """
    @classproperty
    def helpsetidembed(cls):
        ahelpsetid = discord.Embed(title="", color=discord.Color.from_rgb(254, 254, 254), url="https://discordapp.com", description=cls.helpsetid_text)
        return ahelpsetid

    @staticmethod
    def helpshowwish(listofwishers, listofwishersdisc, bdaykiddisc, bdaykidname):
        # list of wishersdisc is a list of the disc names of the people that wished bdaydisc
        # listofwishers is a list of the fullanmes of the poeple that wished bdaykiddisc
        # bdaykidname is the full name of the person who is getting wished
        ashowwish = discord.Embed(title="", color=discord.Color(0xe86eff), url="https://discordapp.com", description="")
        abirthday.set_thumbnail(url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/241/partying-face_1f973.png")
        ashowwish.set_author(name=f"{bdaykidname}'s Birthday Wishers'", icon_url=bdaykiddisc.avatar_url_as(format=None, static_format='webp', size=1024))
        for wishers, discwishers in zip(listofwishers, listofwishersdisc):
            ashowwish.add_field(name=wishers, value=discwishers)

        return ashowwish

    setannouncements_text = """
    This function sets the channel where the bot should send its announcements.

    To use this function, go to the desired channel and type `!setannouncements`
    """
    @classproperty
    def helpsetannouncements(cls):
        ashowsetannouncements = discord.Embed(title="", color=discord.Color(0xe86eff), url="https://discordapp.com", description=cls.setannouncements_text)
        ahshowsetannouncements.set_author(name="!setannouncements command📢",
                                            icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/microsoft/209/public-address-loudspeaker_1f4e2.png")
        return ashowsetannouncements

    getannouncements_text = """
    This function returns the channel where the bot sends the announcements.
    To use the function, do `!getannouncements` in any channel.
    """

    @classproperty
    def helpgetannouncements(cls):
        ashowgetannouncements = discord.Embed(title="", color=discord.Color(0xe86eff), url="https://discordapp.com", description=cls.getannouncements_text)
        ahshowgetannouncements.set_author(name="!getannouncements command📢",
                                          icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/microsoft/209/public-address-loudspeaker_1f4e2.png")
        return ashowgetannouncements

    helpupcoming_text = """
    This function returns the upcoming birthdays
    `!upcoming` and `!up` returns the next 5 birthdays
    If you want a certain amount of birthdays, then use `!upcoming 69` or `!up 69` to get 69 birthdays
    e.g `!up 3` or `!upcoming 3`
    """

    @classproperty
    def helpupcoming(cls):
        ashowupcoming = discord.Embed(title="", color=discord.Color(0xe86eff), url="https://discordapp.com", description="")
        ashowupcoming.set_author(name="!upcoming command📅", icon_url="https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/microsoft/209/calendar_1f4c5.png")
        return ashowupcoming

# @bot.command()
# async def showintro(ctx):
#     introembed()
#     await bot.get_user(id).send(embed=aintroembed)
#
# @bot.command()
# async def showhelp(ctx):
#     helpembed()
#     await bot.get_user(id).send(embed=ahelpembed)
#
# @bot.command()
# async def showwish(ctx):
#     wishembed("bday kid")
#     await bot.get_user(dylanid).send("<@388899325885022211>", embed=awishembed)
#
# @bot.command()
# async def showshowwish(ctx):
#     wishembed("wisher", "bday kid")
#     await bot.get_user(dylanid).send("<@388899325885022211>", embed=awishembed)
#
# @bot.command()
# async def showhelpwish(ctx):
#     helpwish()
#     await bot.get_user(id).send(embed=ahelpwish)
#
# @bot.command()
# async def showbirthday(ctx):
#     birthdayembed(ctx.author, 'Ryan Lee', 17)
#     await bot.get_user(id).send(embed=abirthday)
#
# @bot.command()
# async def showhelpgetid(ctx):
#     helpgetidembed()
#     await bot.get_user(id).send(embed=ahelpgetid)
#
# @bot.command()
# async def showhelpsetid(ctx):
#     helpsetidembed()
#     await bot.get_user(id).send(embed=ahelpsetid)
