import asyncio
import collections
import colorsys
import datetime
import hashlib
import io
import math
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import aiohttp
from async_timeout import timeout
import discord
from async_google_trans_new import AsyncTranslator
from discord.ext import commands
from discord.errors import Forbidden
from PIL import Image, ImageFont, ImageDraw, ImageFilter
from sembed import SEmbed, SField

import _pathmagic  # type: ignore # noqa: F401
from common_resources.consts import Official_discord_id, Gaming, Info, Error, Success
from common_resources.tools import chrsize_len

Activate_aliases = ["on", "active", "true"]
Deactivate_aliases = ["off", "disable", "false"]


def flatten(l):
    for el in l:
        if isinstance(el, collections.abc.Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el


Bot_info = 0x00ccff


Bignum_join = {}
Wolf_join = {}
i = 0
g = []

TRANSLATOR = AsyncTranslator()


def to_lts(s):
    s = math.floor(s)
    res = str((s // 60) % 60).zfill(2) + ":" + str(s % 60).zfill(2)
    if s > 3600:
        res = str(s // 3600).zfill(2) + ":" + res

    return res


Time_format = '%Y-%m-%d %H:%M:%S'

Channel_ids = {
    "log": 756254787191963768,
    "announce": 756254915441197206,
    "emoji_print": 756254956817743903,
    "global_report": 756255003341225996,
    "boot_log": 747764100922343554
}

DBL_id = 264445053596991498
#


def death_generator(message):
    r = list(map(lambda m: m.replace("\r", "").replace(
        "\n", ""), message.split("\n")))
    ml = 0
    for ir in r:
        if chrsize_len(ir) > ml:
            ml = chrsize_len(ir)
    header = "＿"
    if ml % 2 == 0:
        header += "人" * (ml // 2)
    else:
        header += "人" * math.ceil(ml // 2 / 2)
        header += " "
        header += "人" * math.ceil(ml // 2 / 2)
    header += "＿"
    mid = ""
    lr_int = chrsize_len(header) - 4
    for ir in r:
        mid += "＞"
        sc = lr_int - chrsize_len(ir)
        if sc % 2 == 0:
            mid += " " * (sc // 2)
            mid += ir
            mid += " " * (sc // 2)
        else:
            mid += " " * (sc // 2)
            mid += ir
            mid += " " * (sc // 2)
            mid += " "
        mid += "＜" + "\n"
    footer = "￣"
    for fi in range(lr_int):
        footer += "^" if fi % 2 == 0 else "Y"
    return header + "\n" + mid + footer + "￣"


def split_n(text, n):
    return re.split(f"(.{{{n}}})", text)[1::2]


class NotADatetimeFormat(commands.BadArgument):
    def __init__(self, argument):
        self.argument = argument
        super().__init__('"{}" is not a datetime format.'.format(argument))


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


def rgb_tuple(i):
    return (i // 65536, i // 256 % 256, i % 256)


Number_emojis = []
Bump_id = 302050872383242240
Dissoku_id = 761562078095867916
Trans = 0x1a73e8

Mention_re = re.compile(r"<@\!?(\d+?)>")

LAINAN_QUEUE = []
lainan_doing = False

BRACKET_BASE = "()[]{}（）「」［］【】《》｢｣『』〈〉｛｝〔〕〘〙〚〛"
BRACKET_DICT = {BRACKET_BASE[i * 2]: BRACKET_BASE[i * 2 + 1]
                for i in range(len(BRACKET_BASE) // 2)}
BRACKET_TRANS = str.maketrans(BRACKET_DICT)


class FunCog(commands.Cog):
    def __init__(self, _bot):
        global Guild_settings, Official_emojis, get_txt, is_command, Texts
        self.bot = _bot
        get_txt = _bot.get_txt
        is_command = _bot.is_command
        Texts = _bot.texts
        Guild_settings = _bot.guild_settings
        Official_emojis = _bot.consts["oe"]

    @commands.Cog.listener("on_message")
    async def on_message_lainan(self, message):
        global lainan_doing
        if message.author.bot:
            return
        elif message.channel.id not in Guild_settings[message.guild.id]["lainan_talk"]:
            return
        elif is_command(message):
            return
        elif "lainan" not in message.content.lower():
            return
        wh = discord.utils.get((await message.channel.webhooks()), name="sevenbot-lainan")
        if wh is None:
            wh = await message.channel.create_webhook(name="sevenbot-lainan", avatar=(await Official_emojis["lainan"].url_as().read()))

        LAINAN_QUEUE.append([wh, message.content])
        if not lainan_doing:
            lainan_doing = True
            try:
                async with aiohttp.ClientSession() as s:
                    while LAINAN_QUEUE:
                        cr = LAINAN_QUEUE[0]
                        async with s.get('https://api.lainan.one/?msg=' + urllib.parse.quote(cr[1])) as r:
                            if r.status != 200:
                                return
                            data = await r.json()
                            await cr[0].send(data['reaction'], username="Lainan", allowed_mentions=discord.AllowedMentions.none())
                        LAINAN_QUEUE.pop(0)
                        await asyncio.sleep(1)
            except Exception as e:
                lainan_doing = False
                raise e
            lainan_doing = False

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, pl):
        loop = asyncio.get_event_loop()
        if pl.channel_id == Channel_ids["emoji_print"]:
            print(pl.emoji.name)
        channel = self.bot.get_channel(pl.channel_id)
        try:
            message = await channel.fetch_message(pl.message_id)
        except (discord.errors.NotFound, discord.errors.Forbidden):
            return

        guild = self.bot.get_guild(pl.guild_id)
        user = guild.get_member(pl.user_id)
        if message.embeds != [] and message.author.id == self.bot.user.id and pl.user_id != self.bot.user.id:
            m0 = message.embeds[0]
            if m0.title.startswith(get_txt(guild.id, "big-number")["title"] + " - "):
                if m0.title.endswith(get_txt(guild.id, "big-number")["waiting"]):
                    n = datetime.datetime.utcnow()
                    guild = self.bot.get_guild(pl.guild_id)
                    user = guild.get_member(pl.user_id)
                    if message.id not in Bignum_join.keys():
                        Bignum_join[message.id] = m0.fields[0].value.split(
                            "\n")
                    try:
                        await message.remove_reaction(pl.emoji, user)
                    except Forbidden:
                        pass
                    if pl.emoji.name == "check5":
                        if user.mention == Bignum_join[message.id][0]:
                            if len(Bignum_join[message.id]) >= 3:
                                e = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + get_txt(guild.id, "big-number")["ready"],
                                                  description=get_txt(guild.id, "big-number")["ready_desc"].format(len(Bignum_join[message.id])) + "\n" + "\n".join(Bignum_join[message.id]), color=Gaming)
                                try:
                                    await message.clear_reactions()
                                except Forbidden:
                                    pass
                                await message.edit(embed=e)
                                await asyncio.sleep(2)
                                e2 = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + Texts[Guild_settings[guild.id]["lang"]]
                                                   ["big-number"]["input"], description=get_txt(guild.id, "big-number")["input_desc"], color=Gaming)
                                e = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + Texts[Guild_settings[guild.id]["lang"]]
                                                  ["big-number"]["input2"], description=get_txt(guild.id, "big-number")["input2_desc"], color=Gaming)
                                await message.edit(embed=e)
                                players = []
                                inputs = {}
                                ga = []

                                async def single_wait(e, user):
                                    while True:
                                        await self.bot.get_user(user).send(embed=e)
                                        try:
                                            msg = await self.bot.wait_for("message", check=(lambda message: message.author.id == user and message.guild is None), timeout=60)
                                        except asyncio.TimeoutError:
                                            return False
                                        if not msg.content.isdecimal():
                                            continue
                                        elif int(msg.content) not in range(1, 11):
                                            continue
                                        if int(msg.content) not in inputs.keys():
                                            inputs[int(msg.content)] = []
                                        inputs[int(msg.content)].append(
                                            msg.author.id)
                                        e3 = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + Texts[Guild_settings[guild.id]["lang"]]
                                                           ["big-number"]["input"], description=get_txt(guild.id, "big-number")["input_received"], color=Gaming)
                                        await msg.channel.send(embed=e3)
                                        e4 = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + get_txt(guild.id, "big-number")
                                                           ["input"], description=get_txt(guild.id, "big-number")["input_received2"].format(msg.author.mention), color=Gaming)
                                        await message.channel.send(embed=e4)
                                        break
                                for mention in Bignum_join[message.id]:
                                    mn = guild.get_member(
                                        int(re.findall(Mention_re, mention)[0]))
                                    players.append(mn.id)
                                    try:
                                        ga.append(single_wait(e2, mn.id))
                                    except Forbidden:
                                        e = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + Texts[Guild_settings[guild.id]["lang"]]
                                                          ["big-number"]["cancel"], description=get_txt(guild.id, "big-number")["no_dm"], color=Gaming)
                                        await message.edit(embed=e)
                                        return

                                res = await asyncio.gather(*ga)
                                if len(list(flatten(list(inputs.values())))) != len(Bignum_join[message.id]):
                                    e = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + Texts[Guild_settings[guild.id]["lang"]]
                                                      ["big-number"]["cancel"], description=get_txt(guild.id, "big-number")["timeout"], color=Gaming)
                                    await message.edit(embed=e)
                                    await channel.send(embed=e)
                                    return
                                res = None
                                tmax = {}
                                ls = ""
                                for ik, iv in inputs.items():
                                    for iv2 in iv:
                                        ls += guild.get_member(iv2).mention + " - " + str(ik) + (
                                            get_txt(guild.id, "big-number")["double"] if len(iv) > 1 else "") + "\n"
                                    if len(iv) > 1:
                                        pass
                                    else:
                                        tmax[ik] = iv[0]
                                if tmax != {}:
                                    message = max(list(tmax.keys()))
                                    if message == 10 and 1 in tmax.keys():
                                        res = [1, tmax[1]]
                                    else:
                                        res = [message, tmax[message]]
                                    e = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + get_txt(guild.id, "big-number")["result"],
                                                      description=get_txt(guild.id, "big-number")["result_desc1"].format(guild.get_member(res[1]).mention, res[0]) + ls, color=Gaming)
                                else:
                                    e = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + get_txt(guild.id, "big-number")
                                                      ["result"], description=get_txt(guild.id, "big-number")["result_desc2"].format(list(inputs.keys())[0]) + ls, color=Gaming)
                                await channel.send(embed=e)
                        elif user.mention not in Bignum_join[message.id]:
                            Bignum_join[message.id].append(user.mention)

                            m0.set_field_at(
                                0, name=get_txt(guild.id, "big-number")["players"].format(len(Bignum_join[message.id])), value="\n".join(Bignum_join[message.id]))
                            await message.edit(embed=m0)
                            Bignum_join[message.id] = Bignum_join[message.id]
                    elif pl.emoji.name == "check6":
                        if user.mention == Bignum_join[message.id][0]:
                            e = discord.Embed(title=get_txt(guild.id, "big-number")["title"] + " - " + Texts[Guild_settings[guild.id]
                                                                                                             ["lang"]]["big-number"]["cancel"], description=get_txt(guild.id, "canceled"), color=Gaming)
                            try:
                                await message.clear_reactions()
                            except Forbidden:
                                pass
                            await message.edit(embed=e)

                        elif user.mention in Bignum_join[message.id]:
                            Bignum_join[message.id].remove(user.mention)
                            m0.set_field_at(
                                0, name=get_txt(guild.id, "big-number")["players"].format(len(Bignum_join[message.id])), value="\n".join(Bignum_join[message.id]))
                            await message.edit(embed=m0)
                            try:
                                await message.remove_reaction(pl.emoji, user)
                            except Forbidden:
                                pass
                            Bignum_join[message.id] = Bignum_join[message.id]
            elif m0.title.startswith(get_txt(guild.id, "ww")["title"] + " - "):
                if m0.title.endswith(get_txt(guild.id, "ww")["waiting"]):
                    n = datetime.datetime.utcnow()
                    guild = self.bot.get_guild(pl.guild_id)
                    user = guild.get_member(pl.user_id)
                    if message.id not in Wolf_join.keys():
                        Wolf_join[message.id] = m0.fields[0].value.split("\n")
                    try:
                        await message.remove_reaction(pl.emoji, user)
                    except Forbidden:
                        pass
                    if pl.emoji.name == "check5":
                        if user.mention == Wolf_join[message.id][0]:
                            if len(Wolf_join[message.id]) >= 6:

                                e = discord.Embed(title=get_txt(guild.id, "ww")["title"] + " - " + get_txt(guild.id, "ww")["ready"],
                                                  description=get_txt(guild.id, "ww")["ready_desc"].format(len(Wolf_join[message.id])) + "\n" + "\n".join((w.mention if isinstance(w, discord.Member) else w) for w in Wolf_join[message.id]), color=Gaming)
                                try:
                                    await message.clear_reactions()
                                except Forbidden:
                                    pass
                                await message.edit(embed=e)
                                await asyncio.sleep(2)
                                players = []
                                inputs = {}
                                ga = []
                                wolf_members = [guild.get_member(
                                    int(re.findall(Mention_re, mn)[0])) for mn in Wolf_join[message.id]]
                                tmp_roles = [1, 2, 3]
                                n = len(wolf_members) - 3
                                last_defend = None
                                died_role = []
                                tmp_roles.extend([4] * (n // 3))
                                tmp_roles.extend([0] * (n - n // 3))
                                random.shuffle(tmp_roles)
                                wolf_roles = {}
                                wolfs = []
                                for mi, mn in enumerate(wolf_members):
                                    wolf_roles[mn] = tmp_roles[mi]
                                    if tmp_roles[mi] == 4:
                                        wolfs.append(mn.name)
                                for mi, mn in enumerate(wolf_members):
                                    try:
                                        e = discord.Embed(title=get_txt(guild.id, "ww")["your_role"].format(get_txt(guild.id, "ww")["roles"][tmp_roles[mi]][0]),
                                                          description=get_txt(guild.id, "ww")["roles"][tmp_roles[mi]][1] + "\n"
                                                          + get_txt(guild.id, "ww")["win_cond"][0] + "\n"
                                                          + get_txt(guild.id, "ww")["win_cond"][get_txt(guild.id, "ww")["roles"][tmp_roles[mi]][2] + 1], color=Gaming)
                                        if tmp_roles[mi] == 4:
                                            e.add_field(
                                                name="このゲームの人狼", value="\n".join(wolfs))

                                        ga.append(mn.send(embed=e))
                                        if guild.get_role(Guild_settings[guild.id]["ww_role"]["alive"]):
                                            ga.append(mn.add_roles(guild.get_role(
                                                Guild_settings[guild.id]["ww_role"]["alive"])))

                                    except discord.errors.Forbidden:
                                        e = discord.Embed(title=get_txt(guild.id, "ww")["title"] + " - " + Texts[Guild_settings[guild.id]
                                                                                                                 ["lang"]]["ww"]["cancel"], description=get_txt(guild.id, "ww")["no_dm"], color=Gaming)
                                        await message.edit(embed=e)
                                        return
                                desc = ""
                                for rci, rca in enumerate(get_txt(guild.id, "ww")["roles"]):
                                    desc += rca[0] + " x" + \
                                        str(tmp_roles.count(rci)) + "\n"
                                rce = discord.Embed(title=get_txt(guild.id, "ww")["title"] + " - "
                                                    + get_txt(guild.id, "ww")["info"], description=desc, color=Gaming)
                                await asyncio.gather(*ga)
                                day = 0
                                while True:
                                    day += 1
                                    wpl = ""
                                    for wm in wolf_members:
                                        wpl += "__" + wm.mention + "__\n"
                                    e = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(day) + " - " + get_txt(guild.id, "ww")["noon"],
                                                      description=get_txt(guild.id, "ww")["noon_desc"].format(Official_emojis["skip"], Official_emojis["info"], wpl), color=Gaming)
                                    msg = await channel.send(embed=e)
                                    await msg.add_reaction(Official_emojis["skip"])
                                    await msg.add_reaction(Official_emojis["info"])

                                    def check(reaction, user):
                                        if reaction.message.id != msg.id:
                                            return False
                                        elif user.bot:
                                            return False
                                        elif user not in wolf_members:
                                            loop.create_task(
                                                reaction.message.remove_reaction(reaction.emoji, user))
                                            return False
                                        elif reaction.emoji != Official_emojis["skip"]:
                                            loop.create_task(
                                                reaction.message.remove_reaction(reaction.emoji, user))
                                            if reaction.emoji.name == "info":

                                                loop.create_task(
                                                    user.send(embed=rce))
                                            return False
                                        return (reaction.count == len(wolf_members) + 1)
                                    try:
                                        await self.bot.wait_for("reaction_add", timeout=180, check=check)
                                    except asyncio.TimeoutError:
                                        pass
                                    await msg.clear_reactions()

                                    vm = ""
                                    for message, mn in enumerate(wolf_members):
                                        vm += f"`{message+1}` : __{mn.display_name}__\n"
                                    e = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                        day) + " - " + get_txt(guild.id, "ww")["vote"], description=get_txt(guild.id, "ww")["vote_desc"] + "\n" + vm, color=Gaming)
                                    e2 = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                        day) + " - " + get_txt(guild.id, "ww")["vote2"], description=get_txt(guild.id, "ww")["vote_desc"] + "\n" + vm, color=Gaming)
                                    inputs = {}

                                    async def single_wait(e, user, message):
                                        while True:
                                            await self.bot.get_user(user).send(embed=e)
                                            try:
                                                msg = await self.bot.wait_for("message", check=(lambda message: message.author.id == user and message.guild is None), timeout=60)
                                            except asyncio.TimeoutError:
                                                continue
                                            if not msg.content.isdecimal():
                                                continue
                                            elif int(msg.content) not in range(1, message + 1):
                                                continue
                                            if int(msg.content) not in inputs.keys():
                                                inputs[int(msg.content)] = []
                                            inputs[int(msg.content)].append(
                                                msg.author)
                                            e3 = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                                day) + " - " + get_txt(guild.id, "ww")["vote2"], description=get_txt(guild.id, "ww")["vote_received"], color=Gaming)
                                            await msg.channel.send(embed=e3)
                                            e4 = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                                day) + " - " + get_txt(guild.id, "ww")["vote2"], description=get_txt(guild.id, "ww")["vote_received2"].format(msg.author.mention), color=Gaming)
                                            await channel.send(embed=e4)
                                            break
                                    ga = []
                                    for mn in wolf_members:
                                        ga.append(single_wait(
                                            e2, mn.id, len(wolf_members)))
                                    await asyncio.gather(*ga)
                                    tmax = 0
                                    res = []
                                    for ik, iv in inputs.items():
                                        if len(iv) > tmax:
                                            tmax = int(len(iv))
                                    for ik, iv in inputs.items():
                                        if len(iv) == tmax:
                                            res.append(wolf_members[ik - 1])
                                    if len(res) > 1:  # 引き分け
                                        vm = ""
                                        await channel.send(embed=discord.Embed(title=get_txt(guild.id, "ww")["day"].format(day) + " - " + get_txt(guild.id, "ww")["vote3"], description=get_txt(guild.id, "ww")["vote_draw"], color=Gaming))
                                        for message, mn in enumerate(res):
                                            vm += f"`{message+1}` : __{mn.display_name}__\n"
                                        e2 = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                            day) + " - " + get_txt(guild.id, "ww")["vote3"], description=get_txt(guild.id, "ww")["vote_desc"] + "\n" + vm, color=Gaming)
                                        inputs = {}
                                        ga = []
                                        for mn in wolf_members:
                                            ga.append(single_wait(
                                                e2, mn.id, len(res)))
                                        await asyncio.gather(*ga)
                                        tmax = 0
                                        res2 = []
                                        for ik, iv in inputs.items():
                                            if len(iv) > tmax:
                                                tmax = len(iv)
                                        for ik, iv in inputs.items():
                                            if len(iv) == tmax:
                                                res2.append(res[ik - 1])
                                        if len(res2) > 1:
                                            res = random.sample(res2, 1)[0]
                                            rem = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                                day) + " - " + get_txt(guild.id, "ww")["vote_result"], description=get_txt(guild.id, "ww")["vote_draw2"].format(res.mention), color=Gaming)
                                        else:
                                            res = res2[0]
                                            rem = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                                day) + " - " + get_txt(guild.id, "ww")["vote_result"], description=get_txt(guild.id, "ww")["vote_result_desc"].format(res.mention), color=Gaming)
                                    else:
                                        res = res[0]
                                        rem = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(
                                            day) + " - " + get_txt(guild.id, "ww")["vote_result"], description=get_txt(guild.id, "ww")["vote_result_desc"].format(res.mention), color=Gaming)
                                    rem.set_footer(text=get_txt(guild.id, "ww")["remain"].format(
                                        len(wolf_members) - 1))
                                    await channel.send(embed=rem)
                                    await res.send(embed=discord.Embed(title=get_txt(guild.id, "ww")["day"].format(day) + " - " + get_txt(guild.id, "ww")["vote_result"], description=get_txt(guild.id, "ww")["vote_result_dm"], color=Gaming))
                                    died_role.append(wolf_roles[res])
                                    if guild.get_role(Guild_settings[guild.id]["ww_role"]["alive"]):
                                        await res.remove_roles(guild.get_role(Guild_settings[guild.id]["ww_role"]["alive"]))
                                    if guild.get_role(Guild_settings[guild.id]["ww_role"]["dead"]):
                                        await res.add_roles(guild.get_role(Guild_settings[guild.id]["ww_role"]["dead"]))
                                    wolf_members.remove(res)
                                    wc = 0
                                    for wm in wolf_members:
                                        if wolf_roles[wm] == 4:
                                            wc += 1
                                    if wc == 0 or wc * 2 == len(wolf_members):
                                        break
                                    wolf_targets = {}
                                    ga = []

                                    async def single_wait2(e, user, message, wm):
                                        while True:
                                            await self.bot.get_user(user).send(embed=e)
                                            try:
                                                msg = await self.bot.wait_for("message", check=(lambda message: message.author.id == user and message.guild is None), timeout=60)
                                            except asyncio.TimeoutError:
                                                continue
                                            if not msg.content.isdecimal():
                                                continue
                                            elif int(msg.content) not in range(1, message + 1):
                                                continue
                                            if wolf_roles[wm] == 4:
                                                i = 0
                                                for mn in wolf_members:
                                                    if wolf_roles[mn] == 4:
                                                        continue
                                                    i += 1
                                                    if int(msg.content) == i:
                                                        if mn not in wolf_targets.keys():
                                                            wolf_targets[mn] = True
                                                        break

                                            elif wolf_roles[wm] == 3:
                                                i = 0
                                                for mn in wolf_members:
                                                    if mn == last_defend or wm == mn:
                                                        continue
                                                    i += 1
                                                    if int(msg.content) == i:
                                                        wolf_targets[mn] = False
                                                        break

                                            elif wolf_roles[wm] == 1:
                                                target = wolf_members[int(
                                                    msg.content) - 1]
                                                e3 = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(day) + " - " + get_txt(guild.id, "ww")["night"] + " - " + get_txt(guild.id, "ww")["night_txt"][wolf_roles[wm]][0],
                                                                   description=get_txt(guild.id, "ww")["night_txt"][wolf_roles[wm]][3].format(
                                                    target.display_name,
                                                    get_txt(guild.id, "ww")["team"][
                                                        Texts[Guild_settings[guild.id]["lang"]
                                                              ]["ww"]["roles"][wolf_roles[target]][2]
                                                    ]
                                                ),
                                                    color=Gaming
                                                )
                                                await msg.channel.send(embed=e3)
                                                return
                                            else:
                                                return
                                            e3 = discord.Embed(title=get_txt(guild.id, "ww")["day"].format(day) + " - " + get_txt(guild.id, "ww")["night"] + " - "
                                                               + get_txt(guild.id, "ww")["night_txt"][wolf_roles[wm]][0], description=get_txt(guild.id, "ww")["vote_received"], color=Gaming)
                                            await msg.channel.send(embed=e3)
                                            break

                                    for wm in wolf_members:
                                        more = "\n"
                                        i = 0
                                        if wolf_roles[wm] == 1:
                                            for mn in wolf_members:
                                                i += 1
                                                more += f"`{i}` : __{mn.display_name}__\n"
                                        elif wolf_roles[wm] == 3:
                                            i = 0
                                            for mn in wolf_members:
                                                if mn == last_defend or wm == mn:
                                                    continue
                                                i += 1
                                                more += f"`{i}` : __{mn.display_name}__\n"
                                        elif wolf_roles[wm] == 4:
                                            i = 0
                                            for mn in wolf_members:
                                                if wolf_roles[mn] == 4:
                                                    continue
                                                i += 1
                                                more += f"`{i}` : __{mn.display_name}__\n"
                                        else:
                                            pass
                                        e = discord.Embed(
                                            title=get_txt(guild.id, "ww")["day"].format(day) + " - "
                                            + get_txt(guild.id, "ww")["night"] + " - "
                                            + Texts[Guild_settings[guild.id]["lang"]
                                                    ]["ww"]["night_txt"][wolf_roles[wm]][0],
                                            description=(get_txt(guild.id, "ww")["night_txt"][wolf_roles[wm]][1] if wolf_roles[wm] != 2 or day == 1 else
                                                         get_txt(guild.id, "ww")["night_txt"][wolf_roles[wm]][3].format(
                                                             get_txt(guild.id, "ww")["team"][get_txt(guild.id, "ww")["roles"][died_role[-2]][2]])
                                                         ) + more,
                                            color=Gaming)

                                        if i != 0:
                                            ga.append(single_wait2(
                                                e, wm.id, more.count("\n"), wm))
                                        else:
                                            ga.append(wm.send(embed=e))
                                    await asyncio.gather(*ga)
                                    died = ""
                                    e = discord.Embed(
                                        title=get_txt(guild.id, "ww")["day"].format(
                                            day) + " - " + get_txt(guild.id, "ww")["died"],
                                        description=(get_txt(guild.id, "ww")["died_dm"]), color=Gaming)
                                    for wt, wtm in wolf_targets.items():
                                        if wtm:
                                            if guild.get_role(Guild_settings[guild.id]["ww_role"]["alive"]):
                                                await wt.remove_roles(guild.get_role(Guild_settings[guild.id]["ww_role"]["alive"]))
                                            if guild.get_role(Guild_settings[guild.id]["ww_role"]["dead"]):
                                                await wt.add_roles(guild.get_role(Guild_settings[guild.id]["ww_role"]["dead"]))
                                            wolf_members.remove(wt)
                                            died += wt.mention + "\n"
                                            await wt.send(embed=e)
                                    e = discord.Embed(
                                        title=get_txt(guild.id, "ww")["day"].format(
                                            day) + " - " + get_txt(guild.id, "ww")["died"],
                                        description=(get_txt(guild.id, "ww")["died_desc"].format(died) if died != "" else get_txt(guild.id, "ww")["died_fail"]), color=Gaming)
                                    e.set_footer(text=get_txt(guild.id, "ww")["remain"].format(
                                        len(wolf_members)))
                                    await channel.send(embed=e)

                                    wc = 0
                                    for wm in wolf_members:
                                        if wolf_roles[wm] == 4:
                                            wc += 1

                                    if wc == 0 or wc * 2 == len(wolf_members):
                                        break
                                everyone_roles = ""

                                for k, v in wolf_roles.items():
                                    everyone_roles += f'__{k.mention}__ - {get_txt(guild.id,"ww")["roles"][v][0]}'
                                    if guild.get_role(Guild_settings[guild.id]["ww_role"]["alive"]):
                                        await k.remove_roles(guild.get_role(Guild_settings[guild.id]["ww_role"]["alive"]))
                                    if guild.get_role(Guild_settings[guild.id]["ww_role"]["dead"]):
                                        await k.remove_roles(guild.get_role(Guild_settings[guild.id]["ww_role"]["dead"]))
                                    if k not in wolf_members:
                                        everyone_roles += Texts[Guild_settings[guild.id]
                                                                ["lang"]]["ww"]["dead"]
                                    everyone_roles += "\n"
                                if wc * 2 == len(wolf_members):
                                    e = discord.Embed(title=get_txt(guild.id, "ww")["title"].format(
                                        day) + " - " + get_txt(guild.id, "ww")["result"], description=get_txt(guild.id, "ww")["result_desc2"].format(everyone_roles), color=Gaming)
                                else:
                                    e = discord.Embed(title=get_txt(guild.id, "ww")["title"].format(
                                        day) + " - " + get_txt(guild.id, "ww")["result"], description=get_txt(guild.id, "ww")["result_desc1"].format(everyone_roles), color=Gaming)
                                await channel.send(embed=e)
                        elif user.mention not in Wolf_join[message.id]:
                            Wolf_join[message.id].append(user.mention)
                            m0.set_field_at(
                                0, name=get_txt(guild.id, "ww")["players"].format(len(Wolf_join[message.id])), value="\n".join(str(w) for w in Wolf_join[message.id]))
                            await message.edit(embed=m0)
                    elif pl.emoji.name == "check6":
                        if user.mention == Wolf_join[message.id][0]:
                            e = discord.Embed(title=get_txt(guild.id, "ww")["title"] + " - " + Texts[Guild_settings[guild.id]
                                                                                                     ["lang"]]["ww"]["cancel"], description=get_txt(guild.id, "canceled"), color=Gaming)
                            try:
                                await message.clear_reactions()
                            except Forbidden:
                                pass
                            await message.edit(embed=e)

                        elif user.mention in Wolf_join[message.id]:
                            Wolf_join[message.id].remove(user.mention)
                            m0.set_field_at(
                                0, name=get_txt(guild.id, "ww")["players"].format(len(Wolf_join[message.id])), value="\n".join((w.mention if isinstance(w, discord.Member) else w) for w in Wolf_join[message.id]))
                            await message.edit(embed=m0)
                            try:
                                await message.remove_reaction(pl.emoji, user)
                            except Forbidden:
                                pass
                            Wolf_join[message.id] = Wolf_join[message.id]

    @commands.command(name="bignum")
    async def bn(self, ctx):
        e = discord.Embed(title=get_txt(ctx.guild.id, "big-number")["title"] + " - " + get_txt(ctx.guild.id, "big-number")["waiting"],
                          description=get_txt(ctx.guild.id, "big-number")["waiting_desc"].format(Official_emojis["check5"], Official_emojis["check6"]), color=Gaming)
        e.add_field(name=get_txt(ctx.guild.id, "big-number")
                    ["players"].format(1), value=ctx.author.mention)
        msg = await ctx.reply(embed=e)
        Bignum_join[msg] = [ctx.author.mention]
        await msg.add_reaction(Official_emojis["check5"])
        await msg.add_reaction(Official_emojis["check6"])

    @commands.group(name="werewolf", invoke_without_command=True, aliases=["ww"])
    async def ww(self, ctx):
        e = discord.Embed(title=get_txt(ctx.guild.id, "ww")["title"] + " - " + get_txt(ctx.guild.id, "ww")["waiting"],
                          description=get_txt(ctx.guild.id, "ww")["waiting_desc"].format(Official_emojis["check5"], Official_emojis["check6"]), color=Gaming)
        e.add_field(name=get_txt(ctx.guild.id, "ww")[
                    "players"].format(1), value=ctx.author.mention)
        msg = await ctx.reply(embed=e)
        Wolf_join[msg.id] = [ctx.author.mention]
        await msg.add_reaction(Official_emojis["check5"])
        await msg.add_reaction(Official_emojis["check6"])

    @commands.has_guild_permissions(manage_roles=True)
    @ww.command(name="role")
    async def ww_role(self, ctx, rtype, role: discord.Role = None):
        if rtype.lower() not in ("alive", "dead"):
            e = discord.Embed(title=get_txt(ctx.guild.id, "ww")[
                              "role_type"], color=Error)
            return await ctx.reply(embed=e)
        if role is None:
            Guild_settings[ctx.guild.id]["ww_role"][rtype.lower()] = None
            e = discord.Embed(title=get_txt(ctx.guild.id, "ww")["role_set_none"].format(
                get_txt(ctx.guild.id, "ww")[f"role_{rtype.lower()}"]), color=Success)
            return await ctx.reply(embed=e)
        if role.position > ctx.author.top_role.position and ctx.author.id != ctx.guild.owner_id:
            e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")[
                              "no_role_perm"], color=Error)
            return await ctx.reply(embed=e)
        Guild_settings[ctx.guild.id]["ww_role"][rtype.lower()] = role.id
        e = discord.Embed(title=get_txt(ctx.guild.id, "ww")["role_set"].format(get_txt(
            ctx.guild.id, "ww")[f"role_{rtype.lower()}"], "`@" + role.name + "`"), color=Success)
        return await ctx.reply(embed=e)

    @commands.command(aliases=["ree"])
    async def reencode(self, ctx, *, text):
        await ctx.reply(embed=SEmbed(get_txt(ctx.guild.id, "reencode"), text.encode("utf8").decode("sjis", errors="ignore"), color=Success))

    @commands.command(name="tic_tac_toe", aliases=["ox", "tictactoe"])
    async def tic_tac_toe(self, ctx, target: discord.Member):
        turns = [ctx.author, target]
        if random.randrange(2):
            turns.reverse()
        index = 0
        if target.bot:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "ox_bot"), color=Error)
            return await ctx.reply(embed=e)
        elif target.id == ctx.author.id:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "ox_self"), color=Error)
            return await ctx.reply(embed=e)
        base_im = Image.new("RGBA", (480, 480), rgb_tuple(0x36393f))
        try:
            async with timeout(5):
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(turns[0].avatar_url_as(format="png"))) as r:
                        f = io.BytesIO(await r.read())
                    async with session.get(str(turns[1].avatar_url_as(format="png"))) as r:
                        f2 = io.BytesIO(await r.read())
        except asyncio.TimeoutError:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "ox_connection_timeout"), color=Error)
            return await ctx.reply(embed=e)
        size = (640, 640)
        avater1 = Image.open(f).resize(size)
        avater2 = Image.open(f2).resize(size)
        f.close()
        f2.close()
        avater_mask = Image.new("L", size, 0)
        avater_mask_draw = ImageDraw.Draw(avater_mask)
        avater_mask_draw.rectangle(
            (size[0] / 2, 0, size[0], size[1]), fill=255)
        avater1.paste(avater2, mask=avater_mask)
        avater_draw = ImageDraw.Draw(avater1)
        fnt_vs = ImageFont.truetype("hiraw6.OTF", 320)
        w, h = avater_draw.textsize("s", fnt_vs)
        avater_draw.rectangle(
            (size[0] / 2 - 32, 0, size[0] / 2 + 32, size[1]), fill=255)
        w, h = avater_draw.textsize("b", fnt_vs)
        sendio = io.BytesIO()
        avater1.save(sendio, format="png")
        sendio.seek(0)
        try:
            async with timeout(5):
                amsg = await self.bot.get_channel(765528694500360212).send(file=discord.File(sendio, filename="result.png"))
        except asyncio.TimeoutError:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "ox_timeout"), color=Error)
            return await ctx.reply(embed=e)
        sendio.close()
        draw = ImageDraw.Draw(base_im)
        for i in range(1, 3):
            draw.line((160 * i, 0, 160 * i, 480), (255, 255, 255), 8, "curve")
            draw.line((0, 160 * i, 480, 160 * i), (255, 255, 255), 8, "curve")
        fields = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        fnt = ImageFont.truetype("hiraw3.OTF", 128)
        e = discord.Embed(title=get_txt(ctx.guild.id, "ox_title"), description=get_txt(
            ctx.guild.id, "ox_prepare"), color=Gaming)

        msg = await ctx.reply(embed=e)
        loop = asyncio.get_event_loop()
        for n in Number_emojis[1:10]:
            loop.create_task(msg.add_reaction(n))
        await ctx.message.delete()
        e.set_author(name=f"{ctx.author.display_name}(ID:{ctx.author.id}) vs {target.display_name}(ID:{target.id})",
                     icon_url=amsg.attachments[0].url)
        Win_pattern = [
            {0, 1, 2},
            {3, 4, 5},
            {6, 7, 8},
            {0, 3, 6},
            {1, 4, 7},
            {2, 5, 8},
            {0, 4, 8},
            {2, 4, 6},
        ]
        win = 0
        e.description = ""
        for turn in range(10):
            im = base_im.copy()
            draw = ImageDraw.Draw(im)
            text_tmp = Image.new('RGBA', im.size, (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_tmp)
            Simbol_size = 80
            Circle_width = 16
            for i, f in enumerate(fields):
                if fields[i] == 0:

                    w, h = text_draw.textsize(str(i + 1), fnt)
                    text_draw.text((80 - w / 2 + 160 * (i % 3), i // 3 * 160 + 80
                                   - h / 2 - 4), str(i + 1), font=fnt, fill=(255, 255, 255, 128))

                elif fields[i] == 1:
                    draw.ellipse((80 - Simbol_size / 2 + 160 * (i % 3), 80 - Simbol_size / 2 + 160 * (i // 3), 80
                                 + Simbol_size / 2 + 160 * (i % 3), 80 + Simbol_size / 2 + 160 * (i // 3)), discord.Color.red().to_rgb())
                    draw.ellipse((80 - (Simbol_size - Circle_width) / 2 + 160 * (i % 3), 80 - (Simbol_size - Circle_width) / 2 + 160 * (i // 3), 80 + (
                        Simbol_size - Circle_width) / 2 + 160 * (i % 3), 80 + (Simbol_size - Circle_width) / 2 + 160 * (i // 3)), rgb_tuple(0x36393f))
                elif fields[i] == 2:
                    draw.line((80 - Simbol_size / 2 + 160 * (i % 3), 80 - Simbol_size / 2 + 160 * (i // 3), 80 + Simbol_size
                              / 2 + 160 * (i % 3), 80 + Simbol_size / 2 + 160 * (i // 3)), discord.Color.blue().to_rgb(), 8, "curve")
                    draw.line((80 + Simbol_size / 2 + 160 * (i % 3), 80 - Simbol_size / 2 + 160 * (i // 3), 80 - Simbol_size
                              / 2 + 160 * (i % 3), 80 + Simbol_size / 2 + 160 * (i // 3)), discord.Color.blue().to_rgb(), 8, "curve")
            im = Image.alpha_composite(im, text_tmp)
            sendio = io.BytesIO()
            im.save(sendio, format="png")
            sendio.seek(0)
            amsg = await self.bot.get_channel(765528694500360212).send(file=discord.File(sendio, filename="result.png"))
            e.set_image(url=amsg.attachments[0].url)
            sendio.close()

            def check(r, u):
                if (not r.message.id == msg.id) or u.id == self.bot.user.id:
                    return False
                elif (not u.id == turns[index % 2].id) or (r.emoji in Number_emojis and r.count != 2):
                    loop.create_task(msg.remove_reaction(r, u))
                    return False
                return True
            p1_pos = {i for i, f in enumerate(fields) if f == 1}
            p2_pos = {i for i, f in enumerate(fields) if f == 2}
            for wp in Win_pattern:
                if wp <= p1_pos:
                    win = 1
                    break
                if wp <= p2_pos:
                    win = 2
                    break

            if turn == 9 or win != 0:
                break
            else:
                await msg.edit(content=get_txt(ctx.guild.id, "ox_turn").format(str(Official_emojis["ox" + str(index % 2 + 1)]) + turns[index % 2].mention), embed=e)
            try:
                r, u = await self.bot.wait_for("reaction_add", check=check, timeout=60)
            except asyncio.TimeoutError:
                e = discord.Embed(title=get_txt(
                    ctx.guild.id, "ox_user_timeout"), color=Error)
                return await ctx.reply(embed=e)
            fields[Number_emojis.index(r.emoji) - 1] = index % 2 + 1
            await msg.clear_reaction(r.emoji)
            index += 1
        if win == 0:
            e.description = get_txt(ctx.guild.id, "ox_draw")
        else:
            e.description = get_txt(ctx.guild.id, "ox_win").format(
                str(Official_emojis["ox" + str(2 - index % 2)]) + turns[win - 1].mention)
        await msg.clear_reactions()
        await msg.edit(content="", embed=e)

    @commands.Cog.listener("on_message")
    async def on_message_parse(self, message):
        if message.author.bot:
            return
        elif message.channel.id not in Guild_settings[message.guild.id]["auto_parse"]:
            return
        elif is_command(message):
            return
        brq = []
        ignore = ""
        res = ""
        for l in message.content.splitlines():
            if l.startswith(("//", "#")):
                res += l + "\n"
                continue
            for c in l:
                if (c in ('"', "'") and not ignore):
                    ignore = c
                    res += c
                    continue
                elif c == ignore:
                    ignore = ""
                    res += c
                    continue
                elif ignore:
                    res += c
                    continue

                if c in BRACKET_DICT.keys():
                    brq.append(c)
                    res += c
                elif c in BRACKET_DICT.values():
                    try:
                        if brq[-1].translate(BRACKET_TRANS) == c:
                            brq.pop(-1)
                            res += c
                    except IndexError:
                        pass
                else:
                    res += c
            res += "\n"
        res = res.rstrip()
        if brq == [] and ignore == "" and res.splitlines() == message.content.splitlines():
            return

        ch_webhooks = await message.channel.webhooks()
        webhook = discord.utils.get(
            ch_webhooks, name="sevenbot-parse-webhook")
        if webhook is None:
            g = self.bot.get_guild(
                Official_discord_id)
            a = g.icon_url_as(format="png")
            webhook = await message.channel.create_webhook(name="sevenbot-parse-webhook", avatar=await a.read())
        wm = None
        if not (res + ignore).splitlines() == message.content.splitlines():
            await message.delete()
            if res + ignore:
                wm = await webhook.send(content=res + ignore,  # content.replace("@", "@​")
                                        username=message.author.display_name + \
                                        f"({message.author})",
                                        allowed_mentions=discord.AllowedMentions.none(),
                                        avatar_url=message.author.avatar_url_as(
                                            static_format="png"),
                                        files=[await a.to_file() for a in message.attachments],
                                        wait=True)
        if "".join(reversed(brq)).translate(BRACKET_TRANS):
            await (wm or message).reply("".join(reversed(brq)).translate(BRACKET_TRANS))

    @commands.command(name="loop_trans", aliases=["ltrans"])
    @commands.cooldown(1, 10)
    async def loop_trans(self, ctx, *, base):
        try:
            txt = (await commands.MessageConverter().convert(ctx, base)).content
        except commands.errors.MessageNotFound:
            txt = base
        langs = random.sample(get_txt(ctx.guild.id, "lang_name").keys(), 24) + [Guild_settings[ctx.guild.id]['lang']]
        ltxt = ""
        for l in langs:
            ltxt += get_txt(ctx.guild.id, "lang_name")[l] + "→"

        ltxt = ltxt.rstrip("→")
        se = SEmbed(get_txt(ctx.guild.id, "ltrans"), txt[:2047], color=Trans, footer=f"{ltxt} 0/25")
        msg = await ctx.reply(embed=se)
        for i, l in enumerate(langs):
            txt = await TRANSLATOR.translate(txt, l, langs[i - 1])
            se.description = txt[:2047]
            se.footer.text = f"{ltxt} {i + 1}/25"
            await msg.edit(embed=se)
            await asyncio.sleep(2)
        se.description = txt
        se.fields = []
        await msg.edit(embed=se)

    @commands.group(name="image", aliases=["img"])
    async def _image(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @_image.command(name="neko")
    @commands.cooldown(1, 2)
    async def _image_neko(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://nekobot.xyz/api/image?type=neko') as response:
                res = await response.json()
                e = discord.Embed(color=res["color"])
                e.set_image(url=res["message"])
                e.set_footer(text="Powered by NekoBot API",
                             icon_url="https://images.discordapp.net/avatars/310039170792030211/237b80900f1dc974efcd1758701b594d.png")
                await ctx.reply(embed=e)

    @_image.command(name="kemomimi", aliases=["kemo", "kemonomimi"])
    @commands.cooldown(1, 2)
    async def _image_kemomimi(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://nekobot.xyz/api/image?type=kemonomimi') as response:
                res = await response.json()
                e = discord.Embed(color=res["color"])
                e.set_image(url=res["message"])
                e.set_footer(text="Powered by NekoBot API",
                             icon_url="https://images.discordapp.net/avatars/310039170792030211/237b80900f1dc974efcd1758701b594d.png")
                await ctx.reply(embed=e)

    @_image.command(name="food")
    @commands.cooldown(1, 2)
    async def _image_food(self, ctx):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://nekobot.xyz/api/image?type=food') as response:
                res = await response.json()
                e = discord.Embed(color=res["color"])
                e.set_image(url=res["message"])
                e.set_footer(text="Powered by NekoBot API",
                             icon_url="https://images.discordapp.net/avatars/310039170792030211/237b80900f1dc974efcd1758701b594d.png")
                await ctx.reply(embed=e)

    @_image.command(name="5000")
    @commands.cooldown(1, 2)
    async def _image_5000(self, ctx, top, bottom):
        e = SEmbed(color=0xff0000, image_url=f"https://gsapi.cyberrex.ml/image?top={urllib.parse.quote(top)}&bottom={urllib.parse.quote(bottom)}", footer="Powered by 5000choyen-api")
        await ctx.reply(embed=e)

    @_image.command(name="httpcat", aliases=["hcat", "http"])
    @commands.cooldown(1, 2)
    async def _image_httpcat(self, ctx, num: int):
        e = discord.Embed(color=0xd0383e)
        e.set_image(url=f'https://http.cat/{num}')
        e.set_footer(text="Powered by HTTP Cats",
                     icon_url="https://i.imgur.com/fEXdAAB.png")
        await ctx.reply(embed=e)

    @_image.command(name="github")
    @commands.cooldown(1, 2)
    async def _image_github(self, ctx, *, base=None):
        Size = 50
        Base = str(base if base else ctx.author.id)
        im = Image.new('RGB', (Size * 6, Size * 6), (240, 240, 240))
        Base_hashed = hashlib.md5(Base.encode()).hexdigest()
        draw = ImageDraw.Draw(im)
        h = int(Base_hashed[-7:-4], 16) / 4096
        l = int(Base_hashed[-4:-2], 16) / 256
        s = int(Base_hashed[-2:], 16) / 256
        Color = colorsys.hls_to_rgb(h, l, s)
        Color = tuple(map(lambda x: math.floor(x * 256), list(Color)))
        for i in range(15):
            if int(Base_hashed[i], 16) % 2 == 0:

                draw.rectangle(((Size * (i // 5) + Size * 2 + Size / 2, Size * (i % 5) + Size / 2,
                                 (Size * (i // 5) + Size * 3 - 1 + Size / 2, Size * (i % 5) + Size - 1 + Size / 2))), Color)
                draw.rectangle(((Size * 2 - Size * (i // 5) + Size / 2, Size * (i % 5) + Size / 2, (Size
                                                                                                    * 2 - Size * (i // 5) + Size - 1 + Size / 2, Size * (i % 5) + Size - 1 + Size / 2))), Color)
        tmpio = io.BytesIO()
        im.save(tmpio, format="png")
        tmpio.seek(0)
        e = discord.Embed(color=discord.Color.from_rgb(*Color))
        amsg = await self.bot.get_channel(765528694500360212).send(file=discord.File(tmpio, filename="result.png"))
        e.set_image(url=amsg.attachments[0].url)
        tmpio.close()
        await ctx.reply(embed=e)

    @_image.command(name="ps4")
    @commands.cooldown(1, 2)
    async def _image_ps4(self, ctx):
        if not ctx.message.attachments:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "no_attachments"), color=Error)
            await ctx.reply(embed=e)
            return
        image_byte = await ctx.message.attachments[0].read()
        Ps4_X = 7
        Ps4_Y = 85
        Ps4_width = 483
        Ps4_height = 534
        readio = io.BytesIO(image_byte)
        im = Image.open(readio).convert("RGBA")
        ps4_base = Image.open("./base_img/ps4.png").convert("RGBA")
        ps4_mask_base = Image.open("./base_img/ps4_mask.png").convert("L")
        fax = Ps4_width / im.size[0]
        fax2 = Ps4_height / im.size[1]
        if Ps4_height < im.size[1] * fax:
            fax2 = fax + 0
            fax = Ps4_height / im.size[1]
        w = int(im.size[0] * fax)
        h = int(im.size[1] * fax)
        w2 = int(im.size[0] * fax2)
        h2 = int(im.size[1] * fax2)
        ps4_mask = Image.new("L", (w2, h2), 0)
        ps4_mask.paste(ps4_mask_base, box=(
            int(w2 / 2 - Ps4_width / 2) - Ps4_X, int(h2 / 2 - Ps4_height / 2) - Ps4_Y))
        ps4_base.paste(im.resize((w2, h2)).filter(ImageFilter.GaussianBlur(10)), box=(int(
            Ps4_width / 2 - w2 / 2) + Ps4_X, int(Ps4_height / 2 - h2 / 2) + Ps4_Y), mask=ps4_mask)
        ps4_base.paste(im.resize((w, h - 1)), box=(int((Ps4_X + (Ps4_width / 2)
                                                        ) - w / 2), int(Ps4_Y + (Ps4_height / 2) - h / 2) + 1))

        e = discord.Embed(color=0x17399d)
        sendio = io.BytesIO()
        ps4_base.save(sendio, format="png")
        readio.close()
        sendio.seek(0)
        amsg = await self.bot.get_channel(765528694500360212).send(file=discord.File(sendio, filename="result.png"))
        e.set_author(
            name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
        e.set_image(url=amsg.attachments[0].url)
        sendio.close()
        await ctx.reply(embed=e)
        await ctx.message.delete()

    @_image.command(name="switch")
    async def _image_switch(self, ctx):
        if not ctx.message.attachments:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "no_attachments"), color=Error)
            await ctx.reply(embed=e)
            return
        image_byte = await ctx.message.attachments[0].read()
        readio = io.BytesIO(image_byte)
        im = Image.open(readio).convert("RGBA")
        switch_base = Image.open("./base_img/switch.png").convert("RGBA")
        switch_mask_base = Image.open(
            "./base_img/switch_mask.png").convert("L")

        Switch_X = 4
        Switch_Y = 21
        Switch_width = 473
        Switch_height = 768
        fax = Switch_width / im.size[0]
        fax2 = Switch_height / im.size[1]
        if Switch_height < im.size[1] * fax:
            fax2 = fax + 0
            fax = Switch_height / im.size[1]
        w = int(im.size[0] * fax)
        h = int(im.size[1] * fax)
        w2 = int(im.size[0] * fax2)
        h2 = int(im.size[1] * fax2)
        switch_mask = Image.new("L", (w, h), 0)
        switch_mask2 = Image.new("L", (w2, h2), 0)

        switch_mask.paste(switch_mask_base, box=(-int(Switch_width
                                                      / 2 - w / 2), -int(Switch_height / 2 - h / 2)))
        switch_mask2.paste(switch_mask_base, box=(-int(Switch_width
                                                       / 2 - w2 / 2), -int(Switch_height / 2 - h2 / 2)))
        switch_base.paste(im.resize((w2, h2)).filter(ImageFilter.GaussianBlur(10)), box=(int(
            (Switch_X + Switch_width / 2) - w2 / 2), int((Switch_Y + Switch_height / 2) - h2 / 2)), mask=switch_mask2)
        switch_base.paste(im.resize((w, h)), box=(int((Switch_X + Switch_width / 2) - w / 2),
                                                  int((Switch_Y + Switch_height / 2) - h / 2)), mask=switch_mask)
        e = discord.Embed(color=0xe61d15)
        sendio = io.BytesIO()
        switch_base.save(sendio, format="png")
        readio.close()
        sendio.seek(0)
        amsg = await self.bot.get_channel(765528694500360212).send(file=discord.File(sendio, filename="result.png"))
        e.set_author(
            name=f"{ctx.author.display_name}(ID:{ctx.author.id})", icon_url=ctx.author.avatar_url)
        e.set_image(url=amsg.attachments[0].url)
        sendio.close()
        await ctx.reply(embed=e)
        await ctx.message.delete()

    @commands.command(aliases=["lainan", "ltalk"])
    async def lainan_talk(self, ctx, *, text):
        async with aiohttp.ClientSession() as s:
            async with s.get('https://api.lainan.one/?msg=' + urllib.parse.quote(text)) as r:
                if r.status != 200:
                    return
                data = await r.json()
                await ctx.reply(data['reaction'])

    @commands.command(aliases=["sdeath"])
    async def sudden_death(self, ctx, *, text):
        await ctx.reply("```\n" + death_generator(text) + "\n```")

    @commands.command(aliases=["cword"])
    @commands.is_nsfw()
    @commands.cooldown(1, 2)
    async def unshort(self, ctx, word):
        async with aiohttp.ClientSession() as s:
            params = {
                'time': str(time.time()),
                'nm': word[:8],
                'mode': '',
                'data': 'data_ja_ryaku',
                'view': 'view_ja_ryaku',
                'code': 'euc',
            }
            async with s.get('https://seoi.net/cgi-bin/games/anoryaku.cgi', params=params) as r:
                if r.status != 200:
                    raise Exception('Generator has returned error.')
                res = urllib.parse.unquote(await r.text(), encoding="eucjp")
                if "すみません" in res:
                    e = SEmbed("復元に失敗しました。", res.split("~")[1], color=Error)
                    await ctx.reply(embed=e)
                else:
                    e = SEmbed(res.split("~")[1], color=Info)
                    for r in res.split("~")[2].split(",")[1:]:
                        e.fields.append(
                            SField(r.split("@")[0], r.split("@")[1], inline=False))

                    m = await ctx.reply(embed=e)
                    await m.add_reaction(Official_emojis["check6"])
                    try:
                        _ = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == m.id and r.emoji == Official_emojis["check6"] and not u.bot)
                        await m.edit(content="[編集済み]", embed=None)
                        await m.clear_reaction(Official_emojis["check6"])
                    except asyncio.TimeoutError:
                        await m.remove_reaction(Official_emojis["check6"])


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(FunCog(_bot))
