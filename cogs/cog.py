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
from typing import Optional, Union

import aiohttp
import bs4
import discord
from async_google_trans_new import AsyncTranslator
from discord import CategoryChannel, Forbidden, NotFound
from discord.ext import commands
from discord.ext.commands import (BadArgument, CommandNotFound, Context,
                                  MissingRequiredArgument, bot)
from sembed import SAuthor, SEmbed, SField
from texttable import Texttable

import _pathmagic  # type: ignore # noqa: F401
from common_resources.consts import (Activate_aliases, Alert, Chat,
                                     Deactivate_aliases, Error, Info,
                                     Official_discord_id, Success,
                                     Widget, Bot_info, Owner_ID, Event_dict, Stat_dict)
from common_resources.tools import flatten, remove_emoji, convert_timedelta


Categories = {
    "bot": [
        "help",
        "about",
        "tos",
        "ping",
        "invite",
        "tips",
        "search_command",
        "follow"
    ],
    "server": [
        "get_role_count",
        "get_role_member",
        "get_permissions",
        "level",
        "level_ranking",
        "serverinfo",
        "emoji_list"
    ],
    "info": [
        "lookup",
        "check_url",
        "getid",
        "snowflake"
    ],
    "panel": [
        "vote",
        "party"
    ],
    "tools": [
        "translate",
        "afk",
        "music",
        "tts",
        "shorten"
    ],
    "fun": [
        "werewolf",
        "bignum",
        "tic_tac_toe",
        "parse",
        "image",
        "lainan_talk",
        "sudden_death",
        "loop_trans",
        "reencode"
    ],
    "serverpanel": [
        "auth",
        "role",
        "ticket",
        "free_channel"
    ],
    "moderation": [
        "clear_channel",
        "mute",
        "fatal",
        "lockdown",
        "archive",
        "warn"
    ],
    "global": ["gchat", "sevennet", "sgc"],
    "settings": [
        "ww_role",
        "autoreply",
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
        "warn_settings"
    ]

}
Default_settings = {
    "autoreply": {},
    "muted": {},
    "tts_dicts": {},
    "deactivate_command": [],
    "last_everyone": {},
    "everyone_count": {},
    "hasnt_admin": "権限がありません。",
    "do_announce": True,
    "announce_channel": False,
    "auth_role": 0,
    "trans_channel": {},
    "event_messages": {"join": False, "leave": False},
    "event_message_channel": 0,
    "alarm_channels": 0,
    "level_counts": {},
    "levels": {},
    "level_roles": {},
    "level_active": False,
    "level_channel": False,
    "level_ignore_channel": [],
    "bump_role": False,
    "do_dissoku_alert": False,
    "dissoku_role": False,
    "do_stat_channels": False,
    "stat_channels": {},
    "stat_update_counter": 0,
    "ticket_category": 0,
    "ticket_time": {},
    "ticket_subject": {},
    "ticket_message": [],
    "auto_parse": [],
    "do_everyone_alert": True,
    "lang": "ja",
    "expand_message": True,
    "do_bump_alert": True,
    "invites": [],
    "prefix": None,
    "autopub": [],
    "alarms": {},
    "2ch_link": [],
    "role_link": {},
    "role_keep": False,
    "timezone": 0,
    "archive_category": 0,
    "ww_role": {"alive": None, "dead": None},
    "lainan_talk": [],
    "auth_channel": {
        "type": None,
        "channel": 0,
    },
    "starboards": {},
    "level_boosts": {},
    "warns": {},
    "warn_settings": {"punishments": {}, "auto": 0},
    "economy": {
    }
}
Last_favorite = {}
Time_format = '%Y-%m-%d %H:%M:%S'
Image_exts = ["gif", "jpg", "jpeg", "jpe", "jfif", "png", "bmp", "ico"]
Link_2ch_re = re.compile(r">>[0-9]+")
Sevennet_footer_re = re.compile(
    r"Server: (.+?) | ID: (.{8}) | [±\-\+](\d+) \( \+(\d+) / -(\d+) \)")
Message_url_re = re.compile(
    r"https?://(?:(?:ptb|canary)\.)?(?:discord(?:app)?\.com)/channels/(\d+)/(\d+)/(\d+)")
Mention_re = re.compile(r"<@\!?(\d+?)>")
Channel_ids = {
    "log": 756254787191963768,
    "announce": 756254915441197206,
    "emoji_print": 756254956817743903,
    "global_report": 756255003341225996,
    "boot_log": 747764100922343554
}
Blacklists = []
Squares = ["yellow_square", "white_large_square",
           "brown_square", "black_large_square", "black_small_square"]
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


async def send_reaction(channel, reactions, message):
    m = await channel.send(**message)
    g = []
    for r in reactions:
        if r in Official_emojis.keys():
            e = Official_emojis[r]
        else:
            e = r
        g.append(m.add_reaction(e))
    ga = asyncio.gather(*g)
    await ga
    return m


Number_emojis = []
Bump_id = 302050872383242240
Dissoku_id = 761562078095867916
Trans = 0x1a73e8
Bump_color = 0x24b8b8
Dissoku_color = 0x7289da

SB_Bans = {}

translator = AsyncTranslator()


class MainCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Official_emojis, Texts, Global_chat, Bump_alerts, Dissoku_alerts, Command_counter, Global_mute, GBan, Sevennet_channels, Sevennet_posts
        global get_txt, is_command
        self.bot = bot
        if not self.bot.consts.get("gcm"):
            self.bot.consts["gcm"] = collections.defaultdict(dict)
        try:
            Guild_settings = self.bot.guild_settings
            get_txt = self.bot.get_txt
            Official_emojis = self.bot.consts["oe"]
            is_command = self.bot.is_command
            Global_chat = self.bot.raw_config["gc"]
            Bump_alerts = self.bot.raw_config["ba"]
            Dissoku_alerts = self.bot.raw_config["da"]
            Command_counter = self.bot.raw_config["cc"]
            Sevennet_channels = self.bot.raw_config["snc"]
            Sevennet_posts = self.bot.raw_config["snp"]
            Global_mute = self.bot.raw_config["gm"]
            GBan = self.bot.raw_config["gb"]
            Texts = self.bot.texts
            for i in range(11):
                Number_emojis.append(Official_emojis["b" + str(i)])
        except Exception as e:
            raise e

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
        global Guild_settings
        await self.bot.get_channel(756254787191963768).send(f"<サーバー退出>\n名前：{g.name}\nID：{g.id}")

    @commands.Cog.listener(name="on_guild_join")
    async def on_guild_join(self, g):
        global Guild_settings
        if g.id in Blacklists:
            await g.leave()
            return
        Guild_settings[g.id] = copy.deepcopy(Default_settings)
        if g.owner_id == self.bot.user.id:
            return
        await self.bot.get_channel(756254787191963768).send(f"<サーバー参加>\n名前：{g.name}\nID：{g.id}\n現在の個数：{len(self.bot.guilds)}")
        if g.region == discord.VoiceRegion.japan:
            lang = "ja"
        else:
            lang = "en"
        await self.bot.save()
        Guild_settings[g.id]["lang"] = lang

    @commands.Cog.listener("on_message")
    async def on_message_spam(self, message):
        if is_command(message):
            try:
                await self.bot.wait_for("message", check=lambda m: m.guild.id == message.guild.id and is_command(m), timeout=5)
                await self.bot.wait_for("message", check=lambda m: m.guild.id == message.guild.id and is_command(m), timeout=5)
            except asyncio.TimeoutError:
                pass
            else:
                async with aiohttp.ClientSession() as s:
                    async with s.post("https://discord.com/api/webhooks/820630742387785729/Kl8gcxyZOhepGnrch9KfFITDn9zZAWlZNjIZGLlw2WAso71Dw0Ahk21VL8WdkWr7KJJI", json={"content": f"Guild:{message.guild.name} {message.guild.id}\nUser:{message.author} {message.author.id}\nContent:\n```{message.content}\n```", "allowed_mentions": {"parse": []}}):
                        pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not Guild_settings.get(after.guild.id):
            return
        for r in after.roles:
            if r.id in Guild_settings[after.guild.id]["role_link"].keys():
                for rl in Guild_settings[after.guild.id]["role_link"][r.id]:
                    try:
                        await self.bot.get_guild(rl[0]).get_member(after.id).add_roles(
                            self.bot.get_guild(rl[0]).get_role(rl[1]), reason=get_txt(after.guild.id, "role_link")["reason"].format(
                                self.bot.get_guild(rl[0]).name, self.bot.get_guild(
                                    rl[0]).get_role(rl[1]).name
                            )
                        )
                    except AttributeError:
                        pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not Guild_settings.get(member.guild.id):
            return
        if Guild_settings[member.guild.id]["event_messages"]["join"]:
            g = self.bot.get_guild(member.guild.id)
            try:
                sc = self.bot.get_channel(
                    Guild_settings[member.guild.id]["event_message_channel"])
                await sc.send(Guild_settings[member.guild.id]["event_messages"]["join"]
                              .replace("!name", member.name)
                              .replace("!mention", member.mention)
                              .replace("!count", str(len(g.members)))
                              .replace("\\n", "\n"))
            except BaseException:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if not Guild_settings.get(member.guild.id):
            await self.bot.get_command("fix").callback()
        if Guild_settings[member.guild.id]["event_messages"]["leave"]:
            g = self.bot.get_guild(member.guild.id)
            sc = self.bot.get_channel(
                Guild_settings[member.guild.id]["event_message_channel"])
            await sc.send(Guild_settings[member.guild.id]["event_messages"]["leave"]
                          .replace("!name", member.name)
                          .replace("!mention", member.mention)
                          .replace("!count", str(len(g.members)))
                          .replace("\\n", "\n"))

    @commands.Cog.listener("on_message")
    async def on_message_ar(self, message):
        global last_announce
        global Guild_settings
        global Bump_alerts, Dissoku_alerts
        global Afks
        if message.author.id in GBan.keys() or message.channel.id in self.bot.global_chats:
            return
        if not self.bot.is_ready():
            return
        if message.author.bot or message.channel.id in Guild_settings[message.guild.id]["lainan_talk"]:
            return
        if message.author.id in SB_Bans.keys() and is_command(message):
            if SB_Bans[message.author.id] > time.time():
                return
        arp = Guild_settings[message.guild.id].get("autoreply")
        random_tmp = []

        async def ar_send(ch, msg_content):
            try:
                if msg_content.startswith("!"):
                    cmd = msg_content.split(" ", 1)[0][1:].lower()
                    cnt = msg_content.split(" ", 1)[1]
                    if cmd == "noreply":
                        await ch.send(cnt)
                    elif cmd == "pingreply":
                        await message.reply(cnt, mention_author=True)
                    elif cmd == "react":
                        try:
                            await message.add_reaction(cnt)
                        except discord.errors.BadRequest:
                            await message.add_reaction(Official_emojis["check2"])
                    elif cmd == "random":
                        random_tmp.append(cnt)
                else:
                    await message.reply(msg_content)
            except asyncio.TimeoutError:
                pass
        ga = []
        if arp is not None:
            for ar in arp.values():
                if ar[0].startswith("!") and len(ar[0].split(" ", 1)) > 1:
                    cmd = ar[0].split(" ", 1)[0][1:].lower()
                    cnt = ar[0].split(" ", 1)[1]
                    if cmd == "re":
                        if re.search(cnt, message.content):
                            ga.append(ar_send(message.channel, ar[1]))
                elif ar[0].lower() in message.content.lower() and not is_command(message):
                    ga.append(ar_send(message.channel, ar[1]))
        await asyncio.gather(*ga)
        if random_tmp:
            await ar_send(message.channel, random.choice(random_tmp))

    @commands.Cog.listener("on_message")
    async def on_message_cmd(self, message):
        global last_announce
        global Guild_settings
        global Bump_alerts, Dissoku_alerts
        global Afks
        if message.content == "sb#fix":
            await self.bot.process_commands(message)
            return
        elif message.content == "sb#save":
            await self.bot.process_commands(message)
            return
        elif message.content == "sb#exec":
            await self.bot.process_commands(message)
            return
        elif message.content == "sb#reload":
            await self.bot.process_commands(message)
            return
        if message.author.id in GBan.keys():
            return
        if (message.channel.id in Guild_settings[message.guild.id]["deactivate_command"]) and not message.author.permissions_in(message.channel).manage_channels:
            if is_command(message):
                e = discord.Embed(
                    title="このチャンネルではコマンドを使用できません。", description="ここでコマンドを実行するには`チャンネルを管理`が必要です。", color=Error)
                e.set_footer(
                    text=get_txt(message.guild.id, "message_delete").format(5))
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
        global Guild_settings
        global Bump_alerts, Dissoku_alerts
        global Afks
        au = message.author.id
        if message.author.id in GBan.keys():
            return
        if not self.bot.is_ready():
            return
        if message.guild.id not in Guild_settings.keys():
            return
        ls = list(Guild_settings[message.guild.id]["muted"].keys())
        if message.author.id in ls:
            dt = datetime.datetime.utcnow()
            mtr = Guild_settings[message.guild.id]["muted"][au]
            mt = datetime.datetime.strptime(mtr, Time_format)
            if mt > dt:
                e = discord.Embed(
                    title=f"{message.author.name}はミュートされています。", description=f"あと{text_to_delta((mt-dt),message)}", color=Alert)
                e.set_footer(
                    text=get_txt(message.guild.id, "message_delete").format(5))
                msg = await message.channel.send(embed=e)
                await message.delete()
                await msg.delete(delay=5)
                return
        if message.author.bot:  # Dissoku_alerts
            if message.channel.id in self.bot.global_chats and message.author.id != self.bot.user.id and message.author.discriminator != "0000":
                await message.delete()
            if message.author.id == Bump_id and Guild_settings[message.guild.id]["do_bump_alert"]:
                try:
                    if message.embeds[0].image != discord.Embed().Empty:
                        if "disboard.org/images/bot-command-image-bump.png" in str(message.embeds[0].image.url):
                            dt = datetime.datetime.utcnow()
                            dt += datetime.timedelta(hours=2)
                            sdt = dt.strftime(Time_format)
                            Bump_alerts[message.guild.id] = [
                                sdt, message.channel.id]
                            e = discord.Embed(title=get_txt(message.guild.id, "bump_detected"),
                                              description=get_txt(message.guild.id, "bump_detected_desc"), color=Bump_color)
                            await message.channel.send(embed=e)
                except IndexError:
                    pass
            elif message.author.id == Dissoku_id and Guild_settings[message.guild.id]["do_dissoku_alert"]:
                try:
                    if message.embeds[0].fields:
                        if message.guild.name in message.embeds[0].fields[0].name and message.embeds[0].fields[0].value == "\u200b":
                            dt = datetime.datetime.utcnow()
                            dt += datetime.timedelta(hours=1)
                            sdt = dt.strftime(Time_format)
                            Dissoku_alerts[message.guild.id] = [
                                sdt, message.channel.id]
                            e = discord.Embed(title=get_txt(message.guild.id, "dissoku_detected"),
                                              description=get_txt(message.guild.id, "dissoku_detected_desc"), color=Dissoku_color)
                            await message.channel.send(embed=e)
                except IndexError:
                    pass
            return
        if message.content == self.bot.user.mention or message.content == f"<@!{self.bot.user.id}>":
            await message.channel.send(get_txt(message.guild.id, "mention_txt").format(self.bot.command_prefix(self.bot, message)[2]))
        if message.channel.id == Channel_ids["announce"]:

            for gs in Guild_settings:
                if not Guild_settings[gs]["do_announce"]:
                    continue
                if gs != DBL_id:
                    continue
                g = self.bot.get_guild(gs)
                fc = g.text_channels[0]
                if Guild_settings[g.id]["announce_channel"]:
                    fc = self.bot.get_channel(
                        Guild_settings[g.id]["announce_channel"])
                elif g.system_channel is not None:
                    fc = g.system_channel
                try:
                    await fc.send(f"**__SevenBot公式鯖より:__**\n```{message.content}```")
                except Forbidden:
                    pass
            return
        gs = Guild_settings.get(message.guild.id)
        if (message.channel.id in Sevennet_channels) and not is_command(message):
            if message.author.id in Global_mute:
                await message.delete()
                e2 = discord.Embed(title="あなたはミュートされています。", info=Error)
                await message.author.send(embed=e2)
            else:
                dt = datetime.datetime.utcnow()
                flag = True
                g = Sevennet_replies.get(message.author.id)
                if g is not None:
                    rdt = g[1]
                    if rdt > dt:
                        flag = False
                        if message.attachments != []:
                            e2 = discord.Embed(
                                title="返信には画像を添付できません。", info=Error)
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
                                name=f"{message.author}(ID:{message.author.id})", value=message.content, inline=False)
                            gl.append(m2.edit(embed=m0))
                        await asyncio.gather(*gl)
                        await message.delete()
                if flag:
                    e = discord.Embed(description=message.content,
                                      timestamp=message.created_at, color=Chat)
                    if len(message.attachments) > 1:
                        e2 = discord.Embed(
                            title="SevenNetでは画像は1つしか送信できません。", info=Error)
                        m = await message.author.send(embed=e2)
                        await message.delete()
                        return
                    elif message.attachments != []:
                        if "".join(os.path.splitext(os.path.basename(message.attachments[0].filename))[1:])[1:] not in Image_exts:
                            e2 = discord.Embed(
                                title="SevenNetでは画像以外のファイルを送信できません。", info=Error)
                            m = await message.author.send(embed=e2)
                            await message.delete()
                            return
                        amsg = await self.bot.get_channel(765528694500360212).send(file=(await message.attachments[0].to_file()))
                        e.set_image(url=amsg.attachments[0].url)
                    mid = hashlib.md5(
                        str(message.id).encode()).hexdigest()[0:8]
                    e.set_author(name=f"{message.author}(ID:{message.author.id})",
                                 icon_url=message.author.avatar_url_as(static_format="png"))
                    e.set_footer(text=f"Server: {message.guild.name} | ID: {mid} | ±0 ( +0 / -0 )",
                                 icon_url=message.guild.icon_url_as(static_format="png"))
                    mids = []
                    cs = []
                    for c in Sevennet_channels:
                        cn = self.bot.get_channel(c)
                        if cn is None:
                            Sevennet_channels.remove(c)
                        else:
                            cs.append(send_reaction(channel=cn, reactions=[
                                "up", "down", "reply", "report"], message={"embed": e}))
                    ga = asyncio.gather(*cs)
                    tmid = await ga
                    await message.delete()
                    for sm in tmid:
                        mids.append([sm.channel.id, sm.id])
                    while len(Sevennet_posts) > 10:
                        Sevennet_posts.pop(list(Sevennet_posts.keys())[0])
                    Sevennet_posts[mid] = {"upvote": [], "downvote": [
                    ], "messages": mids, "guild": message.guild.id}
        if not is_command(message):
            tc = Guild_settings[message.guild.id]["trans_channel"]
            if message.channel.id in list(tc.keys()):
                lng = (await translator.detect(message.clean_content))[0]
                if lng.lower() != tc[message.channel.id].lower():
                    tr = (await translator.translate(message.content, lang_tgt=tc[message.channel.id]))
                    e = discord.Embed(
                        title=get_txt(message.guild.id, "trans_after"), description=tr, color=Trans)
                    e.set_author(
                        name=f"{message.author.name}(ID:{message.author.id})", icon_url=message.author.avatar_url)
                    e.set_footer(text="Powered by async_google_trans_new",
                                 icon_url="https://i.imgur.com/zPOogXx.png")
                    await message.reply(embed=e)
        if message.channel.id in Guild_settings[message.guild.id]["2ch_link"] and re.findall(Link_2ch_re, message.content):
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
            webhook = discord.utils.get(
                ch_webhooks, name="sevenbot-2ch-link-webhook")
            if webhook is None:
                g = self.bot.get_guild(Official_discord_id)
                a = g.icon_url_as(format="png")
                webhook = await message.channel.create_webhook(name="sevenbot-2ch-link-webhook", avatar=await a.read())
            if flag:
                e = discord.Embed(title="負荷をかけないでください！",
                                  description="1000より大きい数は反応しません。\n2chも1000でスレが終わるからしょうがないね（）", color=Error)
                await message.channel.send(embed=e)
            elif res != message.content:
                await webhook.send(content=res,
                                   username=message.author.display_name,
                                   allowed_mentions=discord.AllowedMentions.none(),
                                   avatar_url=message.author.avatar_url_as(
                                       format="png"),
                                   files=message.attachments,
                                   embeds=message.embeds)
                await message.delete()
        if re.match(Message_url_re, message.content) is not None and Guild_settings[message.guild.id]["expand_message"]:
            rids = re.match(Message_url_re, message.content)
            ids = [int(i) for i in [rids[1], rids[2], rids[3]]]
            flag = (ids[0] == message.guild.id)
            if not flag:
                try:
                    flag = bool(self.bot.get_guild(
                        ids[0]).get_member(message.author.id))
                except AttributeError:
                    flag = False
            if flag:
                c = self.bot.get_channel(ids[1])
                if c is None:
                    e = discord.Embed(title=get_txt(message.guild.id, "expand_message_fail"),
                                      description="", color=Error)
                    await message.channel.send(embed=e)
                try:
                    m = await c.fetch_message(ids[2])
                    mc = m.content
                    if m.author.id != message.author.id:
                        return
                    if len(mc.splitlines()) > 10:
                        mc = "\n".join(mc.splitlines()[:10]) + "\n..."
                    if len(mc) > 1000:
                        mc = mc[:1000] + "..."
                    em = discord.Embed(
                        color=Chat, description=mc, timestamp=m.created_at)
                    try:
                        em.set_image(url=m.attachments[0].url)
                    except BaseException:
                        pass
                    em.set_author(name=m.author.display_name,
                                  icon_url=m.author.avatar_url_as(static_format="png"))
                    footer = Texts[Guild_settings[message.guild.id]
                                   ["lang"]]["expand_message_footer"].format(m.channel)
                    if not ids[0] == message.guild.id:
                        footer = Texts[Guild_settings[message.guild.id]
                                       ["lang"]]["expand_message_footer3"].format(m.guild.name) + footer
                    if m.embeds == []:
                        em.set_footer(text=footer, icon_url=self.bot.get_guild(
                            ids[0]).icon_url_as(static_format="png"))
                        await message.reply(embed=em)
                    else:
                        em.set_footer(text=footer + Texts[Guild_settings[message.guild.id]["lang"]]
                                      ["expand_message_footer2"].format(len(m.embeds)), icon_url=self.bot.get_guild(ids[0]).icon_url_as(static_format="png"))
                        bm = await message.reply(embed=em)
                        for e in m.embeds:
                            await bm.reply(embed=e)
                except Exception as er:
                    e = discord.Embed(title=get_txt(message.guild.id, "expand_message_fail"),
                                      description="", color=Error)
                    await message.reply(str(er), embed=e)

    @commands.command()
    async def getid(self, ctx, un=None):
        if un is None:
            e = discord.Embed(title=get_txt(ctx.guild.id, "getid_self")[0].format(
                ctx.author.id), description=get_txt(ctx.guild.id, "getid_self")[1], color=Info)
            return await ctx.reply(embed=e)
        else:
            per = Texts[Guild_settings[ctx.guild.id]
                        ["lang"]]["getid_search"][3]
            inc = Texts[Guild_settings[ctx.guild.id]
                        ["lang"]]["getid_search"][3]
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
                title=get_txt(ctx.guild.id, "getid_search")[0].format(un), color=Info)
            e.add_field(name=get_txt(ctx.guild.id, "getid_search")
                        [1], inline=False, value=per)
            e.add_field(name=get_txt(ctx.guild.id, "getid_search")
                        [2], inline=False, value=inc)
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
            description="この利用規約（以下、「本規約」といいます。）は、SevenBot運営チーム（以下、「当グループ」といいます。）が提供するDiscord Bot 「SevenBot」によるサービス（以下、「本サービス」といいます。）の利用条件を定めるものです。ユーザーの皆さま（以下、「利用者」といいます。）には、本規約に従って、本サービスをご利用いただきます。", color=Bot_info, url="https://sevenbot.jp/tos")
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
        e = discord.Embed(title=get_txt(ctx.guild.id, "tips_title"),
                          description=desc, color=Bot_info)
        e.set_footer(text="ID: " + tid)
        return await ctx.reply(embed=e)

    async def reset(self, ctx):
        Guild_settings[ctx.guild.id] = Default_settings

    @commands.Cog.listener("on_message")
    async def on_message_autopub(self, message):
        if message.author.bot and not message.webhook_id:
            return
        if is_command(message):
            return
        tc = Guild_settings[message.guild.id]["autopub"]
        if message.channel.id in tc:
            try:
                await message.publish()
            except discord.errors.HTTPException:
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

    @commands.command(aliases=["h"])
    async def help(self, ctx, *, datail=None):
        if not self.bot.consts.get("ads"):
            await self.on_message_ad(await self.bot.get_channel(800628621010141224).fetch_message(800634459178663946))
        if datail is None:
            desc = get_txt(ctx.guild.id, "help_categories")[1] + "\n**`uses`** - " + \
                get_txt(ctx.guild.id, "help_category_helps")["uses"] + "\n"
            for ck, cv in Categories.items():
                desc += "**`" + ck + "`** - " + get_txt(ctx.guild.id, "help_category_helps")[
                    ck] + " - " + f"`{cv[0]}`,`{cv[1]}`..." + "\n"
            e = discord.Embed(title=get_txt(ctx.guild.id, "help_categories")[0],
                              description=desc, url="https://sevenbot.jp/commands", color=Bot_info)
            e.set_author(
                name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
            return await ctx.reply(embed=e)
        elif datail == "uses":
            desc = ""
            for cni, (cnk, cnv) in enumerate(sorted(Command_counter.items(), key=lambda x: x[1], reverse=True)[0:10]):
                c = self.bot.get_command(cnk)
                if c:
                    desc += f"#{cni+1}: **`{c.name}`**({cnv}) " + (get_txt(ctx.guild.id, "help_datail").get(
                        str(c), "_" + get_txt(ctx.guild.id, "help_datail_none") + "_")).split("\n")[0] + "\n"
            e = discord.Embed(title=get_txt(ctx.guild.id, "help_ranking"),
                              description=desc, color=Bot_info)
            e.set_author(
                name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
            e.set_footer(
                text=get_txt(ctx.guild.id, "help_categories")[3])
            return await ctx.reply(embed=e)
        elif datail in Categories.keys():
            desc = ""
            for cn in Categories[datail]:
                c = self.bot.get_command(cn)
                if c:
                    desc += f"**`{c.name}`** " + (get_txt(ctx.guild.id, "help_datail").get(str(
                        c), "_" + get_txt(ctx.guild.id, "help_datail_none") + "_")).split("\n")[0] + "\n"
            e = discord.Embed(title=get_txt(ctx.guild.id, "help_categories")[2].format(datail),
                              description=desc, color=Bot_info, url="https://sevenbot.jp/commands#category-" + datail)
            e.set_author(
                name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
            e.set_footer(
                text=get_txt(ctx.guild.id, "help_categories")[3])
            return await ctx.reply(embed=e)
        else:
            datail = datail.lower()
            if self.bot.get_command(datail):
                c = self.bot.get_command(datail)
                if c.hidden:
                    e = SEmbed(title=get_txt(ctx.guild.id, "help_title") + " - " + str(c), description=get_txt(ctx.guild.id, "help_hidden"),
                               color=Bot_info, author=SAuthor(name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url))
                    return await ctx.reply(embed=e)
                desc_txt = get_txt(ctx.guild.id, "help_datail").get(str(
                    c), get_txt(ctx.guild.id, "help_datail_none")).lstrip("\n ")
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "help_title") + " - " + str(c), color=Bot_info, url="https://sevenbot.jp/commands#" + str(c).replace(" ", "-"))
                if (not isinstance(c, commands.Group)) or (get_txt(ctx.guild.id, "help_datail").get(str(c)) and len(inspect.signature(c.callback).parameters) > 2) or (get_txt(ctx.guild.id, "help_datail").get(str(c), "").count("\n") > 1):
                    if desc_txt != get_txt(ctx.guild.id, "help_datail_none"):
                        name_ary = []
                        for l in desc_txt.split("\n"):
                            if ": " not in l:
                                continue
                            name_ary.append(l.split(": ", 2)[0])
                        txt = str(c)
                        for pi, (pn, pv) in enumerate(inspect.signature(c.callback).parameters.items(), -2):
                            if pi < 0:
                                continue
                            if pv.default == inspect.Signature.empty:
                                txt += f" <{name_ary[pi]}>"
                            else:
                                txt += f" [{name_ary[pi]}]"
                        e.add_field(name=get_txt(
                            ctx.guild.id, "help_datail_syntax_name"), value=txt)
                    e.description = desc_txt
                if isinstance(c, commands.Group):
                    sct = ""
                    for c2 in c.commands:
                        sct += f"**`{c2.name}`** " + (get_txt(ctx.guild.id, "help_datail").get(str(
                            c2), "_" + get_txt(ctx.guild.id, "help_datail_none") + "_")).split("\n")[0] + "\n"
                    e.add_field(name=get_txt(
                        ctx.guild.id, "help_datail_subcommands"), value=sct, inline=False)
                at = "`,`".join(c.aliases)
                if at == "":
                    at = Texts[Guild_settings[ctx.guild.id]
                               ["lang"]]["help_datail_aliases_none"]
                else:
                    at = "`" + at + "`"
                e.add_field(name=get_txt(
                    ctx.guild.id, "help_datail_aliases"), value=at, inline=False)
                e.add_field(name=get_txt(ctx.guild.id, "help_datail_count")[0],
                            value=get_txt(ctx.guild.id, "help_datail_count")[1].format(Command_counter.get(str(c).split()[0], 0)), inline=False)
                e.set_author(
                    name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
                return await ctx.reply(embed=e)
            else:
                e = discord.Embed(title=get_txt(ctx.guild.id, "help_title") + " - " + datail,
                                  description=get_txt(ctx.guild.id, "help_none"), color=Bot_info)
                return await ctx.reply(embed=e)

    @commands.group(name="channel_settings", aliases=["ch"])
    @commands.has_permissions(manage_channels=True)
    async def channel_setting(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @channel_setting.command(name="slowmode", aliases=["cooldown"])
    @commands.has_permissions(manage_channels=True)
    async def ch_slowmode(self, ctx, sec: int):
        await ctx.channel.edit(slowmode_delay=sec)
        e = discord.Embed(title=get_txt(ctx.guild.id, "ch")[
                          "slowmode"][0].format(sec), color=Success)
        return await ctx.reply(embed=e)

    @channel_setting.group(name="commands", aliases=["cmd"])
    @commands.has_permissions(manage_channels=True)
    async def ch_commands(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @channel_setting.group(name="auto_parse")
    @commands.has_permissions(manage_channels=True)
    async def ch_auto_parse(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_auto_parse.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_auto_parse(self, ctx):
        global Guild_settings
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["auto_parse"]:
            e = discord.Embed(
                title="既に無効化されています。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["auto_parse"].remove(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`での自動パースを無効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)

    @ch_auto_parse.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_auto_parse(self, ctx):
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["auto_parse"]:
            Guild_settings[ctx.guild.id]["auto_parse"].append(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`での自動パースを有効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(
                title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="2ch_link")
    @commands.has_permissions(manage_channels=True)
    async def ch_2ch_link(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_2ch_link.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_2ch_link(self, ctx):
        global Guild_settings
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["2ch_link"]:
            e = discord.Embed(
                title="既に無効化されています。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["2ch_link"].remove(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`での2ch風メッセージリンクを無効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)

    @ch_2ch_link.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_2ch_link(self, ctx):
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["2ch_link"]:
            Guild_settings[ctx.guild.id]["2ch_link"].append(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`での2ch風メッセージリンクを有効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(
                title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="lainan_talk", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def ch_lainan_talk(self, ctx):
        await self.bot.send_subcommands(ctx)

    @ch_lainan_talk.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_lainan_talk(self, ctx):
        global Guild_settings
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["lainan_talk"]:
            e = discord.Embed(
                title="既に無効化されています。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["lainan_talk"].remove(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`でのLainan APIの返信を無効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)

    @ch_lainan_talk.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_lainan_talk(self, ctx):
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["lainan_talk"]:
            Guild_settings[ctx.guild.id]["lainan_talk"].append(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`でのLainan APIの返信を有効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(
                title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @ch_commands.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_command(self, ctx):
        global Guild_settings
        if ctx.channel.id in Guild_settings[ctx.guild.id]["deactivate_command"]:
            e = discord.Embed(
                title="既に無効化されています。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["deactivate_command"].append(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`での管理者以外のコマンドを無効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)

    @ch_commands.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_command(self, ctx):
        if ctx.channel.id in Guild_settings[ctx.guild.id]["deactivate_command"]:
            Guild_settings[ctx.guild.id]["deactivate_command"].remove(
                ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`でのコマンドを有効にしました。",
                              description="", color=Success)
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(
                title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="level")
    @commands.has_permissions(manage_channels=True)
    async def ch_level(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_level.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def ch_level_activate(self, ctx):
        global Guild_settings
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["level_ignore_channel"]:
            e = discord.Embed(
                title="既に有効です。", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_ignore_channel"].remove(
                ctx.channel.id)
            e = discord.Embed(
                title="このチャンネルでのレベリングが有効になりました。", description="", color=Success)
            return await ctx.reply(embed=e)

    @ch_level.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def ch_level_deactivate(self, ctx):
        global Guild_settings
        if ctx.channel.id in Guild_settings[ctx.guild.id]["level_ignore_channel"]:
            e = discord.Embed(
                title="既に無効です。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_ignore_channel"].append(
                ctx.channel.id)
            e = discord.Embed(
                title="このチャンネルでのレベリングが無効になりました。", description="", color=Success)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="translate", aliases=["trans"])
    @commands.has_permissions(manage_channels=True)
    async def ch_trans(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_trans.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_translate(self, ctx, lang):
        global Guild_settings
        if ctx.channel.id in list(Guild_settings[ctx.guild.id]["trans_channel"].keys()):
            e = discord.Embed(
                title="既に有効です。", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["trans_channel"][ctx.channel.id] = lang
            e = discord.Embed(
                title="自動翻訳が有効になりました。", description="", color=Success)
            return await ctx.reply(embed=e)

    @ch_trans.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_translate(self, ctx):
        global Guild_settings
        if ctx.channel.id not in list(Guild_settings[ctx.guild.id]["trans_channel"].keys()):
            e = discord.Embed(
                title="既に無効です。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            del Guild_settings[ctx.guild.id]["trans_channel"][ctx.channel.id]
            e = discord.Embed(
                title="自動翻訳が無効になりました。", description="", color=Success)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="auto_publish")
    @commands.has_permissions(manage_channels=True)
    async def ch_autopub(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_autopub.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_autopub(self, ctx):
        global Guild_settings
        if ctx.channel.id in Guild_settings[ctx.guild.id]["autopub"]:
            e = discord.Embed(
                title="既に有効です。", color=Error)
            return await ctx.reply(embed=e)
        elif ctx.channel.type == discord.ChannelType.news:
            Guild_settings[ctx.guild.id]["autopub"].append(ctx.channel.id)
            e = discord.Embed(
                title="自動公開が有効になりました。", color=Success)
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(
                title="自動公開はアナウンスチャンネルでのみ使用できます。", color=Error)
            return await ctx.reply(embed=e)

    @ch_autopub.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_autopub(self, ctx):
        global Guild_settings
        if ctx.channel.id not in Guild_settings[ctx.guild.id]["autopub"]:
            e = discord.Embed(
                title="既に無効です。", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["autopub"].remove(ctx.channel.id)
            e = discord.Embed(
                title="自動公開が無効になりました。", color=Success)
            return await ctx.reply(embed=e)

    @commands.group(aliases=["ar"])
    async def autoreply(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @autoreply.command(name="add", aliases=["set"])
    @commands.has_guild_permissions(manage_messages=True)
    async def ar_add(self, ctx, base, *, reply):
        global Guild_settings
        dat = base + reply
        rid = hashlib.md5(dat.encode()).hexdigest()[0:8]
        if ctx.guild.id not in Guild_settings:
            await self.reset(ctx)
        if "autoreply" not in Guild_settings[ctx.guild.id]:
            Guild_settings[ctx.guild.id]["autoreply"] = {}
        Guild_settings[ctx.guild.id]["autoreply"][rid] = [base, reply]
        e = discord.Embed(title=f"自動返信に`{base}`を追加しました。",
                          description=f"戻すには`sb#autoreply remove {base}`または`sb#autoreply remove {rid}`を使用してください", color=Success)
        return await ctx.reply(embed=e)

    @autoreply.command(name="remove", aliases=["del", "delete", "rem"])
    @commands.has_guild_permissions(manage_messages=True)
    async def ar_remove(self, ctx, *, txt):
        global Guild_settings
        res = ""
        count = 0
        new = {}
        if txt in Guild_settings[ctx.guild.id]["autoreply"].keys():
            res += "`" + \
                Guild_settings[ctx.guild.id]["autoreply"][txt][1] + "`\n"
            for ark, ar in Guild_settings[ctx.guild.id]["autoreply"].items():
                if ark != txt:
                    new[ark] = ar
            count = 1
        else:
            for ark, ar in Guild_settings[ctx.guild.id]["autoreply"].items():
                if ar[0] == txt:
                    count += 1
                    res += "`" + ar[1] + "`\n"
                else:
                    new[ark] = ar
        if count == 0:
            e = discord.Embed(
                title=f"自動返信に`{txt}`は含まれていません。", description="`sb#autoreply list`で確認してください。", color=Error)
        else:
            e = discord.Embed(
                title=f"{count}個の自動返信を削除しました。", description=res, color=Success)
            Guild_settings[ctx.guild.id]["autoreply"] = new
        return await ctx.reply(embed=e)

    @autoreply.command(name="list")
    async def ar_list(self, ctx):
        g = ctx.guild.id
        if g not in Guild_settings:
            await self.reset(ctx)
        gs = Guild_settings[g]
        if gs["autoreply"] == {}:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ar_list_no"), description=get_txt(ctx.guild.id, "ar_list_desc"), color=Error)
            return await ctx.reply(embed=e)
        else:
            def make_new():
                table = Texttable()
                table.set_deco(Texttable.HEADER)
                table.set_cols_dtype(['t', 't',
                                      't'])
                table.set_cols_align(["l", "l", "l"])
                table.add_row(get_txt(ctx.guild.id, "ar_list_row"))
                return table
            table = make_new()
            res = []
            for k, v in gs["autoreply"].items():
                b = table.draw()
                table.add_row([k, v[0].replace("\n", get_txt(ctx.guild.id, "ar_list_br")),
                               v[1].replace("\n", get_txt(ctx.guild.id, "ar_list_br"))])
                if len(table.draw()) > 2000:
                    res.append(b)
                    table = make_new()
                    table.add_row([k, v[0].replace("\n", get_txt(ctx.guild.id, "ar_list_br")),
                                   v[1].replace("\n", get_txt(ctx.guild.id, "ar_list_br"))])
            res.append(b)
            e = discord.Embed(title=get_txt(ctx.guild.id, "ar_list")
                              + f" - {1}/{len(res)}", description=f"```asciidoc\n{res[0]}```", color=Info)
            msg = await ctx.reply(embed=e)
            page = 0
            await msg.add_reaction(Official_emojis["left"])
            await msg.add_reaction(Official_emojis["right"])
            while True:
                try:
                    r, u = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and u.id == ctx.author.id and (r.emoji == Official_emojis["right"] or r.emoji == Official_emojis["left"]), timeout=60)
                    if r.emoji == Official_emojis["left"]:
                        if page > 0:
                            page -= 1
                        await msg.remove_reaction(Official_emojis["left"], u)
                    elif r.emoji == Official_emojis["right"]:
                        if page < (len(res) - 1):
                            page += 1
                        await msg.remove_reaction(Official_emojis["right"], u)
                    else:
                        continue
                    e = discord.Embed(title=get_txt(
                        ctx.guild.id, "ar_list") + f" - {page+1}/{len(res)}", description=f"```asciidoc\n{res[page]}```", color=Info)
                    await msg.edit(embed=e)
                except asyncio.TimeoutError:
                    break
            await msg.remove_reaction(Official_emojis["left"], self.bot.user)
            await msg.remove_reaction(Official_emojis["right"], self.bot.user)

    @commands.command()
    @commands.has_guild_permissions(manage_guild=True)
    async def change_prefix(self, ctx, txt=None):
        global Guild_settings
        before = Guild_settings[ctx.guild.id]["prefix"]
        if before is None:
            before = Texts[Guild_settings[ctx.guild.id]
                           ["lang"]]["prefix_changed"][2]
        Guild_settings[ctx.guild.id]["prefix"] = txt.lstrip(" ")
        after = txt
        pre = txt
        if after is None:
            after = Texts[Guild_settings[ctx.guild.id]
                          ["lang"]]["prefix_changed"][2]
            pre = "sb#"
        e = discord.Embed(title=get_txt(ctx.guild.id, "prefix_changed")[0].format(before, after),
                          description=get_txt(ctx.guild.id, "prefix_changed")[1].format(pre), color=Success)
        return await ctx.reply(embed=e)

    @commands.command()
    async def invite(self, ctx):
        e = discord.Embed(
            title="招待URL", description="[https://sevenbot.jp/invite](https://discord.com/oauth2/authorize?client_id=718760319207473152&scope=bot&permissions=808840532&response_type=code&redirect_uri=https%3A%2F%2Fsevenbot.jp%2Fthanks)", color=Bot_info)
        return await ctx.reply(embed=e)

    @commands.command()
    async def about(self, ctx):
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "abouts")[0], color=Bot_info, url="https://sevenbot.jp")
        e.add_field(name=Texts[Guild_settings[ctx.guild.id]
                               ["lang"]]["abouts"][1], value="[名無し。(@sevenc-nanashi)](https://github.com/sevenc-nanashi)")
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[
                    2], value=f"`python {platform.python_version()}`,`discord.py {discord.__version__}`")
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[3],
                    value="https://discord.gg/GknwhnwbAV")
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[4],
                    value=f"{len(self.bot.guilds)}" + get_txt(ctx.guild.id, "abouts")[-2])
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[5],
                    value=f"{len(self.bot.users)}" + get_txt(ctx.guild.id, "abouts")[-1])
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[6],
                    value=f'{len(Global_chat)}{get_txt(ctx.guild.id,"abouts")[-2]}({round(len(Global_chat)/len(list(Guild_settings.keys()))*100)}%)')
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[7],
                    value=f'{len(Sevennet_channels)}{get_txt(ctx.guild.id,"abouts")[-2]}({round(len(Sevennet_channels)/len(list(Guild_settings.keys()))*100)}%)')
        inf = await self.bot.DBL_client.get_bot_info()
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[8],
                    value=get_txt(ctx.guild.id, "abouts")[9].format(inf["points"], inf["monthlyPoints"]))
        e.add_field(name=get_txt(ctx.guild.id, "abouts")[10],
                    value='[SevenBot-dev/SevenBot](https://github.com/SevenBot-dev/SevenBot)')
        e.add_field(name=get_txt(ctx.guild.id, "abouts")
                    [13], value=get_txt(ctx.guild.id, "abouts")[14])
        return await ctx.reply(embed=e)

    @commands.Cog.listener(name="on_command_error")
    async def on_command_error(self, ctx, error):
        print(error)
        if isinstance(error, CommandNotFound):
            return
        elif isinstance(error, MissingRequiredArgument) or isinstance(error, BadArgument):
            e = discord.Embed(title=get_txt(ctx.guild.id, "bad_arg"),
                              description=get_txt(ctx.guild.id, "see_help") + f"\n```\n{error}```", color=Error)
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.MissingPermissions):
            res = ""
            for p in error.missing_perms:
                try:
                    res += get_txt(ctx.guild.id,
                                   "permissions_text")[0][p] + "\n"
                except KeyError:
                    try:
                        res += get_txt(ctx.guild.id,
                                       "permissions_text")[1][p] + "\n"
                    except KeyError:
                        res += get_txt(ctx.guild.id,
                                       "permissions_text")[2][p] + "\n"
            e = discord.Embed(title=get_txt(ctx.guild.id, "missing_permissions")[0], description=get_txt(
                ctx.guild.id, "missing_permissions")[1] + f"```\n{res}```", color=Error)
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.NotOwner):
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "only_admin"), color=Error)
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.CommandOnCooldown):
            e = discord.Embed(title=get_txt(ctx.guild.id, "cooldown"), description=get_txt(
                ctx.guild.id, "cooldown_desc").format(round(error.retry_after, 2)), color=Error)
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.DisabledCommand):
            e = discord.Embed(title=get_txt(ctx.guild.id, "disabled"), color=Error)
            return await ctx.reply(embed=e)
        elif isinstance(error, commands.errors.NSFWChannelRequired):
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "not_nsfw"), color=Error)
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(title=get_txt(ctx.guild.id, "error"),
                              description=f"```\n{error}```", color=Error)
            msg = await ctx.reply(embed=e)
            await msg.add_reaction(Official_emojis["down"])
            try:
                error_msg = ''.join(
                    traceback.TracebackException.from_exception(error).format())
                await bot.wait_for("reaction_add", check=lambda reaction, user: (not isinstance(reaction.emoji, str)) and reaction.emoji.name == "down" and reaction.message.id == msg.id and reaction.count == 2)
                e = discord.Embed(title=get_txt(
                    ctx.guild.id, "error"), description=f"```\n{error_msg[-1990:]}```", color=Error)
                await msg.edit(embed=e)
            except asyncio.TimeoutError:
                pass
            return

    @commands.Cog.listener()
    async def on_command_suggest(self, ctx, suggested_commands):
        e = SEmbed(title=get_txt(ctx.guild.id, "unknown_cmd"),
                   description=get_txt(ctx.guild.id, "see_help"), color=Error)
        if not suggested_commands:
            e.fields.append(SField(name=get_txt(ctx.guild.id, "suggest"),
                                   value=get_txt(ctx.guild.id, "yt_no_matches"), inline=False))
        else:
            e.fields.append(
                SField(name=get_txt(ctx.guild.id, "suggest"), value="```\n", inline=False))
            for s in suggested_commands:
                bv = e.fields[0].value
                e.fields[0].value += s + "\n"
                if len(e.fields[0].value) > 250:
                    e.fields[0].value = bv
                    break
            e.fields[0].value += "```"
        if ctx.guild.id != DBL_id:
            return await ctx.reply(embed=e)

    @commands.command(aliases=["poll"])
    async def vote(self, ctx, title, time: convert_timedelta, multi: bool, *select):
        if len(select) > 10:
            g = ctx.guild
            e = discord.Embed(title=get_txt(g.id, "vote_error")[0],
                              description=get_txt(g.id, "vote_error")[0], color=Error)
            return await ctx.reply(embed=e)
        dt = datetime.datetime.utcnow()
        g = ctx.guild
        dt += time
        e = discord.Embed(
            title=get_txt(g.id, "voting")[0], color=Widget, timestamp=dt)
        e.add_field(name=Texts[Guild_settings[g.id]["lang"]]
                    ["voting"][1], value=title, inline=False)
        e.add_field(name=get_txt(g.id, "voting")[2], value=(Texts[Guild_settings[g.id]["lang"]]
                                                            ["voting"][3][0]if multi else get_txt(g.id, "voting")[3][1]), inline=False)
        s = ""
        for sfi, sf in enumerate(select):
            em = Official_emojis["b" + str(sfi + 1)]
            s += f":black_small_square:｜{em}：{sf}\n"
        e.add_field(name=Texts[Guild_settings[g.id]["lang"]]
                    ["voting"][4], value=s, inline=False)
        e.set_author(
            name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
        e.set_footer(text=get_txt(ctx.guild.id, "voting")[5])
        m = await ctx.reply(embed=e)
        for sfi in range(len(select)):
            await m.add_reaction(Number_emojis[sfi + 1])

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
            n = datetime.datetime.utcnow()
            if mt < n:
                return
            me = m.embeds[0]
            select = []
            for f in me.fields[2].value.split("\n"):
                select.append(f.split("：", 1)[-1])
            s = ""
            cl = []
            m = await c.fetch_message(pl.message_id)
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
                em = Official_emojis["b" + str(sfi + 1)]
                s += f":{Squares[n]}:｜{em}：{sf}\n"
            me.set_field_at(
                index=2, name=get_txt(g.id, "voting")[4], value=s, inline=False)
            await m.edit(embed=me)

    @commands.Cog.listener(name="on_raw_reaction_add")
    async def on_raw_reaction_add(self, pl):
        global Guild_settings
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
                            await em.add_reaction(Official_emojis["check4"])
                    except NotFound:
                        pass
                return
            elif pl.emoji.name == "reply":
                dt = datetime.datetime.utcnow()
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
                text=f"Server: {sg.name} | ID: {mid} | {p}{uc-dc} ( +{uc} / -{dc} )", icon_url=sg.icon_url_as(static_format="png"))
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
                loop.create_task(message.remove_reaction(
                    Official_emojis["add"], user))
                e = discord.Embed(description=get_txt(
                    guild.id, "free_channel_ask"), color=Widget)
                msg = await channel.send(embed=e)
                try:
                    message = await self.bot.wait_for("message", check=lambda m2: m2.channel == channel and m2.author == user, timeout=30)
                    if channel.category is None:
                        cat = await guild.create_category_channel(get_txt(guild.id, "free_channel_title"), overwrites=channel.overwrites, position=channel.position)
                        await channel.edit(category=cat)
                    nt = await channel.category.create_text_channel(message.content, topic=get_txt(guild.id, "free_channel_topic").format(message.author.mention))
                    await nt.set_permissions(user, manage_channels=True, manage_messages=True)
                    e = discord.Embed(title=get_txt(guild.id, "free_channel_success"), description=get_txt(
                        guild.id, "free_channel_success_desc").format(nt.mention), color=Widget)
                    e.set_footer(text=get_txt(
                        guild.id, "message_delete").format(5))
                    msg2 = await channel.send(embed=e)
                    await asyncio.sleep(5)
                    loop.create_task(message.delete())
                    loop.create_task(msg.delete())
                    loop.create_task(msg2.delete())
                except asyncio.TimeoutError:
                    e = discord.Embed(description=get_txt(
                        guild.id, "timeout"), color=Error)
                    e.set_footer(text=get_txt(
                        guild.id, "message_delete").format(5))
                    await msg.edit(embed=e)
                    await msg.delete(delay=5)
            elif message.embeds[0].title == "募集":
                ft = m0.footer.text
                mt = m0.timestamp
                n = datetime.datetime.utcnow()
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
                        m0.set_field_at(
                            2, name=f"参加者(現在{cn+1}人)", value="\n".join(cm))
                        await message.edit(embed=m0)
                elif pl.emoji.name == "check6" and user.name + f"(ID:{user.id})" in cm:
                    cm.remove(user.name + f"(ID:{user.id})")
                    cn = len(cm)
                    if cm == []:
                        cm = ["現在参加者はいません"]
                        cn = 0
                    m0.set_field_at(
                        2, name=f"参加者(現在{cn}人)", value="\n".join(cm))
                    await message.edit(embed=m0)
                await message.remove_reaction(pl.emoji, user)
            elif message.id in Guild_settings[guild.id]["ticket_message"]:
                if pl.emoji.name == "lock":
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        user: discord.PermissionOverwrite(
                            read_messages=True, send_messages=False)
                    }
                    await channel.edit(overwrites=overwrites, name=channel.name[0:-5] + "クローズ")
                    await message.remove_reaction(Official_emojis["lock"], user)
            elif message.embeds[0].title == "チケット作成":
                await message.remove_reaction(pl.emoji, user)
                if pl.emoji.name == "add":
                    dt = datetime.datetime.utcnow()
                    if user.id in list(Guild_settings[guild.id]["ticket_time"].keys()):
                        ldt = datetime.datetime.strptime(
                            Guild_settings[guild.id]["ticket_time"][user.id], Time_format)
                        if ldt > dt:
                            return
                    dt += datetime.timedelta(hours=1)
                    Guild_settings[guild.id]["ticket_time"][user.id] = dt.strftime(
                        Time_format)
                    cat = self.bot.get_channel(
                        Guild_settings[guild.id]["ticket_category"])
                    if cat is None:
                        ow = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            guild.me: discord.PermissionOverwrite(
                                read_messages=True, send_messages=True)
                        }
                        cat = await guild.create_category_channel(name="チケット", overwrites=ow)
                        Guild_settings[guild.id]["ticket_category"] = cat.id
                    ow = cat.overwrites
                    ow[user] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True)
                    channel = len(Guild_settings[guild.id]["ticket_message"])
                    tc = await guild.create_text_channel(category=cat, name=f"チケット#{str(channel+1).zfill(4)}-アクティブ", overwrites=ow)
                    em = Official_emojis["lock"]
                    s = Guild_settings[guild.id]["ticket_subject"][message.id]
                    e = discord.Embed(
                        title=s[0], description=s[1], color=Widget)
                    e.set_footer(text="下の南京錠ボタンを押して終了")
                    message = await tc.send(user.mention, embed=e)
                    await message.add_reaction(Official_emojis["lock"])
                    Guild_settings[guild.id]["ticket_message"].append(
                        message.id)
            elif message.embeds[0].title == get_txt(guild.id, "voting")[0]:
                ft = message.embeds[0].footer.text
                mt = message.embeds[0].timestamp
                if not mt:
                    return
                n = datetime.datetime.utcnow()
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
                                    if filter(lambda r: r.emoji == nem, message.reactions):
                                        loop.create_task(
                                            message.remove_reaction(nem, user))
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
                            r = guild.get_role(
                                int([s for s in re.split("(: |：)", md) if s][2][3:-1]))
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
                            mdh.append(guild.get_role(
                                int(md.split("：", 1)[-1][3:-1])))
                        while True:
                            e = discord.Embed(
                                description="編集したい番号でリアクションして下さい。", color=Widget)
                            msg = await channel.send(embed=e)
                            for n in Number_emojis[1:len(mdh) + (2 if len(mdh) < 10 else 1)]:
                                loop.create_task(msg.add_reaction(n))
                            loop.create_task(msg.add_reaction(
                                Official_emojis["check6"]))

                            def check(r, ru):
                                if ru.bot:
                                    return
                                if r.count >= 2 and r.emoji in Number_emojis[1:len(mdh) + (2 if len(mdh) < 10 else 1)] + [Official_emojis["check6"]] and ru.id == user.id and r.message.id == msg.id:
                                    return True
                            r, _ = await self.bot.wait_for("reaction_add", check=check)
                            if r.emoji == Official_emojis["check6"]:
                                await message.remove_reaction(pl.emoji, self.bot.get_user(pl.user_id))
                                return await msg.delete()
                            en = Number_emojis.index(r.emoji) - 1
                            await r.message.remove_reaction(r, user)
                            e = discord.Embed(
                                description="ロールを送信して下さい。\n`!none` で削除します。", color=Widget)
                            try:
                                mdh[en]
                            except IndexError:
                                e = discord.Embed(
                                    description="ロールを送信して下さい。", color=Widget)
                            msg2 = await channel.send(embed=e)

                            def check2(message):
                                return message.author.id == user.id and message.channel.id == channel.id
                            m2 = await self.bot.wait_for("message", check=check2)
                            if m2.content != "!none":
                                ctx = await self.bot.get_context(m2)
                                try:
                                    r = await commands.RoleConverter().convert(ctx, m2.content)
                                except commands.errors.RoleNotFound:
                                    e = discord.Embed(
                                        description="不明なロールです。", color=Widget)
                                    e.set_footer(
                                        text=get_txt(guild.id, "message_delete").format(5))
                                    await msg2.edit(embed=e)
                                    await msg2.delete(delay=5)
                                    await msg.delete(delay=0)
                                    await m2.delete(delay=0)
                                    continue
                                if (r.position > user.top_role.position and not guild.owner_id == user.id) or r.position > guild.me.top_role.position:
                                    e = discord.Embed(title=get_txt(
                                        guild.id, "no_role_perm").format(r.name), color=Widget)
                                    e.set_footer(text=get_txt(
                                        guild.id, "message_delete").format(5))
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
                                em = Official_emojis["b" + str(sfi + 1)]
                                s += f"{em}：{r.mention}\n"
                                if Official_emojis["b" + str(sfi + 1)] not in [r.emoji for r in message.reactions]:
                                    await message.add_reaction(Official_emojis["b" + str(sfi + 1)])
                            for r in message.reactions:
                                try:
                                    n = Number_emojis.index(r.emoji)
                                    if n > len(mdh):
                                        try:
                                            await message.clear_reaction(r)
                                        except discord.errors.Forbidden:
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
        starttime = datetime.datetime.utcnow()
        ctime = ctx.message.created_at
        e = discord.Embed(title=get_txt(ctx.guild.id, "ping_title"),
                          description=get_txt(ctx.guild.id, "wait"), color=Bot_info)
        msg = await ctx.reply(embed=e)
        ping = starttime - ctime
        e = discord.Embed(title=get_txt(ctx.guild.id, "ping_title"),
                          description=get_txt(ctx.guild.id, "ping_desc").format(round(self.bot.latency * 1000), round(ping.microseconds / 1000)), color=Bot_info)
        await msg.edit(embed=e)

    @commands.command(aliases=["trans"])
    async def translate(self, ctx, *, txt):
        if Guild_settings[ctx.guild.id]["lang"] == "ja":
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
        e = discord.Embed(title=get_txt(ctx.guild.id, "translate_title").format(get_txt(ctx.guild.id, "lang_name")[lng],
                                                                                get_txt(ctx.guild.id, "lang_name")[t]), description="", color=Trans)
        e.add_field(name=Texts[Guild_settings[ctx.guild.id]
                               ["lang"]]["trans_before"], value=txt, inline=False)
        res = (await translator.translate(txt, lang_tgt=t))
        e.add_field(name=get_txt(ctx.guild.id, "trans_after"),
                    value=res, inline=False)
        e.set_footer(text="Powered by async_google_trans_new",
                     icon_url="https://i.imgur.com/zPOogXx.png")
        return await ctx.reply(embed=e)

    @commands.command(aliases=["recruit", "apply"])
    async def party(self, ctx, title, time: convert_timedelta, max: int):
        dt = datetime.datetime.utcnow()
        dt += time
        e = discord.Embed(title="募集", color=Widget, timestamp=dt)
        e.add_field(name="タイトル", value=title, inline=False)
        e.add_field(name="最大人数", value=f"{max}人", inline=False)
        e.add_field(name="参加者(現在0人)", value="現在参加者はいません", inline=False)
        e.set_author(
            name=f"{ctx.author}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
        e.set_footer(text=get_txt(ctx.guild.id, "voting")[5])
        m = await ctx.reply(embed=e)
        await m.add_reaction(Official_emojis["check5"])
        await m.add_reaction(Official_emojis["check6"])

    @commands.command(name="lang")
    @commands.has_guild_permissions(manage_guild=True)
    async def change_lang(self, ctx, lang_to):
        global Guild_settings
        if lang_to not in Texts.keys():
            e = discord.Embed(title=get_txt(ctx.guild.id, "change_lang")[0][0],
                              description=get_txt(ctx.guild.id, "change_lang")[0][1].format(lang_to), color=Error)
            return await ctx.reply(embed=e)
        Guild_settings[ctx.guild.id]["lang"] = lang_to
        e = discord.Embed(title=get_txt(ctx.guild.id, "change_lang")[1][0],
                          description=get_txt(ctx.guild.id, "change_lang")[1][1].format(lang_to), color=Success)
        return await ctx.reply(embed=e)

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def event_channel(self, ctx):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["event_message_channel"] == 0:
            rc = "登録"
        else:
            rc = "変更"
        Guild_settings[ctx.guild.id]["event_message_channel"] = ctx.channel.id
        e = discord.Embed(
            title=f"イベントメッセージチャンネルを{rc}しました。", description="メッセージを登録するには`sb#event_send`を使用してください", color=Success)
        return await ctx.reply(embed=e)

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def event_send(self, ctx, etype, *, message=""):
        global Guild_settings
        etype = etype.lower()
        if Guild_settings[ctx.guild.id]["event_message_channel"] == 0:
            e = discord.Embed(title="イベントメッセージチャンネルが設定されていません",
                              description="`sb#event_channel`で設定してください", color=Error)
            return await ctx.reply(embed=e)
        if etype not in list(Event_dict.keys()):
            e = discord.Embed(
                title=f"イベント{etype}が見付かりませんでした", description="`sb#help event_send`で確認してください", color=Error)
            return await ctx.reply(embed=e)
        Guild_settings[ctx.guild.id]["event_messages"][etype] = message
        if message == "":
            d = "メッセージが送られなくなりました。"
            Guild_settings[ctx.guild.id][etype] = False
        else:
            d = f"**メッセージ内容：**\n```{message}```\n**サンプル：**\n>>> " + message.replace("!name", "SevenBot").replace(
                "!count", str(len(ctx.guild.members))).replace("!mention", ctx.guild.me.mention)
        e = discord.Embed(
            title=f"{Event_dict[etype]}のメッセージを変更しました。", description=d, color=Success)
        return await ctx.reply(embed=e)

    @commands.command()
    @commands.has_guild_permissions(manage_roles=True)
    async def role(self, ctx, single: Optional[bool], *roles: discord.Role):
        if len(roles) > 10:
            e = discord.Embed(title="ロールが多すぎます。",
                              description="ロールは10個以下にして下さい。", color=Error)
            return await ctx.reply(embed=e)
        s = ""
        for r in roles:
            if (r.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id) or r.position > ctx.guild.me.top_role.position:
                e = discord.Embed(title=get_txt(
                    ctx.guild.id, "no_role_perm").format(r.name), color=Error)
                m = await ctx.reply(embed=e)
                return
        for sfi, sf in enumerate(roles):
            r = sf
            em = Official_emojis["b" + str(sfi + 1)]
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

    @commands.command(aliases=["get_pm"])
    async def get_permissions(self, ctx, user: Union[discord.Member, discord.Role] = None, channel: Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel] = None):
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
                ow.update({k: v for k, v in iter(
                    channel.overwrites_for(r2)) if v is not None})
        em = discord.Embed(title=get_txt(ctx.guild.id, "permission_title").format(n), color=Info)
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
                    e = Official_emojis["check3"]
                    if pk == "administrator":
                        e = Official_emojis["check"]
                elif pv:
                    e = Official_emojis["check"]
                else:
                    e = Official_emojis["check4"]
                r += str(e)
                if channel:
                    if "|" in pk:
                        pw = ow[pk.split("|")[1]]
                    else:
                        pw = ow[pk]
                    if pw is None:
                        e = Official_emojis["check7"]
                    elif pw is False:
                        e = Official_emojis["check4"]
                    elif pw:
                        e = Official_emojis["check"]
                    r += f"({e})"
                r += f"`{pv3}`\n"
            em.add_field(name=tpt["name"], value=r)
        em.set_footer(text=Texts[Guild_settings[ctx.guild.id]
                                 ["lang"]]["permission_value"] + str(hash(u)))
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
        e = discord.Embed(title=get_txt(ctx.guild.id, "get_rm").format(
            role.name), description=res, color=Info)
        if not ri == -1:
            e.set_footer(text=get_txt(ctx.guild.id, "get_rm_more").format(
                str(len(role.members) - ri)))
        return await ctx.reply(embed=e)

    @commands.command(aliases=["get_rc"])
    async def get_role_count(self, ctx, show_bot: bool = False):
        u = ctx.guild.roles
        u.reverse()
        r = ""
        for ui in u:
            flag = False
            if ui.managed:
                flag = True
            mc = ui.members
            mci = len(mc)
            if flag:
                if show_bot:
                    r += f"({ui.mention} : {mci}{Texts[Guild_settings[ctx.guild.id]['lang']]['rc_people']})\n"
            else:
                per = round(len(ui.members) / float(len(ctx.guild.members)) * 100)
                r += f"{ui.mention} : {mci}{Texts[Guild_settings[ctx.guild.id]['lang']]['rc_people']} - {per}%\n"
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "rc_title"), description=r, color=Info)
        return await ctx.reply(embed=e)

    @commands.command(aliases=["cu"])
    @commands.cooldown(10, 10)
    async def check_url(self, ctx, *, url):
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "http://" + url
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://safeweb.norton.com/report/show?url={url}') as r:
                if r.status == 200:
                    get_url_info = await r.text()
        b4o = bs4.BeautifulSoup(get_url_info, 'lxml')
        if b4o.select(".icoUntested") != []:
            ind = 0
        elif b4o.select('.icoSafe') != []:
            ind = 1
        elif b4o.select(".icoCaution") != []:
            ind = 2
        elif b4o.select(".icoWarning") != []:
            ind = 3
        e = discord.Embed(title=get_txt(ctx.guild.id, "norton_res").format(get_txt(ctx.guild.id, "norton_desc")[ind][0]),
                          description=get_txt(ctx.guild.id, "norton_desc")[ind][1].format(url), color=0xffcd00)
        e.set_footer(text="Powered by Norton Safeweb",
                     icon_url="https://i.imgur.com/QUkiSHQ.png")
        return await ctx.reply(embed=e)

    @commands.command(aliases=["user", "ui", "userinfo"])
    async def lookup(self, ctx, u: Union[discord.User, int] = None):
        used_api = False
        if u is None:
            u = ctx.author
        elif isinstance(u, int):
            try:
                u = await self.bot.fetch_user(u)
                used_api = True
            except NotFound:
                e = discord.Embed(title=get_txt(
                    ctx.guild.id, "lookup")[11], color=Error)
                return await ctx.reply(embed=e)
        else:
            if ctx.guild.get_member(u.id) is not None:
                u = ctx.guild.get_member(u.id)
        e = discord.Embed(title=get_txt(ctx.guild.id, "lookup")[0].format(
            u.display_name), color=Info)
        if used_api:
            e.title += get_txt(ctx.guild.id, "lookup")[12]
        e.set_thumbnail(url=u.avatar_url_as(static_format="png"))
        e.add_field(name=Texts[Guild_settings[ctx.guild.id]
                               ["lang"]]["lookup"][1], value=u.display_name)
        e.add_field(name=Texts[Guild_settings[ctx.guild.id]
                               ["lang"]]["lookup"][2], value=str(u))
        e.add_field(name=get_txt(ctx.guild.id, "lookup")[
                    3], value=u.created_at.strftime(Time_format))
        e.add_field(name=get_txt(ctx.guild.id, "lookup")[4], value=u.joined_at.strftime(
            Time_format) if isinstance(u, discord.Member) else get_txt(ctx.guild.id, "lookup")[9])
        e.add_field(
            name="Bot", value=get_txt(ctx.guild.id, "lookup")[10][0 if u.bot else 1])
        if isinstance(u, discord.User):
            st = str(Official_emojis["unknown"]) + \
                get_txt(ctx.guild.id, "lookup")[5][0]
        elif u.status == discord.Status.online:
            st = str(Official_emojis["online"]) + \
                get_txt(ctx.guild.id, "lookup")[5][1]
        elif u.status == discord.Status.idle:
            st = str(Official_emojis["idle"]) + \
                get_txt(ctx.guild.id, "lookup")[5][2]
        elif u.status == discord.Status.dnd:
            st = str(Official_emojis["dnd"]) + \
                get_txt(ctx.guild.id, "lookup")[5][3]
        elif u.status == discord.Status.offline:
            st = str(Official_emojis["offline"]) + \
                get_txt(ctx.guild.id, "lookup")[5][4]
        else:
            st = str(Official_emojis["unknown"]) + str(u.status)
        e.add_field(name=Texts[Guild_settings[ctx.guild.id]
                               ["lang"]]["lookup"][5][5], value=st)
        rs = ""
        if isinstance(u, discord.Member):
            for r in reversed(u.roles):
                rs += r.mention + ","
            e.add_field(
                name=get_txt(ctx.guild.id, "lookup")[6], value=rs.rstrip(","))
            e.add_field(name=Texts[Guild_settings[ctx.guild.id]
                                   ["lang"]]["lookup"][7], value=get_txt(ctx.guild.id, "lookup")[8].format(Guild_settings[ctx.guild.id]["warns"].get(u.id, 0)))
        return await ctx.reply(embed=e)

    @commands.command(aliases=["guildinfo", "si", "gi"])
    async def serverinfo(self, ctx, guild: int = None):
        guild = self.bot.get_guild(guild or ctx.guild.id)
        if guild is None:
            e = discord.Embed(title=get_txt(ctx.guild.id, "serverinfo")[
                              "unknown"], color=Error)
            return await ctx.reply(embed=e)
        if (not guild.get_member(ctx.author.id)) and not self.bot.is_owner(ctx.author):
            e = discord.Embed(title=get_txt(ctx.guild.id, "serverinfo")[
                              "noperm"], color=Error)
            return await ctx.reply(embed=e)
        e = discord.Embed(title=guild.name + " - "
                          + f"`{guild.id}`", color=Info, timestamp=guild.created_at)
        e.set_author(name=f"{guild.owner.display_name}({guild.owner}, ID:{guild.owner.id})",
                     icon_url=guild.owner.avatar_url_as(static_format="png"))
        e.set_thumbnail(url=guild.icon_url_as(static_format="png"))
        chs = str(Official_emojis["cc"]) + " " + get_txt(ctx.guild.id, "serverinfo")[
            "channels"][1] + ":" + str(len(guild.categories)) + "\n"
        chs += str(Official_emojis["tc"]) + " " + get_txt(ctx.guild.id, "serverinfo")[
            "channels"][2] + ":" + str(len(guild.text_channels)) + "\n"
        chs += str(Official_emojis["vc"]) + " " + get_txt(ctx.guild.id, "serverinfo")[
            "channels"][3] + ":" + str(len(guild.voice_channels)) + "\n"
        e.add_field(name=get_txt(ctx.guild.id, "serverinfo")
                    ["channels"][0], value=chs)
        e.add_field(name=get_txt(ctx.guild.id, "serverinfo")["members"][0], value=get_txt(ctx.guild.id, "serverinfo")["members"][1].format(len(
            guild.members), len([m for m in guild.members if not m.bot]), len([m for m in guild.members if m.bot]), Official_emojis["user"], Official_emojis["bot"]))
        e.add_field(name=get_txt(ctx.guild.id, "serverinfo")["emoji"][0], value=get_txt(ctx.guild.id, "serverinfo")["emoji"][1].format(
            len([e for e in guild.emojis if not e.animated]),
            len([e for e in guild.emojis if e.animated]),
            guild.emoji_limit
        ))
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
                title="既に有効です。", description="SevenNetチャンネルではないチャンネルで使用してください。", color=Error)
            return await ctx.reply(embed=e)
        else:
            e2 = discord.Embed(
                title="SevenNetに仲間が入ってきた!", description=f"{ctx.guild.name}がSevenNetに参加しました！", timestamp=ctx.message.created_at, color=Chat)
            e2.set_thumbnail(
                url=ctx.guild.icon_url_as(static_format='png'))
            e2.set_footer(text=f"現在のチャンネル数：{len(Sevennet_channels)+1}")
            for c in Sevennet_channels:
                cn = self.bot.get_channel(c)
                if cn is None:
                    Sevennet_channels.remove(c)
                else:
                    await cn.send(embed=e2)
            e = discord.Embed(title=f"`#{ctx.channel.name}`はSevenNetチャンネルになりました。",
                              description="ルールを確認してください。", color=Success)
            await ctx.reply(embed=e)
            e3 = discord.Embed(title="SevenNetチャンネルのルールについて", color=Info)
            e3.add_field(name="宣伝禁止", value="宣伝はしないで下さい。", inline=False)
            e3.add_field(name="暴言・エロ画像など、不快に感じる行為禁止",
                         value="不快に感じる行為はしないで下さい。", inline=False)
            f1 = Official_emojis["up"]
            f2 = Official_emojis["down"]
            f3 = Official_emojis["reply"]
            f4 = Official_emojis["report"]
            e3.add_field(
                name="ボタンについて", value=f"{f1}：高評価\n{f2}：低評価\n{f3}：返信（押して消えた後10秒以内に送信）\n{f4}：報告/削除", inline=False)
            r = await ctx.send(embed=e3)
            await r.pin()
            Sevennet_channels.append(ctx.channel.id)

    @sevennet.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_sevennet(self, ctx):
        global Sevennet_channels
        if ctx.channel.id in Sevennet_channels:
            Sevennet_channels.remove(ctx.channel.id)
            e = discord.Embed(title=f"`#{ctx.channel.name}`はSevenNetチャンネルではなくなりました。",
                              description="", color=Success)
            await ctx.reply(embed=e)
            e2 = discord.Embed(
                title="SevenNetの仲間が抜けちゃった…", description=f"{ctx.guild.name}がSevenNetから退出しました。", timestamp=ctx.message.created_at, color=Chat)
            e2.set_thumbnail(url=ctx.guild.icon_url)
            e2.set_footer(text=f"現在のチャンネル数：{len(Sevennet_channels)}")
            for c in Sevennet_channels:
                cn = self.bot.get_channel(c)
                if cn is None:
                    Sevennet_channels.remove(c)
                else:
                    await cn.send(embed=e2)
        else:
            e = discord.Embed(title="ここはSevenNetチャンネルではありません。",
                              description="SevenNetチャンネルで使用してください。", color=Error)
            return await ctx.reply(embed=e)

    @commands.group()
    @commands.has_permissions(manage_guild=True)
    async def server_stat(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @server_stat.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_guild=True)
    async def ss_activate(self, ctx, *list):
        global Guild_settings
        cat = None
        for l in list:
            if l not in Stat_dict.keys():
                e = discord.Embed(
                    title=f"統計{l}が見付かりませんでした。", description="`sb#help server_stat`で確認してください。", color=Error)
                return await ctx.reply(embed=e)
        if Guild_settings[ctx.guild.id]["do_stat_channels"]:
            for sc in Guild_settings[ctx.guild.id]["stat_channels"].values():
                c = self.bot.get_channel(sc)
                if isinstance(c, CategoryChannel):
                    cat = c
                    continue
                if c is not None:
                    await c.delete()
        else:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(
                    connect=False)
            }
            cat = await ctx.guild.create_category("統計", overwrites=overwrites)
        for l in list:
            n = await ctx.guild.create_voice_channel(f"{Stat_dict[l]}： --", category=cat)
            Guild_settings[ctx.guild.id]["stat_channels"][l] = n.id
        Guild_settings[ctx.guild.id]["stat_channels"]["category"] = cat.id
        Guild_settings[ctx.guild.id]["do_stat_channels"] = True
        e = discord.Embed(title="統計チャンネルが有効になりました。",
                          description="無効化するには`sb#server_stat deactivate`を実行してください。", color=Success)
        return await ctx.reply(embed=e)

    @server_stat.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_guild=True)
    async def ss_deactivate(self, ctx):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["do_stat_channels"]:
            for sc in Guild_settings[ctx.guild.id]["stat_channels"].values():
                c = self.bot.get_channel(sc)
                if c is not None:
                    await c.delete()
            Guild_settings[ctx.guild.id]["stat_channels"] = {}
            Guild_settings[ctx.guild.id]["do_stat_channels"] = False
            e = discord.Embed(
                title="統計チャンネルが無効になりました。", description="もう一度有効にするには`sb#server_stat activate`を使用してください。", color=Success)
            return await ctx.reply(embed=e)

    @commands.command(name="ticket")
    @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
    async def ticket(self, ctx, subject, description):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["ticket_category"] == 0:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True)
            }
            cat = await ctx.guild.create_category("チケット", overwrites=overwrites)
            Guild_settings[ctx.guild.id]["ticket_category"] = cat.id
        else:
            cat = self.bot.get_channel(
                Guild_settings[ctx.guild.id]["ticket_category"])
        Official_emojis["add"]
        e = discord.Embed(
            title="チケット作成", description=subject, color=Widget)
        e.set_footer(text="下のボタンを押してチケットを作成（1時間に1回）")
        m = await ctx.send(embed=e)
        await m.add_reaction(Official_emojis["add"])
        Guild_settings[ctx.guild.id]["ticket_subject"][m.id] = [
            subject, description]

    @commands.command(name="free_channel")
    @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
    async def free_channel(self, ctx):
        global Guild_settings
        if ctx.channel.category is None:
            cat = await ctx.guild.create_category_channel(get_txt(ctx.guild.id, "free_channel_title"), overwrites=ctx.channel.overwrites, position=ctx.channel.position)
            await ctx.channel.edit(category=cat)
        Official_emojis["add"]
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "free_channel_title"), description=get_txt(ctx.guild.id, "free_channel_desc").format(Official_emojis["add"]), color=Widget)
        m = await ctx.send(embed=e)
        await m.add_reaction(Official_emojis["add"])
