import asyncio
import base64
import datetime
import hashlib
import hmac
import io
import json
import random
import re
import string
import unicodedata

import aiohttp
import bs4
import discord
from authlib.integrations.base_client import errors as authlib_err
from authlib.integrations.httpx_client.oauth1_client import AsyncOAuth1Client
from discord.ext import commands, tasks
from sembed import SEmbed

import _pathmagic  # type: ignore # noqa: F401
from common_resources.consts import (Deactivate_aliases, Info, Process, Success)
from common_resources.tools import flatten
from common_resources.tokens import (twitter_consumer_key, twitter_consumer_secret)


def hmac_sha1(input_str, key):
    raw = input_str.encode("utf-8")
    key = key.encode('utf-8')
    hashed = hmac.new(key, raw, hashlib.sha1)
    return base64.encodebytes(hashed.digest()).decode('utf-8')


def gen_random_str(num):
    dat = string.digits + string.ascii_lowercase + string.ascii_uppercase
    return ''.join([random.choice(dat) for i in range(num)])


Batch = {}
Python_color = 0x35669a
DJS_COLOR = 0x33b5e5
Message_url_re = re.compile(
    r"https?://(?:(?:ptb|canary)\.)?(?:discord(?:app)?\.com)/channels/(\d+)/(\d+)/(\d+)")


