import asyncio
import math
import datetime
import io
import json
import random
import time

import discord
from discord.ext import commands
from discord.ext.commands import bot
from sembed import SEmbed
from texttable import Texttable


import _pathmagic  # type: ignore # noqa
from common_resources.consts import Info, Success, Error, Chat
from common_resources.tools import flatten, convert_timedelta


async def punish(target, p):
    if p["action"] == "mute":
        dt = discord.utils.utcnow() + datetime.timedelta(seconds=p["length"])
        Guild_settings[target.guild.id]["muted"][target.id] = dt.timestamp()
    elif p["action"] == "kick":
        await target.kick()
    elif p["action"] == "ban":
        await target.ban()
    elif p["action"] == "role_add":
        await target.add_roles(target.guild.get_role(p["role"]))
    elif p["action"] == "role_remove":
        await target.remove_roles(target.guild.get_role(p["role"]))


def delta_to_text(delta, ctx):
    s = math.floor(delta.seconds)
    res = ""
    #     if s > 3600:
    #         res = ""
    if delta.days:
        res += str(delta.days) + get_txt(ctx.guild.id, "delta_txt")[0]
    if s >= 3600:
        res += str(s // 3600) + get_txt(ctx.guild.id, "delta_txt")[1]
    if s >= 60:
        res += str((s // 60) % 60) + get_txt(ctx.guild.id, "delta_txt")[2]
        if s < 3600:
            res += get_txt(ctx.guild.id, "delta_txt")[4]
        if s % 60 != 0:
            res += str(s % 60) + get_txt(ctx.guild.id, "delta_txt")[3]
        return res
    elif not delta.seconds:
        return res
    else:
        return (
            res
            + str(s % 60)
            + get_txt(ctx.guild.id, "delta_txt")[3]
            + get_txt(ctx.guild.id, "delta_txt")[4]
        )


def get_warn_text(bot, ctx, p):
    res = get_txt(ctx.guild.id, "warn_punish")[p["action"]]
    if p["action"] == "mute":
        res += f'({delta_to_text(datetime.timedelta(seconds=p["length"]), ctx)})'
    elif p["action"] in ("role_add", "role_remove"):
        r = ctx.guild.get_role(p["role"])
        res += f"({r.name})"
    return res


class ModerationCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Official_emojis
        global get_txt
        self.bot: commands.Bot = bot
        Guild_settings = bot.guild_settings
        get_txt = bot.get_txt
        Official_emojis = bot.consts["oe"]

    @commands.command(aliases=["purge", "delete_log"])
    @commands.has_permissions(manage_channels=True)
    async def clear_channel(self, ctx, *, args=None):
        if not args:
            await ctx.channel.purge()
            return
        Options = {
            "user": ("u", "from"),
            "limit": ("l", "c", "count"),
            "length": ("len",),
        }
        Option_back = {}
        for ok, ov in Options.items():
            for ovi in ov:
                Option_back[ovi] = ok
        quote = False
        raw_keys = [""]
        for c in list(args):
            if quote:
                if c == quote:
                    quote = False
            else:
                if c == " ":
                    raw_keys.append("")
                elif c in ('"', "'") and raw_keys[-1] == "":
                    quote = c
                else:
                    raw_keys[-1] += c
        limit = None
        checks = []
        for rk in raw_keys:
            try:
                k, v = rk.split("=", 1)
            except ValueError:
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "clear_format"), color=Error
                )
                await ctx.reply(embed=e)
                return
            if k not in flatten(Options.items()):
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "clear_keys").format(k), color=Error
                )
                await ctx.reply(embed=e)
                return
            k = Option_back.get(k, k)
            if k == "limit":
                limit = int(v) + 1
            elif k == "user":
                tmp_user = await commands.MemberConverter().convert(ctx, v)

                def tmp(m):
                    return m.author.id == tmp_user.id

                checks.append(tmp)
            elif k == "length":
                dt = discord.utils.utcnow() - convert_timedelta(v)

                def tmp(m):
                    return m.created_at > dt

                checks.append(tmp)

        def gcheck(m):
            for c in checks:
                if not c(m):
                    return False

            return True

        await ctx.channel.purge(limit=limit, check=gcheck)
        try:
            await ctx.message.add_reaction(Official_emojis["check8"])
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass

    @commands.command(name="archive")
    @commands.has_permissions(manage_channels=True)
    async def archive(self, ctx):
        global Guild_settings
        ow = ctx.channel.overwrites.copy()
        if not self.bot.get_channel(Guild_settings[ctx.guild.id]["archive_category"]):
            cat = await ctx.guild.create_category_channel(
                get_txt(ctx.guild.id, "archive_category")
            )
            Guild_settings[ctx.guild.id]["archive_category"] = cat.id
        else:

            cat = self.bot.get_channel(Guild_settings[ctx.guild.id]["archive_category"])
        for ok, ov in ow.items():
            if isinstance(ok, discord.Member):
                continue
            elif ok.position >= ctx.guild.me.top_role.position:
                continue
            if ov.send_messages:
                ov.update(send_messages=False)

        await ctx.channel.edit(overwrites=ow, category=cat)

        e = discord.Embed(title=get_txt(ctx.guild.id, "archive_title"), color=Success)
        return await ctx.reply(embed=e)

    @commands.command(name="lockdown", aliases=["lock"])
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx):
        pins = await ctx.channel.pins()
        roles = ""
        loop = asyncio.get_event_loop()
        for p in pins:
            if p.embeds:
                if p.embeds[0].color == Success and p.embeds[0].title == get_txt(
                    ctx.guild.id, "lockdown_title"
                ):
                    roles = p.embeds[0].description
                    loop.create_task(p.unpin())
                    break

        if roles:
            desc = get_txt(ctx.guild.id, "unlock_desc") + "\n"
            ow = ctx.channel.overwrites.copy()
            for i, r in enumerate(roles.splitlines()):
                if i == 0:
                    continue
                role = ctx.guild.get_role(int(r[3:-1]))
                if role:
                    try:
                        ow[role].update(send_messages=True)
                        desc += role.mention + "\n"
                    except KeyError:
                        pass
            await ctx.channel.edit(overwrites=ow)
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "unlock_title"),
                description=desc,
                color=Success,
            )
            #             e.set_footer(icon_url="https://i.imgur.com/RCndJ6a.png",text=get_txt(ctx.guild.id,"lockdown_footer"))
            msg = await ctx.reply(embed=e)
        else:
            desc = get_txt(ctx.guild.id, "lockdown_desc") + "\n"
            ow = ctx.channel.overwrites.copy()
            tr = ctx.guild.default_role
            for r in set(ow.keys()) & set(ctx.guild.me.roles):
                if r.position >= tr.position:
                    tr = r

            for ok, ov in ow.items():
                if isinstance(ok, discord.Member):
                    continue
                elif ok.position >= tr.position:
                    continue
                if ov.send_messages:
                    ov.update(send_messages=False)
                    desc += ok.mention + "\n"
            await ctx.channel.edit(overwrites=ow)
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "lockdown_title"),
                description=desc,
                color=Success,
            )
            e.set_footer(
                icon_url="https://i.imgur.com/RCndJ6a.png",
                text=get_txt(ctx.guild.id, "lockdown_footer"),
            )
            msg = await ctx.reply(embed=e)
            await msg.pin()

    @commands.group()
    @commands.has_guild_permissions(administrator=True)
    async def fatal(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @fatal.group(name="nick")
    async def fatal_nick(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @fatal.group(name="role", invoke_without_command=True)
    async def fatal_role(self, ctx):
        await self.bot.send_subcommands(ctx)

    @fatal_role.command(name="add")
    async def fatal_role_add(
        self, ctx, role: discord.Role, target: discord.Role = None
    ):
        c = 0
        s = 0
        e = 0
        for m in (target or ctx.guild.default_role).members:
            c += 1
            try:
                await m.add_roles(role)
                s += 1

            except discord.HTTPException:
                e += 1
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "fatal_role_add").format(c, s, e), color=Success
        )
        await ctx.reply(embed=e)

    @fatal_role.command(name="remove", aliases=["rem", "del", "delete"])
    async def fatal_role_remove(
        self, ctx, role: discord.Role, target: discord.Role = None
    ):
        c = 0
        s = 0
        e = 0
        for m in (target or ctx.guild.default_role).members:
            c += 1
            try:
                await m.remove_roles(role)
                s += 1

            except discord.HTTPException:
                e += 1
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "fatal_role_remove").format(c, s, e),
            color=Success,
        )
        await ctx.reply(embed=e)

    @fatal_role.command(name="kick")
    async def fatal_role_kick(self, ctx, role: discord.Role, *, reason=None):
        c = 0
        s = 0
        e = 0
        for m in role.members:
            c += 1
            try:
                await m.kick(reason=reason)
                s += 1

            except discord.HTTPException:
                e += 1
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "fatal_role_kick").format(c, s, e),
            color=Success,
        )
        await ctx.reply(embed=e)

    @fatal_role.command(name="dm")
    @commands.cooldown(5, 600, commands.BucketType.guild)
    async def fatal_role_dm(self, ctx, role: discord.Role, *, message):
        c = 0
        s = 0
        e = 0
        await ctx.reply(f"送信を開始します。およそ{6 * len(role.members) / 60}分かかります。")
        em = discord.Embed(
            title=get_txt(ctx.guild.id, "fatal_role_dm_title").format(ctx.guild.name),
            description=message,
            color=Chat,
        )
        em.set_author(
            name=f"{ctx.author}(ID:{ctx.author.id})", icon_url=ctx.author.avatar.url
        )
        for m in role.members:
            c += 1
            await asyncio.sleep(5)
            try:

                await m.send(embed=em)
                s += 1

            except discord.HTTPException:
                e += 1
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "fatal_role_dm").format(c, s, e), color=Success
        )
        await ctx.reply(embed=e)

    @fatal_nick.command(name="shuffle")
    async def fatal_nick_shuffle(self, ctx):
        member_nicks = []
        targets = []
        for m in ctx.guild.members:
            if (
                m.top_role.position < ctx.guild.me.top_role.position
                and m.id != ctx.guild.owner_id
                and m.id != bot.user.id
            ):
                member_nicks.append(m.display_name)
                targets.append(m)
        #        sb#fatal shuffle_nick
        loop = asyncio.get_event_loop()
        random.shuffle(member_nicks)

        for i, m in enumerate(targets):
            loop.create_task(m.edit(nick=member_nicks[i]))
        e = discord.Embed(title=f"`{len(targets)}`人のニックネームをシャッフルしています。", color=Success)
        await ctx.reply(embed=e)

    @fatal_nick.command(name="reset")
    async def fatal_nick_reset(self, ctx):
        loop = asyncio.get_event_loop()
        c = 0
        for m in ctx.guild.members:
            if (
                m.top_role.position < ctx.guild.me.top_role.position
                and m.id != ctx.guild.owner_id
                and m.id != bot.user.id
            ):
                loop.create_task(m.edit(nick=None))
                c += 1
        e = discord.Embed(title=f"`{c}`人のニックネームをリセットしています。", color=Success)
        await ctx.reply(embed=e)

    @fatal_nick.command(name="export")
    async def fatal_nick_export(self, ctx):
        asyncio.get_event_loop()
        res = {}
        for m in ctx.guild.members:
            res[m.id] = m.display_name
        e = discord.Embed(
            title=f"`{len(res.keys())}`人のニックネームをエクスポートしました。", color=Success
        )
        sio = io.StringIO(json.dumps(res))
        await ctx.reply(
            embed=e,
            file=discord.File(
                sio, filename=f"{ctx.guild.id}_{int(time.time())}.sbnicks"
            ),
        )
        sio.close()

    @fatal_nick.command(name="import")
    async def fatal_nick_import(self, ctx):
        if len(ctx.message.attachments) == []:
            e = discord.Embed(title="エクスポートしたファイルを添付してください。", color=Error)
            await ctx.reply(embed=e)
            return
        try:
            l = json.loads(await ctx.message.attachments[0].read())
        except BaseException:
            e = discord.Embed(title="読み込みに失敗しました。", color=Error)
            await ctx.reply(embed=e)
            return
        asyncio.get_event_loop()
        c = 0
        for m in ctx.guild.members:
            if (
                m.top_role.position < ctx.guild.me.top_role.position
                and m.id != ctx.guild.owner_id
                and m.id != bot.user.id
            ):
                try:
                    await m.edit(nick=l[str(m.id)])
                    c += 1
                except KeyError:
                    pass
        e = discord.Embed(title=f"`{c}`人のニックネームをインポートしています。", color=Success)
        await ctx.reply(embed=e)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, target: discord.Member, count: int = 1):
        e = SEmbed(get_txt(ctx.guild.id, "warn").format(target, count), color=Info)
        if not Guild_settings[ctx.guild.id]["warns"].get(target.id):
            Guild_settings[ctx.guild.id]["warns"][target.id] = 0
        Guild_settings[ctx.guild.id]["warns"][target.id] += count
        pun = Guild_settings[ctx.guild.id]["warn_settings"]["punishments"]
        nw = Guild_settings[ctx.guild.id]["warns"][target.id]
        e.description += (
            get_txt(ctx.guild.id, "warn_desc_info").format(target, nw) + "\n"
        )
        if pun.get(nw):
            e.description += (
                get_txt(ctx.guild.id, "warn_desc_now").format(
                    nw, get_warn_text(self.bot, ctx, pun[nw])
                )
                + "\n"
            )
            await punish(target, pun[nw])

        if [c for c in sorted(pun.keys()) if c > nw]:
            l = [c for c in sorted(pun.keys()) if c > nw][0]
            e.description += get_txt(ctx.guild.id, "warn_desc_next").format(
                get_warn_text(self.bot, ctx, pun[l]), l
            )
        else:
            e.description += get_txt(ctx.guild.id, "warn_desc_next_none").format()
        await ctx.reply(embed=e)

    @commands.group(aliases=["ws"])
    async def warn_settings(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @warn_settings.command(name="add", aliases=["set"])
    @commands.has_guild_permissions(kick_members=True)
    async def ws_add(self, ctx, count: int, punish, arg=None):
        global Guild_settings
        res = {"action": punish}
        if punish not in get_txt(ctx.guild.id, "warn_punish").keys():
            return await ctx.reply(embed=SEmbed("不明な処罰です。"))
        elif punish == "mute":
            res["length"] = convert_timedelta(arg).total_seconds()
        elif punish == "role_add":
            res["role"] = (await commands.RoleConverter().convert(ctx, arg)).id
        elif punish == "role_remove":
            res["role"] = (await commands.RoleConverter().convert(ctx, arg)).id

        Guild_settings[ctx.guild.id]["warn_settings"]["punishments"][count] = res
        e = discord.Embed(title="処罰を追加しました。", color=Success)
        await ctx.reply(embed=e)

    @warn_settings.command(name="remove", aliases=["del", "delete", "rem"])
    @commands.has_guild_permissions(kick_members=True)
    async def ws_remove(self, ctx, *, txt):
        global Guild_settings
        res = ""
        count = 0
        new = {}
        if txt in Guild_settings[ctx.guild.id]["warn_settings"]["punishments"].keys():
            res += (
                "`"
                + Guild_settings[ctx.guild.id]["warn_settings"]["punishments"][txt][1]
                + "`\n"
            )
            for ark, ar in Guild_settings[ctx.guild.id]["warn_settings"][
                "punishments"
            ].items():
                if ark != txt:
                    new[ark] = ar
            count = 1
        else:
            for ark, ar in Guild_settings[ctx.guild.id]["warn_settings"][
                "punishments"
            ].items():
                if ar[0] == txt:
                    count += 1
                    res += "`" + ar[1] + "`\n"
                else:
                    new[ark] = ar
        if count == 0:
            e = discord.Embed(
                title=f"Warn`{txt}`回の処罰はありません。",
                description="`sb#warn_settings list`で確認してください。",
                color=Error,
            )
        else:
            e = discord.Embed(title="処罰を削除しました。", description=res, color=Success)
            Guild_settings[ctx.guild.id]["warn_settings"]["punishments"] = new
        await ctx.reply(embed=e)

    @warn_settings.command(name="list")
    async def ws_list(self, ctx):
        g = ctx.guild.id
        if g not in Guild_settings:
            await self.reset(ctx)
        gs = Guild_settings[g]
        if gs["warn_settings"]["punishments"] == {}:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ws_list_no"),
                description=get_txt(ctx.guild.id, "ws_list_desc"),
                color=Error,
            )
            await ctx.reply(embed=e)
        else:

            def make_new():
                table = Texttable()
                table.set_deco(Texttable.HEADER)
                table.set_cols_dtype(["t", "t"])
                table.set_cols_align(["l", "l"])
                table.add_row(get_txt(ctx.guild.id, "ws_list_row"))
                return table

            table = make_new()
            res = []
            for k, v in gs["warn_settings"]["punishments"].items():
                table.add_row([k, get_warn_text(self.bot, ctx, v)])
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ws_list"),
                description=f"```asciidoc\n{res}```",
                color=Info,
            )
            await ctx.reply(embed=e)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def mute(
        self,
        ctx,
        u: discord.Member,
        time: convert_timedelta = datetime.timedelta(hours=1),
    ):
        global Guild_settings
        if u == self.bot.user:
            return await ctx.reply(
                embed=SEmbed("SevenBotをミュートすることはできません。", color=Error)
            )
        if time.total_seconds() == 0:
            del Guild_settings[ctx.guild.id]["muted"][u.id]
            e = discord.Embed(title=f"`{u.display_name}`のミュートを解除しました。", color=Success)
            await ctx.reply(embed=e)
        else:
            dt = discord.utils.utcnow() + time
            Guild_settings[ctx.guild.id]["muted"][u.id] = dt.timestamp()
            e = discord.Embed(
                title=f"`{u.display_name}`を{discord.utils.format_dt(dt)}までミュートしました。",
                color=Success,
            )
            await ctx.reply(embed=e)


def setup(_bot):
    global bot
    bot = _bot
    #     logging.info("cog.py reloaded")
    _bot.add_cog(ModerationCog(_bot), override=True)
