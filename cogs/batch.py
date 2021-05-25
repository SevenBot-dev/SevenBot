import asyncio
import datetime
# import sys
import time
import traceback

import aiohttp
import discord
import psutil
from discord import Forbidden, NotFound
from discord.ext import commands, tasks

import _pathmagic  # type: ignore # noqa
from common_resources.lang_ja import Stat_dict
from common_resources.tools import recr_items
from common_resources.tokens import botdd_token

Last_favorite = {}
Time_format = '%Y-%m-%d %H:%M:%S'
Bump_alerts = {}
Guild_settings = {}
Batchs = []
Number_emojis = []
Bump_id = 302050872383242240
Dissoku_id = 761562078095867916
Bump_color = 0x24b8b8
Dissoku_color = 0x7289da
Game_cache = [None, None, None, None]


class BatchCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Bump_alerts, Dissoku_alerts
        global get_txt
        self.bot = bot
        Guild_settings = self.bot.guild_settings
        Bump_alerts = self.bot.raw_config["ba"]
        Dissoku_alerts = self.bot.raw_config["da"]
        get_txt = self.bot.get_txt
        Batchs.append(self.batch_change_activity.start())
        time.sleep(0.1)
        Batchs.append(self.bot.loop.create_task(self.sync_db()))
        time.sleep(0.1)
        Batchs.append(self.batch_save.start())
        time.sleep(0.1)
        Batchs.append(self.batch_update_stat_channel.start())
        if not self.bot.debug:
            time.sleep(0.1)
            Batchs.append(self.batch_bump_alert.start())
            time.sleep(0.1)
            Batchs.append(self.botdd_post.start())
            time.sleep(0.1)
            Batchs.append(self.batch_send_status.start())

    @tasks.loop(seconds=10)
    async def batch_change_activity(self):
        s = getattr(self.bot, "status", None)
        n = s or (f'sb#help to Help | {len(self.bot.guilds)} Servers | ' + ("https://sevenbot.jp"))
        if not self.bot.get_guild(715540925081714788).me.activity or self.bot.get_guild(715540925081714788).me.activity.name.replace("⠀", "") != n:
            await self.bot.change_presence(activity=discord.Game(name=n + "⠀" * 20), status=discord.Status.online)

    @tasks.loop(minutes=10)
    async def batch_send_status(self):
        loop = asyncio.get_event_loop()
        cpu = await loop.run_in_executor(None, psutil.cpu_percent, 1)
        mem = await loop.run_in_executor(None, psutil.virtual_memory)
        gb = 1024 * 1024 * 1024
        call = await self.bot.db.command("dbstats")
        await self.bot.db.status_log.insert_one({
            "ping": round(self.bot.latency * 1000),
            "guilds": len(self.bot.guilds),
            "users": len(self.bot.users),
            "cpu": cpu,
            "mem": {
                "percent": mem.percent,
                "gb": mem.used / gb
            },
            "time": time.time(),
            "save": {
                "main": len(str(self.bot.raw_config).encode("utf8")) / 1024,
                "db": call["dataSize"] / 1024
            }
        })
        async for r in self.bot.db.status_log.find():
            if time.time() - r["time"] > 60 * 60 * 24:
                await self.bot.db.status_log.delete_one(r)

    @batch_send_status.before_loop
    async def batch_send_status_before(self):
        await asyncio.sleep((10 - datetime.datetime.now().minute % 10) * 60)

    @tasks.loop(seconds=10)
    async def batch_bump_alert(self):

        for rg in self.bot.guilds:
            gi = rg.id
            if gi not in Bump_alerts.keys():
                continue
            try:
                bt = datetime.datetime.strptime(
                    Bump_alerts[gi][0], Time_format)
                nt = datetime.datetime.utcnow()
                if bt < nt:
                    e = discord.Embed(title=get_txt(gi, "bump_alert"),
                                      description=get_txt(gi, "bump_alert_desc"), color=Bump_color)
                    c = self.bot.get_channel(Bump_alerts[gi][1])
                    m = ""
                    if Guild_settings[c.guild.id]["bump_role"]:
                        r = c.guild.get_role(
                            Guild_settings[c.guild.id]["bump_role"])
                        if r:
                            m = r.mention
                    await c.send(content=m, embed=e)
                    del Bump_alerts[gi]

            except BaseException:
                pass
        for gi, gs in Guild_settings.items():
            if gi not in Dissoku_alerts.keys():
                continue
            try:
                bt = datetime.datetime.strptime(
                    Dissoku_alerts[gi][0], Time_format)
                nt = datetime.datetime.utcnow()
                if bt < nt:
                    e = discord.Embed(title=get_txt(gi, "dissoku_alert"),
                                      description=get_txt(gi, "dissoku_alert_desc"), color=Dissoku_color)
                    c = self.bot.get_channel(Dissoku_alerts[gi][1])
                    m = ""
                    if Guild_settings[c.guild.id]["dissoku_role"]:
                        r = c.guild.get_role(
                            Guild_settings[c.guild.id]["dissoku_role"])
                        if r:
                            m = r.mention
                    await c.send(content=m, embed=e)
                    del Dissoku_alerts[gi]

            except Exception:
                pass

    @tasks.loop(minutes=5, seconds=10)
    async def batch_update_stat_channel(self):
        try:
            for g in self.bot.guilds:
                if Guild_settings[g.id]["do_stat_channels"]:
                    for sck, scv in Guild_settings[g.id]["stat_channels"].items():
                        if sck == "category":
                            continue
                        s = self.bot.get_channel(scv)
                        if s is None:
                            continue

                        val = "--"
                        if sck == "members":
                            val = g.member_count
                        elif sck == "humans":
                            val = len(
                                list(filter(lambda m: not m.bot, g.members)))
                        elif sck == "bots":
                            val = len(list(filter(lambda m: m.bot, g.members)))
                        elif sck == "channels":
                            val = len(g.text_channels) + len(g.voice_channels) - \
                                len(Guild_settings[g.id]
                                    ["stat_channels"].keys()) + 1
                        elif sck == "text_channels":
                            val = len(g.text_channels)
                        elif sck == "voice_channels":
                            val = len(
                                g.voice_channels) - len(Guild_settings[g.id]["stat_channels"].keys()) + 1
                        elif sck == "roles":
                            val = len(g.roles)
                        else:
                            try:
                                await s.delete()
                            except (NotFound, Forbidden):
                                pass

                            continue
                        try:
                            await s.edit(name=f"{Stat_dict[sck]}: {val}")
                        except (NotFound, Forbidden):
                            pass
            await asyncio.sleep(5)
        except Exception:
            pass

    @tasks.loop(minutes=5)
    async def batch_save(self):
        try:
            await self.bot.save()
        except Exception as e:
            await self.bot.get_user(686547120534454315).send("batch_save:```\n" + "".join(traceback.TracebackException.from_exception(e).format()) + "```")

    @tasks.loop(seconds=50)
    async def botdd_post(self):
        async with aiohttp.ClientSession() as s:
            async with s.post("https://botdd.alpaca131.tk/api/heartbeat", headers={"token": botdd_token}):
                pass

    async def sync_db(self):
        async with self.bot.db.guild_settings.watch() as change_stream:
            async for change in change_stream:
                if change["operationType"] == "update":
                    gs = await self.bot.db.guild_settings.find_one(change["documentKey"])
                    gid = gs["gid"]
                    for ufk, ufv in recr_items(change["updateDescription"]["updatedFields"]):
                        if ".".join(ufk) in ["levels", "level_counts", "warns", "warn_settings.punishments", "ticket_time", "ticket_subject", "level_boosts"]:
                            ufv = dict([(int(k), v) for k, v in ufv.items()])
                        t = Guild_settings[gid]
                        for k in ufk[:-1]:
                            t = t[k]
                        t[ufk[-1]] = ufv

    def cog_unload(self):
        for ba in Batchs:
            ba.cancel()


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(BatchCog(_bot))