class ToolCog(commands.Cog):
    def __init__(self, _bot):
        global Guild_settings, Official_emojis, Texts, Global_chat, Private_chats, get_txt, Sevennet_channels

        self.bot = _bot
        Guild_settings = self.bot.raw_config["gs"]
        get_txt = self.bot.get_txt
        Texts = self.bot.texts
        Official_emojis = self.bot.consts["oe"]
        Global_chat = self.bot.raw_config["gc"]
        Private_chats = self.bot.raw_config["pc"]
        Sevennet_channels = self.bot.raw_config["snc"]
        Batch["sync_afk"] = self.sync_afk.start()
        if "afk" not in self.bot.consts.keys():
            self.bot.consts["afk"] = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id in Sevennet_channels or message.channel.id in Global_chat or message.channel.id in flatten(list(Private_chats.values())) or message.channel.is_news():
            return
        asyncio.get_event_loop()
        js = self.bot.consts["afk"]
        msgs = []
        if [j for j in js if j["uid"] == message.author.id]:

            await self.bot.db.afks.delete_one({"uid": message.author.id})
            d = Texts[Guild_settings[message.guild.id]["lang"]
                      ]["afk_off_desc"].format(len([j for j in js if j["uid"] == message.author.id][0]["urls"]))
            a = [j for j in js if j["uid"] == message.author.id][0]
            for ac in a["urls"]:
                rids = re.match(Message_url_re, ac)
                ids = [int(i) for i in [rids[2], rids[3], rids[4]]]
                c = self.bot.get_channel(ids[1])
                t_txt = Texts[Guild_settings[message.guild.id]
                              ["lang"]]["afk_off"]
                if c is None:
                    tt = "\n" + \
                        Texts[Guild_settings[message.guild.id]
                              ["lang"]]["afk_off_unknown"]
                    if len(d) + len(tt) > 2048:
                        e = discord.Embed(
                            title=t_txt, description=d, color=Info)
                        t_txt = ""
                        msgs.append(await message.reply(embed=e))
                        d = ""

                    d += tt
                try:
                    tt = f"\n[{c.guild.name} - #{c.name}]({ac})"
                    if len(d) + len(tt) > 2048:
                        e = discord.Embed(
                            title=t_txt, description=d, color=Info)
                        t_txt = ""
                        msgs.append(await message.reply(embed=e))
                        d = ""
                    d += tt

                except Exception:
                    pass

            e = discord.Embed(
                title=get_txt(message.guild.id, "afk_off"), description=d, color=Info)
            if len([j for j in js if j["uid"] == message.author.id][0]["urls"]) == 0:
                e.set_footer(text=get_txt(message.guild.id, "message_delete").format(5))
            msgs.append(await message.reply(embed=e))
            if len([j for j in js if j["uid"] == message.author.id][0]["urls"]) == 0:
                for m in msgs:
                    await m.delete(delay=5)

            self.bot.consts["afk"] = list(filter(lambda a: a["uid"] != message.author.id, self.bot.consts["afk"]))
            # ----Twitter----
            t = await self.bot.db.twitter_keys.find_one({"uid": message.author.id})
            t2 = await self.bot.db.afk_twitter_text.find_one({"uid": message.author.id})
            if t is not None:
                txt = t2["deactivate"].replace("!user", "@" + t["name"])
                client = AsyncOAuth1Client(twitter_consumer_key, twitter_consumer_secret, t["token"], t["secret"])
                await client.post("https://api.twitter.com/1.1/statuses/update.json", params={"status": txt})
                await client.aclose()
                # print(res.status, res.text)

        else:
            for m in message.mentions:

                if [j for j in js if j["uid"] == m.id]:

                    j = [j for j in js if j["uid"] == m.id][0]

                    # print(0)
                    j["urls"].append(message.jump_url)
                    # print(1)
                    await self.bot.db.afks.replace_one({"uid": j["uid"]}, j)
                    if j["reason"]:
                        d = "**" + Texts[Guild_settings[message.guild.id]
                                         ["lang"]]["afk_reason"] + "**\n" + j["reason"].encode().decode("utf-8")
                    else:
                        d = Texts[Guild_settings[message.guild.id]
                                  ["lang"]]["afk_reason_none"]
                    # print(2)
                    e = discord.Embed(
                        title=get_txt(message.guild.id, "afk_title").format(m.display_name), description=d, color=Info)
                    e.set_footer(
                        text=get_txt(message.guild.id, "message_delete").format(5))
                    # print(3)
                    msg = await message.reply(embed=e)
                    await msg.delete(delay=5)

    @commands.group(name="afk", invoke_without_command=True)
    async def _afk(self, ctx, *, reason=None):
        await self.bot.db.afks.insert_one({"uid": ctx.author.id, "reason": reason, "urls": []})
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "afk_register"),
            description=get_txt(ctx.guild.id, "afk_register_desc"), color=Success)
        await ctx.send(embed=e)
        self.bot.consts["afk"].append({"uid": ctx.author.id, "reason": reason, "urls": []})

        # ----Twitter----
        t = await self.bot.db.twitter_keys.find_one({"uid": ctx.author.id})
        texts = await self.bot.db.afk_twitter_text.find_one({"uid": ctx.author.id})
        if t is not None:
            txt = texts["activate"].replace("!reason", (reason or get_txt(ctx.guild.id, "afk_reason_none"))).replace("!user", "@" + t["name"])
            client = AsyncOAuth1Client(twitter_consumer_key, twitter_consumer_secret, t["token"], t["secret"])
            await client.post("https://api.twitter.com/1.1/statuses/update.json", params={"status": txt})

    @_afk.command(name="key", aliases=["api", "apikey"])
    async def afk_key(self, ctx):
        await self.bot.db.afk_keys.delete_one({"uid": ctx.author.id, "oauth": False})
        key = gen_random_str(16)
        await self.bot.db.afk_keys.insert_one({"uid": ctx.author.id, "hash": key, "oauth": False})
        await ctx.author.send(get_txt(ctx.guild.id, "afk_api").replace("!key", key).replace("!userid", str(ctx.author.id)))
        await ctx.message.add_reaction(Official_emojis["check8"])

    @_afk.group(name="twitter", invoke_without_command=True)
    @commands.cooldown(60, 60, commands.BucketType.default)
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def afk_twitter(self, ctx):
        client = AsyncOAuth1Client(twitter_consumer_key, twitter_consumer_secret, redirect_uri="oob")
        await ctx.message.add_reaction(Official_emojis["check8"])
        token = await client.fetch_request_token('https://api.twitter.com/oauth/request_token')
        # await ctx.author.send(token)
        url = "https://api.twitter.com/oauth/authorize?oauth_token=" + token["oauth_token"]
        msg = await ctx.author.send(url + "\n" + get_txt(ctx.guild.id, "afk_twitter"))
        try:
            pin = await self.bot.wait_for("message", check=lambda m: m.author.id == ctx.author.id and m.channel.id == msg.channel.id, timeout=60)
            try:
                t = await client.fetch_access_token('https://api.twitter.com/oauth/access_token', verifier=pin.content)
                await self.bot.db.twitter_keys.delete_one({"uid": ctx.author.id})
                await self.bot.db.twitter_keys.insert_one({"uid": ctx.author.id,
                                                           "token": t["oauth_token"],
                                                           "secret": t["oauth_token_secret"],
                                                           "twiid": t["user_id"],
                                                           "name": t["screen_name"]
                                                           })
                await self.bot.db.afk_twitter_text.delete_one({"uid": ctx.author.id})
                await self.bot.db.afk_twitter_text.insert_one({"uid": ctx.author.id, "activate": get_txt(ctx.guild.id, "afk_twitter_content"),
                                                               "deactivate": get_txt(ctx.guild.id, "afk_twitter_content2")})
                await ctx.author.send(get_txt(ctx.guild.id, "afk_twitter_success").format(t["screen_name"]))
            except authlib_err.OAuthError:
                await ctx.author.send(get_txt(ctx.guild.id, "afk_twitter_fail"))
        except asyncio.TimeoutError:
            await ctx.author.send(get_txt(ctx.guild.id, "timeout"))

    @afk_twitter.command(name="deactivate", aliases=Deactivate_aliases)
    async def afk_twitter_off(self, ctx):
        await self.bot.db.twitter_keys.delete_one({"uid": ctx.author.id})
        await ctx.send(embed=discord.Embed(title=get_txt(ctx.guild.id, "afk_twitter_off"), color=Success))
