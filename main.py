
import ast
import datetime
import importlib
import io
import json
import logging
import os
import sys
from typing import Union

import discord
import pymongo
import requests
import topgg
from discord.ext import commands, levenshtein
from motor import motor_asyncio as motor

from common_resources import consts as common_resources
from common_resources.tokens import TOKEN, cstr, dbl_token, web_pass
from common_resources.consts import Official_discord_id, Sub_discord_id

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
# handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
# handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
# logger.addHandler(handler)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

print('*********************')
print("      SevenBot       ")
print("  Created by 名無し。  ")
print("*********************")


Channel_ids = {
    "log": 756254787191963768,
    "announce": 756254915441197206,
    "emoji_print": 756254956817743903,
    "global_report": 756255003341225996,
    "boot_log": 747764100922343554,
    "error": 763877469928554517
}
Premium_guild = 715540925081714788
Premium_role = 779685018964066336
Save_channel_id = 765489262123548673


def prefix(bot, message):
    if Guild_settings[message.guild.id]["prefix"] is None:
        if bot.debug:
            return ['sbb#', "sbb. ", 'sbb.']
        else:
            return ['sb#', "sb. ", 'sb.']
    else:
        return Guild_settings[message.guild.id]["prefix"]


intent = discord.Intents.all()
intent.typing = False
# intent.members=True
# intent.messages=True
# intent.reactions=True

# Save_game = discord.Game(name="Saving..." + "⠀" * 100)
# Save_game2 = discord.Game(name="Complete!" + "⠀" * 100)
print("Loading save from attachment...", end="")
try:
    r = requests.get(f"https://discord.com/api/v8/channels/{Save_channel_id}/messages?limit=1", headers={"authorization": "Bot " + TOKEN})
    r.raise_for_status()
    s = requests.get(r.json()[0]["attachments"][0]["url"])
    s.raise_for_status()
    raw_save = s.content.decode("utf8")
except requests.exceptions.HTTPError:
    print("\nUnable to get save, loaded save.sample.")
    with open("./save.sample", "r", encoding="utf8") as f:
        raw_save = f.read()
print("Done")
print("Loading saves from db...", end="")
gs = {}
tmp_client = pymongo.MongoClient(cstr)
for g in tmp_client.sevenbot.guild_settings.find({}, {"_id": False}):
    for ik in ["levels", "level_counts", "warns", "warn_settings.punishments", "ticket_time", "ticket_subject", "level_boosts"]:
        t = g
        for ikc in ik.split("."):
            t = t[ikc]
        t2 = dict([(int(k), v) for k, v in t.items()])
        t.clear()
        t.update(t2)
    gs[g["gid"]] = g
print("Done")


class SevenBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consts = {"qu": {}, "ch": {}, "oe": {}, "ne": [], "tc": {}}
        self.raw_config = ast.literal_eval(raw_save)
        self.guild_settings = gs
        self.dbclient = motor.AsyncIOMotorClient(cstr)
        self.sync_dbclient = tmp_client
        self.db = self.dbclient.sevenbot
        self.sync_db = self.sync_dbclient.sevenbot
        self.web_pass = web_pass
        self.debug = len(sys.argv) != 1 and sys.argv[1] == "debug"
        self.texts = common_resources.Texts
        print("Debug mode: " + str(self.debug))
        self.check(commands.cooldown(2, 2))

    async def on_ready(self):
        global Guild_settings
        print("on_ready fired")
        Guild_settings = self.guild_settings
        for k, v in Channel_ids.items():
            self.consts["ch"][k] = self.get_channel(v)
        g = self.get_guild(Official_discord_id)
        for oe in g.emojis:
            self.consts["oe"][oe.name] = oe
        g = self.get_guild(Sub_discord_id)
        for oe in g.emojis:
            self.consts["oe"][oe.name] = oe
        for i in range(11):
            self.consts["ne"].append(self.consts["oe"]["b" + str(i)])
        bot.load_extension("jishaku")
        for o in os.listdir("./cogs"):
            if o.endswith(".py") and not o.startswith("_"):
                bot.load_extension("cogs." + os.path.splitext(os.path.basename(o))[0])
        self.levenshtein = levenshtein.Levenshtein(self, max_length=1)
        if not self.debug:
            self.DBL_client = topgg.DBLClient(self, dbl_token, autopost=True)
        print("on_ready done")

    def is_premium(self, user: Union[discord.User, discord.Member]):
        return (self.get_guild(Premium_guild).get_member(user.id) and (self.get_guild(Premium_guild).get_member(user.id).premium_since or Premium_role in [r.id for r in self.get_guild(715540925081714788).get_member(user.id).roles]))

    async def save(self):
        # await self.change_presence(activity=Save_game, status=discord.Status.dnd)
        gs2 = list(Guild_settings.keys())
        if not self.debug:
            for gs in gs2:
                if self.get_guild(gs) is None:
                    del Guild_settings[gs]
        # r = str(self.raw_config)
        # ar = []
        # PastebinAPI.paste(PB_key, r, paste_private = "private",paste_expire_date = None)

        # file = open('Save.txt', 'w+', encoding='utf-8')

        # file.write(r)
        # file.close()
        for gk, gv in Guild_settings.items():
            r = json.loads(json.dumps(gv))
            r["gid"] = gk
            res = await self.db.guild_settings.replace_one({"gid": gk}, r)
            if not res.matched_count:
                await self.db.guild_settings.insert_one(r)
        if not self.debug:
            async for gk in self.db.guild_settings.find():
                if not self.get_guild(gk["gid"]):
                    await self.db.guild_settings.delete_one({"gid": gk["gid"]})

        sio = await self.loop.run_in_executor(None, lambda: io.StringIO(str({k: v for k, v in self.raw_config.items() if k != "gs"})))
        await (await self.fetch_channel(765489262123548673)).send(
            file=discord.File(sio, filename=f"save_{datetime.datetime.now()}.txt"))
        sio.close()
#         print(games)
        try:
            pass  # await self.change_presence(activity=Save_game2, status=discord.Status.online)
        except BaseException:
            pass

    def get_txt(self, guild_id, name):
        try:
            return Texts[Guild_settings[guild_id]["lang"]][name]
        except KeyError:
            return Texts["ja"].get(name, "*" + name + "*")

    def is_command(self, msg):
        return msg.content.startswith(tuple(self.command_prefix(bot, msg)))

    async def send_subcommands(self, ctx):
        desc = ""
        for c in ctx.command.commands:
            desc += f"**`{c.name}`** " + (self.get_txt(ctx.guild.id, "help_datail").get(str(c), "_" + self.get_txt(ctx.guild.id, "help_datail_none") + "_")).split("\n")[0] + "\n"
        e = discord.Embed(title=self.get_txt(ctx.guild.id, "subcommand").format(ctx.command.name),
                          description=desc, color=0x00ccff)
        await ctx.send(embed=e)

    @property
    def global_chats(self):
        return set(self.raw_config["snc"]) | set(self.raw_config["gc"]) | set(self.consts["pci"])


bot = SevenBot(command_prefix=prefix, help_command=None, allowed_mentions=discord.AllowedMentions(everyone=False, replied_user=False), intents=intent)


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


print("ログイン中…")

Texts = common_resources.Texts
bot.run(TOKEN)
