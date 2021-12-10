import datetime
import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from sembed import SEmbed

import _pathmagic  # type: ignore # noqa
from cogs.moderation import delta_to_text
from common_resources.consts import (  # Activate_aliases,; Deactivate_aliases,; Error,; Attention,
    Attention,
    Success,
)

if TYPE_CHECKING:
    from moderation import ModerationCog

token_pattern = re.compile(r"[A-Za-z0-9\-_]{23,30}\.[A-Za-z0-9\-_]{6,7}\.[A-Za-z0-9\-_]{27,40}")


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.group(name="automod", aliases=["am"], invoke_without_command=True)
    async def automod(self, ctx):
        await self.bot.send_subcommands(ctx)

    @automod.command("token")
    async def automod_token(self, ctx, warn: int):
        self.bot.guild_settings[ctx.guild.id]["automod"]["token_spam"] = warn
        await ctx.reply(embed=SEmbed("トークンスパムの設定を変更しました。", f"Warn回数: {warn}", color=Success))

    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        if message.author.bot:
            return
        if ts := self.bot.guild_settings[message.guild.id]["automod"]["token_spam"]:
            await self.check_token_spam(message, ts)

    async def check_token_spam(self, message, ts):
        if token_pattern.search(message.content):
            txt = await self.add_warn(message.author, message, "トークンスパム", ts)
            await message.channel.send(
                message.author.mention,
                embed=SEmbed("トークンスパムが検出されました。", txt, color=Attention, footer="このメッセージは5秒後に削除されます。"),
                mention_author=True,
                delete_after=5,
            )
            await message.delete()

    def get_warn_text(self, bot, message, p):
        res = get_txt(message.guild.id, "warn_punish")[p["action"]]
        if p["action"] == "mute":
            res += f'({delta_to_text(datetime.timedelta(seconds=p["length"]), message)})'
        elif p["action"] in ("role_add", "role_remove"):
            r = message.guild.get_role(p["role"])
            res += f"({r.name})"
        return res

    async def add_warn(self, target: discord.User, message: discord.Message, reason: str, level: int):
        guild = message.guild
        if not self.bot.guild_settings[guild.id]["warns"].get(target.id):
            self.bot.guild_settings[guild.id]["warns"][target.id] = 0
        res = get_txt(guild.id, "warn_desc_info").format(
            target, self.bot.guild_settings[guild.id]["warns"][target.id] + level
        )
        for _ in range(level):
            self.bot.guild_settings[guild.id]["warns"][target.id] += 1
            if self.bot.guild_settings[guild.id]["warns"][target.id] < 0:
                self.bot.guild_settings[guild.id]["warns"][target.id] = 0
            elif self.bot.guild_settings[guild.id]["warns"][target.id] >= 2 ** 64:
                self.bot.guild_settings[guild.id]["warns"][target.id] = 2 ** 64 - 1
            pun = self.bot.guild_settings[guild.id]["warn_settings"]["punishments"]
            nw = self.bot.guild_settings[guild.id]["warns"][target.id]
            if pun.get(nw):
                res += (
                    get_txt(guild.id, "warn_desc_now").format(
                        nw, self.moderation.get_warn_text(message, pun[nw])
                    )
                    + "\n"
                )
                await self.moderation.punish(target, pun[nw])
        return res

    @property
    def moderation(self) -> "ModerationCog":
        return self.bot.cogs["ModerationCog"]


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(AutoModCog(_bot), override=True)
