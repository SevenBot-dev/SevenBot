import asyncio
import datetime

# import sys
import time

import aiohttp
import discord
import psutil
from discord.ext import commands, tasks

import _pathmagic  # type: ignore # noqa
from common_resources.settings import GuildSettings
from common_resources.tokens import botdd_token

Last_favorite = {}
Time_format = "%Y-%m-%d %H:%M:%S"
Bump_alerts = {}
Batchs = []
Number_emojis = []
Bump_id = 302050872383242240
Dissoku_id = 761562078095867916
Bump_color = 0x24B8B8
Dissoku_color = 0x7289DA


class BatchCog(commands.Cog):
    def __init__(self, bot):
        global Bump_alerts, Dissoku_alerts
        global get_txt
        self.bot: commands.Bot = bot
        self.bot.guild_settings = self.bot.guild_settings
        Bump_alerts = self.bot.raw_config["ba"]
        Dissoku_alerts = self.bot.raw_config["da"]
        get_txt = self.bot.get_txt
        Batchs.append(self.restart_tasks.start())
        time.sleep(0.1)
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
        n = s or (f"sb#help to Help | {len(self.bot.guilds)} Servers | " + ("https://sevenbot.jp"))
        if (
            not self.bot.get_guild(715540925081714788).me.activity
            or self.bot.get_guild(715540925081714788).me.activity.name.replace("⠀", "") != n
        ):
            await self.bot.change_presence(
                activity=discord.Game(name=n + "⠀" * 10),
                status=discord.Status.online,
            )

    @tasks.loop(seconds=30)
    async def restart_tasks(self):
        value: dict[str, discord.ext.tasks.Loop] = {}
        for c in self.bot.cogs.values():
            for a in filter(lambda a: not a.startswith("_"), dir(c)):
                v = getattr(c, a)
                if isinstance(v, discord.ext.tasks.Loop):
                    value[a] = v
        for k, v in value.items():
            if not v.is_running():
                v.start()

    @tasks.loop(minutes=10)
    async def batch_send_status(self):
        loop = asyncio.get_event_loop()
        if self.bot.latency > 5:
            return
        if len(self.bot.users) < 10000:
            for guild in self.bot.guilds:
                await guild.chunk()
            return
        cpu = await loop.run_in_executor(None, psutil.cpu_percent, 1)
        mem = await loop.run_in_executor(None, psutil.virtual_memory)
        gb = 1024 * 1024 * 1024
        call = await self.bot.db.command("dbstats")
        ping_before = time.time()
        await self.bot.db.ping.insert_one({"ping": "pong"})
        db_ping = time.time() - ping_before
        ping_before = time.time()
        async with aiohttp.ClientSession() as c:
            async with c.get("https://sevenbot.jp") as r:
                await r.text()
        web_ping = time.time() - ping_before
        await self.bot.db.status_log.insert_one(
            {
                "ping": round(self.bot.latency * 1000),
                "db_ping": round(db_ping * 1000),
                "web_ping": round(web_ping * 1000),
                "guilds": len(self.bot.guilds),
                "users": len(self.bot.users),
                "cpu": cpu,
                "mem": {"percent": mem.percent, "gb": mem.used / gb},
                "time": time.time(),
                "save": {
                    "main": len(str(self.bot.raw_config).encode("utf8")) / 1024,
                    "db": call["dataSize"] / 1024,
                },
            }
        )
        await self.bot.db.status_log.delete_many({"time": {"$lt": time.time() - 60 * 60 * 24 * 7}})
        await self.bot.db.ping.delete_many({"ping": "pong"})

    @batch_send_status.before_loop
    async def batch_send_status_before(self):
        await asyncio.sleep((10 - datetime.datetime.now().minute % 10) * 60)

    @tasks.loop(minutes=5)
    async def batch_save(self):
        await self.bot.save()

    @tasks.loop(seconds=30)
    async def botdd_post(self):
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "https://botdd.alpaca131.com/api/heartbeat",
                headers={"authorization": "Bearer " + botdd_token},
            ):
                pass

    async def sync_db(self):
        async with self.bot.db.guild_settings.watch() as change_stream:
            async for change in change_stream:
                if change["operationType"] == "delete":
                    # del self.bot.guild_settings[change["documentKey"]["gid"]]
                    pass  # TODO: delete guild settings
                if change["operationType"] == "update":
                    gs = await self.bot.db.guild_settings.find_one(change["documentKey"])
                    for ik in GuildSettings.int_keys:
                        t = gs
                        for ikc in ik.split("."):
                            t = t[ikc]
                        t2 = dict([(int(k), v) for k, v in t.items()])
                        t.clear()
                        t.update(t2)
                    del gs["_id"]
                    self.bot.guild_settings[gs["gid"]] = gs
                if change["operationType"] == "insert":
                    gs = change["fullDocument"]
                    for ik in GuildSettings.int_keys:
                        t = gs
                        for ikc in ik.split("."):
                            t = t[ikc]
                        t2 = dict([(int(k), v) for k, v in t.items()])
                        t.clear()
                        t.update(t2)
                    del gs["_id"]
                    self.bot.guild_settings[gs["gid"]] = gs

    def cog_unload(self):
        for ba in Batchs:
            ba.cancel()


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(BatchCog(_bot), override=True)
