import asyncio
from copy import deepcopy
import datetime
import re2 as re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks
from sembed import SEmbed

import _pathmagic  # type: ignore # noqa
from cogs.moderation import delta_to_text
from common_resources.consts import (  # Activate_aliases,; Deactivate_aliases,; Error,; Attention,
    Activate_aliases,
    Attention,
    Deactivate_aliases,
    Error,
    Success,
)
from common_resources.settings import AutoMod, AutoModItem, DEFAULT_AUTOMOD_ITEM

if TYPE_CHECKING:
    from moderation import ModerationCog

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\-_]{23,30}\.[A-Za-z0-9\-_]{6,7}\.[A-Za-z0-9\-_]{27,40}")
INVITE_PATTERN = re.compile(r"(https?://)?((ptb|canary)\.)?(discord\.(gg|io)|discord(app)?.com/invite)/[0-9a-zA-Z]+")


class AutoModCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        Texts = bot.texts
        get_txt = bot.get_txt
        self._fetch_event = None
        if self.bot.consts.get("automod"):
            self.automod_settings: dict[int, AutoMod] = self.bot.consts["automod"]
        else:
            self.automod_settings = None
            self.bot.loop.create_task(self.fetch_automod_settings())
        if not self.save.is_running():
            self.save.start()

    @commands.group(name="automod", aliases=["am"], invoke_without_command=True)
    async def automod(self, ctx):
        await self.bot.send_subcommands(ctx)

    @automod.command("activate", aliases=Activate_aliases)
    async def activate(self, ctx: commands.Context, items: list[str]):
        for item in items:
            if not AutoModItem.__annotations__.get(item):
                return await ctx.reply(
                    embed=SEmbed(f"AutoModの設定 `{item}` が見つかりませんでした。", "`sb#help` でヘルプを参照してください。", color=Error)
                )
            self.automod_settings[int(ctx.guild.id)][item]["enabled"] = True
            await ctx.reply(
                embed=SEmbed(
                    f"`{item}` を有効化しました。",
                    f"オフにするときは`sb#automod {item} deactivate`を実行してください。",
                    color=Success,
                    fields=self.get_automod_settings_fields(ctx.guild, item),
                )
            )

    @automod.command("deactivate", aliases=Deactivate_aliases)
    async def deactivate(self, ctx: commands.Context, item: str):
        if not AutoModItem.__annotations__.get(item):
            return await ctx.reply(
                embed=SEmbed(f"AutoModの設定 `{item}` が見つかりませんでした。", "`sb#help` でヘルプを参照してください。", color=Error)
            )
        self.automod_settings[int(ctx.guild.id)][item]["enabled"] = False
        await ctx.reply(
            embed=SEmbed(
                f"`{item}` を無効化しました。",
                f"有効化するときは`sb#automod {item} activate`を実行してください。",
                color=Success,
                fields=self.get_automod_settings_fields(ctx.guild, item),
            )
        )

    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        if message.author.bot:
            return
        await self.validate_automod_settings(message.guild)
        if self.moderate_for(message, "token_spam"):
            await self.check_token_spam(message)
        if self.moderate_for(message, "invite_spam"):
            await self.check_invite_spam(message)

    def moderate_for(self, message: discord.Message, setting: str) -> bool:
        global_setting = self.automod_settings[message.guild.id]["$global"]
        setting_data = self.automod_settings[message.guild.id][setting]
        if not setting_data["enabled"]:
            return False
        if message.channel.id in setting_data["disabled_channel"] + global_setting["disabled_channel"]:
            return False
        return True

    async def check_token_spam(self, message: discord.Message):
        if TOKEN_PATTERN.search(message.content):
            warn = (
                self.automod_settings[message.guild.id]["token_spam"]["warn"]
                or self.automod_settings[message.guild.id]["$global"]["warn"]
            )
            txt = await self.add_warn(message.author, message, "トークンスパム", warn)
            await message.channel.send(
                message.author.mention,
                embed=SEmbed("トークンスパムが検出されました。", txt, color=Attention, footer="このメッセージは5秒後に削除されます。"),
                mention_author=True,
                delete_after=5,
            )
            await message.delete()

    async def check_invite_spam(self, message: discord.Message):
        if INVITE_PATTERN.search(message.content):
            warn = (
                self.automod_settings[message.guild.id]["invite_spam"]["warn"]
                or self.automod_settings[message.guild.id]["$global"]["warn"]
            )
            txt = await self.add_warn(message.author, message, "招待リンクスパム", warn)
            await message.channel.send(
                message.author.mention,
                embed=SEmbed("招待リンクスパムが検出されました。", txt, color=Attention, footer="このメッセージは5秒後に削除されます。"),
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
                    get_txt(guild.id, "warn_desc_now").format(nw, self.moderation.get_warn_text(message, pun[nw]))
                    + "\n"
                )
                await self.moderation.punish(target, pun[nw])
        return res

    @property
    def moderation(self) -> "ModerationCog":
        return self.bot.cogs["ModerationCog"]

    async def cog_check(self, ctx: commands.Context) -> bool:
        return self.automod_settings is not None

    async def fetch_automod_settings(self):
        if self._fetch_event:
            return await self._fetch_event
        self._fetch_event = asyncio.Event()
        self.automod_settings = {}
        async for item in self.bot.db.automod.find({}):
            self.automod_settings[item["id"]] = item["data"]
        self.bot.consts["automod"] = self.automod_settings
        self._fetch_event.set()

    @tasks.loop(minutes=5)
    async def save(self):
        print("-- Saving automod settings...")
        for k, v in self.automod_settings.items():
            self.bot.db.automod.replace_one({"id": k}, {"id": k, "data": v}, upsert=True)

    async def validate_automod_settings(self, guild: discord.Guild):
        if self.automod_settings is None:
            await self.fetch_automod_settings()
        if guild.id not in self.automod_settings:
            self.automod_settings[guild.id] = dict([[i, (DEFAULT_AUTOMOD_ITEM)] for i in AutoMod.__annotations__])
        if missing_keys := (set(AutoMod.__annotations__) - set(self.automod_settings[guild.id])):
            for key in missing_keys:
                self.automod_settings[guild.id][key] = deepcopy(DEFAULT_AUTOMOD_ITEM)

    async def cog_before_invoke(self, ctx: commands.Context) -> None:
        await self.validate_automod_settings(ctx.guild)

    def cog_unload(self):
        self.save.stop()


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(AutoModCog(_bot), override=True)
