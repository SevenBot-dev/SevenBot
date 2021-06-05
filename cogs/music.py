import asyncio
import copy
import datetime
import math
import re
import sys
import urllib.error
import urllib.parse
from functools import partial
from html import unescape

import aiohttp
import discord
from googleapiclient.discovery import build  # type:ignore
import xmltodict
import youtube_dl
from discord import Forbidden, NotFound
from discord.ext import commands

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (Info, Success, Error, Process, Premium_color)
from common_resources.tools import (to_lts)
from common_resources.tokens import YOUTUBE_API_KEY

Default_queue = [[], 0, False, 0, False, False, 0.5]
Number_emojis = []
YTB = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}
ffmpeg_options = {
    'options': '-vn -af volume=-15dB',
    "executable": (r"c:/tools/ffmpeg/bin/ffmpeg.exe" if sys.platform == "win32" else r"ffmpeg"),
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel quiet"
}
Last_favorite = {}
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)


def get_url(rf):
    if rf.get("webpage_url") is not None:
        return rf.get("webpage_url")
#     print(rf)
    return f'https://youtu.be/{rf["id"]["videoId"]}'


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


class MusicCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Official_emojis, Number_emojis, Favorite_songs, Texts
        global get_txt
        self.bot = bot
        Guild_settings = bot.guild_settings
        Official_emojis = bot.consts["oe"]
        Texts = bot.texts
        Favorite_songs = bot.raw_config["fs"]
        get_txt = bot.get_txt
        for i in range(11):
            Number_emojis.append(Official_emojis["b" + str(i)])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, pl):
        loop = asyncio.get_event_loop()
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
        if message.embeds and pl.user_id != self.bot.user.id:
            if message.embeds[0].title == get_txt(guild.id, "favorite") and m0.description != get_txt(guild.id, "canceled") and not m0.description.endswith(get_txt(guild.id, "selected")):
                if m0.author.name != f"{user}(ID:{user.id})":
                    try:
                        await message.remove_reaction(pl.emoji, user)
                    except Forbidden:
                        pass
                elif pl.emoji in Number_emojis:
                    pass
                elif pl.emoji.name == "right2" or pl.emoji.name == "remove":
                    numbers = []
                    for mi, mr in enumerate(message.reactions):
                        if mr.emoji in Number_emojis:
                            if mr.count == 2:
                                numbers.append(mi)
                    rl = m0.description.split("\n")[1:]
                    l = []
                    res = ""
                    for rli, rle in enumerate(rl):
                        if rli % 2 == 1:
                            continue
                        l.append(rle[0:-3].split(" - "))
                    for n in numbers:
                        res += f'```\n{" - ".join(l[n][0:-2])}```\n'
                    e = discord.Embed(title=get_txt(guild.id, "favorite"),
                                      description=f"{res}" + get_txt(guild.id, "selected"), color=Success)
                    await message.edit(embed=e)
                    p = int(re.findall(
                            get_txt(guild.id, "page_footer"), m0.footer.text)[0])
                    try:
                        await message.clear_reactions()
                    except Forbidden:
                        pass
                    b = False
                    v = self.bot.voice_clients
                    voice = False
                    for v2 in v:
                        if v2.channel.guild.id == guild.id:
                            voice = v2
                            break
                    if not voice:
                        await self.mus_join({"message": message, "channel": channel, "guild": guild, "author": user})
                    for n in numbers:
                        if pl.emoji.name == "remove":
                            Favorite_songs[user.id].pop(n + p * 10)
                        else:
                            loop.create_task(self.mus_play(
                                {"message": message, "channel": channel, "guild": guild, "author": user, "force_queue": b}, l[n][-1]))
                            if not b:
                                await asyncio.sleep(1)
                            b = True
                elif pl.emoji.name == "check6":
                    e = discord.Embed(title=get_txt(guild.id, "favorite"),
                                      description=get_txt(guild.id, "canceled"), color=Success)
                    try:
                        await message.clear_reactions()
                    except Forbidden:
                        pass
                    await message.edit(embed=e)
                elif pl.emoji.name == "left" or pl.emoji.name == "right":
                    try:
                        await message.remove_reaction(pl.emoji, user)
                    except Forbidden:
                        pass
                    res = Favorite_songs[user.id]
                    e = discord.Embed(title=get_txt(guild.id, "getting"),
                                      description=get_txt(guild.id, "wait"), color=Process)
                    await message.edit(embed=e)
                    r = ""
                    p = int(re.findall(
                            get_txt(guild.id, "page_footer"), m0.footer.text)[0])
                    if pl.emoji.name == "left":
                        p -= 2
                    p %= math.ceil(len(res) / 10)
                    a = 10 * p
                    res_ary = {}

                    async def get_info(i, url):
                        while True:
                            try:
                                res_ary[i] = await loop.run_in_executor(None, partial(ytdl.extract_info,
                                                                                      url, download=False, process=False))
                                return
                            except youtube_dl.DownloadError:
                                pass

                    ga = []
                    for i, rf in enumerate(res[0 + a:10 + a]):
                        i + 2
                        ga.append(get_info(i, rf))
                    await asyncio.gather(*ga)
                    for i, f in sorted(res_ary.items(), key=lambda v: v[0]):
                        r += f'{Number_emojis[i+1]}:```\n{unescape(f["title"])} - {unescape(f["uploader"])} - {get_url(rf)}```\n'
                    e = discord.Embed(
                        title=get_txt(guild.id, "favorite"), description=f"{r}", color=Process)
                    e.set_author(name=f"{user}(ID:{user.id})",
                                 icon_url=user.avatar_url)
                    e.set_footer(
                        text=f'{get_txt(guild.id,"page")} {p+1}/{math.ceil(len(res)/10)}')
                    await message.edit(embed=e)
                else:
                    try:
                        await message.remove_reaction(pl.emoji, user)
                    except Forbidden:
                        pass
            if message.embeds[0].title and (message.embeds[0].title.endswith("`" + get_txt(guild.id, "yt_played")) or message.embeds[0].title.endswith("`" + get_txt(guild.id, "yt_queued"))):
                try:
                    await message.remove_reaction(pl.emoji, user)
                except Forbidden:
                    pass
                if m0.author.name == f"{user.display_name}(ID:{user.id})":

                    if pl.emoji.name == "add":
                        if pl.user_id in Last_favorite.keys():
                            tf = Last_favorite[pl.user_id] + datetime.timedelta(
                                seconds=5) < datetime.datetime.utcnow()
                        else:
                            tf = True
                        if tf:
                            Last_favorite[pl.user_id] = datetime.datetime.utcnow()
                            if user.id not in Favorite_songs.keys():
                                Favorite_songs[user.id] = []
                            url = m0.url
                            info = await loop.run_in_executor(None, partial(ytdl.extract_info, url, download=False, process=False))
                            t = ""

                            if await self.bot.db.find_one({"uid": user.id, "url": url}):
                                await self.bot.db.delete_one({"uid": user.id, "url": url})
                                t = Texts[Guild_settings[guild.id]["lang"]
                                          ]["yt_fav_del"].format(info["title"])
                            else:
                                await self.bot.db.insert_one({"uid": user.id, "url": get_url(info), "title": info["title"], "uploader": info["uploader"]})
                                t = Texts[Guild_settings[guild.id]["lang"]
                                          ]["yt_fav_add"].format(info["title"])
                            e = discord.Embed(title=t, url=get_url(info), description=get_txt(guild.id, "yt_fav_info").format(
                                len(Favorite_songs[user.id])), color=Success)
                            e.set_author(
                                name=f"{user}(ID:{user.id})", icon_url=user.avatar_url)
                            e.set_thumbnail(url=info["thumbnails"][-1]["url"])
                            await channel.send(embed=e)

    @commands.group(aliases=["mus"])
    async def music(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @music.command(name="join", aliases=["connect", "summon"])
    async def mus_join(self, ctx):
        if isinstance(ctx, dict):
            a = ctx["author"]
            c = ctx["channel"]
        else:
            a = ctx.author
            c = ctx.channel
        if a.voice is None:
            e = discord.Embed(title=get_txt(c.guild.id, "yt_not_connect3"),
                              description=get_txt(c.guild.id, "yt_not_connect2"), color=Error)

            await c.send(embed=e)
            return
        channel = a.voice.channel
        e = discord.Embed(title=get_txt(c.guild.id, "yt_join_wait").format(
            channel.name), description=get_txt(c.guild.id, "wait"), color=Process)
        m = await c.send(embed=e)
        await discord.VoiceChannel.connect(a.voice.channel)

        print("ボイチャ参加：" + channel.guild.name + " - " + channel.name)
        Queues[channel.id] = copy.deepcopy(Default_queue)
        e = discord.Embed(title=get_txt(c.guild.id, "yt_join_done").format(
            channel.name), description=get_txt(c.guild.id, "yt_join_desc"), color=Success)
        await m.edit(embed=e)
    # https://www.music.com/results?search_query=%EF%BD%91

#     @music.group(name="search_play", aliases=["sp", "search"])
#     async def music_search_play(self, ctx):
#         if ctx.invoked_subcommand is None:
#             e = discord.Embed(title=get_txt(ctx.guild.id,"how_to_use"),
#                               description="```\nmusic search_play youtube|yt\nmusic search_play niconico|nicovideo|nico```", color=Info)
#
#             await ctx.reply(embed=e)
    @music.command(name="search_play", aliases=["sp"])
    async def mus_yt_search_play(self, ctx, *, query):
        search_response = YTB.search().list(part='snippet', q=query,
                                            order='viewCount', type='video').execute()
        r = ""
        i2 = 0
        ms = []
        gu = ctx.guild
        for i, rf in enumerate(search_response["items"][0:9]):
            i2 = i + 2
            f = rf["snippet"]
#             print(rf)
            ms.append([unescape(f["title"]), unescape(
                f["channelTitle"]), get_url(rf)])
            r += f'{Number_emojis[i+1]}:```\n{unescape(f["title"])} - {unescape(f["channelTitle"])} - {get_url(rf)}```\n'
        if i2 == 0:
            e = discord.Embed(title=get_txt(ctx.guild.id, "yt_no_matches"),
                              description=get_txt(ctx.guild.id, "yt_search_try_again"), color=Error)
            await ctx.reply(embed=e)
            return
        e = discord.Embed(title=Texts[Guild_settings[ctx.guild.id]["lang"]]
                          ["yt_search_result"], description=f"{r}", color=Process)
        ta = Number_emojis[1:i2]
        ta.append(Official_emojis["check6"])
        m = await send_reaction(ctx, ta, {"embed": e})

        def check(r, u):
            return u.id == ctx.author.id and (r.emoji in Number_emojis or r.emoji.name == "check6")
        try:
            r, u = await self.bot.wait_for("reaction_add", check=check)
            if r.emoji in Number_emojis:
                for mr in m.reactions:
                    if mr.emoji != r.emoji:
                        continue
                    if mr.count == 1:
                        try:
                            await m.remove_reaction(r.emoji, u)
                        except Forbidden:
                            pass
                        return
                try:
                    await m.clear_reactions()
                except Forbidden:
                    pass
                # escape
                tms = ms[Number_emojis.index(r.emoji) - 1]
                e = discord.Embed(title=get_txt(gu.id, "yt_search_result"), description="```\n"
                                  + tms[0] + " - " + tms[1] + "```\n" + get_txt(gu.id, "selected"), color=Success)
                await m.edit(embed=e)
                await self.mus_play({"message": m, "channel": ctx.channel, "guild": gu, "author": u}, tms[2])
            elif r.emoji.name == "check6":
                e = discord.Embed(title=get_txt(gu.id, "yt_search_result"),
                                  description=get_txt(gu.id, "canceled"), color=Success)

                try:
                    await m.clear_reactions()
                except Forbidden:
                    pass
                await m.edit(embed=e)
            else:
                await m.remove_reaction(r.emoji, u)
        except asyncio.TimeoutError:
            await m.clear_reactions()
            e = discord.Embed(title=get_txt(gu.id, "yt_search_result"),
                              description=get_txt(gu.id, "canceled"), color=Success)
            await m.edit(embed=e)
# http://flapi.nicovideo.jp/api/getflv?v=
#     @music_search_play.command(name="niconico",aliases=["nicovideo","nico"])
#     async def mus_nico_search_play(self, ctx, *, query):
#         p={
#             "q":query,
#             "targets":"title,description,tags",
#             "_sort":"-viewCounter",
#             "_context":"SevenBot#1769",
#             "_limit":5,
#             "fields":["contentId"]
#         }
#
#         ua = "SevenBot#1769's niconico searching system"
#         header = {'User-Agent': ua}
#         req=requests.get("https://api.search.nicovideo.jp/api/v2/video/contents/search",params=p,headers=header).json()
#
#         if req["meta"]["status"] != 200:
#             if req["meta"]["status"] == 400:
#                 type="nico_wrong_query"
#             else:
#                 type="nico_api_die"
#             e = discord.Embed(title=get_txt(ctx.guild.id,"nico_failed"),
#                               description=get_txt(ctx.guild.id,type), color=Error)
#             await ctx.reply(embed=e)
#             return
#         ms=[]
#         for rr in req["data"]:
#             req2=xmltodict.parse(requests.get(f"https://ext.nicovideo.jp/api/getthumbinfo/{rr['contentId']}").text)["nicovideo_thumb_response"]["thumb"]
#             ms.append({"title":req2["title"],"channelTitle":req2["user_nickname"],"url":f"nico.ms/{rr['contentId']}"})
#
#         r = ""
#         i2 = 0
#
#         gu=ctx.guild
#         for i, rf in enumerate(ms):
#             i2 = i + 2
#             f = rf
#             r += f'{Number_emojis[i+1]}:```\n{unescape(f["title"])} - {unescape(f["channelTitle"])} - {rf["url"]}```\n'
# #         if i2 == 0:
# #             e = discord.Embed(title=get_txt(ctx.guild.id,"yt_no_matches"),
# #                               description=get_txt(ctx.guild.id,"yt_search_try_again"), color=Error)
# #             await ctx.reply(embed=e)
# #             return
#         e = discord.Embed(title=Texts[Guild_settings[ctx.guild.id]["lang"]]
#                           ["yt_search_result"], description=f"{r}", color=Process)
#         ta=Number_emojis[1:i2]
#         ta.append(Official_emojis["check6"])
#         m = await send_reaction(ctx, ta, {"embed": e})
#         def check(r,u):
#             return u.id == ctx.author.id and (r.emoji in Number_emojis or r.emoji.name == "check6")
#         try:
#             r,u = await self.bot.wait_for("reaction_add",check=check)
#             if r.emoji in Number_emojis:
#                 for mr in m.reactions:
#                     if mr.emoji != r.emoji:
#                         continue
#                     if mr.count == 1:
#                         try:
#                             await m.remove_reaction(r.emoji, u)
#                         except Forbidden:
#                             pass
#                         return
#                 try:
#                     await m.clear_reactions()
#                 except Forbidden:
#                     pass
#                 # escape
#                 tms=ms[Number_emojis.index(r.emoji) - 1]
#                 e = discord.Embed(title=get_txt(gu.id,"yt_search_result"), description="```\n" + tms["title"] + " - " + tms["channelTitle"] + "```\n" + get_txt(gu.id,"selected"), color=Success)
#                 await m.edit(embed=e)
#                 await self.mus_play({"message": m, "channel": ctx.channel, "guild": gu, "author": u}, tms["url"])
#             elif r.emoji.name == "check6":
#                 e = discord.Embed(title=get_txt(gu.id,"yt_search_result"),
#                                   description=get_txt(gu.id,"canceled"), color=Success)
#
#                 try:
#                     await m.clear_reactions()
#                 except Forbidden:
#                     pass
#                 await m.edit(embed=e)
#             else:
#                 await m.remove_reaction(r.emoji, u)
#         except asyncio.TimeoutError:
#             await m.clear_reactions()
#             e = discord.Embed(title=get_txt(gu.id,"yt_search_result"),
#                   description=get_txt(gu.id,"canceled"), color=Success)
#             await m.edit(embed=e)

    @music.command(name="favorite", aliases=["fav"])
    async def mus_favorite(self, ctx):
        if ctx.author.id not in Favorite_songs.keys():
            e = discord.Embed(title=get_txt(ctx.guild.id, "yt_no_fav"),
                              description=get_txt(ctx.guild.id, "yt_no_fav_desc").format(Official_emojis["add"]), color=Error)
            msg = await ctx.reply(embed=e)
            return
        res = Favorite_songs[ctx.author.id]

        cn = ctx.channel
        loop = asyncio.get_event_loop()
        e = discord.Embed(title=get_txt(ctx.guild.id, "getting"),
                          description=get_txt(ctx.guild.id, "wait"), color=Process)
        msg = await cn.send(embed=e)
        ga = []
        for nm in Number_emojis[1:(len(res) + 1 if len(res) + 1 < 10 else 11)]:
            loop.create_task(msg.add_reaction(nm))
        loop.create_task(msg.add_reaction(Official_emojis["check6"]))
        loop.create_task(msg.add_reaction(Official_emojis["left"]))
        loop.create_task(msg.add_reaction(Official_emojis["right"]))
        loop.create_task(msg.add_reaction(Official_emojis["right2"]))
        loop.create_task(msg.add_reaction(Official_emojis["remove"]))
        r = ""
        res_ary = {}

        async def get_info(i, url):
            try:
                res_ary[i] = await loop.run_in_executor(None, partial(ytdl.extract_info, url, download=False, process=False))
                return
            except youtube_dl.DownloadError as e:
                raise e

        ga = []
        for i, rf in enumerate(res[0:10]):
            ga.append(get_info(i, rf))
        await asyncio.gather(*ga)
        for i, f in sorted(res_ary.items(), key=lambda v: v[0]):
            r += f'{Number_emojis[i + 1]}:```\n{unescape(f["title"])} - {unescape(f["uploader"])} - {get_url(f)}```\n'
#             r += f'{Number_emojis[i+1]}:```\n{unescape(f["title"])} - {unescape(f["uploader"])} - {get_url(rf)}```\n'
        e = discord.Embed(title=Texts[Guild_settings[ctx.guild.id]
                                      ["lang"]]["favorite"], description=f"{r}", color=Process)
        e.set_author(name=f"{ctx.author}(ID:{ctx.author.id})",
                     icon_url=ctx.author.avatar_url)
        e.set_footer(
            text=f'{get_txt(ctx.guild.id,"page")} 1/{math.ceil(len(res)/10)}')
        await msg.edit(embed=e)
        # await asyncio.gather(*ga)

    @music.command(name="fast_play", aliases=["fp", "fsp"])
    async def mus_fast_search_play(self, ctx, *, query):
        try:
            rf = YTB.search().list(part='snippet', q=query, order='viewCount',
                                   type='video').execute()["items"][0]
            await self.mus_play(ctx, f'{get_url(rf)}')
        except IndexError:
            e = discord.Embed(title=get_txt(ctx.guild.id, "yt_no_matches"),
                              description=get_txt(ctx.guild.id, "yt_search_try_again"), color=Error)
            await ctx.reply(embed=e)

    def queue_add(id, u):
        global Queues
        Queues[id][0].append(u)

    def queue_get(id):
        global Queues
        return Queues[id]

    @music.command(name="play", aliases=["p"])
    async def mus_play(self, ctx, url):
        global Queues
        loop = asyncio.get_event_loop()
        v = self.bot.voice_clients
        fq = False
        if isinstance(ctx, dict):
            g = ctx["guild"]
            cn = ctx["channel"]
            au = ctx["author"]
            fq = ctx.get("force_queue", False)

        else:
            g = ctx.guild
            cn = ctx.channel
            au = ctx.author
        voice = False

        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break

        if not voice:
            await self.mus_join(ctx)
            v = self.bot.voice_clients
            for v2 in v:
                if v2.channel.guild.id == g.id:
                    voice = v2
                    break
            if not voice:
                return
        try:
            if url.split("/")[-1].startswith("sm"):
                # s = requests.session()
                async with aiohttp.ClientSession() as s:
                    async with s.post('https://secure.nicovideo.jp/secure/login?site=niconico:443', data={"mail": "sevenbot@outlook.jp", "password": "sevenbot"}) as r:

                        user_session = s.cookie_jar._cookies['nicovideo.jp']["user_session"].value
                    cookies = {
                        'user_session': user_session
                    }
                    params = (
                        ('v', url.split("/")[-1]),
                    )
                    async with s.get('https://flapi.nicovideo.jp/api/getflv', params=params, cookies=cookies) as r:
                        resp = await r.text()
                        if "error" in resp:
                            e = discord.Embed(title=get_txt(g.id, "yt_fail_get"),
                                              description=get_txt(g.id, "yt_fail_get_desc"), color=Error)
                            await cn.send(embed=e)
                            return
                        async with s.get(f'https://ext.nicovideo.jp/api/getthumbinfo/{url.split("/")[-1]}', cookies=cookies) as r:
                            info = dict(xmltodict.parse(await r.text())[
                                        "nicovideo_thumb_response"]["thumb"])

            else:
                info = await loop.run_in_executor(None, partial(ytdl.extract_info, url, download=False, process=False))
                try:
                    info["title"]
                except KeyError:

                    e = discord.Embed(title=get_txt(g.id, "yt_fail_get"),
                                      description=get_txt(g.id, "yt_fail_get_desc"), color=Error)
                    await cn.send(embed=e)
                    return
            Queues[voice.channel.id][0].append([url, au.id])
            c = 0

            if (len(Queues[voice.channel.id][0]) == 1 or c >= len(Queues[voice.channel.id][0])) and not voice.is_playing() and not fq:

                while True:
                    u = Queues[voice.channel.id][0][Queues[voice.channel.id][1]][0]
                    u_req = g.get_member(
                        Queues[voice.channel.id][0][Queues[voice.channel.id][1]][1])
                    if not u_req:
                        u_req = self.bot.get_user(
                            Queues[voice.channel.id][0][Queues[voice.channel.id][1]][1])
                    c += 1
                    Queues[voice.channel.id][1] = c
                    e = discord.Embed(title=get_txt(g.id, "yt_play_wait"),
                                      description=get_txt(g.id, "wait"), color=Process)
                    msg = await cn.send(embed=e)
                    info = await loop.run_in_executor(None, partial(ytdl.extract_info, u, download=False, process=False))
                    ru = ""
                    rf = ""
                    try:
                        info["title"]
                        for f in info['formats']:
                            if len(f["url"]) < len(ru) or rf == "":
                                if f["ext"] == "mp4":
                                    ru = f["url"]
                                    rf = f["ext"]
                                    # unescape(response.text.split("&")[-1])
                    except KeyError:
                        ru = urllib.parse.unquote(
                            resp.split("&")[2][4:])
                        rf = "???"
                    b = 64
                    if self.bot.is_premium(u_req):
                        b = 512
                        pe = discord.Embed(title=get_txt(g.id, "yt_premium"), description=get_txt(
                            g.id, "yt_premium_desc"), color=Premium_color)
                        await cn.send(embed=pe)
                    local_option = ffmpeg_options.copy()
                    vol = (Queues[voice.channel.id][6] - 1) * 30
                    local_option["options"] = f'-vn -af volume={vol}dB'
                    # print(1)
                    # async with aiohttp.ClientSession(headers={'Connection': 'keep-alive'}) as s:
                    #     async with s.get() as r:
                    #         print(r.status)
                    #         tio = io.BytesIO(await r.read())
                    #         print(3)
                    # print(2)
                    # msg = (await self.bot.get_channel(765528694500360212).send(file=discord.File(tio,filename="temp"))).attachments[0].url
                    # print(msg)
                    voice.play(discord.FFmpegOpusAudio(
                        unescape(ru), bitrate=b, stderr=sys.stdout, **local_option))

                    if url.split("/")[-1].startswith("sm"):
                        async with aiohttp.ClientSession() as s:
                            async with s.get(f'https://ext.nicovideo.jp/api/getthumbinfo/{url.split("/")[-1]}', cookies=cookies) as r:
                                info = dict(xmltodict.parse(await r.text())[
                                            "nicovideo_thumb_response"]["thumb"])
                        rf = info["movie_type"]
                        ls = info["length"].split(":")
                        info["duration"] = int(ls[0]) * 60 + int(ls[1])
                        e = discord.Embed(title=f"`{info['title']}`" + get_txt(g.id, "yt_played"), url=f"http://nico.ms/{info['video_id']}", description="\n".join(
                            info.get("description", get_txt(g.id, "no_desc")).split("\n")[:8]), color=Success)
                        e.set_thumbnail(url=info["thumbnail_url"])
                    else:
                        e = discord.Embed(title=f"`{info['title']}`" + get_txt(g.id, "yt_played"), url=get_url(info), description="\n".join(
                            info.get("description", get_txt(g.id, "no_desc")).split("\n")[:8]), color=Success)
                        e.set_thumbnail(url=info["thumbnails"][-1]["url"])
                    e.set_author(
                        name=f"{u_req.display_name}(ID:{u_req.id})", icon_url=u_req.avatar_url_as(static_format="png"))
                    e.set_footer(text=get_txt(g.id, "yt_footer").format(
                        c, len(Queues[voice.channel.id][0]), rf))
                    loop.create_task(msg.edit(embed=e))
                    loop.create_task(msg.add_reaction(Official_emojis["add"]))
                    tdt = datetime.datetime.utcnow()
                    tdt += datetime.timedelta(seconds=info["duration"])
                    while True:
                        dt = datetime.datetime.utcnow()
                        if dt > tdt or Queues[voice.channel.id][2] or Queues[voice.channel.id][5]:
                            Queues[voice.channel.id][2] = False
                            break
                        await asyncio.sleep(1)
                        if voice.is_paused():
                            tdt += datetime.timedelta(seconds=1)
                        Queues[voice.channel.id][3] = 1 - \
                            ((tdt - dt).seconds / info["duration"])
                    voice.stop()
                    if c >= len(Queues[voice.channel.id][0]) or Queues[voice.channel.id][5]:
                        if Queues[voice.channel.id][5]:
                            Queues[voice.channel.id][5] = False
                            return
                        elif Queues[voice.channel.id][4]:
                            c = 0
                            Queues[voice.channel.id][1] = 0
                        else:
                            e = discord.Embed(title=get_txt(g.id, "yt_queue_end"),
                                              description=get_txt(g.id, "yt_queue_end_desc"), color=Info)
                            Queues[voice.channel.id][0] = []
                            Queues[voice.channel.id][1] = 0
                            await cn.send(embed=e)
                            return
            else:
                e = discord.Embed(title=f"`{info['title']}`" + get_txt(g.id, "yt_queued"), url=get_url(info), description="\n".join(
                    info.get("description", get_txt(g.id, "no_desc")).split("\n")[:8]), color=Success)
                e.set_author(
                    name=f"{au.display_name}(ID:{au.id})", icon_url=au.avatar_url)
                e.set_footer(text=get_txt(g.id, "yt_queued_footer").format(
                    len(Queues[voice.channel.id][0])))
                e.set_thumbnail(url=info["thumbnails"][-1]["url"])
                msg = await cn.send(embed=e)
                loop.create_task(msg.add_reaction(Official_emojis["add"]))
                return
        except Exception as e:

            Queues[voice.channel.id] = copy.deepcopy(Default_queue)
            raise e

    @music.command(name="queue", aliases=["q"])
    async def mus_queue(self, ctx, past: bool = False):
        global Queues
        v = self.bot.voice_clients
        loop = asyncio.get_event_loop()
        if isinstance(ctx, dict):
            g = ctx["guild"]
            ctx["channel"]
        else:
            g = ctx.guild
            ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        q = Queues[voice.channel.id][0]
        if q == []:
            res = get_txt(g.id, "yt_queue_empty")
            e = discord.Embed(title=Texts[Guild_settings[g.id]["lang"]]
                              ["yt_queue_list"], description=res, color=Success)
            await ctx.reply(embed=e)
        else:
            e = discord.Embed(title=get_txt(g.id, "yt_queue_list"),
                              description=get_txt(g.id, "getting"), color=Process)
            msg = await ctx.reply(embed=e)
            res = ""
            for ei, eq in enumerate(q):
                info = await loop.run_in_executor(None, partial(ytdl.extract_info, eq, download=False, process=False))
                rf = info
                if Queues[voice.channel.id][1] == ei + 1:
                    k = "check5"
                elif Queues[voice.channel.id][1] > ei + 1:
                    k = "check7"
                    if not past:
                        continue
                else:
                    k = "offline"
                res += f'{Official_emojis[k]}```\n{rf["title"]} - {rf["uploader"]} - {get_url(rf)}```\n'
            e = discord.Embed(title=Texts[Guild_settings[g.id]["lang"]]
                              ["yt_queue_list"], description=res, color=Success)
            await msg.edit(embed=e)

    @music.command(name="now", aliases=["info", "np"])
    async def mus_now(self, ctx):
        global Queues
        v = self.bot.voice_clients
        loop = asyncio.get_event_loop()
        if isinstance(ctx, dict):
            g = ctx["guild"]
            ctx["channel"]
        else:
            g = ctx.guild
            ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        q = Queues[voice.channel.id]
        if q == []:
            res = get_txt(g.id, "yt_not_playing")
            e = discord.Embed(title=Texts[Guild_settings[g.id]["lang"]]
                              ["yt_current_song"], description=res, color=Success)
            await ctx.reply(embed=e)
        else:
            eq = Queues[voice.channel.id][0][Queues[voice.channel.id][1] - 1][0]
            e = discord.Embed(title=get_txt(g.id, "yt_current_song"),
                              description=get_txt(g.id, "getting"), color=Process)
            msg = await ctx.reply(embed=e)
            info = await loop.run_in_executor(None, partial(ytdl.extract_info, eq, download=False, process=False))
            rf = info

            e = discord.Embed(
                title=get_txt(g.id, "yt_current_song"), color=Success)
            e.add_field(name=Texts[Guild_settings[g.id]["lang"]]
                        ["yt_now_playing"][0], value=rf["title"])
            e.add_field(name=Texts[Guild_settings[g.id]["lang"]]
                        ["yt_now_playing"][1], value=rf["uploader"])
            e.add_field(name=Texts[Guild_settings[g.id]["lang"]]
                        ["yt_now_playing"][2], value=f'{get_url(rf)}')
            r = str(Official_emojis["barl"])
            p = math.floor(Queues[voice.channel.id][3] * 100)
            for i in range(10):
                if p >= (i * 10 + 10):
                    ae = Official_emojis["barcy210"]
                elif p <= (i * 10):
                    ae = Official_emojis["barc1"]
                else:
                    ae = Official_emojis[f"barcy2{10-abs(p - (i*10+10))}"]
                r += str(ae)
            r += str(Official_emojis["barr"])
            nt = to_lts(rf["duration"] * (p / 100))
            at = to_lts(rf["duration"])
            e.add_field(name=Texts[Guild_settings[g.id]["lang"]]
                        ["yt_now_playing"][3], value=r + f" {nt} / {at}")
            e.set_thumbnail(url=info["thumbnails"][-1]["url"])
            await msg.edit(embed=e)

    @music.command(name="skip", aliases=["next"])
    async def mus_skip(self, ctx):
        global Queues
        v = self.bot.voice_clients
        if isinstance(ctx, dict):
            g = ctx["guild"]
            cn = ctx["channel"]
        else:
            g = ctx.guild
            cn = ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        Queues[voice.channel.id][2] = True
        e = discord.Embed(title=get_txt(g.id, "yt_skip"),
                          description=get_txt(ctx.guild.id, "wait"), color=Success)
        await cn.send(embed=e)

    @music.command(name="volume", aliases=["vol"])
    async def mus_volume(self, ctx, volume: int = None):
        global Queues
        v = self.bot.voice_clients
        if isinstance(ctx, dict):
            g = ctx["guild"]
            cn = ctx["channel"]
        else:
            g = ctx.guild
            cn = ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not volume:
            e = discord.Embed(title=get_txt(g.id, "yt_volume_now").format(
                int(Queues[voice.channel.id][6] * 100)), color=Info)
            await ctx.reply(embed=e)
            return
        if volume <= 0 or volume > 200:
            e = discord.Embed(title=get_txt(
                g.id, "yt_volume_range"), color=Error)
            await ctx.reply(embed=e)
            return
        Queues[voice.channel.id][6] = volume / 100.0
        e = discord.Embed(title=get_txt(g.id, "yt_volume"),
                          description=get_txt(ctx.guild.id, "yt_volume_desc"), color=Success)
        await cn.send(embed=e)

    @music.command(name="delete", aliases=["del", "remove", "rem"])
    async def mus_rem(self, ctx, ind: int):
        global Queues
        v = self.bot.voice_clients
        if isinstance(ctx, dict):
            g = ctx["guild"]
            cn = ctx["channel"]
        else:
            g = ctx.guild
            cn = ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        try:
            Queues[voice.channel.id][0].pop(ind - 1)
            if Queues[voice.channel.id][1] == ind:
                Queues[voice.channel.id][2] = True
            if Queues[voice.channel.id][1] >= ind:
                Queues[voice.channel.id][1] -= 1
            e = discord.Embed(title=get_txt(g.id, "yt_queue_del"), description=Texts[Guild_settings[g.id]
                                                                                     ["lang"]]["yt_queue_del_desc"].format(len(Queues[voice.channel.id][0])), color=Success)
        except IndexError:
            e = discord.Embed(title=get_txt(g.id, "yt_queue_del_fail"),
                              description=get_txt(g.id, "yt_queue_del_fail_desc"), color=Error)

        await cn.send(embed=e)

    @music.command(name="stop")
    async def mus_stop(self, ctx):
        global Queues
        v = self.bot.voice_clients
        if isinstance(ctx, dict):
            g = ctx["guild"]
            cn = ctx["channel"]
        else:
            g = ctx.guild
            cn = ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        Queues[voice.channel.id][2] = True
        e = discord.Embed(title=get_txt(g.id, "yt_stop"),
                          description=get_txt(ctx.guild.id, "wait"), color=Success)
        await cn.send(embed=e)
        Queues[voice.channel.id] = copy.deepcopy(Default_queue)
        Queues[voice.channel.id][5] = True

    @music.command(name="loop")
    async def mus_loop(self, ctx):
        global Queues
        v = self.bot.voice_clients
        if isinstance(ctx, dict):
            g = ctx["guild"]
            cn = ctx["channel"]
        else:
            g = ctx.guild
            cn = ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        Queues[voice.channel.id][4] = not Queues[voice.channel.id][4]
        if Queues[voice.channel.id][4]:
            e = discord.Embed(title=get_txt(g.id, "yt_loop_activate"),
                              description=get_txt(g.id, "yt_loop_activate_desc"), color=Success)
        else:
            e = discord.Embed(title=get_txt(g.id, "yt_loop_deactivate"),
                              description=get_txt(g.id, "yt_loop_deactivate_desc"), color=Success)

        await cn.send(embed=e)

    @music.command(name="pause")
    async def mus_pause(self, ctx):
        global Queues
        v = self.bot.voice_clients
        if isinstance(ctx, dict):
            g = ctx["guild"]
            cn = ctx["channel"]
        else:
            g = ctx.guild
            cn = ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return
        if not voice.is_paused():
            ym = get_txt(g.id, "yt_pause_activate")
            voice.pause()
        else:
            ym = get_txt(g.id, "yt_pause_deactivate")
            voice.resume()
        e = discord.Embed(
            title=ym, description=get_txt(g.id, "yt_pause_desc"), color=Success)
        await cn.send(embed=e)

    @music.command(name="leave", aliases=["disconnect", "dc", "kick"])
    async def mus_leave(self, ctx):
        v = self.bot.voice_clients
        if isinstance(ctx, dict):
            g = ctx["guild"]
            ctx["channel"]
        else:
            g = ctx.guild
            ctx.channel
        voice = False
        for v2 in v:
            if v2.channel.guild.id == g.id:
                voice = v2
                break
        if not voice:
            e = discord.Embed(title=get_txt(g.id, "yt_not_connect"),
                              description=get_txt(g.id, "yt_not_connect2"), color=Error)
            await ctx.reply(embed=e)
            return

        channel = voice.channel
        print("ボイチャ退出：" + channel.guild.name + " - " + channel.name)
        try:
            Queues[voice.channel.id][5] = True
        except KeyError:
            pass
        await voice.disconnect()
        e = discord.Embed(title=get_txt(g.id, "yt_disconnect").format(
            channel.name), description=get_txt(g.id, "yt_reconnect"), color=Success)
        await ctx.reply(embed=e)


def setup(_bot):
    global bot, Queues
    bot = _bot
    Queues = _bot.consts["qu"]
#     logging.info("cog.py reloaded")
    _bot.add_cog(MusicCog(_bot))