#
#
#
#
#
#

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def bump(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @bump.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def bump_activate(self, ctx):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["do_bump_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "activate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_bump_alert"] = True
            e = discord.Embed(title=get_txt(ctx.guild.id, "activate").format(
                "Bump通知"), color=Success)
            return await ctx.reply(embed=e)

    @bump.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def bump_deactivate(self, ctx):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["do_bump_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "deactivate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_bump_alert"] = False
            e = discord.Embed(title=get_txt(ctx.guild.id, "deactivate").format(
                "Bump通知"), color=Success)
            return await ctx.reply(embed=e)

    @bump.command(name="role")
    @commands.has_permissions(manage_messages=True)
    async def bump_role(self, ctx, role: Optional[discord.Role] = None):
        global Guild_settings
        if role:
            Guild_settings[ctx.guild.id]["bump_role"] = role.id
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "bump_role_set"), color=Success)
        else:
            Guild_settings[ctx.guild.id]["bump_role"] = None
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "bump_role_set_none"), color=Success)
        return await ctx.reply(embed=e)

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def dissoku(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @dissoku.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def dissoku_activate(self, ctx):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["do_dissoku_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "activate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_dissoku_alert"] = True
            e = discord.Embed(title=get_txt(ctx.guild.id, "activate").format(
                "ディス速通知"), color=Success)
            return await ctx.reply(embed=e)

    @dissoku.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def dissoku_deactivate(self, ctx):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["do_dissoku_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "deactivate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_dissoku_alert"] = False
            e = discord.Embed(title=get_txt(ctx.guild.id, "deactivate").format(
                "ディス速通知"), color=Success)
            return await ctx.reply(embed=e)

    @dissoku.command(name="role")
    @commands.has_permissions(manage_messages=True)
    async def dissoku_role(self, ctx, role: Optional[discord.Role] = None):
        global Guild_settings
        if role:
            Guild_settings[ctx.guild.id]["dissoku_role"] = role.id
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "dissoku_role_set"), color=Success)
        else:
            Guild_settings[ctx.guild.id]["dissoku_role"] = None
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "dissoku_role_set_none"), color=Success)
        return await ctx.reply(embed=e)

    @commands.group()
    @commands.has_guild_permissions(manage_messages=True)
    async def expand_message(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @expand_message.command(name="activate", aliases=Activate_aliases)
    @commands.has_guild_permissions(manage_messages=True)
    async def expand_activate(self, ctx):
        global Guild_settings
        gi = ctx.guild.id
        if Guild_settings[ctx.guild.id]["expand_message"]:
            e = discord.Embed(title=get_txt(gi, "activate_fail"), description=Texts[Guild_settings[gi]
                                                                                    ["lang"]]["activate_desc"].format("sb#expand_message deactivate"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["expand_message"] = True
            e = discord.Embed(title=get_txt(gi, "activate").format(
                "メッセージ展開"), description=get_txt(gi, "activate_desc").format("sb#expand_message deactivate"), color=Success)
            return await ctx.reply(embed=e)

    @expand_message.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_guild_permissions(manage_messages=True)
    async def expand_deactivate(self, ctx):
        global Guild_settings
        gi = ctx.guild.id
        if not Guild_settings[ctx.guild.id]["expand_message"]:
            e = discord.Embed(title=get_txt(gi, "deactivate_fail"), description=get_txt(ctx.guild.id, "deactivate_desc").format("sb#expand_message deactivate"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["expand_message"] = False
            e = discord.Embed(title=get_txt(gi, "deactivate").format(
                "メッセージ展開"), description=get_txt(gi, "deactivate_desc").format("sb#expand_message deactivate"), color=Success)
            return await ctx.reply(embed=e)

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
            for l in m.content.split("\n"):
                if l.startswith("#") or l.startswith("//"):
                    continue
                for i, c in enumerate(l):
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
        if not(b1 == 0 and lb1 == 0 and b2 == 0 and lb2 == 0 and b3 == 0 and lb3 == 0):
            if b1 - lb1 != 0:
                err += Texts[Guild_settings[ctx.guild.id]["lang"]
                             ]["parse"][2].format(('(' if b1 - lb1 < 0 else ')'), abs(b1 - lb1))
            if lb1 != 0:
                err += Texts[Guild_settings[ctx.guild.id]
                             ["lang"]]["parse"][3].format(")", lb1)
            if b2 - lb2 != 0:
                err += Texts[Guild_settings[ctx.guild.id]["lang"]
                             ]["parse"][2].format(('{' if b2 - lb2 < 0 else '}'), abs(b2 - lb2))
            if lb2 != 0:
                err += Texts[Guild_settings[ctx.guild.id]
                             ["lang"]]["parse"][3].format("}", lb2)
            if b3 - lb3 != 0:
                err += Texts[Guild_settings[ctx.guild.id]["lang"]
                             ]["parse"][2].format(('[' if b3 - lb3 < 0 else ']'), abs(b3 - lb3))
            if lb3 != 0:
                err += Texts[Guild_settings[ctx.guild.id]
                             ["lang"]]["parse"][3].format("]", lb3)
        if ignore:
            err += Texts[Guild_settings[ctx.guild.id]
                         ["lang"]]["parse"][4].format(ignore)
        if err == "":
            e = discord.Embed(title=get_txt(ctx.guild.id, "parse")[0][0],
                              description=get_txt(ctx.guild.id, "parse")[0][1], color=Success)
        else:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "parse")[1], description=err, color=Error)
        return await ctx.reply(embed=e)

    @commands.group(aliases=["rl"])
    @commands.has_guild_permissions(manage_roles=True)
    async def role_link(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @role_link.command(name="add", aliases=["set"])
    async def role_link_add(self, ctx, role: discord.Role, target: int, target_role: int):
        global Guild_settings
        target = bot.get_guild(target)
        if not target:
            e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                              "unknown_server"], color=Error)
            return await ctx.reply(embed=e)
        if target.get_member(ctx.author.id):
            if not target.get_member(ctx.author.id).guild_permissions.manage_roles:
                e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                                  "no_role_perm"], color=Error)
                return await ctx.reply(embed=e)
        else:
            e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                              "not_in_server"], color=Error)
            return await ctx.reply(embed=e)
        target_role = target.get_role(target_role)
        if not target_role:
            e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                              "unknown_role"], color=Error)
            return await ctx.reply(embed=e)
        elif target.get_member(ctx.author.id).top_role.position <= target_role.position and not target.owner_id == ctx.author.id:
            e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                              "no_role_perm"], color=Error)
            return await ctx.reply(embed=e)
        if role.id not in Guild_settings[ctx.guild.id]["role_link"].keys():
            Guild_settings[ctx.guild.id]["role_link"][role.id] = []
        Guild_settings[ctx.guild.id]["role_link"][role.id].append(
            [target.id, target_role.id])
        if target_role.id not in Guild_settings[target.id]["role_link"].keys():
            Guild_settings[target.id]["role_link"][target_role.id] = []
        Guild_settings[target.id]["role_link"][target_role.id].append(
            [ctx.guild.id, role.id])
        e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")["add"].format(role.name), description=get_txt(
            ctx.guild.id, "role_link")["add_desc"].format(ctx.guild.name, role.mention, target.name, "@" + target_role.name), color=Success)
        return await ctx.reply(embed=e)

    @role_link.command(name="remove", aliases=["del", "delete", "rem"])
    async def role_link_remove(self, ctx, role: discord.Role, target_role: int):
        global Guild_settings
        res = []
        g = 0
        for rl in Guild_settings[ctx.guild.id]["role_link"][role.id]:
            if rl[1] != target_role:
                res.append(rl)
            else:
                g = rl[0]
        if g == 0:
            e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                              "remove_fail"], color=Error)
            return
        Guild_settings[ctx.guild.id]["role_link"][role.id] = res.copy()
        res = []
        for rl in Guild_settings[g]["role_link"][target_role]:
            if rl[1] != role.id:
                res.append(rl)
            else:
                g = rl[0]
        Guild_settings[g]["role_link"][role.id] = res.copy()
        e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                          "remove"].format(role.name), color=Success)
        return await ctx.reply(embed=e)

    @role_link.command(name="update")
    async def role_link_update(self, ctx):
        for m in ctx.guild.members:
            for r in m.roles:
                if r.id in Guild_settings[m.guild.id]["role_link"].keys():
                    for rl in Guild_settings[m.guild.id]["role_link"][r.id]:
                        try:
                            await self.bot.get_guild(rl[0]).get_member(m.id).add_roles(self.bot.get_guild(rl[0]).get_role(rl[1]), reason=get_txt(m.guild.id, "role_link")["reason"].format(self.bot.get_guild(rl[0]).name, self.bot.get_guild(rl[0]).get_role(rl[1]).name))
                        except (NotFound, AttributeError):
                            pass
        e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                          "update"], color=Success)
        return await ctx.reply(embed=e)

    @role_link.command(name="list")
    async def role_link_list(self, ctx):
        g = ctx.guild.id
        global Guild_settings
        gs = Guild_settings[g]
        if gs["role_link"] == {}:
            e = discord.Embed(
                title="登録されていません。", description="`sb#role_link add`で登録してください。", color=Error)
            return await ctx.reply(embed=e)
        else:
            table = Texttable()
            table.set_deco(Texttable.HEADER)
            table.set_cols_dtype(['t',
                                  't', "t"])
            table.set_cols_align(["c", "l", "c"])
            res = [["ロール", "サーバー", "ロール"]]
            for k, v in gs["role_link"].items():
                for v2 in v:
                    if ctx.guild.get_role(k) is None:
                        continue
                    elif self.bot.get_guild(v2[0]) is None:
                        continue
                    elif self.bot.get_guild(v2[0]).get_role(v2[1]) is None:
                        continue
                    res.append(["@" + remove_emoji(ctx.guild.get_role(k).name), remove_emoji(self.bot.get_guild(
                        v2[0]).name), "@" + remove_emoji(self.bot.get_guild(v2[0]).get_role(v2[1]).name)])
            table.add_rows(res)
            e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                              "list"], description=f"```asciidoc\n{table.draw()}```", color=Info)
            return await ctx.reply(embed=e)
