# flake8: noqa
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


class TemplateCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        self.bot.guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt


async def setup(_bot):
    global bot
    bot = _bot
    await _bot.add_cog(TemplateCog(_bot), override=True)
