import asyncio
import datetime
# import sys
import time
import traceback

import aiohttp
import discord
import psutil
from discord.ext import commands, tasks

import _pathmagic  # type: ignore # noqa
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
        if not self.bot.debug:
            time.sleep(0.1)
            Batchs.append(self.botdd_post.start())
            time.sleep(0.1)
            Batchs.append(self.batch_send_status.start())

    @tasks.loop(seconds=10)
    async def batch_change_activity(self):
        s = getattr(self.bot, "custom_status", None)
        n = s or (f'sb#help to Help | {len(self.bot.guilds)} Servers | ' + ("https://sevenbot.jp"))
        if not self.bot.get_guild(715540925081714788).me.activity or self.bot.get_guild(715540925081714788).me.activity.name.replace("⠀", "") != n:
            await self.bot.change_presence(activity=discord.Game(name=n + "⠀" * 10), status=discord.Status.online)

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