#

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
                tmp_txt = f"**`{pm}`** " + (get_txt(ctx.guild.id, "help_datail").get(
                    pm, "_" + get_txt(ctx.guild.id, "help_datail_none") + "_")).split("\n")[0] + "\n"
                if len(perf_res + tmp_txt) < 1024:
                    perf_res += tmp_txt
                else:
                    break
        else:
            perf_res = get_txt(ctx.guild.id, "getid_search")[3]
        if part_match:
            for pm in part_match:
                tmp_txt = f"**`{pm}`** " + (get_txt(ctx.guild.id, "help_datail").get(
                    pm, "_" + get_txt(ctx.guild.id, "help_datail_none") + "_")).split("\n")[0] + "\n"
                if len(part_res + tmp_txt) < 1024:
                    part_res += tmp_txt
                else:
                    break
        else:
            part_res = get_txt(ctx.guild.id, "getid_search")[3]
        e = discord.Embed(title=get_txt(
            ctx.guild.id, "command_search"), color=Bot_info)
        e.add_field(name=get_txt(ctx.guild.id, "getid_search")
                    [1], value=perf_res, inline=False)
        e.add_field(name=get_txt(ctx.guild.id, "getid_search")
                    [2], value=part_res, inline=False)
        return await ctx.reply(embed=e)

    @commands.Cog.listener("on_guild_voice_update")
    async def on_voice_state_update(member, before, after):
        if not [m for m in after.channel.members if not m.bot]:
            await after.guild.voice_client.disconnect()

    @commands.command(hidden=True, name="exec_cog")
    @commands.is_owner()
    async def _exec(self, ctx, *, script):
        script = script.replace("```py", "").replace("```", "")
        exec(
            'async def __ex(self,_bot,_ctx,ctx): '
            + ''.join(f'\n {l}' for l in script.split('\n'))
        )
        ret = await locals()['__ex'](self, self.bot, ctx, ctx)
        try:
            await ctx.reply(ret)
        except BaseException:
            pass
        await ctx.message.add_reaction(Official_emojis["check8"])

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_webhooks=True)
    async def follow(self, ctx):
        await self.bot.send_subcommands(ctx)

    @follow.command("announce")
    async def follow_announce(self, ctx):
        await self.bot.get_channel(738879378196267009).follow(destination=ctx.channel)
        await ctx.message.add_reaction(Official_emojis["check8"])

    @follow.command("updates")
    async def follow_updates(self, ctx):
        await self.bot.get_channel(817751838719868950).follow(destination=ctx.channel)
        await ctx.message.add_reaction(Official_emojis["check8"])

    @commands.command(aliases=["vote_rank"])
    async def vote_ranking(self, ctx):
        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(['t', 't', 't'])
        table.set_cols_align(["r", "l", "r"])
        res = [get_txt(ctx.guild.id, "vote_rank")]
        tmp_rank = collections.Counter([v["id"] for v in await self.bot.DBL_client.get_bot_votes()])
        rank = collections.defaultdict(lambda: 0)
        rank.update(dict(map(lambda k: (int(k[0]), k[1]), sorted(
            tmp_rank.items(), key=lambda a: a[1], reverse=True))))
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
                a = [("-" if break_flag or rank[ctx.author.id] == 0 else str(i)
                      + "."), remove_emoji(str(ctx.author)), rank[ctx.author.id]]
                res.append([" ", " ", " "])
                res.append(a)
            except KeyError:
                pass
        table.add_rows(res)
        e = discord.Embed(title=get_txt(ctx.guild.id, "vote_rank_title"),
                          description=f"```asciidoc\n{table.draw()}```", color=Info)
        return await ctx.reply(embed=e)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def upload_commands(self, ctx):
        li = []
        start = time.time()

        async def add_l(c):
            if Texts["ja"]["help_datail"].get(str(c)):
                await self.bot.db.commands.delete_many({"name": str(c)})
                ca = [(ck, cv) for ck, cv in Categories.items()
                      if str((c.parents or [c])[-1]) in cv]
                if not ca:
                    return
                ca = ca[0]
                desc_txt = get_txt(ctx.guild.id, "help_datail").get(str(
                    c), get_txt(ctx.guild.id, "help_datail_none")).lstrip("\n ")
                if (not isinstance(c, commands.Group)) or (get_txt(ctx.guild.id, "help_datail").get(str(c)) and len(inspect.signature(c.callback).parameters) > 2):
                    if desc_txt != get_txt(ctx.guild.id, "help_datail_none"):
                        name_ary = []
                        for l in desc_txt.split("\n"):
                            if ": " not in l:
                                continue
                            name_ary.append(l.split(": ", 2))
                        syntax = []
                        for pi, (_, pv) in enumerate(inspect.signature(c.callback).parameters.items(), -2):
                            if pi < 0:
                                continue
                            if pv.default == inspect.Signature.empty:
                                syntax.append({"name": name_ary[pi][0],
                                               "optional": False, "datail": name_ary[pi][1]})
                            else:
                                syntax.append({"name": name_ary[pi][0],
                                               "optional": True, "datail": name_ary[pi][1]})
                else:
                    syntax = None
                li.append({
                    "name": str(c),
                    "desc": Texts["ja"]["help_datail"].get(str(c)),
                    "parents": c.full_parent_name, "category": ca[0],
                    "index": ca[1].index(str((c.parents or [c])[-1])),
                    "aliases": c.aliases, "syntax": syntax
                })
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
            if gid not in Guild_settings.keys():
                fixed.append("all")
                res[gid] = Default_settings.copy()
            else:
                res[gid] = Guild_settings[gid]
                for ds, dsv in Default_settings.items():
                    if ds not in Guild_settings[gid]:
                        res[gid][ds] = dsv
                        fixed.append(ds)
        try:
            self.bot.guild_settings.clear()
            self.bot.guild_settings.update(res)
        except Exception as e:
            raise e
        print(id(Guild_settings))
        try:
            if fixed == {}:
                await ctx.channel.send("キーは修復されませんでした。")
            else:
                await ctx.channel.send(f"キー`{collections.Counter(fixed)}`を修復しました。")
        except BaseException:
            pass


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(MainCog(_bot))

    @bot.before_invoke
    async def count_commands(ctx):
        if str(ctx.command) not in flatten(Categories.values()):
            return
        if str(ctx.command).split(" ")[0] not in Command_counter.keys():
            Command_counter[str(ctx.command).split(" ")[0]] = 0
        Command_counter[str(ctx.command).split(" ")[0]] += 1
        async with aiohttp.ClientSession() as s:
            async with s.post("https://discord.com/api/webhooks/835270097374674954/xQQVcW2IJT4Rhwm5q3u2CrvWJ3miCdY6TaXGTdrHT9AeE5aEWbbu5-JeHJhv35YqMPwO", json={"content": ctx.message.content, "allowed_mentions": {"parse": []}}):
                pass
        return

    @bot.event
    async def on_error(_, *args, **__):
        try:
            ex = sys.exc_info()[1]
            print(traceback.format_exc())
            if not bot.is_ready():
                return
            if isinstance(ex, (AttributeError, aiohttp.client_exceptions.ClientOSError)):
                return
            if len(args) == 0:
                c = bot.get_channel(763877469928554517)
                e = discord.Embed(title=get_txt(c.guild.id, "error"),
                                  description="```" + traceback.format_exc() + "```", color=Error)
            else:
                e = None
                if isinstance(args[0], Context):
                    c = args[0].message.channel
                else:
                    c = bot.get_channel(763877469928554517)
                    e = discord.Embed(title=get_txt(c.guild.id, "error"),
                                      description="```" + traceback.format_exc() + "```", color=Error)
                    if "Forbidden" in e.description:
                        return
                if e is None:
                    e = discord.Embed(title=get_txt(c.guild.id, "error"), description="```" + "\n".join(
                        traceback.format_exception_only(type(ex), ex)) + "```", color=Error)
            try:
                msg = await c.send(embed=e)
                await msg.add_reaction(Official_emojis["down"])
                await bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and r.emoji.name == "down" and not u.bot)
                e = discord.Embed(title=get_txt(c.guild.id, "error"),
                                  description="```" + traceback.format_exc() + "```", color=Error)
                await msg.edit(embed=e)
            except Forbidden:
                pass
        except BaseException:
            pass
