import asyncio
import copy
import hashlib
import io
import re
import sys
import time
import unicodedata

import aiohttp
import discord
from discord.ext import commands
from texttable import Texttable

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (Info, Success, Error, Premium_color)
from common_resources.tools import delay_react_remove


def only_premium():
    async def predicate(ctx):

        res = ctx.bot.is_premium(ctx.author)
        if res:
            return True
        e = discord.Embed(title=get_txt(ctx.guild.id, "premium"), description=get_txt(
            ctx.guild.id, "premium_desc"), color=Premium_color)
        await ctx.reply(embed=e)
        return False
    return commands.check(predicate)


Tts_channels = {}
last_request = 0
Codeblock_re = re.compile(r"```[\s\S]+?```")
Tts_default = {"qu": [], "playing": False,
               "called_channel": 0, "last_speaker": 0}
Emoji_re = re.compile(r"<a?:(.+?):\d+?>")
Url_re = re.compile(r"[ ^]https?://.+?[ $]")
SLASH_PATTERN = re.compile(r"^</.+:\d+>.*$")
DEMO_SHIFTS = {
    5: 3.7,
    6: 3.6,
    7: 3.3
}
ffmpeg_options = {
    'options': '-vn',
    "executable": (r"c:/tools/ffmpeg/bin/ffmpeg.exe" if sys.platform == "win32" else r"ffmpeg"),
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel quiet"
}


class TtsCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Official_emojis, Tts_channels, Tts_settings
        global get_txt
        self.bot: commands.Bot = bot
        Guild_settings = bot.guild_settings
        get_txt = bot.get_txt
        Official_emojis = bot.consts["oe"]
        Tts_channels = bot.consts["tc"]
        Tts_settings = bot.raw_config["ts"]
        self.make_session()

    def make_session(self):
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @commands.group()
    async def tts(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @tts.command(name="join", aliases=["connect", "summon"])
    async def tts_join(self, ctx):
        if ctx.author.voice is None:
            e = discord.Embed(title=get_txt(ctx.guild.id, "tts_vc_none"), description=get_txt(
                ctx.guild.id, "tts_vc_none_desc"), color=Error)
            await ctx.reply(embed=e)
            return
        await ctx.author.voice.channel.connect()
        Tts_channels[ctx.author.voice.channel.id] = copy.deepcopy(Tts_default)
        Tts_channels[ctx.author.voice.channel.id]["called_channel"] = ctx.channel.id
        e = discord.Embed(title=get_txt(ctx.guild.id, "tts_joined").format(
            ctx.author.voice.channel.name), color=Success)
        await ctx.reply(embed=e)

    @commands.Cog.listener(name="on_message")
    async def on_message(self, message):
        # print("an")
        if message.author.bot:
            return
        elif not message.guild:

            return
        elif not message.content:
            return
        elif not message.author.voice:
            # print("av")
            return
        # elif not message.author.voice.channel:
        #     return
        elif not message.guild.voice_client:
            # print("vc")
            return
        #
        elif message.author.voice.channel.id not in Tts_channels.keys():
            return
        elif message.content.startswith(tuple(await self.bot.get_prefix(message))):
            # print("pr")
            return
        # elif not message.author.voice.channel.id == message.guild.voice_client.channel.id:
        #     return
        elif not message.channel.id == Tts_channels[message.author.voice.channel.id]["called_channel"]:
            return
        elif SLASH_PATTERN.match(message.content):
            return
        elif unicodedata.category(message.content[0])[0] in "PS":
            return
        # print("av")
        if self.session.closed:
            self.make_session()
        flag = False
        # loop = asyncio.get_event_loop()
        if Tts_channels[message.guild.voice_client.channel.id].get("last_speaker", 0) != message.author.id:
            flag = True
        Tts_channels[message.guild.voice_client.channel.id]["last_speaker"] = message.author.id
        txt = ""
        if flag:
            txt += message.author.display_name + "  "
        txt += message.clean_content
        await self.play_voice(txt, message)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            if not member.guild.voice_client:
                return
            elif member.id == self.bot.user.id:
                return

            if before.channel != after.channel and (after.channel.id in Tts_channels.keys() or before.channel.id in Tts_channels.keys()):
                name = member.display_name
                if f"<@{member.id}>" in map(lambda m: m.replace("!", ""), Guild_settings[member.guild.id]["tts_dicts"].keys()):
                    name = Guild_settings[member.guild.id]["tts_dicts"].get(f"<@{member.id}>") or Guild_settings[member.guild.id]["tts_dicts"].get(f"<@!{member.id}>")
                if after.channel.id in Tts_channels.keys():
                    txt = get_txt(member.guild.id, "tts_join").format(
                        name, len(after.channel.members))
                elif before.channel.id in Tts_channels.keys():
                    txt = get_txt(member.guild.id, "tts_left").format(
                        name, len(after.channel.members))
                await self.play_voice(txt, {"user": member, "guild": member.guild})
        except discord.errors.ClientException:
            pass

    @commands.Cog.listener("on_voice_state_update")
    async def auto_left(self, member, before, after):
        if before.channel is None:
            return
        elif before.channel.guild.voice_client is None:
            return
        if (not [m for m in before.channel.members if not m.bot]) and before.channel.guild.voice_client.channel == before.channel:
            await before.channel.guild.voice_client.disconnect(force=True)
        delete_list = []
        for t in Tts_channels.keys():
            try:
                if self.bot.user.id not in [m.id for m in self.bot.get_channel(t).members]:
                    delete_list.append(t)
            except KeyError:
                pass
        for d in delete_list:
            del Tts_channels[d]

    @tts.command(name="leave", aliases=["disconnect", "dc", "kick"])
    async def tts_dc(self, ctx):
        if ctx.guild.voice_client is None:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "tts_dc_none"), color=Error)
            await ctx.reply(embed=e)
            return
        ch = ctx.guild.voice_client.channel
        await ctx.guild.voice_client.disconnect()
        del Tts_channels[ch.id]
        e = discord.Embed(title=get_txt(ctx.guild.id, "tts_dc"), color=Success)
        await ctx.reply(embed=e)

    @tts.command(name="voice", aliases=["v"])
    async def tts_change_voice(self, ctx, voice):
        if voice.lower() not in "abcdefgh" or len(voice) != 1:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "tts_voice_fail"), color=Error)
            await ctx.reply(embed=e)
            return
        elif voice.lower() not in "abcd" and not self.bot.is_premium(ctx.author):
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "tts_voice_fail_premium"), color=Premium_color)
            await ctx.reply(embed=e)
            return
        if not Tts_settings.get(ctx.author.id):
            Tts_settings[ctx.author.id] = {}
        Tts_settings[ctx.author.id]["speaker"] = "abcde".index(
            voice.lower())
        e = discord.Embed(title=get_txt(ctx.guild.id, "tts_voice_changed").format(
            voice.upper()), color=Success)
        await ctx.reply(embed=e)

    @tts.command(name="speed", aliases=["spd"])
    @only_premium()
    async def tts_change_speed(self, ctx, speed: int):
        if not 50 <= speed <= 400:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "tts_speed_range"), color=Error)
            await ctx.reply(embed=e)
            return
        if not Tts_settings.get(ctx.author.id):
            Tts_settings[ctx.author.id] = {}
        Tts_settings[ctx.author.id]["speed"] = speed
        e = discord.Embed(title=get_txt(
            ctx.guild.id, "tts_speed_changed").format(speed), color=Success)
        await ctx.reply(embed=e)

    @tts.group(name="dicts", aliases=["d"])
    async def tts_dicts(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @tts_dicts.command(name="add", aliases=["set"])
    # @commands.has_guild_permissions(manage_messages=True)
    async def tts_dicts_add(self, ctx, base, *, reply):
        global Guild_settings
        dat = base + reply
        rid = hashlib.md5(dat.encode()).hexdigest()[0:8]
        Guild_settings[ctx.guild.id]["tts_dicts"][rid] = [base, reply]
        e = discord.Embed(title=get_txt(ctx.guild.id, "tts_dicts_add"),
                          description=get_txt(ctx.guild.id, "tts_dicts_add_desc").format(base, rid), color=Success)
        await ctx.reply(embed=e)

    @tts_dicts.command(name="remove", aliases=["del", "delete", "rem"])
    # @commands.has_guild_permissions(manage_messages=True)
    async def tts_dicts_remove(self, ctx, *, txt):
        global Guild_settings
        res = ""
        count = 0
        new = {}
        if txt in Guild_settings[ctx.guild.id]["tts_dicts"].keys():
            res += "`" + \
                Guild_settings[ctx.guild.id]["tts_dicts"][txt][1] + "`\n"
            for ark, ar in Guild_settings[ctx.guild.id]["tts_dicts"].items():
                if ark != txt:
                    new[ark] = ar
            count = 1
        else:
            for ark, ar in Guild_settings[ctx.guild.id]["tts_dicts"].items():
                if ar[0] == txt:
                    count += 1
                    res += "`" + ar[1] + "`\n"
                else:
                    new[ark] = ar
        if count == 0:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "tts_dicts_rem_fail").format(txt), description=get_txt(ctx.guild.id, "tts_dicts_rem_fail_desc"), color=Error)
        else:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "tts_dicts_rem_success").format(count), description=res, color=Success)
            Guild_settings[ctx.guild.id]["tts_dicts"] = new
        await ctx.reply(embed=e)

    @tts_dicts.command(name="list")
    async def tts_dicts_list(self, ctx):
        g = ctx.guild.id
        gs = Guild_settings[g]
        if gs["tts_dicts"] == {}:
            e = discord.Embed(
                title="登録されていません。", description="`sb#tts dicts add`で登録してください。", color=Error)
            await ctx.reply(embed=e)
        else:

            table = Texttable()
            table.set_deco(Texttable.HEADER)
            table.set_cols_dtype(['t', 't', 't'])
            table.set_cols_align(["l", "l", "l"])
            res = [["ID", "置換元", "置換先"]]
            for k, v in gs["tts_dicts"].items():
                res.append([k, v[0].replace("\n", "[改行]"),
                            v[1].replace("\n", "[改行]")])
            table.add_rows(res)
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "tts_dicts_list"), description=f"```asciidoc\n{table.draw()}```", color=Info)
            await ctx.reply(embed=e)

    async def play_voice(self, txt, message):
        loop = asyncio.get_event_loop()
        txt = Emoji_re.sub(r":\1:", txt)
        txt = Codeblock_re.sub("", txt)
        txt = Url_re.sub("[URL]", txt)
        txt = txt.lower()
        if isinstance(message, discord.Message):
            message = message
            user = message.author
            guild = message.guild
        else:
            user = message["user"]
            guild = message["guild"]
            message = None

        for _, dv in Guild_settings[message.guild.id]["tts_dicts"].items():
            txt = txt.replace(dv[0].lower(), dv[1].lower())

        ts = Tts_settings.get(user.id, {})
        global last_request
        if last_request - time.time() < 2:
            await asyncio.sleep(last_request - time.time())
        last_request = time.time()
        if ts.get("speaker", user.id % 4) in (0, 1, 2, 3, 4):
            if sys.platform == "win32":
                open_jtalk = [r'E:\open_jtalk-1.11\bin\open_jtalk.exe']
                mech = ['-x', r'E:\open_jtalk-1.11\bin\dic']
                outwav = ['-ow', 'CON']
            else:
                open_jtalk = [r'~/bin/open-jtalk/bin/open_jtalk']
                mech = ['-x', r'~/bin/open-jtalk/dic']
                outwav = ['-ow', '/dev/stdout']
            htsvoice = [
                '-m', f'./htsvoices/{ts.get("speaker", user.id % 4)}.htsvoice']
            speed = ['-r', str(ts.get("speed", 100) / 100.0)]
            cmd = open_jtalk + mech + htsvoice + speed + outwav
            # await message.channel.send(" ".join(cmd))
            loop.create_task(message.add_reaction(
                Official_emojis["network"]))
            c = await asyncio.create_subprocess_shell((" ".join(cmd)).encode(), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
            try:
                stdout, _ = await c.communicate((txt.replace("\n", " ")[:30] + "\n").encode("utf8"))
            except asyncio.TimeoutError:
                c.terminate()
            loop.create_task(message.remove_reaction(Official_emojis["network"], message.guild.me))
            # await c.wait()
            # await message.reply((await c.stderr.read()).decode())
            bio = io.BytesIO(stdout)
            bio.seek(0)
            msg = (await (self.bot.get_channel(765528694500360212)).send(file=discord.File(bio, filename="tmp.wav")))
            bio.close()
        Tts_channels[guild.voice_client.channel.id]["qu"].append(
            (message, msg))
        if not Tts_channels[guild.voice_client.channel.id]["playing"]:

            try:
                Tts_channels[guild.voice_client.channel.id]["playing"] = True

                while Tts_channels[guild.voice_client.channel.id]["qu"]:
                    rm, msg = Tts_channels[guild.voice_client.channel.id]["qu"].pop(
                        0)
                    if message:
                        loop.create_task(rm.add_reaction(
                            Official_emojis["voice"]))
                        loop.create_task(rm.remove_reaction(
                            Official_emojis["queue"], self.bot.user))
    #                     txt=q.clean_content

    #                     params = {"text":txt[:49],"speaker":"hikari","format":"mp3"}
    #                     async with self.session.post('https://api.voicetext.jp/v1/tts',params=params) as response:
    #                         txt=Emoji_re.sub(r":\1:",txt)
    #                         bio=io.BytesIO(await response.read())
    #                         bio.seek(0)
    #                         guild.voice_client.play(discord.FFmpegOpusAudio(
    #                         bio, pipe=True,**ffmpeg_options))
    #                         bio.close()
    #
                    guild.voice_client.play(discord.FFmpegOpusAudio(
                        msg.attachments[0].url, **ffmpeg_options))
                    while guild.voice_client.is_playing():
                        await asyncio.sleep(0.1)
                    if message:
                        loop.create_task(rm.remove_reaction(
                            Official_emojis["voice"], self.bot.user))
                        loop.create_task(rm.add_reaction(
                            Official_emojis["check8"]))
                        # loop.create_task(msg.delete())
                        loop.create_task(delay_react_remove(
                            rm, Official_emojis["check8"], self.bot.user, 3))

                Tts_channels[guild.voice_client.channel.id]["playing"] = False
            except Exception as e:
                Tts_channels[guild.voice_client.channel.id]["qu"] = []
                Tts_channels[guild.voice_client.channel.id]["playing"] = False
                raise e
        else:
            await message.add_reaction(Official_emojis["queue"])


def setup(_bot):
    global bot
    bot = _bot
#     logging.info("cog.py reloaded")
    _bot.add_cog(TtsCog(_bot))
