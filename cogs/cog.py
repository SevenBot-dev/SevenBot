import asyncio
import collections
import copy
import datetime
import hashlib
import inspect
import math
import os
import platform
import random
import re
import sys
import time
import traceback
import urllib.parse
from typing import TYPE_CHECKING, Optional, Union

import aiohttp
import discord
import sentry_sdk
from async_google_trans_new import AsyncTranslator
from discord import Forbidden, NotFound
from discord.ext import commands, components, syntaxer
from discord.ext.commands import BadArgument, CommandNotFound, Context
from sembed import SAuthor, SEmbed, SField
from texttable import Texttable

import _pathmagic  # type: ignore # noqa: F401
from common_resources.consts import (
    Activate_aliases,
    Alert,
    Bot_info,
    Chat,
    Deactivate_aliases,
    Error,
    Event_dict,
    Info,
    Official_discord_id,
    Owner_ID,
    Success,
    Widget,
)
from common_resources.settings import DEFAULT_SETTINGS
from common_resources.tools import flatten, remove_emoji

if TYPE_CHECKING:
    from ..main import SevenBot


Categories = {
    "bot": [
        "help",
        "about",
        "tos",
        "ping",
        "invite",
        "tips",
        "search_command",
        "follow",
    ],
    "server": [
        "get_role_count",
        "get_role_member",
        "get_permissions",
        "level",
        "level_ranking",
        "serverinfo",
        "emoji_list",
    ],
    "info": ["lookup", "check_url", "getid", "snowflake"],
    "panel": ["vote", "party", "top"],
    "tools": ["translate", "afk", "shorten"],
    "fun": [
        "werewolf",
        "bignum",
        "tic_tac_toe",
        "parse",
        "image",
        "kana_talk",
        "sudden_death",
        "loop_trans",
        "reencode",
    ],
    "serverpanel": ["auth", "role", "ticket", "free_channel"],
    "moderation": ["clear_channel", "mute", "fatal", "lockdown", "archive", "warn", "unwarn"],
    "global": ["gchat", "sevennet", "sgc"],
    "settings": [
        "ww_role",
        "autoreply",
        "timed_role",
        "channel_settings",
        "level_settings",
        "expand_message",
        "event_channel",
        "event_send",
        "role_link",
        "bump",
        "dissoku",
        "lang",
        "change_prefix",
        "server_stat",
        "warn_settings",
        "automod",
        "auto_text",
        "gban_settings",
        "lock_message",
    ],
}
Last_favorite = {}
Time_format = "%Y-%m-%d %H:%M:%S"
Image_exts = ["gif", "jpg", "jpeg", "jpe", "jfif", "png", "bmp", "ico"]
Link_2ch_re = re.compile(r">>[0-9]+")
Sevennet_footer_re = re.compile(r"Server: (.+?) | ID: (.{8}) | [±\-\+](\d+) \( \+(\d+) / -(\d+) \)")
Mention_re = re.compile(r"<@\!?(\d+?)>")
Channel_ids = {
    "log": 756254787191963768,
    "announce": 756254915441197206,
    "emoji_print": 756254956817743903,
    "global_report": 756255003341225996,
    "boot_log": 747764100922343554,
}
Blacklists = []
Squares = [
    "yellow_square",
    "white_large_square",
    "brown_square",
    "black_large_square",
    "black_small_square",
]
Channels = {}
Sevennet_channels = []
Sevennet_posts = {}
Sevennet_replies = {}
DBL_id = 264445053596991498


