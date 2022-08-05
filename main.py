import ast
import asyncio
from collections import defaultdict
import copy
import datetime
import importlib
import io
import json
import logging
import os
import sys
import traceback
from typing import DefaultDict, Union

import discord
import pymongo
import requests
from sembed import SEmbed
import sentry_sdk
import topgg
from discord.ext import commands, levenshtein
from motor import motor_asyncio as motor
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from common_resources import consts as common_resources
from common_resources.consts import Official_discord_id, Sub_discord_id
from common_resources.settings import GuildSettings, DEFAULT_SETTINGS
from common_resources.tokens import (
    DEBUG_TOKEN,
    TOKEN,
    cstr,
    dbl_token,
    emergency,
    sentry_url,
    web_pass,
)
from common_resources.tools import flatten

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
# handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
# logger.addHandler(handler)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)
if "debug" in sys.argv:
    os.environ["DEBUG"] = "True"
elif "prod" in sys.argv:
    os.environ["DEBUG"] = "False"
else:
    os.environ["DEBUG"] = "True" if sys.platform == "win32" else "False"
if os.environ["DEBUG"] == "True":
    db_name = "development"
    token = DEBUG_TOKEN
else:
    sentry_sdk.init(
        sentry_url,
        traces_sample_rate=1.0,
    )
    token = TOKEN
    db_name = "production"


class ReloadEventHandler(FileSystemEventHandler):
    def __init__(self, loop, bot, *args, **kwargs):
        self._loop = loop
        self.bot = bot
        self.times = {}
        super().__init__(*args, **kwargs)

    def will_run(self, event: FileSystemEvent):
        if not self.bot.is_ready():
            return False
        if "__pycache__" in event.src_path:
            return False
        if event.is_directory:
            return False
        if not event.src_path.endswith(".py"):
            return False
        self.check_loop()

        if event.src_path not in self.times:
            self.times[event.src_path] = 0
        self.times[event.src_path] += 1
        if self.times[event.src_path] > 1:
            self.times[event.src_path] = 0
            return True
        else:
            return False

    def check_loop(self):
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(self._loop)

    def on_created(self, event: FileSystemEvent):
        if not self.will_run(event):
            return
        try:
            self.bot.load_extension("cogs." + event.src_path.split("\\")[-1].split(".")[0])
        except Exception:
            print(traceback.format_exc())
        else:
            print(f"-- Loaded: {event.src_path}")

    def on_modified(self, event: FileSystemEvent, import_fail: bool = False):
        if not self.will_run(event):
            return
        try:
            self.bot.reload_extension("cogs." + event.src_path.split("\\")[-1].split(".")[0])
        except discord.ExtensionFailed as e:
            if isinstance(e.original, ImportError) and not import_fail:
                message = e.original.args[0]
                cls = message.split("'")[3]
                print("-- Detected import error in the module: " + cls)
                print("-- Attempting to reload the module...")
                importlib.reload(sys.modules[cls])
                self.on_modified(event, True)
            else:
                traceback.print_exc()
        except discord.ExtensionNotLoaded:
            try:
                self.bot.load_extension("cogs." + event.src_path.split("\\")[-1].split(".")[0])
            except Exception:
                print(traceback.format_exc())
        except discord.NoEntryPointError:
            self.on_modified(event, True)
        except Exception:
            print(traceback.format_exc())
        else:
            print(f"-- Reloaded: {event.src_path}")

    def on_deleted(self, event: FileSystemEvent):
        if not self.will_run(event):
            return
        try:
            self.bot.unload_extension("cogs." + event.src_path.split("\\")[-1].split(".")[0])
        except Exception:
            print(traceback.format_exc())
        else:
            print(f"-- Unloaded: {event.src_path}")


Channel_ids = {
    "log": 756254787191963768,
    "announce": 756254915441197206,
    "emoji_print": 756254956817743903,
    "global_report": 756255003341225996,
    "boot_log": 747764100922343554,
    "error": 763877469928554517,
}
Premium_guild = 715540925081714788
Premium_role = 779685018964066336
Save_channel_id = 765489262123548673


intent = discord.Intents.all()
intent.typing = False
# intent.members=True
# intent.messages=True
# intent.reactions=True

# Save_game = discord.Game(name="Saving..." + "⠀" * 100)
# Save_game2 = discord.Game(name="Complete!" + "⠀" * 100)
print("-- Loading save from attachment: ", end="")
try:
    r = requests.get(
        f"https://discord.com/api/v9/channels/{Save_channel_id}/messages?limit=1",
        headers={"authorization": "Bot " + TOKEN},
    )
    r.raise_for_status()
    s = requests.get(r.json()[0]["attachments"][0]["url"])
    s.raise_for_status()
    raw_save = s.content.decode("utf8")
