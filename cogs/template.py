import discord
from discord.ext import commands

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (Activate_aliases, Deactivate_aliases,
                                     Info, Success, Error)


class TemplateCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts, Official_emojis
        global get_txt
        self.bot: commands.Bot = bot
        Guild_settings = bot.guild_settings
        Official_emojis = bot.consts["oe"]
        Texts = bot.texts
        get_txt = bot.get_txt


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(TemplateCog(_bot), override=True)