#     @_afk.command(name="list",aliases=["l"])
#     async def afk_list(self, ctx):
#         pass

    @commands.command(aliases=["el"])
    async def emoji_list(self, ctx):
        l = [[]]
        for e in ctx.guild.emojis:

            l[-1].append(e)
            if len(l[-1]) >= 20:
                l.append([])
        loop = asyncio.get_event_loop()
        for li in l:
            if li:
                m = await ctx.reply("".join(map(str, li)))
                for e in li:
                    loop.create_task(m.add_reaction(e))

    @commands.command(aliases=["sh"])
    async def shorten(self, ctx, url, shortid=None):
        async with aiohttp.ClientSession() as session:
            async with session.post('https://7bot.ml/api', json=({"url": url, "shortId": shortid} if shortid else {"url": url})) as r:
                r.raise_for_status()
                e = discord.Embed(title=get_txt(ctx.guild.id, "short_ok"), description=(await r.json())["url"], color=Success)
                msg = await ctx.send(embed=e)
                await msg.add_reaction(Official_emojis["down"])
                try:
                    _ = await self.bot.wait_for("reaction_add", check=lambda r, u: r.message.id == msg.id and r.emoji == Official_emojis["down"] and not u.bot, timeout=30)
                    await msg.edit(content=get_txt(ctx.guild.id, "short_ok") + "\n" + msg.embeds[0].description, embed=None)
                    try:
                        await msg.clear_reaction(Official_emojis["down"])
                    except discord.errors.Forbidden:
                        await msg.remove_reaction(Official_emojis["down"], self.bot.user)
                except asyncio.TimeoutError:
                    await msg.remove_reaction(Official_emojis["down"], self.bot.user)

    @tasks.loop(minutes=10)
    async def sync_afk(self):
        tl = []
        async for t in self.bot.db.afks.find():
            tl.append(t)
        self.bot.consts["afk"] = tl.copy()

    @commands.command()
    @commands.is_owner()
    async def reload_doc(self, ctx):
        global Dpy_classes, Dpy_attrs, Dpy_methods
        global Djs_classes, Djs_attrs, Djs_methods
        urls = [
            "https://discordpy.readthedocs.io/en/latest/api.html",
            "https://discordpy.readthedocs.io/en/latest/ext/commands/api.html",
            "https://discordpy.readthedocs.io/en/latest/ext/tasks/api.html"
        ]

        classes = []
        methods = []
        attrs = []

        async with aiohttp.ClientSession() as s:
            for url in urls:
                async with s.get(url) as r:
                    text = await r.read()

                bs = bs4.BeautifulSoup(text.decode('utf-8'))
                raw_attrs = bs.select('dt:not(.field-odd):not(.field-even)')
                classes.extend(map(lambda n: n["id"].replace("discord.discord.", "discord.").replace("discord.ext.", ""), filter(lambda n: "class" in n.parent.get("class", []), raw_attrs)))
                methods.extend(map(lambda n: n["id"].replace("discord.discord.", "discord.").replace("discord.ext.", ""), filter(lambda n: "method" in n.parent.get("class", []), raw_attrs)))
                attrs.extend(map(lambda n: n["id"].replace("discord.discord.", "discord.").replace("discord.ext.", ""), filter(lambda n: "attribute" in n.parent.get("class", []), raw_attrs)))
        with open("./dpy_docs/classes.txt", "w") as f:
            f.write("\n".join(classes))
        Dpy_classes = classes.copy()

        with open("./dpy_docs/methods.txt", "w") as f:
            f.write("\n".join(methods))
        Dpy_methods = methods.copy()

        with open("./dpy_docs/attrs.txt", "w") as f:
            f.write("\n".join(attrs))
        Dpy_attrs = attrs.copy()
        await ctx.send("d.py done")

        async with aiohttp.ClientSession() as s:
            async with s.get("https://raw.githubusercontent.com/discordjs/discord.js/docs/master.json") as r:
                j = json.loads(await r.text())
        c = j["classes"]
        classes = []
        methods = []
        attrs = []
        for cl in c:
            classes.append(cl["name"])
            print(cl.keys())
            methods.extend(cl["name"] + "." + mt["name"] for mt in cl.get("methods", []) if mt.get("access") != "private")
            attrs.extend(cl["name"] + "." + mt["name"] for mt in cl.get("props", []) if mt.get("access") != "private")
        with open("./djs_docs/classes.txt", "w") as f:
            f.write("\n".join(classes))
        Djs_classes = classes.copy()

        with open("./djs_docs/methods.txt", "w") as f:
            f.write("\n".join(methods))
        Djs_methods = methods.copy()

        with open("./djs_docs/attrs.txt", "w") as f:
            f.write("\n".join(attrs))
        Djs_attrs = attrs.copy()
        await ctx.send("d.js done")

    @commands.group(name="develop_tool", aliases=["dev", "develop"])
    async def develop_tool(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @develop_tool.command(name="chr_info", aliases=["c"])
    async def develop_chr_info(self, ctx, *, _chr):
        res = ""
        for c in list(_chr):
            if not c:
                continue
            try:
                res += f"`{c}` : `{hex(ord(c))}` `\\U{hex(ord(c))[2:].zfill(8)}` - `{unicodedata.name(c)}`\n"
            except ValueError:
                res += f"`{c}` : unknown\n"

        await ctx.send(res)

    @develop_tool.group(name="rtfm", aliases=["rtfd"], invoke_without_command=True)
    async def rtfm(self, ctx):
        await self.bot.send_subcommands(ctx)

    @rtfm.command("dpy")
    async def rtfm_dpy(self, ctx, *, text):
        query = text.replace("ctx", "Context")
        cres = ""
        res = ""
        pres = ""
        base_url = get_txt(ctx.guild.id, "dpy_docs")
        lower_classes = [da.lower() for da in Dpy_classes]
        for di, tda in enumerate(lower_classes):
            if query.lower() in tda:
                da = Dpy_classes[di]
                if da.startswith("discord."):
                    cres += f"[{da.split('.',1)[1]}]({base_url}api.html#{da})\n"
                elif da.startswith("commands."):
                    cres += f"[{da.split('.',1)[1]}]({base_url}ext/commands/api.html#discord.ext.{da})\n"
                elif da.startswith("tasks."):
                    cres += f"[{da.split('.',1)[1]}]({base_url}ext/tasks/api.html#discord.ext.{da})\n"
        lower_attrs = [da.lower() for da in Dpy_attrs]
        for di, tda in enumerate(lower_attrs):
            if query.lower() in tda:
                da = Dpy_attrs[di]
                if da.startswith("discord."):
                    res += f"[{da.split('.',1)[1]}]({base_url}api.html#{da})\n"
                elif da.startswith("commands."):
                    res += f"[{da.split('.',1)[1]}]({base_url}ext/commands/api.html#discord.ext.{da})\n"
                elif da.startswith("tasks."):
                    res += f"[{da.split('.',1)[1]}]({base_url}ext/tasks/api.html#discord.ext.{da})\n"
        lower_props = [da.lower() for da in Dpy_methods]
        for di, tda in enumerate(lower_props):
            if query.lower() in tda:
                da = Dpy_methods[di]
                if da.startswith("discord."):
                    pres += f"[{da.split('.',1)[1]}]({base_url}api.html#{da})\n"
                elif da.startswith("commands."):
                    pres += f"[{da.split('.',1)[1]}]({base_url}ext/commands/api.html#discord.ext.{da})\n"
                elif da.startswith("tasks."):
                    pres += f"[{da.split('.',1)[1]}]({base_url}ext/tasks/api.html#discord.ext.{da})\n"
        e = discord.Embed(title=get_txt(ctx.guild.id, "dpy_title"), color=Python_color)
        if not cres:
            val = get_txt(ctx.guild.id, "dpy_fail")
        else:
            res2 = ""
            res_i = -1
            for i, r in enumerate(cres.splitlines()):
                if len(res2 + r) > 1000:
                    res_i = i
                    break
                res2 += r + "\n"
            if res_i > 0:
                res2 += get_txt(ctx.guild.id, "dpy_more").format(cres.count("\n") - res_i)
            val = res2
        e.add_field(name=get_txt(ctx.guild.id, "dpy_classes") + '(`' + str(cres.count("\n")) + '`)', value=val)
        if not res:
            val = get_txt(ctx.guild.id, "dpy_fail")
        else:
            res2 = ""
            res_i = -1
            for i, r in enumerate(res.splitlines()):
                if len(res2 + r) > 1000:
                    res_i = i
                    break
                res2 += r + "\n"
            if res_i > 0:
                res2 += get_txt(ctx.guild.id, "dpy_more").format(res.count("\n") - res_i)
            val = res2
        e.add_field(name=get_txt(ctx.guild.id, "dpy_props") + '(`' + str(res.count("\n")) + '`)', value=val)
        if not pres:
            val = get_txt(ctx.guild.id, "dpy_fail")
        else:
            res2 = ""
            res_i = -1
            for i, r in enumerate(pres.splitlines()):
                if len(res2 + r) > 1000:
                    res_i = i
                    break
                res2 += r + "\n"
            if res_i > 0:
                res2 += get_txt(ctx.guild.id, "dpy_more").format(pres.count("\n") - res_i)
            val = res2
        e.add_field(name=get_txt(ctx.guild.id, "dpy_methods") + '(`' + str(pres.count("\n")) + '`)', value=val)
        await ctx.send(embed=e)

    @rtfm.command("djs")
    async def rtfm_djs(self, ctx, *, text):
        query = text
        cres = ""
        res = ""
        pres = ""
        lower_classes = [da.lower() for da in Djs_classes]
        for di, tda in enumerate(lower_classes):
            if query.lower() in tda:
                da = Djs_classes[di]
                cres += f"[{da}](https://discord.js.org/#/docs/main/master/class/{da})\n"
        lower_attrs = [da.lower() for da in Djs_attrs]
        for di, tda in enumerate(lower_attrs):
            if query.lower() in tda:
                da = Djs_attrs[di]
                res += f"[{da}](https://discord.js.org/#/docs/main/master/class/{da.split('.', 1)[0]}?scrollTo={da.split('.', 1)[1]})\n"
        lower_props = [da.lower() for da in Djs_methods]
        for di, tda in enumerate(lower_props):
            if query.lower() in tda:
                da = Djs_methods[di]
                pres += f"[{da}](https://discord.js.org/#/docs/main/master/class/{da.split('.', 1)[0]}?scrollTo={da.split('.', 1)[1]})\n"
        e = discord.Embed(title=get_txt(ctx.guild.id, "djs_title"), color=DJS_COLOR)
        if not cres:
            val = get_txt(ctx.guild.id, "djs_fail")
        else:
            res2 = ""
            res_i = -1
            for i, r in enumerate(cres.splitlines()):
                if len(res2 + r) > 1000:
                    res_i = i
                    break
                res2 += r + "\n"
            if res_i > 0:
                res2 += get_txt(ctx.guild.id, "djs_more").format(cres.count("\n") - res_i)
            val = res2
        e.add_field(name=get_txt(ctx.guild.id, "djs_classes") + '(`' + str(cres.count("\n")) + '`)', value=val)
        if not res:
            val = get_txt(ctx.guild.id, "djs_fail")
        else:
            res2 = ""
            res_i = -1
            for i, r in enumerate(res.splitlines()):
                if len(res2 + r) > 1000:
                    res_i = i
                    break
                res2 += r + "\n"
            if res_i > 0:
                res2 += get_txt(ctx.guild.id, "djs_more").format(res.count("\n") - res_i)
            val = res2
        e.add_field(name=get_txt(ctx.guild.id, "djs_props") + '(`' + str(res.count("\n")) + '`)', value=val)
        if not pres:
            val = get_txt(ctx.guild.id, "djs_fail")
        else:
            res2 = ""
            res_i = -1
            for i, r in enumerate(pres.splitlines()):
                if len(res2 + r) > 1000:
                    res_i = i
                    break
                res2 += r + "\n"
            if res_i > 0:
                res2 += get_txt(ctx.guild.id, "djs_more").format(pres.count("\n") - res_i)
            val = res2
        e.add_field(name=get_txt(ctx.guild.id, "djs_methods") + '(`' + str(pres.count("\n")) + '`)', value=val)
        await ctx.send(embed=e)

    @commands.command(aliases=["sf"])
    async def snowflake(self, ctx, sf: int):
        rawbin = str(bin(sf))[2:].zfill(64)
        bins = [rawbin[0:42], rawbin[42:47], rawbin[47:52], rawbin[52:]]
        res = []
        for b in bins:
            res.append(int(b, 2))
        dt_utc_aware = datetime.datetime.fromtimestamp((res[0] + 1420070400000) / 1000.0, datetime.timezone.utc)
        res[0] = str(dt_utc_aware)
        e = discord.Embed(title=get_txt(ctx.guild.id, "snowflake")[0], description=get_txt(ctx.guild.id, "snowflake")[1].format(*res), color=Info)
        await ctx.send(embed=e)

    @commands.command()
    @commands.cooldown(10, 5)
    async def webshot(self, ctx, *, url):
        msg = await ctx.send(embed=SEmbed("取得中です。しばらくお待ち下さい。", color=Process))
        async with aiohttp.ClientSession() as s:
            async with s.post("https://api.sevenbot.jp/webshot", json={"password": self.bot.web_pass, "url": url}) as r:
                temp = await self.bot.get_channel(765528694500360212).send(file=discord.File(io.BytesIO(await r.read()), filename="result.png"))
        title = f"`{url}`のスクリーンショット"
        if len(title) > 256:
            s = len(title) - len(url)
            title = f"`{url[:256 - s - 4]}...`のスクリーンショット"
        await msg.edit(embed=SEmbed(title, url=url, image_url=temp.attachments[0].url, color=Success))

    def cog_unload(self):
        Batch["sync_afk"].cancel()


def setup(_bot):
    global bot
    bot = _bot
#     logging.info("cog.py reloaded")
    _bot.add_cog(ToolCog(_bot))