def text_to_delta(delta, ctx):
    s = math.floor(delta.seconds)
    res = ""
    if delta.days:
        res += str(delta.days) + get_txt(ctx.guild.id, "delta_txt")[0]
    if s >= 3600:
        res += str(s // 3600) + get_txt(ctx.guild.id, "delta_txt")[1]
    if s >= 60:
        res += str((s // 60) % 60) + get_txt(ctx.guild.id, "delta_txt")[2]
        if s < 3600:
            res += get_txt(ctx.guild.id, "delta_txt")[4]
        if s % 60 != 0:
            res += str(s % 60) + get_txt(ctx.guild.id, "delta_txt")[3]
        return res
    elif not delta.seconds:
        return res
    else:
        return res + str(s % 60) + get_txt(ctx.guild.id, "delta_txt")[3] + get_txt(ctx.guild.id, "delta_txt")[4]


Number_emojis = []
Trans = 0x1A73E8

SB_Bans = {}

translator = AsyncTranslator()


class MainCog(commands.Cog):
    def __init__(self, bot):
        global Texts, Global_chat, Command_counter, Global_mute, GBan
        global Sevennet_channels, Sevennet_posts, Blacklists
        global get_txt, is_command
        self.bot: commands.Bot = bot
        if not self.bot.consts.get("gcm"):
            self.bot.consts["gcm"] = collections.defaultdict(dict)
        try:
            get_txt = self.bot.get_txt
            is_command = self.bot.is_command
            Global_chat = self.bot.raw_config["gc"]
            Command_counter = self.bot.raw_config["cc"]
            Sevennet_channels = self.bot.raw_config["snc"]
            Sevennet_posts = self.bot.raw_config["snp"]
            Global_mute = self.bot.raw_config["gm"]
            Blacklists = self.bot.raw_config["il"]
            GBan = self.bot.raw_config["gb"]
            Texts = self.bot.texts
            for i in range(11):
                Number_emojis.append(self.bot.oemojis["b" + str(i)])
        except Exception as e:
            raise e

    async def send_reaction(self, channel, reactions, message):
        m = await channel.send(**message)
        g = []
        for r in reactions:
            if r in self.bot.oemojis.keys():
                e = self.bot.oemojis[r]
            else:
                e = r
            g.append(m.add_reaction(e))
        ga = asyncio.gather(*g)
        await ga
        return m

    @commands.Cog.listener()
    async def on_ready(self):
        loop = asyncio.get_event_loop()

        async def send_boot_log():
            msg = await Channels["boot_log"].send("起動完了。")
            await msg.publish()

        loop.create_task(send_boot_log())
        self.bot.consts["gcm"] = collections.defaultdict(dict)
        await self.bot.get_channel(800628621010141224).send("reload")

    @commands.Cog.listener(name="on_guild_remove")
    async def on_guild_remove(self, g):
        if g.id in Blacklists:
            return
        elif g.name is None:
            return
        await self.bot.get_channel(756254787191963768).send(
            "サーバー退出", embeds=[SEmbed("<サーバー退出>", f"名前：{g.name}\nID：{g.id}", color=discord.Color.red())]
        )
        await self.bot.db.guild_settings.delete_one({"gid": g.id})

    @commands.Cog.listener(name="on_guild_join")
    async def on_guild_join(self, g: discord.Guild):
        if g.id in Blacklists:
            await g.leave()
            return
        self.bot.guild_settings[g.id] = copy.deepcopy(DEFAULT_SETTINGS)
        if g.owner_id == self.bot.user.id:
            return
        await self.bot.get_channel(756254787191963768).send(
            f"サーバー参加\n{g.id}",
            embeds=[
                SEmbed(
                    "<サーバー参加>", f"名前：{g.name}\nID：{g.id}\n現在の個数：{len(self.bot.guilds)}", color=discord.Color.green()
                ),
                SEmbed("", f"人数：{len(g.members)}\nオーナー：{self.bot.get_user(g.owner_id)}"),
            ],
        )
        lang = "ja"
        self.bot.guild_settings[g.id]["lang"] = lang
        await self.bot.db.guild_settings.insert_one(dict(self.bot.guild_settings[g.id], gid=g.id))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not self.bot.guild_settings.get(member.guild.id):
            return
        if self.bot.guild_settings[member.guild.id]["event_messages"]["join"]:
            g = self.bot.get_guild(member.guild.id)
            try:
                sc = self.bot.get_channel(self.bot.guild_settings[member.guild.id]["event_message_channel"])
                await sc.send(
                    self.bot.guild_settings[member.guild.id]["event_messages"]["join"]
                    .replace("!name", member.name)
                    .replace("!mention", member.mention)
                    .replace("!count", str(len(g.members)))
                    .replace("\\n", "\n")
                )
            except BaseException:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not self.bot.guild_settings.get(member.guild.id):
            await self.bot.get_command("fix").callback()
        if self.bot.guild_settings[member.guild.id]["event_messages"]["leave"]:
            g = self.bot.get_guild(member.guild.id)
            sc = self.bot.get_channel(self.bot.guild_settings[member.guild.id]["event_message_channel"])
            await sc.send(
                self.bot.guild_settings[member.guild.id]["event_messages"]["leave"]
                .replace("!name", member.name)
                .replace("!mention", member.mention)
                .replace("!count", str(len(g.members)))
                .replace("\\n", "\n")
            )

    @commands.Cog.listener("on_message")
    async def on_message_cmd(self, message):
        global last_announce

        global Bump_alerts, Dissoku_alerts
        global Afks
        if message.content.startswith(("sb/" if self.bot.debug else "sb#", "sb.")) and message.content[3:].split(" ")[
            0
        ] in ["reload", "fix", "exec", "save"]:
            await self.bot.process_commands(message)
            return
        if message.author.id in GBan.keys():
            return
        if (
            message.channel.id in self.bot.guild_settings[message.guild.id]["deactivate_command"]
        ) and not message.channel.permissions_for(message.author).manage_channels:
            if is_command(message):
                e = discord.Embed(
                    title="このチャンネルではコマンドを使用できません。",
                    description="ここでコマンドを実行するには`チャンネルを管理`が必要です。",
                    color=Error,
                )
                e.set_footer(text=get_txt(message.guild.id, "message_delete").format(5))
                msg = await message.channel.send(embed=e)
                await msg.delete(delay=5)
        else:
            if message.author.id in SB_Bans.keys() and is_command(message):
                if SB_Bans[message.author.id] > time.time():
                    return await message.reply("あなたはSevenBotからBANされています。")
            await self.bot.process_commands(message)

    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        global last_announce

        global Bump_alerts, Dissoku_alerts
        global Afks
        au = message.author.id
        if message.author.id in GBan.keys():
            return
        if not self.bot.is_ready():
            return
        if message.guild is None:
            return
        if message.guild.id not in self.bot.guild_settings.keys():
            return
        if message.author.bot:
            return
        ls = list(self.bot.guild_settings[message.guild.id]["muted"].keys())
        if message.author.id in ls:
            dt = discord.utils.utcnow()
            mtr = self.bot.guild_settings[message.guild.id]["muted"][au]
            if mtr > time.time():
                e = discord.Embed(
                    title=f"{message.author.name}はミュートされています。",
                    description=f"<t:{int(mtr)}:R>にミュートが解除されます。",
                    color=Alert,
                )
                e.set_footer(text=get_txt(message.guild.id, "message_delete").format(5))
                msg = await message.channel.send(embed=e)
                await message.delete()
                await msg.delete(delay=5)
                return
        if message.content == self.bot.user.mention or message.content == f"<@!{self.bot.user.id}>":
            await message.channel.send(
                get_txt(message.guild.id, "mention_txt").format(self.bot.command_prefix(self.bot, message)[0])
            )
            return
        # gs = self.bot.guild_settings.get(message.guild.id)
        if (message.channel.id in Sevennet_channels) and not is_command(message):
            if message.author.id in Global_mute:
                await message.delete()
                e2 = discord.Embed(title="あなたはミュートされています。", info=Error)
                await message.author.send(embed=e2)
            else:
                dt = discord.utils.utcnow()
                flag = True
                g = Sevennet_replies.get(message.author.id)
                if g is not None:
                    rdt = g[1]
                    if rdt > dt:
                        flag = False
                        if message.attachments != []:
                            e2 = discord.Embed(title="返信には画像を添付できません。", info=Error)
                            m = await message.author.send(embed=e2)
                            await message.delete()
                            return
                        mid = g[0]
                        ml = Sevennet_posts[mid]["messages"]
                        m0 = None
                        gl = []
                        g = []
                        for m in ml:
                            c = self.bot.get_channel(m[0])
                            if c is not None:
                                try:
                                    g.append(c.fetch_message(m[1]))
                                except NotFound:
                                    continue
                        msgs = await asyncio.gather(*g)
                        for m2 in msgs:
                            m0 = m2.embeds[0]
                            m0.add_field(
                                name=f"{message.author}(ID:{message.author.id})",
                                value=message.content,
                                inline=False,
                            )
                            gl.append(m2.edit(embed=m0))
                        await asyncio.gather(*gl)
                        await message.delete()
                if flag:
                    e = discord.Embed(
                        description=message.content,
                        timestamp=message.created_at,
                        color=Chat,
                    )
                    if len(message.attachments) > 1:
                        e2 = discord.Embed(title="SevenNetでは画像は1つしか送信できません。", info=Error)
                        m = await message.author.send(embed=e2)
                        await message.delete()
                        return
                    elif message.attachments != []:
                        if (
                            "".join(os.path.splitext(os.path.basename(message.attachments[0].filename))[1:])[1:]
                            not in Image_exts
                        ):
                            e2 = discord.Embed(title="SevenNetでは画像以外のファイルを送信できません。", info=Error)
                            m = await message.author.send(embed=e2)
                            await message.delete()
                            return
                        amsg = await self.bot.get_channel(765528694500360212).send(
                            file=(await message.attachments[0].to_file())
                        )
                        e.set_image(url=amsg.attachments[0].url)
                    mid = hashlib.md5(str(message.id).encode()).hexdigest()[0:8]
                    e.set_author(
                        name=f"{message.author}(ID:{message.author.id})",
                        icon_url=message.author.display_avatar.url,
                    )
                    e.set_footer(
                        text=f"Server: {message.guild.name} | ID: {mid} | ±0 ( +0 / -0 )",
                        icon_url=message.guild.icon.url,
                    )
                    mids = []
                    cs = []
                    for c in Sevennet_channels:
                        cn = self.bot.get_channel(c)
                        if cn is None:
                            Sevennet_channels.remove(c)
                        else:
                            cs.append(
                                self.send_reaction(
                                    channel=cn,
                                    reactions=["up", "down", "reply", "report"],
                                    message={"embed": e},
                                )
                            )
                    ga = asyncio.gather(*cs)
                    tmid = await ga
                    await message.delete()
                    for sm in tmid:
                        mids.append([sm.channel.id, sm.id])
                    while len(Sevennet_posts) > 10:
                        Sevennet_posts.pop(list(Sevennet_posts.keys())[0])
                    Sevennet_posts[mid] = {
                        "upvote": [],
                        "downvote": [],
                        "messages": mids,
                        "guild": message.guild.id,
                    }
        if not is_command(message):
            tc = self.bot.guild_settings[message.guild.id]["trans_channel"]
            if message.channel.id in list(tc.keys()):
                lng = (await translator.detect(message.clean_content))[0]
                if lng.lower() != tc[message.channel.id].lower():
                    tr = await translator.translate(message.content, lang_tgt=tc[message.channel.id])
                    e = discord.Embed(
                        title=get_txt(message.guild.id, "trans_after"),
                        description=tr,
                        color=Trans,
                    )
                    e.set_author(
                        name=f"{message.author.name}(ID:{message.author.id})",
                        icon_url=message.author.display_avatar.url,
                    )
                    e.set_footer(
                        text="Powered by async_google_trans_new",
                        icon_url="https://i.imgur.com/zPOogXx.png",
                    )
                    await message.reply(embed=e)
        if message.channel.id in self.bot.guild_settings[message.guild.id]["2ch_link"] and re.findall(
            Link_2ch_re, message.content
        ):
            rmn = re.findall(Link_2ch_re, message.content)
            rmn.sort(key=len, reverse=True)
            res = message.content
            flag = False
            for r in rmn:
                if int(r[2:]) > 1000:
                    flag = True
                else:
                    hs = await message.channel.history(limit=int(r[2:]), oldest_first=True).flatten()
                    if len(hs) >= int(r[2:]):
                        res = res.replace(r, f"[{r}]({hs[-1].jump_url} )")
            ch_webhooks = await message.channel.webhooks()
            webhook = discord.utils.get(ch_webhooks, name="sevenbot-2ch-link-webhook")
            if webhook is None:
                g = self.bot.get_guild(Official_discord_id)
                a = g.icon.url
                webhook = await message.channel.create_webhook(name="sevenbot-2ch-link-webhook", avatar=await a.read())
            if flag:
                e = discord.Embed(
                    title="負荷をかけないでください！",
                    description="1000より大きい数は反応しません。\n2chも1000でスレが終わるからしょうがないね（）",
                    color=Error,
                )
                await message.channel.send(embed=e)
            elif res != message.content:
                await webhook.send(
                    content=res,
                    username=message.author.display_name,
                    allowed_mentions=discord.AllowedMentions.none(),
                    avatar_url=message.author.display_avatar.url_as(format="png"),
                    files=message.attachments,
                    embeds=message.embeds,
                )
                await message.delete()

    @commands.command()
    async def getid(self, ctx, un=None):
        if un is None:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "getid_self")[0].format(ctx.author.id),
                description=get_txt(ctx.guild.id, "getid_self")[1],
                color=Info,
            )
            return await ctx.reply(embed=e)
        else:
            per = Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["getid_search"][3]
            inc = Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["getid_search"][3]
            pcf = False
            icf = False
            for gm in ctx.channel.guild.members:
                if gm.display_name.lower() == un.lower():
                    if not pcf:
                        per = ""
                    pcf = True
                    per += f"{gm.mention} - `{gm.id}` - `{gm}`\n"
                elif un.lower() in gm.display_name.lower():
                    if not icf:
                        inc = ""
                    icf = True
                    inc += f"{gm.mention} - `{gm.id}` - `{gm}`\n"
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "getid_search")[0].format(un),
                color=Info,
            )
            e.add_field(
                name=get_txt(ctx.guild.id, "getid_search")[1],
                inline=False,
                value=per,
            )
            e.add_field(
                name=get_txt(ctx.guild.id, "getid_search")[2],
                inline=False,
                value=inc,
            )
            return await ctx.reply(embed=e)

    @commands.command(name="tos")
    async def _tos(self, ctx):
        tos = await self.bot.get_channel(736707812905975829).history(limit=9).flatten()
        tos.reverse()
        ts = ""
        for t in tos:
            ts += t.content
        embed = discord.Embed(
            title="利用規約",
            description="この利用規約（以下、「本規約」といいます。）は、SevenBot運営チーム（以下、「当グループ」といいます。）が提供する"
            "Discord Bot 「SevenBot」によるサービス（以下、「本サービス」といいます。）の利用条件を定めるものです。"
            "ユーザーの皆さま（以下、「利用者」といいます。）には、本規約に従って、本サービスをご利用いただきます。",
            color=Bot_info,
            url="https://sevenbot.jp/tos",
        )
        for ts2 in ts.split("``` ```"):
            ts3 = ts2.split("**")  # 利用規約
            if len(ts3) > 1:
                embed.add_field(name=ts3[1], value=ts3[2], inline=False)
            else:
                embed.add_field(name="⠀", value=ts3[0], inline=False)
        await ctx.reply(embed=embed)

    @commands.command()
    async def tips(self, ctx, name=None):
        if name:
            name = name.lower()
            try:
                get_txt(ctx.guild.id, "tips")[name]
                tid = name
            except KeyError:
                tid = random.choice(list(get_txt(ctx.guild.id, "tips").keys()))
        else:
            tid = random.choice(list(get_txt(ctx.guild.id, "tips").keys()))
        desc = get_txt(ctx.guild.id, "tips")[tid]
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "tips_title"),
            description=desc,
            color=Bot_info,
        )
        e.set_footer(text="ID: " + tid)
        return await ctx.reply(embed=e)

    async def reset(self, ctx):
        self.bot.guild_settings[ctx.guild.id] = DEFAULT_SETTINGS

    @commands.Cog.listener("on_message")
    async def on_message_autopub(self, message):
        if message.author.bot and not message.webhook_id:
            return
        if is_command(message):
            return
        tc = self.bot.guild_settings[message.guild.id]["autopub"]
        if message.channel.id in tc:
            try:
                await message.publish()
            except discord.HTTPException:
                pass

    @commands.Cog.listener("on_message")
    async def on_message_ad(self, message):
        if message.channel.id != 800628621010141224 or (message.author.bot and message.content != "reload"):
            return
        adc = self.bot.get_channel(800628621010141224)
        tad = []
        async for ad in adc.history(limit=1000):
            if len(urllib.parse.urlparse(ad.content).scheme) == 0 or not ad.attachments:
                await ad.delete()
                continue
            tad.append([ad.content, ad.attachments[0].url, str(ad.author)])
        self.bot.consts["ads"] = tad

    @commands.command(aliases=["h", "?"])
    async def help(self, ctx, *, detail=None):
        if detail is None:
            desc = (
                get_txt(ctx.guild.id, "help_categories")[1]
                + "\n**`uses`** - "
                + get_txt(ctx.guild.id, "help_category_helps")["uses"]
                + "\n"
            )
            for ck, cv in Categories.items():
                desc += (
                    "**`"
                    + ck
                    + "`** - "
                    + get_txt(ctx.guild.id, "help_category_helps")[ck]
                    + " - "
                    + f"`{cv[0]}`,`{cv[1]}`..."
                    + "\n"
                )
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "help_categories")[0],
                description=desc,
                url="https://sevenbot.jp/commands",
                color=Bot_info,
            )
            return await ctx.reply(embed=e)
        elif detail == "uses":
            desc = ""
            for cni, (cnk, cnv) in enumerate(sorted(Command_counter.items(), key=lambda x: x[1], reverse=True)[0:10]):
                c = self.bot.get_command(cnk)
                if c:
                    desc += (
                        f"#{cni+1}: **`{c.name}`**({cnv}) "
                        + (
                            get_txt(ctx.guild.id, "help_detail").get(
                                str(c),
                                "_" + get_txt(ctx.guild.id, "help_detail_none") + "_",
                            )
                        ).split("\n")[0]
                        + "\n"
                    )
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "help_ranking"),
                description=desc,
                color=Bot_info,
            )
            e.set_footer(text=get_txt(ctx.guild.id, "help_categories")[3])
            return await ctx.reply(embed=e)
        elif detail in Categories.keys():
            desc = ""
            for cn in Categories[detail]:
                c = self.bot.get_command(cn)
                if c:
                    desc += (
                        f"**`{c.name}`** "
                        + (
                            get_txt(ctx.guild.id, "help_detail").get(
                                str(c),
                                "_" + get_txt(ctx.guild.id, "help_detail_none") + "_",
                            )
                        ).split("\n")[0]
                        + "\n"
                    )
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "help_categories")[2].format(detail),
                description=desc,
                color=Bot_info,
                url="https://sevenbot.jp/commands#category-" + detail,
            )
            e.set_footer(text=get_txt(ctx.guild.id, "help_categories")[3])
            return await ctx.reply(embed=e)
        else:
            detail = detail.lower()
            if self.bot.get_command(detail):
                c = self.bot.get_command(detail)
                if c.hidden:
                    e = SEmbed(
                        title=get_txt(ctx.guild.id, "help_title") + " - " + str(c),
                        description=get_txt(ctx.guild.id, "help_hidden"),
                        color=Bot_info,
                        author=SAuthor(
                            name=f"{ctx.author.display_name}(ID:{ctx.author.id})",
                            icon_url=ctx.author.display_avatar.url,
                        ),
                    )
                    return await ctx.reply(embed=e)
                desc_txt = (
                    get_txt(ctx.guild.id, "help_detail")
                    .get(str(c), get_txt(ctx.guild.id, "help_detail_none"))
                    .lstrip("\n ")
                )
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "help_title") + " - " + str(c),
                    color=Bot_info,
                    url="https://sevenbot.jp/commands#" + str(c).replace(" ", "-"),
                )
                if (
                    (not isinstance(c, commands.Group))
                    or (
                        get_txt(ctx.guild.id, "help_detail").get(str(c))
                        and len(inspect.signature(c.callback).parameters) > 2
                    )
                    or (get_txt(ctx.guild.id, "help_detail").get(str(c), "").count("\n") > 1)
                ):
                    if desc_txt != get_txt(ctx.guild.id, "help_detail_none"):
                        txt = syntaxer.Syntax(c, desc_txt)
                        e.add_field(
                            name=get_txt(ctx.guild.id, "help_detail_syntax_name"),
                            value="```apache\n{}\n```".format(str(txt)),
                        )
                    e.description = desc_txt
                if isinstance(c, commands.Group):
                    sct = ""
                    for c2 in c.commands:
                        sct += (
                            f"**`{c2.name}`** "
                            + (
                                get_txt(ctx.guild.id, "help_detail").get(
                                    str(c2),
                                    "_" + get_txt(ctx.guild.id, "help_detail_none") + "_",
                                )
                            ).split("\n")[0]
                            + "\n"
                        )
                    e.add_field(
                        name=get_txt(ctx.guild.id, "help_detail_subcommands"),
                        value=sct,
                        inline=False,
                    )
                at = "`,`".join(c.aliases)
                if at == "":
                    at = Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["help_detail_aliases_none"]
                else:
                    at = "`" + at + "`"
                e.add_field(
                    name=get_txt(ctx.guild.id, "help_detail_aliases"),
                    value=at,
                    inline=False,
                )
                e.add_field(
                    name=get_txt(ctx.guild.id, "help_detail_count")[0],
                    value=get_txt(ctx.guild.id, "help_detail_count")[1].format(
                        Command_counter.get(str(c).split()[0], 0)
                    ),
                    inline=False,
                )
                return await ctx.reply(embed=e)
            else:
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "help_title") + " - " + detail,
                    description=get_txt(ctx.guild.id, "help_none"),
                    color=Bot_info,
                )
                return await ctx.reply(embed=e)

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def change_prefix(self, ctx, txt=None):
        before = self.bot.guild_settings[ctx.guild.id]["prefix"]
        if before is None:
            before = Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["prefix_changed"][2]
        self.bot.guild_settings[ctx.guild.id]["prefix"] = txt.lstrip(" ")
        after = txt
        pre = txt
        if after is None:
            after = Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["prefix_changed"][2]
            pre = "sb#"
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "prefix_changed")[0].format(before, after),
            description=get_txt(ctx.guild.id, "prefix_changed")[1].format(pre),
            color=Success,
        )
        return await ctx.reply(embed=e)

    @commands.command()
    async def invite(self, ctx):
        e = discord.Embed(
            title="招待URL",
            description="[https://sevenbot.jp/invite](https://discord.com/oauth2/authorize?"
            "client_id=718760319207473152&scope=bot%20applications.commands&permissions=808840532)",
            color=Bot_info,
        )
        return await ctx.reply(embed=e)

    @commands.command()
    async def about(self, ctx):
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "abouts")[0],
            color=Bot_info,
            url="https://sevenbot.jp",
        )
        e.add_field(
            name=Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["abouts"][1],
            value="[名無し。(@sevenc-nanashi)](https://github.com/sevenc-nanashi)",
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "abouts")[2],
            value=f"`python {platform.python_version()}`, `Pycord {discord.__version__}`",
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "abouts")[3],
            value="https://discord.gg/GknwhnwbAV",
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "abouts")[4],
            value=f"{len(self.bot.guilds)}" + get_txt(ctx.guild.id, "abouts")[-2],
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "abouts")[5],
            value=f"{len(self.bot.users)}" + get_txt(ctx.guild.id, "abouts")[-1],
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "abouts")[6],
            value=f"{len(Global_chat)}"
            f'{get_txt(ctx.guild.id,"abouts")[-2]}'
            f"({round(len(Global_chat)/len(list(self.bot.guild_settings.keys()))*100)}%)",
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "abouts")[7],
            value=f"{len(Sevennet_channels)}"
            f'{get_txt(ctx.guild.id,"abouts")[-2]}'
            f"({round(len(Sevennet_channels)/len(list(self.bot.guild_settings.keys()))*100)}%)",
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "abouts")[13],
            value=get_txt(ctx.guild.id, "abouts")[14],
        )
        return await components.reply(
            ctx,
            embed=e,
            components=[
                components.Button("利用規約", style=components.ButtonType.link, url="https://sevenbot.jp/tos"),
                components.Button("プライバシーポリシー", style=components.ButtonType.link, url="https://sevenbot.jp/privacy"),
                components.Button(
                    "ソースコード", style=components.ButtonType.link, url="https://github.com/SevenBot-dev/SevenBot"
                ),
            ],
        )

    @commands.Cog.listener(name="on_command_error")
    async def on_command_error(self, ctx, error):
        if isinstance(error, CommandNotFound):
            return
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            synt = syntaxer.Syntax(
                ctx.command,
                get_txt(ctx.guild.id, "help_detail")[str(ctx.command)],
            )
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "missing_argument").format(
                    discord.utils.get(synt.args, param=error.param).name
                ),
                description=get_txt(ctx.guild.id, "missing_argument_desc").format(synt),
                color=Error,
            )
            return await components.reply(
                ctx.message,
                embed=e,
                components=[
                    components.Button(
                        get_txt(ctx.guild.id, "online_help"),
                        style=5,
                        url="https://sevenbot.jp/commands#" + str(ctx.command).replace(" ", "-"),
                    )
                ],
            )
        elif isinstance(error, BadArgument):
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "bad_arg"),
                description=get_txt(ctx.guild.id, "see_help") + f"\n```\n{error}```",
                color=Error,
            )
            e.add_field(name="ヒント", value="[]、<>は不必要です。")

            return await components.reply(
                ctx,
                embed=e,
                components=[
                    components.Button(
                        "パラメータについてのヘルプ",
                        style=components.ButtonType.link,
                        url="https://sevenbot.jp/tutorial/command-howto",
                    )
                ],
            )
        elif isinstance(error, commands.MissingPermissions):
            res = ""
            for p in error.missing_permissions:
                try:
                    res += get_txt(ctx.guild.id, "permissions_text")[0][p] + "\n"
                except KeyError:
                    try:
                        res += get_txt(ctx.guild.id, "permissions_text")[1][p] + "\n"
                    except KeyError:
                        res += get_txt(ctx.guild.id, "permissions_text")[2][p] + "\n"
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "missing_permissions")[0],
                description=get_txt(ctx.guild.id, "missing_permissions")[1] + f"```\n{res}```",
                color=Error,
            )
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.NotOwner):
            e = discord.Embed(title=get_txt(ctx.guild.id, "only_admin"), color=Error)
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.CommandOnCooldown):
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "cooldown"),
                description=get_txt(ctx.guild.id, "cooldown_desc").format(round(error.retry_after, 2)),
                color=Error,
            )
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.DisabledCommand):
            e = discord.Embed(title=get_txt(ctx.guild.id, "disabled"), color=Error)
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.NSFWChannelRequired):
            e = discord.Embed(title=get_txt(ctx.guild.id, "not_nsfw"), color=Error)
            return await ctx.reply(embed=e)
        else:
            sentry_sdk.capture_exception(error)
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "error"),
                description=f"```\n{error}```",
                color=Error,
            )
            msg = await ctx.reply(embed=e)
            await msg.add_reaction(self.bot.oemojis["down"])
            try:
                error_msg = "".join(traceback.TracebackException.from_exception(error).format())
                await bot.wait_for(
                    "reaction_add",
                    check=lambda reaction, user: (not isinstance(reaction.emoji, str))
                    and reaction.emoji.name == "down"
                    and reaction.message.id == msg.id
                    and reaction.count == 2,
                )
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "error"),
                    description=f"```\n{error_msg[-1990:]}```",
                    color=Error,
                )
                await msg.edit(embed=e)
            except asyncio.TimeoutError:
                pass
            return

    @commands.Cog.listener()
    async def on_command_suggest(self, ctx: commands.Context, suggested_commands):
        e = SEmbed(
            title=get_txt(ctx.guild.id, "unknown_cmd"),
            description=get_txt(ctx.guild.id, "see_help"),
            color=Error,
        )
        suggested_commands = filter(
            lambda x: set(x) & set(ctx.message.content.split(" ")[0].removeprefix(ctx.prefix)), suggested_commands
        )
        if not suggested_commands:
            e.fields.append(
                SField(
                    name=get_txt(ctx.guild.id, "suggest"),
                    value=get_txt(ctx.guild.id, "no_match"),
                    inline=False,
                )
            )
        else:
            e.fields.append(
                SField(
                    name=get_txt(ctx.guild.id, "suggest"),
                    value="```\n",
                    inline=False,
                )
            )
            for s in suggested_commands:
                bv = e.fields[0].value
                e.fields[0].value += s + "\n"
                if len(e.fields[0].value) > 250:
                    e.fields[0].value = bv
                    break
            e.fields[0].value += "```"
        if ctx.guild.id != DBL_id:
            return await ctx.reply(embed=e)

    @commands.Cog.listener(name="on_raw_reaction_remove")
    async def on_raw_reaction_remove(self, pl):
        c = self.bot.get_channel(pl.channel_id)
        try:
            m = await c.fetch_message(pl.message_id)
        except (NotFound, Forbidden):
            return
        g = self.bot.get_guild(pl.guild_id)
        if m.embeds == []:
            return
        if m.author.id != self.bot.user.id:
            return
        if m.embeds[0].title == get_txt(g.id, "voting")[0]:
            mt = m.embeds[0].timestamp
            n = discord.utils.utcnow()
            if mt < n:
                return
            me = m.embeds[0]
            select = []
            for f in me.fields[2].value.split("\n"):
                select.append(f.split("：", 1)[-1])
            s = ""
            cl = []
            for rc in m.reactions:
                if rc.count not in cl:
                    cl.append(rc.count)
            cl.sort(reverse=True)
            cl = cl[0:3]
            for sfi, sf in enumerate(select):
                rc2 = m.reactions[sfi]
                n = 3
                if rc2.count in cl:
                    n = cl.index(rc2.count)
                if rc2.count == 1:
                    n = 4
                em = self.bot.oemojis["b" + str(sfi + 1)]
                s += f":{Squares[n]}:｜{em}：{sf}\n"
            me.set_field_at(index=2, name=get_txt(g.id, "voting")[4], value=s, inline=False)
            await m.edit(embed=me)

    @commands.Cog.listener(name="on_raw_reaction_add")
    async def on_raw_reaction_add(self, pl):
        global Bignum_join
        global Wolf_join
        loop = asyncio.get_event_loop()
        if pl.channel_id == Channel_ids["emoji_print"]:
            print(pl.emoji.name)
        if pl.user_id == self.bot.user.id:
            return
        channel = self.bot.get_channel(pl.channel_id)
        try:
            message = await channel.fetch_message(pl.message_id)
        except (NotFound, Forbidden):
            return
        guild = self.bot.get_guild(pl.guild_id)
        user = guild.get_member(pl.user_id)
        if message.embeds == []:
            return
        m0 = message.embeds[0]
        if message.channel.id in Sevennet_channels and message.author.id == guild.me.id and not user.bot:
            ft = re.findall(Sevennet_footer_re, m0.footer.text)
            mid = ft[1][1]
            if mid not in Sevennet_posts.keys():
                return
            pinf = Sevennet_posts[mid]
            if pl.emoji.name == "up":
                if message.id not in pinf["upvote"]:
                    if message.id in pinf["downvote"]:
                        pinf["downvote"].remove(message.id)
                    pinf["upvote"].append(message.id)
                else:
                    pinf["upvote"].remove(message.id)
            elif pl.emoji.name == "down":
                if message.id not in pinf["downvote"]:
                    if message.id in pinf["upvote"]:
                        pinf["upvote"].remove(message.id)
                    pinf["downvote"].append(message.id)
                else:
                    pinf["downvote"].remove(message.id)
            elif pl.emoji.name == "report" or pl.emoji.name == "check4":
                for channel in pinf["messages"]:
                    cn = self.bot.get_channel(channel[0])
                    if cn is None:
                        continue
                    try:
                        em = await cn.fetch_message(channel[1])
                        if em.embeds[0].author.name == str(user) + f"(ID:{user.id})" or user.id == Owner_ID:
                            await em.delete()
                        else:
                            await em.remove_reaction(pl.emoji, cn.guild.me)
                            await em.add_reaction(self.bot.oemojis["check4"])
                    except NotFound:
                        pass
                return
            elif pl.emoji.name == "reply":
                dt = discord.utils.utcnow()
                dt += datetime.timedelta(seconds=10)
                Sevennet_replies[user.id] = [mid, dt]
                await message.remove_reaction(pl.emoji, user)
                return
            await message.remove_reaction(pl.emoji, user)
            Sevennet_posts[mid] = pinf
            uc = len(pinf["upvote"])
            dc = len(pinf["downvote"])
            if (uc - dc) == 0:
                p = "±"
            elif (uc - dc) > 0:
                p = "+"
            else:
                p = ""
            sg = self.bot.get_guild(pinf["guild"])
            m0.set_footer(
                text=f"Server: {sg.name} | ID: {mid} | {p}{uc-dc} ( +{uc} / -{dc} )",
                icon_url=sg.icon.url,
            )
            loop = asyncio.get_event_loop()
            for channel in pinf["messages"]:
                cn = self.bot.get_channel(channel[0])
                try:
                    em = await cn.fetch_message(channel[1])
                    loop.create_task(em.edit(embed=m0))
                except NotFound:
                    pass
        elif message.embeds != [] and message.author.id == self.bot.user.id and pl.user_id != self.bot.user.id:
            if not m0.title:
                return
            if m0.title == get_txt(guild.id, "free_channel_title") and pl.emoji.name == "add":
                loop.create_task(message.remove_reaction(self.bot.oemojis["add"], user))
                e = discord.Embed(
                    description=get_txt(guild.id, "free_channel_ask"),
                    color=Widget,
                )
                msg = await channel.send(embed=e)
                try:
                    message = await self.bot.wait_for(
                        "message",
                        check=lambda m2: m2.channel == channel and m2.author == user,
                        timeout=30,
                    )
                    if channel.category is None:
                        cat = await guild.create_category_channel(
                            get_txt(guild.id, "free_channel_title"),
                            overwrites=channel.overwrites,
                            position=channel.position,
                        )
                        await channel.edit(category=cat)
                    nt = await channel.category.create_text_channel(
                        message.content,
                        topic=get_txt(guild.id, "free_channel_topic").format(message.author.mention),
                    )
                    await nt.set_permissions(user, manage_channels=True, manage_messages=True)
                    e = discord.Embed(
                        title=get_txt(guild.id, "free_channel_success"),
                        description=get_txt(guild.id, "free_channel_success_desc").format(nt.mention),
                        color=Widget,
                    )
                    e.set_footer(text=get_txt(guild.id, "message_delete").format(5))
                    msg2 = await channel.send(embed=e)
                    await asyncio.sleep(5)
                    loop.create_task(message.delete())
                    loop.create_task(msg.delete())
                    loop.create_task(msg2.delete())
                except asyncio.TimeoutError:
                    e = discord.Embed(description=get_txt(guild.id, "timeout"), color=Error)
                    e.set_footer(text=get_txt(guild.id, "message_delete").format(5))
                    await msg.edit(embed=e)
                    await msg.delete(delay=5)
            elif message.embeds[0].title == "募集":
                ft = m0.footer.text
                mt = m0.timestamp
                n = discord.utils.utcnow()
                guild = self.bot.get_guild(pl.guild_id)
                user = guild.get_member(pl.user_id)
                cm = m0.fields[2].value.split("\n")
                if mt < n:
                    pass
                elif pl.emoji.name == "check5" and user.name + f"(ID:{user.id})" not in cm:
                    mx = int(m0.fields[1].value[0:-1])
                    cn = int(m0.fields[2].name[6:-2])
                    if mx > cn:
                        if cm == ["現在参加者はいません"]:
                            cm = []
                        cm.append(user.name + f"(ID:{user.id})")
                        m0.set_field_at(2, name=f"参加者(現在{cn+1}人)", value="\n".join(cm))
                        await message.edit(embed=m0)
                elif pl.emoji.name == "check6" and user.name + f"(ID:{user.id})" in cm:
                    cm.remove(user.name + f"(ID:{user.id})")
                    cn = len(cm)
                    if cm == []:
                        cm = ["現在参加者はいません"]
                        cn = 0
                    m0.set_field_at(2, name=f"参加者(現在{cn}人)", value="\n".join(cm))
                    await message.edit(embed=m0)
                await message.remove_reaction(pl.emoji, user)
            elif message.embeds[0].title == get_txt(guild.id, "voting")[0]:
                ft = message.embeds[0].footer.text
                mt = message.embeds[0].timestamp
                if not mt:
                    return
                n = discord.utils.utcnow()
                if mt < n:
                    return
                loop = asyncio.get_event_loop()
                if pl.emoji in Number_emojis[1:]:
                    me = message.embeds[0]
                    if not me.fields[1].value == get_txt(guild.id, "voting")[3][0]:
                        user = self.bot.get_user(pl.user_id)
                        for nemi, nem in enumerate(Number_emojis):
                            if nemi == 0:
                                continue
                            if len(message.reactions) < nemi:
                                break
                            if nem != pl.emoji:
                                try:
                                    if filter(
                                        lambda r: r.emoji == nem,
                                        message.reactions,
                                    ):
                                        loop.create_task(message.remove_reaction(nem, user))
                                except Forbidden:
                                    pass
                    await self.on_raw_reaction_remove(pl)
                else:
                    await message.remove_reaction(pl.emoji, self.bot.get_user(pl.user_id))
            elif message.embeds[0].title == "ロールパネル" or message.embeds[0].title == "ロールパネル（複数選択不可）":
                try:
                    if pl.emoji in Number_emojis:
                        mda = m0.description.split("\n")
                        mdh = []
                        for md in mda:
                            r = guild.get_role(int([s for s in re.split("(: |：)", md) if s][2][3:-1]))
                            mdh.append(r)
                            if m0.title == "ロールパネル（複数選択不可）" and r in user.roles:
                                await user.remove_roles(r)
                        rl = mdh[Number_emojis.index(pl.emoji) - 1]
                        if rl not in user.roles:
                            await user.add_roles(rl)
                        else:
                            await user.remove_roles(rl)
                    elif pl.emoji.name == "🛠️" and user.guild_permissions.manage_roles:
                        asyncio.new_event_loop()
                        mda = m0.description.split("\n")
                        mdh = []
                        for md in mda:
                            mdh.append(guild.get_role(int(md.split("：", 1)[-1][3:-1])))
                        while True:
                            e = discord.Embed(description="編集したい番号でリアクションして下さい。", color=Widget)
                            msg = await channel.send(embed=e)
                            for n in Number_emojis[1 : len(mdh) + (2 if len(mdh) < 10 else 1)]:
                                loop.create_task(msg.add_reaction(n))
                            loop.create_task(msg.add_reaction(self.bot.oemojis["check6"]))

                            def check(r, ru):
                                if ru.bot:
                                    return
                                if (
                                    r.count >= 2
                                    and r.emoji
                                    in Number_emojis[1 : len(mdh) + (2 if len(mdh) < 10 else 1)]
                                    + [self.bot.oemojis["check6"]]
                                    and ru.id == user.id
                                    and r.message.id == msg.id
                                ):
                                    return True

                            r, _ = await self.bot.wait_for("reaction_add", check=check)
                            if r.emoji == self.bot.oemojis["check6"]:
                                await message.remove_reaction(pl.emoji, self.bot.get_user(pl.user_id))
                                return await msg.delete()
                            en = Number_emojis.index(r.emoji) - 1
                            await r.message.remove_reaction(r, user)
                            e = discord.Embed(
                                description="ロールを送信して下さい。\n`!none` で削除します。",
                                color=Widget,
                            )
                            try:
                                mdh[en]
                            except IndexError:
                                e = discord.Embed(description="ロールを送信して下さい。", color=Widget)
                            msg2 = await channel.send(embed=e)

                            def check2(message):
                                return message.author.id == user.id and message.channel.id == channel.id

                            m2 = await self.bot.wait_for("message", check=check2)
                            if m2.content != "!none":
                                ctx = await self.bot.get_context(m2)
                                try:
                                    r = await commands.RoleConverter().convert(ctx, m2.content)
                                except commands.errors.RoleNotFound:
                                    e = discord.Embed(description="不明なロールです。", color=Widget)
                                    e.set_footer(text=get_txt(guild.id, "message_delete").format(5))
                                    await msg2.edit(embed=e)
                                    await msg2.delete(delay=5)
                                    await msg.delete(delay=0)
                                    await m2.delete(delay=0)
                                    continue
                                if (
                                    r.position > user.top_role.position and not guild.owner_id == user.id
                                ) or r.position > guild.me.top_role.position:
                                    e = discord.Embed(
                                        title=get_txt(guild.id, "no_role_perm").format(r.name),
                                        color=Widget,
                                    )
                                    e.set_footer(text=get_txt(guild.id, "message_delete").format(5))
                                    await msg2.edit(embed=e)
                                    await msg2.delete(delay=5)
                                    return
                                try:
                                    mdh[en] = r
                                except IndexError:
                                    mdh.append(r)
                            else:
                                mdh.pop(en)
                            await msg.delete(delay=0)
                            await msg2.delete(delay=0)
                            await m2.delete(delay=0)
                            s = ""
                            for sfi, sf in enumerate(mdh):
                                r = sf
                                em = self.bot.oemojis["b" + str(sfi + 1)]
                                s += f"{em}：{r.mention}\n"
                                if self.bot.oemojis["b" + str(sfi + 1)] not in [r.emoji for r in message.reactions]:
                                    await message.add_reaction(self.bot.oemojis["b" + str(sfi + 1)])
                            for r in message.reactions:
                                try:
                                    n = Number_emojis.index(r.emoji)
                                    if n > len(mdh):
                                        try:
                                            await message.clear_reaction(r)
                                        except discord.Forbidden:
                                            pass
                                except ValueError:
                                    pass
                            message.embeds[0].description = s
                            message.embeds[0].set_footer(text="🛠️で編集")
                            await message.edit(embed=message.embeds[0])
                    await message.remove_reaction(pl.emoji, self.bot.get_user(pl.user_id))
                except Forbidden:
                    pass

    @commands.command()
    async def ping(self, ctx):
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "ping_title"),
            description=get_txt(ctx.guild.id, "ping_desc").format(
                round(self.bot.latency * 1000),
            ),
            color=Bot_info,
        )
        await ctx.reply(embed=e)

    @commands.command(aliases=["trans"])
    async def translate(self, ctx, *, txt):
        if self.bot.guild_settings[ctx.guild.id]["lang"] == "ja":
            t = "ja"
            if (await translator.detect(txt))[0] == "ja":
                t = "en"
        else:
            t = "en"
            if (await translator.detect(txt))[0] == "en":
                t = "ja"
        lang = txt.split(" ")[-1]
        if lang in get_txt(ctx.guild.id, "lang_name").keys():
            t = lang
            txt = " ".join(txt.split(" ")[0:-1])
        asyncio.get_event_loop()
        lng = (await translator.detect(txt))[0]
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "translate_title").format(
                get_txt(ctx.guild.id, "lang_name")[lng],
                get_txt(ctx.guild.id, "lang_name")[t],
            ),
            description="",
            color=Trans,
        )
        e.add_field(
            name=Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["trans_before"],
            value=txt,
            inline=False,
        )
        res = await translator.translate(txt, lang_tgt=t)
        e.add_field(name=get_txt(ctx.guild.id, "trans_after"), value=res, inline=False)
        e.set_footer(
            text="Powered by async_google_trans_new",
            icon_url="https://i.imgur.com/zPOogXx.png",
        )
        return await ctx.reply(embed=e)

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def event_channel(self, ctx):
        if self.bot.guild_settings[ctx.guild.id]["event_message_channel"] == 0:
            rc = "登録"
        else:
            rc = "変更"
        self.bot.guild_settings[ctx.guild.id]["event_message_channel"] = ctx.channel.id
        e = discord.Embed(
            title=f"イベントメッセージチャンネルを{rc}しました。",
            description="メッセージを登録するには`sb#event_send`を使用してください",
            color=Success,
        )
        return await ctx.reply(embed=e)

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def event_send(self, ctx, etype, *, message=""):
        etype = etype.lower()
        if self.bot.guild_settings[ctx.guild.id]["event_message_channel"] == 0:
            e = discord.Embed(
                title="イベントメッセージチャンネルが設定されていません",
                description="`sb#event_channel`で設定してください",
                color=Error,
            )
            return await ctx.reply(embed=e)
        if etype not in list(Event_dict.keys()):
            e = discord.Embed(
                title=f"イベント{etype}が見付かりませんでした",
                description="`sb#help event_send`で確認してください",
                color=Error,
            )
            return await ctx.reply(embed=e)
        self.bot.guild_settings[ctx.guild.id]["event_messages"][etype] = message
        if message == "":
            d = "メッセージが送られなくなりました。"
            self.bot.guild_settings[ctx.guild.id][etype] = False
        else:
            d = f"**メッセージ内容：**\n```{message}```\n**サンプル：**\n>>> " + message.replace("!name", "SevenBot").replace(
                "!count", str(len(ctx.guild.members))
            ).replace("!mention", ctx.guild.me.mention)
        e = discord.Embed(
            title=f"{Event_dict[etype]}のメッセージを変更しました。",
            description=d,
            color=Success,
        )
        return await ctx.reply(embed=e)

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def role(self, ctx, single: Optional[bool], *roles: discord.Role):
        if len(roles) > 10:
            e = discord.Embed(title="ロールが多すぎます。", description="ロールは10個以下にして下さい。", color=Error)
            return await ctx.reply(embed=e)
        s = ""
        for r in roles:
            if (
                r.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id
            ) or r.position > ctx.guild.me.top_role.position:
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "no_role_perm").format(r.name),
                    color=Error,
                )
                m = await ctx.reply(embed=e)
                return
        for sfi, sf in enumerate(roles):
            r = sf
            em = self.bot.oemojis["b" + str(sfi + 1)]
            s += f"{em}：{r.mention}\n"
        sn = ""
        if single:
            sn = "（複数選択不可）"
        e = discord.Embed(title=f"ロールパネル{sn}", description=s, color=Widget)
        e.set_footer(text="🛠️で編集")
        m = await ctx.send(embed=e)
        for sfi in range(len(roles)):
            await m.add_reaction(Number_emojis[sfi + 1])
        await ctx.message.delete()

    @commands.command(aliases=["get_perm", "get_pm"])
    async def get_permissions(
        self,
        ctx,
        user: Union[discord.Member, discord.Role] = None,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.CategoryChannel,
        ] = None,
    ):
        if user is None:
            u2 = ctx.author
            n = u2.display_name
            if channel:
                u = channel.permissions_for(u2)
            else:
                u = u2.guild_permissions
        elif isinstance(user, discord.Role):
            u2 = user
            n = u2.name
            u = u2.permissions
        else:
            u2 = user
            n = u2.display_name
            if channel:
                u = channel.permissions_for(u2)
            else:
                u = u2.guild_permissions
        admin = False
        if u.administrator:
            admin = True
        r = ""
        ph = dict(iter(u))
        if channel:
            ow = dict(iter(channel.overwrites_for(user)))
            for r2 in user.roles:
                if r2.is_default():
                    continue
                ow.update({k: v for k, v in iter(channel.overwrites_for(r2)) if v is not None})
        em = discord.Embed(
            title=get_txt(ctx.guild.id, "permission_title").format(n),
            color=Info,
        )
        if channel:
            em.title = get_txt(ctx.guild.id, "permission_title_channel").format(n, channel.name)
        for tpt in get_txt(ctx.guild.id, "permissions_text"):
            r = ""
            for pk, pv3 in tpt.items():
                if pk == "name":
                    continue
                elif "|" in pk:
                    if not channel:
                        continue
                    pv = ph[pk.split("|")[0]]
                else:
                    pv = ph[pk]
                if admin:
                    e = self.bot.oemojis["check8"]
                    if pk == "administrator":
                        e = self.bot.oemojis["check"]
                elif pv:
                    e = self.bot.oemojis["check"]
                else:
                    e = self.bot.oemojis["check4"]
                r += str(e)
                if channel:
                    if "|" in pk:
                        pw = ow[pk.split("|")[1]]
                    else:
                        pw = ow[pk]
                    if pw is None:
                        e = self.bot.oemojis["check7"]
                    elif pw is False:
                        e = self.bot.oemojis["check4"]
                    elif pw:
                        e = self.bot.oemojis["check"]
                    r += f"({e})"
                r += f"`{pv3}`\n"
            em.add_field(name=tpt["name"], value=r)
        em.set_footer(text=Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["permission_value"] + str(hash(u)))
        await ctx.reply(embed=em)

    @commands.command(aliases=["get_rm"])
    async def get_role_member(self, ctx, role: discord.Role):
        res = ""
        ri = -1
        for i, m in enumerate(role.members):
            at = f"{m.mention}(`{m}`)\n"
            if len(res + at) > 2048:
                ri = i
                break
            res += at
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "get_rm").format(role.name),
            description=res,
            color=Info,
        )
        if not ri == -1:
            e.set_footer(text=get_txt(ctx.guild.id, "get_rm_more").format(str(len(role.members) - ri)))
        return await ctx.reply(embed=e)

    @commands.command(aliases=["get_rc"])
    async def get_role_count(self, ctx, show_bot: bool = False):
        u = ctx.guild.roles
        u.reverse()
        r = ""
        title = get_txt(ctx.guild.id, "rc_title")
        for ui in u:
            flag = False
            if ui.managed:
                flag = True
            mc = ui.members
            mci = len(mc)
            if flag:
                if show_bot:
                    r += f"({ui.mention} : {mci}{Texts[self.bot.guild_settings[ctx.guild.id]['lang']]['rc_people']})\n"
            else:
                per = round(len(ui.members) / float(len(ctx.guild.members)) * 100, 2)
                r += (
                    f"{ui.mention} : {mci}{Texts[self.bot.guild_settings[ctx.guild.id]['lang']]['rc_people']}"
                    + f" - {per}%\n"
                )
            if len(r) > 4000:
                e = discord.Embed(title=title, description=r, color=Info)
                await ctx.reply(embed=e)
                r = ""
                title = ""
        e = discord.Embed(title=title, description=r, color=Info)
        return await ctx.reply(embed=e)

    @commands.command(aliases=["user", "ui", "userinfo"])
    async def lookup(self, ctx, u: Union[discord.User, discord.Member, int] = None):
        used_api = False
        if u is None:
            u = ctx.author
        elif isinstance(u, int):
            try:
                u = await self.bot.fetch_user(u)
                used_api = True
            except NotFound:
                e = discord.Embed(title=get_txt(ctx.guild.id, "lookup")[11], color=Error)
                return await ctx.reply(embed=e)
        else:
            if ctx.guild.get_member(u.id) is not None:
                u = ctx.guild.get_member(u.id)
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "lookup")[0].format(u.display_name),
            color=Info,
        )
        if used_api:
            e.title += get_txt(ctx.guild.id, "lookup")[12]
        e.set_thumbnail(url=u.display_avatar.url)
        e.add_field(
            name=Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["lookup"][1],
            value=u.display_name,
        )
        e.add_field(
            name=Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["lookup"][2],
            value=str(u),
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "lookup")[3],
            value=discord.utils.format_dt(u.created_at),
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "lookup")[4],
            value=discord.utils.format_dt(u.joined_at)
            if isinstance(u, discord.Member)
            else get_txt(ctx.guild.id, "lookup")[9],
        )
        e.add_field(
            name="Bot",
            value=get_txt(ctx.guild.id, "lookup")[10][0 if u.bot else 1],
        )
        if isinstance(u, discord.User):
            st = str(self.bot.oemojis["unknown"]) + get_txt(ctx.guild.id, "lookup")[5][0]
        elif u.status == discord.Status.online:
            st = str(self.bot.oemojis["online"]) + get_txt(ctx.guild.id, "lookup")[5][1]
        elif u.status == discord.Status.idle:
            st = str(self.bot.oemojis["idle"]) + get_txt(ctx.guild.id, "lookup")[5][2]
        elif u.status == discord.Status.dnd:
            st = str(self.bot.oemojis["dnd"]) + get_txt(ctx.guild.id, "lookup")[5][3]
        elif u.status == discord.Status.offline:
            st = str(self.bot.oemojis["offline"]) + get_txt(ctx.guild.id, "lookup")[5][4]
        else:
            st = str(self.bot.oemojis["unknown"]) + str(u.status)
        e.add_field(
            name=Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["lookup"][5][5],
            value=st,
        )
        rs = ""
        if isinstance(u, discord.Member):
            for r in reversed(u.roles):
                rs += r.mention + ","
            e.add_field(name=get_txt(ctx.guild.id, "lookup")[6], value=rs.rstrip(","))
            e.add_field(
                name=Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["lookup"][7],
                value=get_txt(ctx.guild.id, "lookup")[8].format(
                    self.bot.guild_settings[ctx.guild.id]["warns"].get(u.id, 0)
                ),
            )
        return await ctx.reply(embed=e)

    @commands.command(aliases=["guildinfo", "si", "gi"])
    async def serverinfo(self, ctx, *, guild: discord.Guild = None):
        guild = guild or ctx.guild
        if guild is None:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "serverinfo")["unknown"],
                color=Error,
            )
            return await ctx.reply(embed=e)
        if (not guild.get_member(ctx.author.id)) and not await self.bot.is_owner(ctx.author):
            e = discord.Embed(title=get_txt(ctx.guild.id, "serverinfo")["noperm"], color=Error)
            return await ctx.reply(embed=e)
        e = discord.Embed(
            title=guild.name + " - " + f"`{guild.id}`",
            color=Info,
            timestamp=guild.created_at,
        )
        e.set_author(
            name=f"{guild.owner.display_name}({guild.owner}, ID:{guild.owner.id})",
            icon_url=guild.owner.display_avatar.url,
        )
        e.set_thumbnail(url=guild.icon.url)
        chs = (
            str(self.bot.oemojis["cc"])
            + " "
            + get_txt(ctx.guild.id, "serverinfo")["channels"][1]
            + ":"
            + str(len(guild.categories))
            + "\n"
        )
        chs += (
            str(self.bot.oemojis["tc"])
            + " "
            + get_txt(ctx.guild.id, "serverinfo")["channels"][2]
            + ":"
            + str(len(guild.text_channels))
            + "\n"
        )
        chs += (
            str(self.bot.oemojis["vc"])
            + " "
            + get_txt(ctx.guild.id, "serverinfo")["channels"][3]
            + ":"
            + str(len(guild.voice_channels))
            + "\n"
        )
        e.add_field(name=get_txt(ctx.guild.id, "serverinfo")["channels"][0], value=chs)
        e.add_field(
            name=get_txt(ctx.guild.id, "serverinfo")["members"][0],
            value=get_txt(ctx.guild.id, "serverinfo")["members"][1].format(
                len(guild.members),
                len([m for m in guild.members if not m.bot]),
                len([m for m in guild.members if m.bot]),
                self.bot.oemojis["user"],
                self.bot.oemojis["bot"],
            ),
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "serverinfo")["emoji"][0],
            value=get_txt(ctx.guild.id, "serverinfo")["emoji"][1].format(
                len([e for e in guild.emojis if not e.animated]),
                len([e for e in guild.emojis if e.animated]),
                guild.emoji_limit,
            ),
        )
        e.set_footer(text=get_txt(ctx.guild.id, "serverinfo")["created_at"])
        return await ctx.reply(embed=e)

    @commands.group(name="sevennet")
    @commands.has_guild_permissions(manage_channels=True)
    async def sevennet(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @sevennet.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_sevennet(self, ctx):
        global Sevennet_channels
        if ctx.channel.id in Sevennet_channels:
            e = discord.Embed(
                title="既に有効です。",
                description="SevenNetチャンネルではないチャンネルで使用してください。",
                color=Error,
            )
            return await ctx.reply(embed=e)
        else:
            e2 = discord.Embed(
                title="SevenNetに仲間が入ってきた!",
                description=f"{ctx.guild.name}がSevenNetに参加しました！",
                timestamp=ctx.message.created_at,
                color=Chat,
            )
            e2.set_thumbnail(url=ctx.guild.icon.url)
            e2.set_footer(text=f"現在のチャンネル数：{len(Sevennet_channels)+1}")
            for c in Sevennet_channels:
                cn = self.bot.get_channel(c)
                if cn is None:
                    Sevennet_channels.remove(c)
                else:
                    await cn.send(embed=e2)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`はSevenNetチャンネルになりました。",
                description="ルールを確認してください。",
                color=Success,
            )
            await ctx.reply(embed=e)
            e3 = discord.Embed(title="SevenNetチャンネルのルールについて", color=Info)
            e3.add_field(name="宣伝禁止", value="宣伝はしないで下さい。", inline=False)
            e3.add_field(
                name="暴言・エロ画像など、不快に感じる行為禁止",
                value="不快に感じる行為はしないで下さい。",
                inline=False,
            )
            f1 = self.bot.oemojis["up"]
            f2 = self.bot.oemojis["down"]
            f3 = self.bot.oemojis["reply"]
            f4 = self.bot.oemojis["report"]
            e3.add_field(
                name="ボタンについて",
                value=f"{f1}：高評価\n{f2}：低評価\n{f3}：返信（押して消えた後10秒以内に送信）\n{f4}：報告/削除",
                inline=False,
            )
            r = await ctx.send(embed=e3)
            await r.pin()
            Sevennet_channels.append(ctx.channel.id)

    @sevennet.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_sevennet(self, ctx):
        global Sevennet_channels
        if ctx.channel.id in Sevennet_channels:
            Sevennet_channels.remove(ctx.channel.id)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`はSevenNetチャンネルではなくなりました。",
                description="",
                color=Success,
            )
            await ctx.reply(embed=e)
            e2 = discord.Embed(
                title="SevenNetの仲間が抜けちゃった…",
                description=f"{ctx.guild.name}がSevenNetから退出しました。",
                timestamp=ctx.message.created_at,
                color=Chat,
            )
            e2.set_thumbnail(url=ctx.guild.icon.url)
            e2.set_footer(text=f"現在のチャンネル数：{len(Sevennet_channels)}")
            for c in Sevennet_channels:
                cn = self.bot.get_channel(c)
                if cn is None:
                    Sevennet_channels.remove(c)
                else:
                    await cn.send(embed=e2)
        else:
            e = discord.Embed(
                title="ここはSevenNetチャンネルではありません。",
                description="SevenNetチャンネルで使用してください。",
                color=Error,
            )
            return await ctx.reply(embed=e)

    @commands.command(name="free_channel")
    @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
    async def free_channel(self, ctx):
        if ctx.channel.category is None:
            cat = await ctx.guild.create_category_channel(
                get_txt(ctx.guild.id, "free_channel_title"),
                overwrites=ctx.channel.overwrites,
                position=ctx.channel.position,
            )
            await ctx.channel.edit(category=cat)
        self.bot.oemojis["add"]
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "free_channel_title"),
            description=get_txt(ctx.guild.id, "free_channel_desc").format(self.bot.oemojis["add"]),
            color=Widget,
        )
        m = await ctx.send(embed=e)
        await m.add_reaction(self.bot.oemojis["add"])

    @commands.command(name="parse")
    async def text_parse(self, ctx):
        b1 = 0
        b2 = 0
        b3 = 0
        lb1 = 0
        lb2 = 0
        lb3 = 0
        lb = " "
        err = ""
        ignore = False
        hs = await ctx.channel.history(limit=100).flatten()
        hs.reverse()
        for m in hs:
            for line in m.content.split("\n"):
                if line.startswith("#") or line.startswith("//"):
                    continue
                for i, c in enumerate(line):
                    if c == '"':
                        if not ignore:
                            ignore = '"'
                        elif ignore == '"':
                            ignore = False
                    elif c == "'":
                        if not ignore:
                            ignore = "'"
                        elif ignore == "'":
                            ignore = False
                    elif ignore:
                        pass
                    elif c == "(":
                        lb += "("
                    elif c == ")":
                        if lb[-1] == "(":
                            lb = lb[:-1]
                        else:
                            lb1 += 1
                    elif c == "{":
                        lb += "{"
                    elif c == "}":
                        if lb[-1] == "{":
                            lb = lb[:-1]
                        else:
                            lb2 += 1
                    elif c == "[":
                        lb += "["
                    elif c == "]":
                        if lb[-1] == "[":
                            lb = lb[:-1]
                        else:
                            lb3 += 1
        b1 = lb.count("(")
        b2 = lb.count("{")
        b3 = lb.count("[")
        if not (b1 == 0 and lb1 == 0 and b2 == 0 and lb2 == 0 and b3 == 0 and lb3 == 0):
            if b1 - lb1 != 0:
                err += Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["parse"][2].format(
                    ("(" if b1 - lb1 < 0 else ")"), abs(b1 - lb1)
                )
            if lb1 != 0:
                err += Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["parse"][3].format(")", lb1)
            if b2 - lb2 != 0:
                err += Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["parse"][2].format(
                    ("{" if b2 - lb2 < 0 else "}"), abs(b2 - lb2)
                )
            if lb2 != 0:
                err += Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["parse"][3].format("}", lb2)
            if b3 - lb3 != 0:
                err += Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["parse"][2].format(
                    ("[" if b3 - lb3 < 0 else "]"), abs(b3 - lb3)
                )
            if lb3 != 0:
                err += Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["parse"][3].format("]", lb3)
        if ignore:
            err += Texts[self.bot.guild_settings[ctx.guild.id]["lang"]]["parse"][4].format(ignore)
        if err == "":
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "parse")[0][0],
                description=get_txt(ctx.guild.id, "parse")[0][1],
                color=Success,
            )
        else:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "parse")[1],
                description=err,
                color=Error,
            )
        return await ctx.reply(embed=e)

    @commands.command(name="search_command", aliases=["search_cmd"])
    async def search_command(self, ctx, *, text):
        perf_match = []
        part_match = []
        for c in self.bot.walk_commands():
            if str(c) not in flatten(Categories.values()):
                continue
            elif c.hidden:
                continue
            elif c.name == text:
                perf_match.append(str(c))
            elif text in c.name:
                part_match.append(str(c))
        perf_res = ""
        part_res = ""
        if perf_match:
            for pm in perf_match:
                tmp_txt = (
                    f"**`{pm}`** "
                    + (
                        get_txt(ctx.guild.id, "help_detail").get(
                            pm,
                            "_" + get_txt(ctx.guild.id, "help_detail_none") + "_",
                        )
                    ).split("\n")[0]
                    + "\n"
                )
                if len(perf_res + tmp_txt) < 1024:
                    perf_res += tmp_txt
                else:
                    break
        else:
            perf_res = get_txt(ctx.guild.id, "getid_search")[3]
        if part_match:
            for pm in part_match:
                tmp_txt = (
                    f"**`{pm}`** "
                    + (
                        get_txt(ctx.guild.id, "help_detail").get(
                            pm,
                            "_" + get_txt(ctx.guild.id, "help_detail_none") + "_",
                        )
                    ).split("\n")[0]
                    + "\n"
                )
                if len(part_res + tmp_txt) < 1024:
                    part_res += tmp_txt
                else:
                    break
        else:
            part_res = get_txt(ctx.guild.id, "getid_search")[3]
        e = discord.Embed(title=get_txt(ctx.guild.id, "command_search"), color=Bot_info)
        e.add_field(
            name=get_txt(ctx.guild.id, "getid_search")[1],
            value=perf_res,
            inline=False,
        )
        e.add_field(
            name=get_txt(ctx.guild.id, "getid_search")[2],
            value=part_res,
            inline=False,
        )
        return await ctx.reply(embed=e)

    @commands.Cog.listener("on_guild_voice_update")
    async def on_voice_state_update(member, before, after):
        if not [m for m in after.channel.members if not m.bot]:
            await after.guild.voice_client.disconnect()

    @commands.command(hidden=True, name="exec_cog")
    @commands.is_owner()
    async def _exec(self, ctx, *, script):
        script = script.replace("```py", "").replace("```", "")
        exec("async def __ex(self,_bot,_ctx,ctx): " + "".join(f"\n {line}" for line in script.split("\n")))
        ret = await locals()["__ex"](self, self.bot, ctx, ctx)
        try:
            await ctx.reply(ret)
        except BaseException:
            pass
        await ctx.message.add_reaction(self.bot.oemojis["check8"])

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_webhooks=True)
    async def follow(self, ctx):
        await self.bot.send_subcommands(ctx)

    @follow.command("announce")
    async def follow_announce(self, ctx):
        await self.bot.get_channel(738879378196267009).follow(destination=ctx.channel)
        await ctx.message.add_reaction(self.bot.oemojis["check8"])

    @follow.command("updates")
    async def follow_updates(self, ctx):
        await self.bot.get_channel(817751838719868950).follow(destination=ctx.channel)
        await ctx.message.add_reaction(self.bot.oemojis["check8"])

    @commands.command(aliases=["vote_rank"])
    async def vote_ranking(self, ctx):
        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(["t", "t", "t"])
        table.set_cols_align(["r", "l", "r"])
        res = [get_txt(ctx.guild.id, "vote_rank")]
        tmp_rank = collections.Counter([v["id"] for v in await self.bot.DBL_client.get_bot_votes()])
        rank = collections.defaultdict(lambda: 0)
        rank.update(
            dict(
                map(
                    lambda k: (int(k[0]), k[1]),
                    sorted(tmp_rank.items(), key=lambda a: a[1], reverse=True),
                )
            )
        )
        i = 0
        break_flag = False
        show_author = True
        for _, tav in enumerate(rank.items()):
            if i >= 10:
                if show_author:
                    i += 1
                    continue
                else:
                    break_flag = True
                    break
            i += 1
            m = self.bot.get_user(int(tav[0])) or await self.bot.fetch_user(int(tav[0]))
            if m == ctx.author:
                show_author = False
            res.append([str(i) + ".", remove_emoji(str(m)), tav[1]])
        if show_author:
            try:
                a = [
                    ("-" if break_flag or rank[ctx.author.id] == 0 else str(i) + "."),
                    remove_emoji(str(ctx.author)),
                    rank[ctx.author.id],
                ]
                res.append([" ", " ", " "])
                res.append(a)
            except KeyError:
                pass
        table.add_rows(res)
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "vote_rank_title"),
            description=f"```asciidoc\n{table.draw()}```",
            color=Info,
        )
        return await ctx.reply(embed=e)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def upload_commands(self, ctx):
        li = []
        start = time.time()

        async def add_l(c):
            if Texts["ja"]["help_detail"].get(str(c)):
                await self.bot.db.commands.delete_many({"name": str(c)})
                ca = [(ck, cv) for ck, cv in Categories.items() if str((c.parents or [c])[-1]) in cv]
                if not ca:
                    return
                ca = ca[0]
                desc_txt = (
                    get_txt(ctx.guild.id, "help_detail")
                    .get(str(c), get_txt(ctx.guild.id, "help_detail_none"))
                    .lstrip("\n ")
                )
                if (not isinstance(c, commands.Group)) or (
                    get_txt(ctx.guild.id, "help_detail").get(str(c))
                    and len(inspect.signature(c.callback).parameters) > 2
                ):
                    if desc_txt != get_txt(ctx.guild.id, "help_detail_none"):
                        synt = syntaxer.Syntax(c, desc_txt)
                        syntaxes = []
                        for s in synt.args:
                            syntaxes.append(
                                {
                                    "name": s.name,
                                    "optional": s.optional,
                                    "variable": bool(s.flag & syntaxer.ArgumentType.variable),
                                    "kwarg": bool(s.flag & syntaxer.ArgumentType.kwarg),
                                    "detail": s.description,
                                }
                            )
                else:
                    syntaxes = None
                li.append(
                    {
                        "name": str(c),
                        "desc": Texts["ja"]["help_detail"].get(str(c)),
                        "parents": c.full_parent_name,
                        "category": ca[0],
                        "index": ca[1].index(str((c.parents or [c])[-1])),
                        "aliases": c.aliases,
                        "syntax": syntaxes,
                    }
                )
                if isinstance(c, commands.Group):
                    for sc in c.commands:
                        await add_l(sc)

        for _, cc in Categories.items():
            for c in cc:
                try:
                    await add_l(self.bot.get_command(c))
                except Exception as e:
                    await ctx.reply(c)
                    raise e
        await self.bot.db.commands.insert_many(li)
        await ctx.reply(f"Done\nTook: {time.time() - start}")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def fix(self, ctx=None):
        fixed = []
        res = {}
        for tg in self.bot.guilds:
            gid = tg.id
            if gid not in self.bot.guild_settings.keys():
                fixed.append("all")
                res[gid] = DEFAULT_SETTINGS.copy()
            else:
                res[gid] = self.bot.guild_settings[gid]
                for ds, dsv in DEFAULT_SETTINGS.items():
                    if ds not in self.bot.guild_settings[gid]:
                        res[gid][ds] = dsv
                        fixed.append(ds)
        try:
            self.bot.guild_settings.clear()
            self.bot.guild_settings.update(res)
        except Exception as e:
            raise e
        print(id(self.bot.guild_settings))
        try:
            if fixed == {}:
                await ctx.channel.send("キーは修復されませんでした。")
            else:
                await ctx.channel.send(f"キー`{collections.Counter(fixed)}`を修復しました。")
        except BaseException:
            pass


