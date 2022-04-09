import asyncio
import time

import discord
from discord.ext import commands, components, tasks
from texttable import Texttable

import _pathmagic  # type: ignore # noqa
from common_resources.consts import Error, Info, Success
from common_resources.tools import chrsize_len, convert_timedelta, remove_emoji, to_lts


class TimedRoleCog(commands.Cog):
    def __init__(self, bot):
        global Texts, Timed_roles
        global get_txt
        self.bot: commands.Bot = bot
        Timed_roles = self.bot.raw_config["tr"]
        self.bot.guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt
        self.remove_timed_role.start()

    @commands.Cog.listener("on_member_update")
    async def on_member_update(self, before, after):
        nr = set(after.roles) - set(before.roles)
        for r in nr:
            if r.id in self.bot.guild_settings[after.guild.id]["timed_role"]:
                t = self.bot.guild_settings[after.guild.id]["timed_role"][r.id]
                Timed_roles.append(
                    {
                        "time": time.time() + t,
                        "guild": after.guild.id,
                        "role": r.id,
                        "member": after.id,
                    }
                )

    @commands.group(aliases=["tr"])
    async def timed_role(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @timed_role.command(name="add", aliases=["set"])
    @commands.has_guild_permissions(manage_messages=True)
    async def tr_add(self, ctx, role: discord.Role, limit: convert_timedelta):
        self.bot.guild_settings[ctx.guild.id]["timed_role"][role.id] = limit.total_seconds()
        e = discord.Embed(
            title=f"時間つきロールに`@{role.name}`を追加しました。",
            description=f"戻すには`sb#timed_role remove @{role.name}`を使用してください。",
            color=Success,
        )
        return await ctx.reply(embed=e)

    @timed_role.command(name="remove", aliases=["del", "delete", "rem"])
    @commands.has_guild_permissions(manage_messages=True)
    async def tr_remove(self, ctx, *role: discord.Role):
        count = 0
        for r in role:
            try:
                del self.bot.guild_settings[ctx.guild.id]["timed_role"][r.id]
                count += 1
            except KeyError:
                pass
        if count == 0:
            e = discord.Embed(title="何も削除されませんでした。", color=Error)
        else:
            e = discord.Embed(title=f"{count}個の時間付きロールを削除しました。", color=Success)
        return await ctx.reply(embed=e)

    @timed_role.command(name="list")
    async def tr_list(self, ctx):
        g = ctx.guild.id
        if g not in self.bot.guild_settings:
            await self.reset(ctx)
        gs = self.bot.guild_settings[g]
        if gs["timed_role"] == {}:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "tr_list_no"),
                description=get_txt(ctx.guild.id, "tr_list_desc"),
                color=Error,
            )
            return await ctx.reply(embed=e)
        else:

            def make_new():
                table = Texttable(max_width=80)
                table.set_deco(Texttable.HEADER)
                table.set_cols_width(
                    [
                        max([chrsize_len(str(c)) for c in gs["timed_role"].keys()]),
                        max([chrsize_len(str(to_lts(c))) for c in gs["timed_role"].values()]),
                    ]
                )
                table.set_cols_dtype(["t", "t"])
                table.set_cols_align(["l", "l"])
                table.add_row(get_txt(ctx.guild.id, "tr_list_row"))
                return table

            table = make_new()
            res = []
            for k, v in gs["timed_role"].items():
                b = table.draw()
                if ctx.guild.get_role(k):
                    rn = ctx.guild.get_role(k).name
                else:
                    continue
                table.add_row([f"@{remove_emoji(rn)}", to_lts(v)])
                if len(table.draw()) > 2000:
                    res.append(b)
                    table = make_new()
                    table.add_row(
                        [
                            k,
                            v[0].replace("\n", get_txt(ctx.guild.id, "tr_list_br")),
                            v[1].replace("\n", get_txt(ctx.guild.id, "tr_list_br")),
                        ]
                    )
            res.append(table.draw())
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "tr_list") + f" - {1}/{len(res)}",
                description=f"```asciidoc\n{res[0]}```",
                color=Info,
            )
            buttons = [
                components.Button("前のページ", "left", style=2),
                components.Button("次のページ", "right", style=2),
                components.Button("終了", "exit", style=4),
            ]
            msg = await components.reply(ctx, embed=e, components=buttons)
            page = 0
            while True:
                try:
                    com = await self.bot.wait_for(
                        "button_click",
                        check=lambda com: com.message == msg and com.member == ctx.author,
                        timeout=60,
                    )
                    await com.defer_update()
                    if com.custom_id == "left":
                        if page > 0:
                            page -= 1
                        buttons[0].enabled = page != 0
                    elif com.custom_id == "right":
                        if page < (len(res) - 1):
                            page += 1
                        buttons[1].enabled = page != (len(res) - 1)
                    elif com.custom_id == "exit":
                        break
                    e = discord.Embed(
                        title=get_txt(ctx.guild.id, "tr_list") + f" - {page+1}/{len(res)}",
                        description=f"```asciidoc\n{res[page]}```",
                        color=Info,
                    )
                    await msg.edit(embed=e)
                except asyncio.TimeoutError:
                    break
            for c in buttons:
                c.enabled = False
            await components.edit(msg, components=buttons)

    @tasks.loop(minutes=1)
    async def remove_timed_role(self):
        nt = []
        for t in Timed_roles:
            if t["time"] < time.time():
                try:
                    guild = self.bot.get_guild(t["guild"])
                    await guild.get_member(t["member"]).remove_roles(guild.get_role(t["role"]))
                except (AttributeError, discord.Forbidden):
                    pass
            else:
                nt.append(t)

        Timed_roles.clear()
        Timed_roles.extend(nt)

    def cog_unload(self):
        self.remove_timed_role.stop()


async def setup(_bot):
    global bot
    bot = _bot
    await _bot.add_cog(TimedRoleCog(_bot), override=True)
