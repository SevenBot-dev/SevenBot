import math
import time
from typing import Union

import discord
from discord.ext import commands
from discord.errors import Forbidden
from texttable import Texttable

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (Activate_aliases, Deactivate_aliases,
                                     Info, Success, Error, Level)
from common_resources.tools import remove_emoji, chrsize_len


class LevelCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts, GBan, SB_Bans, Official_emojis
        global get_txt, is_command
        self.bot = bot
        Guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt
        is_command = self.bot.is_command
        GBan = self.bot.raw_config["gb"]
        Official_emojis = self.bot.consts["oe"]
        SB_Bans = self.bot.raw_config["sbb"]

    @commands.Cog.listener("on_message")
    async def on_message_level(self, message):
        if message.author.id in GBan.keys() or message.channel.id in self.bot.global_chats:
            return
        if not self.bot.is_ready():
            return
        if message.author.bot or message.channel.id in Guild_settings[message.guild.id]["lainan_talk"]:
            return
        if message.guild is None:
            if message.content == "level":
                us = await self.bot.db.user_settings.find_one({"uid": message.author.id})
                if us is None:
                    await self.bot.init_user_settings(message.author.id)
                    res = False
                elif us["level_dm"]:
                    await self.bot.db.user_settings.update_one({
                        "uid": message.author.id
                    }, {
                        "$set": {"level_dm": False}
                    })
                    res = False
                else:
                    await self.bot.db.user_settings.update_one({
                        "uid": message.author.id
                    }, {
                        "$set": {"level_dm": True}
                    })
                    res = True
                e = discord.Embed(title="通知設定", description="レベルアップ通知は" + (
                    "OFF" if res else "ON") + "になりました。", color=Success)
                await message.author.send(embed=e)
            return
        if message.author.id in SB_Bans.keys() and is_command(message):
            if SB_Bans[message.author.id] > time.time():
                return
        if Guild_settings[message.guild.id]["level_active"] and message.channel.id not in Guild_settings[message.guild.id]["level_ignore_channel"]:
            if message.author.id not in Guild_settings[message.guild.id]["level_counts"].keys():
                Guild_settings[message.guild.id]["level_counts"][message.author.id] = 0
                Guild_settings[message.guild.id]["levels"][message.author.id] = 0
            if not is_command(message):
                fax = 1
                for r in message.author.roles:
                    fax *= Guild_settings[message.guild.id]["level_boosts"].get(r.id, 1)
                fax *= Guild_settings[message.guild.id]["level_boosts"].get(message.author.id, 1)
                Guild_settings[message.guild.id]["level_counts"][message.author.id] += int(fax)
            if Guild_settings[message.guild.id]["levels"][message.author.id] * 10 <= Guild_settings[message.guild.id]["level_counts"][message.author.id]:
                Guild_settings[message.guild.id]["level_counts"][message.author.id] = 0
                Guild_settings[message.guild.id]["levels"][message.author.id] += 1
                l = Guild_settings[message.guild.id]["levels"][message.author.id]
                extra = ""
                rr = Guild_settings[message.guild.id]["level_roles"].get(l)
                if rr:
                    rr2 = message.guild.get_role(rr)
                    if rr2:
                        try:
                            await message.author.add_roles(rr2)
                            extra = f"レベル{l}になったため、{rr2.mention}が与えられました！"
                        except Forbidden:
                            extra = f"{rr2.mention}を与えられませんでした。"
                e = discord.Embed(
                    title="レベルアップ！", description=f"{message.guild.name}でのあなたのレベルが{l}に上がりました！\n次まで： {l*10}\n{extra}", color=Level)
                e.set_footer(text="`level` でレベルアップ通知を切り換え")
                us = await self.bot.db.user_settings.find_one({"uid": message.author.id})
                if us is None or us["level_dm"]:
                    try:
                        await message.author.send(embed=e)
                    except discord.errors.Forbidden:
                        pass
                if Guild_settings[message.guild.id]["level_channel"]:
                    e2 = discord.Embed(
                        title="レベルアップ！", description=f"{message.author.mention}のレベルが{l}に上がりました！\n{extra}", color=Level)
                    await self.bot.get_channel(Guild_settings[message.guild.id]["level_channel"]).send(embed=e2)

    @commands.command(aliases=["lv"])
    async def level(self, ctx, user: discord.User = None):
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc2"], color=Error)
            return await ctx.reply(embed=e)
        try:
            if user is None:
                u = ctx.author
            else:
                u = user
            if u.bot:
                e = discord.Embed(
                    title=f"{u.display_name}のレベル", description="Botにはレベルがありません。", color=Level)
                return await ctx.reply(embed=e)
            lv = Guild_settings[ctx.guild.id]["levels"][u.id]
            mc = Guild_settings[ctx.guild.id]["level_counts"][u.id]
            nm = lv * 10
            if nm == 0:
                p = 0
            else:
                p = math.floor(mc / nm * 100)
            e = Official_emojis["barl"]
            r = str(e)
            for i in range(10):
                if p >= (i * 10 + 10):
                    e = Official_emojis["barc210"]
                elif p <= (i * 10):
                    e = Official_emojis["barc1"]
                else:
                    e = Official_emojis[f"barc2{10-abs(p - (i*10+10))}"]
                r += str(e)
            e = Official_emojis["barr"]
            r += str(e)
            e = discord.Embed(
                title=f"{u.display_name}のレベル", description=f"レベル: {lv}\n{r} {p}%\n次まで: {nm-mc}", color=Level)
            return await ctx.reply(embed=e)
        except KeyError:
            e = discord.Embed(
                title=f"{u.display_name}のレベル", description="このユーザーはまだレベルを獲得していません。", color=Level)
            return await ctx.reply(embed=e)

    @commands.command(aliases=["level_rank"])
    async def level_ranking(self, ctx):
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc2"], color=Error)
            return await ctx.reply(embed=e)
        table = Texttable()
        table.set_deco(Texttable.HEADER)
        table.set_cols_dtype(['t', 't', 't',
                              't'])
        table.set_cols_align(["r", "l", "r", "r"])
        res = [get_txt(ctx.guild.id, "ls")["rank"]]
        tmp_ary = {}
        for k in Guild_settings[ctx.guild.id]["levels"].keys():
            if Guild_settings[ctx.guild.id]["levels"][k] not in tmp_ary.keys():
                tmp_ary[Guild_settings[ctx.guild.id]["levels"][k]] = []
            tmp_ary[Guild_settings[ctx.guild.id]["levels"][k]].append(
                [k, Guild_settings[ctx.guild.id]["level_counts"][k]])
        for tak, tav in tmp_ary.copy().items():
            tmp_ary[tak] = sorted(tav, key=lambda a: a[1], reverse=True)
        tmp_ary = sorted(tmp_ary.items(), key=lambda a: a[0], reverse=True)
        i = 0
        break_flag = False
        show_author = True
        for _, (tak, tav) in enumerate(tmp_ary):
            for t in tav:
                if i >= 10:
                    if show_author:
                        i += 1
                        continue
                    else:
                        break_flag = True
                        break
                i += 1
                taxp = t[1]
                m = ctx.guild.get_member(t[0])
                if m:
                    if m == ctx.author:
                        show_author = False
                    res.append([str(i) + ".", remove_emoji(str(m)), tak, taxp])
                else:
                    i -= 1
            if break_flag:
                break
        if show_author:
            try:
                a = [str(i) + ".", remove_emoji(str(ctx.author)), Guild_settings[ctx.guild.id]["levels"]
                     [ctx.author.id], Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id]]
                res.append([" ", " ", " ", " "])
                res.append(a)
            except KeyError:
                pass
        table.add_rows(res)
        e = discord.Embed(title=get_txt(ctx.guild.id, "ls")
                          ["rank_title"], description=f"```asciidoc\n{table.draw()}```", color=Info)
        return await ctx.reply(embed=e)

    @commands.group(name="level_settings", aliases=["ls"])
    @commands.has_guild_permissions(manage_guild=True)
    async def ls(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ls.command(name="activate", aliases=Activate_aliases)
    @commands.has_guild_permissions(manage_guild=True)
    async def ls_activate(self, ctx):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title="既に有効です。", description="レベルシステムを無効にするには`sb#level_settings deactivate`を使用してください。", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_active"] = True
            e = discord.Embed(
                title="レベルシステムが有効になりました。", description="レベルシステムを無効にするには`sb#level_settings deactivate`を使用してください。", color=Success)
            return await ctx.reply(embed=e)

    @ls.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_guild_permissions(manage_guild=True)
    async def ls_deactivate(self, ctx):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title="既に無効です。", description="レベルシステムを有効にするには`sb#level_settings activate`を使用してください。", color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_active"] = False
            e = discord.Embed(
                title="レベルシステムが無効になりました。", description="レベルシステムを有効にするには`sb#level_settings activate`を使用してください。", color=Success)
            return await ctx.reply(embed=e)

    @ls.group(name="manage", invoke_without_command=True)
    async def ls_manage(self, ctx):
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            await self.bot.send_subcommands(ctx)

    @ls_manage.group(name="add", aliases=["set"])
    async def ls_manage_add(self, ctx, target: discord.Member, xp: int):
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        elif xp > 10000:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "too_high"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] += xp
            if ctx.author.id not in Guild_settings[ctx.guild.id]["level_counts"].keys():
                Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] = 0
                Guild_settings[ctx.guild.id]["levels"][ctx.author.id] = 0
            while Guild_settings[ctx.guild.id]["levels"][ctx.author.id] * 10 <= Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id]:
                Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] -= Guild_settings[ctx.guild.id]["levels"][ctx.author.id] * 10
                Guild_settings[ctx.guild.id]["levels"][ctx.author.id] += 1
            e = discord.Embed(title=get_txt(ctx.guild.id, "ls")["manage"]["add"].format(
                target.display_name, xp), color=Success)
            return await ctx.reply(embed=e)

    @ls_manage.group(name="remove")
    async def ls_manage_remove(self, ctx, target: discord.Member, xp: int):
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            if ctx.author.id not in Guild_settings[ctx.guild.id]["level_counts"].keys():
                Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] = 0
                Guild_settings[ctx.guild.id]["levels"][ctx.author.id] = 0
            else:
                Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] -= xp
            while Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] < 0:
                Guild_settings[ctx.guild.id]["levels"][ctx.author.id] -= 1
                Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] = Guild_settings[ctx.guild.id]["levels"][ctx.author.id] * \
                    10 + \
                    Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id]
                if Guild_settings[ctx.guild.id]["levels"][ctx.author.id] < 0:
                    Guild_settings[ctx.guild.id]["levels"][ctx.author.id] = 0
                    Guild_settings[ctx.guild.id]["level_counts"][ctx.author.id] = 0
                    break
            e = discord.Embed(title=get_txt(ctx.guild.id, "ls")["manage"]["remove"].format(
                target.display_name, xp), color=Success)
            return await ctx.reply(embed=e)

    @ls_manage.group(name="reset")
    async def ls_manage_reset(self, ctx):
        if ctx.invoked_subcommand is not None:
            return
        elif not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_counts"] = {}
            Guild_settings[ctx.guild.id]["levels"] = {}
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["manage"]["reset"], color=Success)
            return await ctx.reply(embed=e)

    @ls.command(name="channel")
    @commands.has_guild_permissions(manage_guild=True)
    async def ls_channel(self, ctx, to: discord.TextChannel = None):
        global Guild_settings
        if ctx.invoked_subcommand is not None:
            return
        elif not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            if to is None:
                Guild_settings[ctx.guild.id]["level_channel"] = False
                d = "レベルアップお知らせチャンネルはなくなりました。"
            else:
                if to is None:
                    to = ctx.channel
                Guild_settings[ctx.guild.id]["level_channel"] = to.id
                d = f"レベルアップお知らせチャンネルは{to.mention}になりました。"
            e = discord.Embed(title="レベルアップお知らせチャンネル変更",
                              description=d, color=Success)
            return await ctx.reply(embed=e)

    @ls.group(name="boost", aliases=["b"])
    async def ls_boost(self, ctx):
        if ctx.invoked_subcommand is not None:
            return
        elif not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            await self.bot.send_subcommands(ctx)

    @ls_boost.command(name="add", aliases=["set"])
    async def ls_boost_add(self, ctx, target: Union[discord.Role, discord.Member], fax: float):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_boosts"][target.id] = fax
            e = discord.Embed(title=get_txt(ctx.guild.id, "ls")["boost"]["add"].format(fax), color=Success)
            return await ctx.reply(embed=e)

    @ls_boost.command(name="remove", aliases=["del", "delete", "rem"])
    async def ls_boost_remove(self, ctx, target: Union[discord.Role, discord.Member]):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            try:
                del Guild_settings[ctx.guild.id]["level_boosts"][target.id]
                e = discord.Embed(title=get_txt(ctx.guild.id, "ls")[
                                  "boost"]["remove"].format(target.name), color=Success)
            except KeyError:
                e = discord.Embed(title=get_txt(ctx.guild.id, "ls")[
                                  "boost"]["remove_fail"].format(target.name), color=Error)
            return await ctx.reply(embed=e)

    @ls_boost.command(name="list")
    async def ls_boost_list(self, ctx):
        g = ctx.guild.id
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            gs = Guild_settings[g]
            if gs["level_boosts"] == {}:
                e = discord.Embed(
                    title="登録されていません。", description="`sb#level_settings boost add`で登録してください。", color=Error)
                return await ctx.reply(embed=e)
            else:
                table = Texttable()
                table.set_deco(Texttable.HEADER)
                table.set_cols_dtype(['t', 'f'])
                table.set_cols_width([max([chrsize_len(str(c)) for c in gs["timed_role"].keys()]), max([chrsize_len(str(c)) for c in gs["timed_role"].values()])])
                table.set_cols_align(["l", "l"])
                res = [["ロール", "倍率"]]
                for k, v in gs["level_boosts"].items():
                    if ctx.guild.get_role(k):
                        rn = ctx.guild.get_role(k).name
                    elif ctx.guild.get_member(k):
                        rn = str(ctx.guild.get_member(k))
                    else:
                        continue
                    res.append([remove_emoji(rn), v])
                table.add_rows(res)
                e = discord.Embed(title=get_txt(ctx.guild.id, "ls")
                                  ["boost"]["list"], description=f"```asciidoc\n{table.draw()}```", color=Info)
                return await ctx.reply(embed=e)

    @ls.group(name="roles", aliases=["r"])
    async def ls_roles(self, ctx):
        if ctx.invoked_subcommand is not None:
            return
        elif not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            await self.bot.send_subcommands(ctx)

    @ls_roles.command(name="add", aliases=["set"])
    async def ls_role_add(self, ctx, lv: int, role: discord.Role):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["level_roles"][lv] = role.id
            e = discord.Embed(title=get_txt(ctx.guild.id, "ls")[
                              "roles"]["add"].format(lv), color=Success)
            return await ctx.reply(embed=e)

    @ls_roles.command(name="remove", aliases=["del", "delete", "rem"])
    async def ls_role_remove(self, ctx, lv: int):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            try:
                del Guild_settings[ctx.guild.id]["level_roles"][lv]
                e = discord.Embed(title=get_txt(ctx.guild.id, "ls")[
                                  "roles"]["remove"].format(lv), color=Success)
            except KeyError:
                e = discord.Embed(title=get_txt(ctx.guild.id, "ls")[
                                  "roles"]["remove_fail"].format(lv), color=Error)
            return await ctx.reply(embed=e)

    @ls_roles.command(name="list")
    async def ls_role_list(self, ctx):
        g = ctx.guild.id
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["level_active"]:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ls")["not_active"], description=get_txt(ctx.guild.id, "ls")["not_active_desc"], color=Error)
            return await ctx.reply(embed=e)
        else:
            gs = Guild_settings[g]
            if gs["level_roles"] == {}:
                e = discord.Embed(
                    title="登録されていません。", description="`sb#level_settings roles add`で登録してください。", color=Error)
                return await ctx.reply(embed=e)
            else:
                table = Texttable()
                table.set_deco(Texttable.HEADER)
                table.set_cols_dtype(['t',
                                      't'])
                table.set_cols_align(["l", "l"])
                res = [["レベル", "ロール"]]
                for k, v in gs["level_roles"].items():
                    if ctx.guild.get_role(v) is None:
                        continue
                    res.append([k, remove_emoji(ctx.guild.get_role(v).name)])
                table.add_rows(res)
                e = discord.Embed(title=get_txt(ctx.guild.id, "ls")
                                  ["roles"]["list"], description=f"```asciidoc\n{table.draw()}```", color=Info)
                return await ctx.reply(embed=e)


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(LevelCog(_bot))