def setup(_bot: "SevenBot"):
    global bot
    bot = _bot
    _bot.add_cog(MainCog(_bot), override=True)

    @bot.before_invoke
    async def count_commands(ctx):
        if str(ctx.command) not in flatten(Categories.values()):
            return
        if str(ctx.command).split(" ")[0] not in Command_counter.keys():
            Command_counter[str(ctx.command).split(" ")[0]] = 0
        Command_counter[str(ctx.command).split(" ")[0]] += 1
        return

    @bot.event
    async def on_error(_, *args, **__):
        try:
            ex = sys.exc_info()[1]
            if bot.debug:
                return print(traceback.format_exc())
            if not bot.is_ready():
                return
            if isinstance(ex, (AttributeError, aiohttp.client_exceptions.ClientOSError)):
                return
            if isinstance(ex, discord.HTTPException):
                if ex.status == 400:
                    if "message_reference: Unknown message" not in ex.text:
                        return sentry_sdk.capture_exception(ex)
                elif ex.status in (403, 404):
                    return

            if len(args) == 0:
                c = bot.get_channel(763877469928554517)
                e = discord.Embed(
                    title=get_txt(c.guild.id, "error"),
                    description="```" + traceback.format_exc() + "```",
                    color=Error,
                )
                e = None
                if isinstance(args[0], Context):
                    c = args[0].message.channel
                else:
                    c = bot.get_channel(763877469928554517)
                    e = discord.Embed(
                        title=get_txt(c.guild.id, "error"),
                        description="```" + traceback.format_exc() + "```",
                        color=Error,
                    )
                    if "Forbidden" in e.description:
                        return
                if e is None:
                    e = discord.Embed(
                        title=get_txt(c.guild.id, "error"),
                        description="```" + "\n".join(traceback.format_exception_only(type(ex), ex)) + "```",
                        color=Error,
                    )
            try:
                sentry_sdk.capture_exception(ex)
                msg = await c.send(embed=e)
                await msg.add_reaction(bot.oemojis["down"])
                await bot.wait_for(
                    "reaction_add",
                    check=lambda r, u: r.message.id == msg.id and r.emoji.name == "down" and not u.bot,
                )
                e = discord.Embed(
                    title=get_txt(c.guild.id, "error"),
                    description="```" + traceback.format_exc() + "```",
                    color=Error,
                )
                await msg.edit(embed=e)
            except Forbidden:
                pass
        except BaseException:
            pass
