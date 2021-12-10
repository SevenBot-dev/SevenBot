import discord
from discord.ext import commands

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (
    Activate_aliases,
    Deactivate_aliases,
    Error,
    Info,
    Success,
)


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        Texts = bot.texts
        get_txt = bot.get_txt


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(AutoModCog(_bot), override=True)
