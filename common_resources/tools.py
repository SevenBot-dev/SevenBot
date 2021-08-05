import asyncio
import collections
import datetime
import math
import re
import unicodedata

import discord
from discord.ext import commands
from discord_emoji.table import UNICODE_TO_DISCORD

Datetime_re = re.compile(
    r"(\d+[w(週間?)(weeks?)])?(\d+[d(日)(days?)])? ?(\d+[:h(時間)(hours?)])?(\d+[:m(分)(minutes?)])?(\d+[s(秒)seconds?)]?)?"
)
Datetime_args = ["weeks", "days", "hours", "minutes", "seconds"]
Shard_re = re.compile(r"(\d+)([^\d]+)?")


def flatten(li):
    for el in li:
        if isinstance(el, collections.abc.Iterable) and not isinstance(
            el, (str, bytes)
        ):
            yield from flatten(el)
        else:
            yield el


def to_lts(s):
    s = math.floor(s)
    res = str((s // 60) % 60).zfill(2) + ":" + str(s % 60).zfill(2)
    if s > 3600:
        if s > 3600 * 24:
            res = (
                str(s // 3600  24)
                + "d "
                + str(s // 3600 % 24).zfill(2)
                + ":"
                + res
            )
        else:
            res = str(s // 3600).zfill(2) + ":" + res
    return res


def remove_emoji(src_str):
    return "".join(
        "?" if c in UNICODE_TO_DISCORD.keys() else c for c in src_str
    )


def recr_keys(d):
    res = []

    def _recr_keys(p, d2):
        for k, v in d2.items():
            if isinstance(v, dict):
                _recr_keys(p + [k], v)
            else:
                res.append(tuple(p + [k]))

    _recr_keys([], d)
    return res


def recr_items(d):
    res = []

    def _recr_items(p, d2):
        for k, v in d2.items():
            if isinstance(v, dict):
                _recr_items(p + [k], v)
            else:
                res.append((tuple(p + [k]), v))

    _recr_items([], d)
    return res


class NotADatetimeFormat(commands.BadArgument):
    def __init__(self, argument):
        self.argument = argument
        super().__init__('"{}" is not a datetime format.'.format(argument))


def convert_timedelta(arg):
    fm = Datetime_re.fullmatch(arg)
    if not fm:
        raise NotADatetimeFormat(arg)
    res = {}
    for i, f in enumerate(fm.groups()):
        if not f:
            continue
        sh = Shard_re.fullmatch(f)
        res[Datetime_args[i]] = int(sh[1])
    return datetime.timedelta(**res)


def chrsize_len(text):
    count = 0
    for c in text:
        if unicodedata.east_asian_width(c) in "FWA":
            count += 2
        else:
            count += 1
    return count


async def send_subcommands(ctx):
    desc = ""
    for c in ctx.command.commands:
        desc += (
            f"**`{c.name}`** "
            + (
                ctx.bot.get_txt(ctx.guild.id, "help_detail").get(
                    str(c),
                    "_"
                    + ctx.bot.get_txt(ctx.guild.id, "help_detail_none")
                    + "_",
                )
            ).split("\n")[0]
            + "\n"
        )
    e = discord.Embed(
        title=ctx.bot.get_txt(ctx.guild.id, "subcommand").format(
            ctx.command.name
        ),
        description=desc,
        color=0x00CCFF,
    )
    await ctx.send(embed=e)


async def delay_react_remove(message, emoji, user, sec):
    await asyncio.sleep(sec)
    await message.remove_reaction(emoji, user)