except requests.exceptions.HTTPError:
    print("\n!! Unable to get save, loaded save.sample.")
    with open("./save.sample", "r", encoding="utf8") as f:
        raw_save = f.read()
print("Done")


class SevenBot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=self.prefix,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(everyone=False, replied_user=False),
            intents=intent,
            strip_after_prefix=True,
            case_insensitive=True,
            enable_debug_events=True,
        )
        self.consts = {"qu": {}, "ch": {}, "ne": [], "tc": {}, "pci": {}, "ticket_time": {}}
        self.raw_config = ast.literal_eval(raw_save)
        self.dbclient = motor.AsyncIOMotorClient(cstr)
        self.sync_dbclient = pymongo.MongoClient(cstr)
        self.db = self.dbclient[db_name]
        self.sync_db = self.sync_dbclient[db_name]
        self.web_pass = web_pass
        self.debug = os.environ["DEBUG"] == "True"
        self.texts = common_resources.Texts
        self.default_user_settings = {
            "level_dm": False,
        }
        self.oemojis: dict[str, discord.Emoji] = {}
        self.guild_settings: DefaultDict[int, GuildSettings] = defaultdict(lambda: copy.deepcopy(DEFAULT_SETTINGS))
        print("-- Loading saves from db: ", end="")
        self.load_saves()
        print("Done")
        print("Debug mode: " + str(self.debug))
        if self.debug:
            self.loop.create_task(self.auto_reload())
        self.check(commands.cooldown(2, 2))

    def prefix(self, bot, message):
        if self.guild_settings[message.guild.id]["prefix"] is None:
            if self.debug:
                return ["sb/"]
            else:
                return ["sb#", "sb."]
        else:
            return self.guild_settings[message.guild.id]["prefix"]

    def load_saves(self):
        if self.debug:
            self.loop.create_task(self.load_saves_debug())

        for g in self.sync_dbclient[db_name].guild_settings.find({}, {"_id": False}):
            for ik in GuildSettings.int_keys:
                t = g
                for ikc in ik.split("."):
                    t = t[ikc]
                t2 = dict([(int(k), v) for k, v in t.items()])
                t.clear()
                t.update(t2)
            self.guild_settings[g["gid"]] = g

    async def to_coro(self, f: asyncio.Future):
        await f

    async def load_saves_debug(self):
        pass
        # for c in await self.dbclient["production"].list_collection_names():
        #     async for r in self.dbclient["production"][c].find():
        #         self.loop.create_task(
        #             self.to_coro(self.dbclient["development"][c].replace_one({"_id": r["_id"]}, r, upsert=True))
        #         )

    async def auto_reload(self):
        event_handler = ReloadEventHandler(self.loop, self)
        observer = Observer()
        observer.schedule(event_handler, "./cogs", recursive=False)
        observer.start()

    async def on_ready(self):
        print("on_ready fired")
        for k, v in Channel_ids.items():
            self.consts["ch"][k] = self.get_channel(v)
        g = self.get_guild(Official_discord_id)
        for oe in g.emojis:
            self.oemojis[oe.name] = oe
        g = self.get_guild(Sub_discord_id)
        for oe in g.emojis:
            self.oemojis[oe.name] = oe
        for i in range(11):
            self.consts["ne"].append(self.oemojis["b" + str(i)])
        if not emergency:
            await self.get_channel(934611880146780200).send("em:shutdown")
        bot.load_extension("jishaku")
        bot.load_extension("dpy_peper")
        bot.load_extension("discord.ext.components")
        if not self.debug:
            self.DBL_client = topgg.DBLClient(self, dbl_token, autopost=True)
        for o in os.listdir("./cogs"):
            if o.endswith(".py") and not o.startswith("_"):
                with open(f"./cogs/{o}") as f:
                    if f.read().startswith("# -*- ignore_on_debug -*-") and self.debug:
                        continue
                try:
                    bot.load_extension("cogs." + os.path.splitext(os.path.basename(o))[0])
                except Exception as e:
                    print("!! Failed to load extension: ", e)
                    traceback.print_exc()
        self.levenshtein = levenshtein.Levenshtein(self, max_length=1)
        print("on_ready done")

    def is_premium(self, user: Union[discord.User, discord.Member]):
        return self.get_guild(Premium_guild).get_member(user.id) and (
            self.get_guild(Premium_guild).get_member(user.id).premium_since
            or Premium_role in [r.id for r in self.get_guild(715540925081714788).get_member(user.id).roles]
        )

    async def save(self):
        # await self.change_presence(activity=Save_game, status=discord.Status.dnd)
        if self.debug:
            return
        gs2 = list(self.guild_settings.keys())
        for gs in gs2:
            if self.get_guild(gs) is None:
                del self.guild_settings[gs]
        # r = str(self.raw_config)
        # ar = []
        # PastebinAPI.paste(PB_key, r, paste_private = "private",paste_expire_date = None)

        # file = open('Save.txt', 'w+', encoding='utf-8')

        # file.write(r)
        # file.close()
        for gk, gv in self.guild_settings.copy().items():
            r = json.loads(json.dumps(gv))
            r["gid"] = gk
            if self.find_overflow(r):
                guild = self.get_guild(gk)
                try:
                    await self.get_user(guild.owner_id).send(
                        embed=SEmbed(
                            "攻撃を発見しました",
                            f"本サービスへの意図的な攻撃が確認されたため、`{guild.name}`から退出しました。\n"
                            "Ban解除は[公式サーバー](https://discord.gg/GknwhnwbAV)まで。",
                            color=discord.Colour.gold(),
                        )
                    )
                except Exception:
                    pass
                await guild.leave()
                self.bot.raw_config["il"].append(gk)

            else:
                await self.db.guild_settings.replace_one({"gid": gk}, r, upsert=True)
        if not self.debug:
            async for gk in self.db.guild_settings.find():
                if not self.get_guild(gk["gid"]):
                    await self.db.guild_settings.delete_one({"gid": gk["gid"]})

        sio = await self.loop.run_in_executor(
            None,
            lambda: io.StringIO(str({k: v for k, v in self.raw_config.items() if k != "gs"})),
        )
        await (await self.fetch_channel(765489262123548673)).send(
            file=discord.File(sio, filename=f"save_{datetime.datetime.now()}.txt")
        )
        sio.close()
        #         print(games)
        try:
            pass  # await self.change_presence(activity=Save_game2, status=discord.Status.online)
        except BaseException:
            pass

    def find_overflow(self, data):
        if isinstance(data, int):
            if data >= 2 ** 64 - 1:
                return True
            else:
                return False
        elif isinstance(data, str):
            return False
        elif isinstance(data, list):
            for i in data:
                if self.find_overflow(i):
                    return True
            return False
        elif isinstance(data, dict):
            for i in data.values():
                if self.find_overflow(i):
                    return True
            return False

    def get_txt(self, guild_id, name):
        try:
            return Texts[self.guild_settings[guild_id]["lang"]][name]
        except KeyError:
            return Texts["ja"].get(name, "*" + name + "*")

    def is_command(self, msg):
        return msg.content.startswith(tuple(self.command_prefix(bot, msg)))

    async def send_subcommands(self, ctx):
        desc = ""
        for c in ctx.command.commands:
            desc += (
                f"**`{c.name}`** "
                + (
                    self.get_txt(ctx.guild.id, "help_detail").get(
                        str(c),
                        "_" + self.get_txt(ctx.guild.id, "help_detail_none") + "_",
                    )
                ).split("\n")[0]
                + "\n"
            )
        e = discord.Embed(
            title=self.get_txt(ctx.guild.id, "subcommand").format(ctx.command.name),
            description=desc,
            color=0x00CCFF,
        )
        await ctx.send(embed=e)

    async def init_user_settings(self, uid):
        nd = copy.deepcopy(self.default_user_settings)
        nd["uid"] = uid
        await self.db.user_settings.insert_one(nd)

    @property
    def global_chats(self):
        return (
            set(self.raw_config["snc"])
            | set(self.raw_config["gc"])
            | set(flatten(c["channels"] for c in self.consts["pci"].values()))
        )


bot = SevenBot()


@bot.command()
async def reload_lang(ctx):
    global Texts
    importlib.reload(common_resources)
    Texts = common_resources.Texts
    bot.texts.update(common_resources.Texts)
    await ctx.reply("Done")


@bot.event
async def on_message(msg):
    pass


@bot.event
async def on_socket_raw_receive(event):
    bot.dispatch("socket_response", json.loads(event))


Texts = common_resources.Texts

if __name__ == "__main__":
    print("*********************")
    print("      SevenBot       ")
    print("  Created by 名無し。  ")
    print("*********************")
    print("ログイン中…")
    bot.run(token)
