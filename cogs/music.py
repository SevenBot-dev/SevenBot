import asyncio
import copy
import datetime
import math
import sys
import time
from functools import partial
from html import unescape

import discord
from googleapiclient.discovery import build
from sembed import SEmbed  # type:ignore
import youtube_dl
from discord import Forbidden
from discord.ext import commands, components

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
        global Guild_settings, Official_emojis, Number_emojis, Texts
        global get_txt
        self.bot: commands.Bot = bot
        Guild_settings = bot.guild_settings
        Official_emojis = bot.consts["oe"]
        Texts = bot.texts
        get_txt = bot.get_txt
        for i in range(11):
            Number_emojis.append(Official_emojis["b" + str(i)])

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
#                             ic(await m.remove_reaction)(r.emoji, u)
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
#                 ic(await m.remove_reaction)(r.emoji, u)
#         except asyncio.TimeoutError:
#             await m.clear_reactions()
#             e = discord.Embed(title=get_txt(gu.id,"yt_search_result"),
#                   description=get_txt(gu.id,"canceled"), color=Success)
#             await m.edit(embed=e)

    def make_favorite_description(self, musics):
        r = ""
        for i, music in enumerate(musics):
            r += f'{Number_emojis[i + 1]}: [{music["title"]} - {music["uploader"]}]({music["url"]})\n'

        return r

    async def get_music_info(self, url):
        loop = asyncio.get_event_loop()
        try:
            info = await loop.run_in_executor(None, partial(ytdl.extract_info, url, download=False, process=False))
            info["url"] = url
            info["time"] = time.time() + 60 * 60 * 24 * 7
            return info
        except youtube_dl.DownloadError as e:
            raise e

    @music.command(name="favorite", aliases=["fav"])
    async def mus_favorite(self, ctx):
        favs = await self.bot.db.user_settings.find_one({"uid": ctx.author.id})
        if favs is None:
            e = discord.Embed(title=get_txt(ctx.guild.id, "yt_no_fav"),
                              description=get_txt(ctx.guild.id, "yt_no_fav_desc").format(Official_emojis["add"]), color=Error)
            msg = await ctx.reply(embed=e)
            return
        res = favs["favorite_musics"]

        cn = ctx.channel
        loop = asyncio.get_event_loop()
        e = discord.Embed(title=get_txt(ctx.guild.id, "getting"),
                          description=get_txt(ctx.guild.id, "wait"), color=Process)
        buttons = [
            [
                components.Button("前のページ", custom_id="favorite_prev", style=components.ButtonType.gray),
                components.Button("次のページ", custom_id="favorite_next", style=components.ButtonType.gray)
            ],
            [
                components.Button("再生", custom_id="favorite_play", style=components.ButtonType.blurple),
                components.Button("削除", custom_id="favorite_delete", style=components.ButtonType.green),
                components.Button("キャンセル", custom_id="favorite_cancel", style=components.ButtonType.danger)
            ]
        ]
        msg = await components.send(cn, embed=e, components=buttons)
        ga = []
        for nm in Number_emojis[1:(len(res) + 1 if len(res) + 1 < 10 else 11)]:
            loop.create_task(msg.add_reaction(nm))

        ga = []
        for rf in res:
            ga.append(self.get_music_info(rf))
        music_infos = await asyncio.gather(*ga)
