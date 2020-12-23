import discord
from discord.ext import commands

def fake_ctx(bot, command, guild):
    # Used to so that we can call command
    # from within the bot itself
    if isinstance(command, str):
        command = bot.get_command(command)
    if not isinstance(command, commands.Command):
        raise ValueError(f'command must be either a str or Commmand type, not {type(command)}')
    stringview = commands.view.StringView(f'{bot.parsed_command_prefix}{command.name}')
    message_dict = {
        'id': 0,
        'attachments': [],
        'embeds': [],
        'edited_timestamp': None,
        'type': None,
        'pinned': False,
        'mention_everyone': False,
        'tts': False
    }
    message_dict['content'] = f'{bot.parsed_command_prefix}{command.name}'
    message = discord.message.Message(state='lol', channel=guild.text_channels[0], data=message_dict)
    return commands.Context(message=message, bot=bot, prefix=bot.parsed_command_prefix,
                            invoked_with=command.name, view=stringview, command=command)

def apostrophe(name):
    return "'" if name[-1] == "s" else "'s"

def maybe_mention(ctx):
    return f'{ctx.author.mention} ' if ctx.guild else ''

def permissions(channel, member, permissions, condition='all'):
    if channel is None:
        return True
    condition = condition.lower()
    perms = channel.permissions_for(member)
    if isinstance(permissions, (list, tuple)):
        if condition == 'all':
            return all([getattr(perms, perm) for perm in permissions])
        elif condition == 'any':
            return any([getattr(perms, perm) for perm in permissions])
        else:
            raise ValueError((f"'{condition}' is not an acceptable condition. "
                               "The acceptable conditions are 'all' or 'any'."))
    else:
        return getattr(perms, permissions)