#             r += f'{Number_emojis[i+1]}:```\n{unescape(f["title"])} - {unescape(f["uploader"])} - {get_url(rf)}```\n'
        e = SEmbed(
            title=Texts[Guild_settings[ctx.guild.id]["lang"]]["favorite"],
            description=self.make_favorite_description(music_infos[:10]),
            footer=f'{get_txt(ctx.guild.id,"page")} 1/{math.ceil(len(res)/10)}',
            color=Process)
        page = 0
        await msg.edit(embed=e)
        try:
            while True:
                com = await self.bot.wait_for("button_click", check=lambda com: com.message == msg)
                if com.custom_id in ("favorite_prev", "favorite_next"):
                    await com.defer_update()
                    page += -1 if com.custom_id == "favorite_prev" else 1
                    page %= math.ceil(len(res) / 10)
                    e.description = self.make_favorite_description(music_infos[(page * 10):(page * 10 + 10)])
                    e.footer.text = f'{get_txt(ctx.guild.id,"page")} {page + 1}/{math.ceil(len(res)/10)}'
                    await msg.edit(embed=e)
                elif com.custom_id in ("favorite_play", "favorite_delete"):
                    if com.custom_id == "favorite_play":
                        await com.defer_update()
                    else:
                        await com.defer_source()
                    for b in buttons:
                        for bu in b:
                            bu.enabled = False
                    await components.edit(msg, components=buttons)
                    numbers = []
                    msg = await msg.channel.fetch_message(msg.id)
                    for mi, mr in enumerate(msg.reactions):
                        if mr.emoji in Number_emojis:
                            if mr.count == 2:
                                numbers.append(mi)
                    deletes = set()
                    await msg.clear_reactions()
                    for i, number in enumerate(numbers):
                        url = res[page * 10 + number]
                        if com.custom_id == "favorite_play":
                            await self.mus_play({"message": com, "channel": ctx.channel, "guild": ctx.guild, "author": ctx.author, "force_queue": i > 0}, url)
                        else:
                            deletes.add(url)
                    if com.custom_id == "favorite_delete":
                        await self.bot.db.user_settings.update_one({"uid": ctx.author.id}, {"$set": {"favorite_musics": [mus for mus in res if mus not in deletes]}})
                        await com.send("削除しました。")
                    return
                elif com.custom_id == "favorite_cancel":
                    await com.defer_update()
                    break

        except asyncio.TimeoutError:
            pass
        for b in buttons:
            for bu in b:
                bu.enabled = False
        await components.edit(msg, components=buttons)
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

    async def wait_favorite_add(self, msg, button, user, url):
        button.enabled = False
        try:
            com = await self.bot.wait_for("button_click", check=lambda com: com.message == msg)
        except asyncio.TimeoutError:
            pass
        else:
            await com.defer_source(hidden=True)
            await components.edit(msg, components=[button])
            us = await self.bot.db.user_settings.find_one({"uid": user.id})
            if us is None:
                await self.bot.init_user_settings(user.id)
                us = await self.bot.db.user_settings.find_one({"uid": user.id})
            us["favorite_musics"].append(url)
            await self.bot.db.user_settings.update_one({"uid": user.id}, {"$set": {"favorite_musics": us["favorite_musics"]}})
            await com.send("お気に入りに追加しました。")
            return
        await components.edit(msg, components=[button])

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
            info = await self.get_music_info(url)
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
                    add_fav_component = components.Button("お気に入りに追加", "music_add_favorite", style=components.ButtonType.blurple, enabled=False)
                    msg = await components.send(cn, embed=e, components=[add_fav_component])
                    info = await self.get_music_info(u)
                    ru = ""
                    rf = ""
                    info["title"]
                    for f in info['formats']:
                        if len(f["url"]) < len(ru) or rf == "":
                            if f["ext"] == "mp4":
                                ru = f["url"]
                                rf = f["ext"]
                                # unescape(response.text.split("&")[-1])
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
                    e = discord.Embed(title=f"`{info['title']}`" + get_txt(g.id, "yt_played"), url=get_url(info), description="\n".join(
                        info.get("description", get_txt(g.id, "no_desc")).split("\n")[:8]), color=Success)
                    e.set_thumbnail(url=info["thumbnails"][-1]["url"])
                    e.set_author(
                        name=f"{u_req.display_name}(ID:{u_req.id})", icon_url=u_req.avatar.url)
                    e.set_footer(text=get_txt(g.id, "yt_footer").format(
                        c, len(Queues[voice.channel.id][0]), rf))
                    add_fav_component.enabled = True
                    loop.create_task(components.edit(msg, embed=e, components=[add_fav_component]))
                    loop.create_task(self.wait_favorite_add(msg, add_fav_component, au, u))
                    tdt = discord.utils.utcnow()
                    tdt += datetime.timedelta(seconds=info["duration"])
                    while True:
                        dt = discord.utils.utcnow()
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
                add_fav_component = components.Button("お気に入りに追加", "music_add_favorite", style=components.ButtonType.blurple, enabled=True)
                msg = await components.send(cn, embed=e, components=[add_fav_component])
                loop.create_task(self.wait_favorite_add(msg, add_fav_component, au, url))
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
    _bot.add_cog(MusicCog(_bot), override=True)
