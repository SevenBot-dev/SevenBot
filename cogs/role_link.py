import discord
from discord.errors import NotFound
from discord.ext import commands
from texttable import Texttable

import _pathmagic  # type: ignore # noqa
from common_resources.consts import Error, Info, Success
from common_resources.tools import remove_emoji


class RoleLinkCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        self.bot.guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if not self.bot.guild_settings.get(after.guild.id):
            return
        for r in after.roles:
            if r.id in self.bot.guild_settings[after.guild.id]["role_link"].keys():
                for rl in self.bot.guild_settings[after.guild.id]["role_link"][r.id]:
                    try:
                        await self.bot.get_guild(rl[0]).get_member(after.id).add_roles(
                            self.bot.get_guild(rl[0]).get_role(rl[1]),
                            reason=get_txt(after.guild.id, "role_link")["reason"].format(
                                self.bot.get_guild(rl[0]).name,
                                self.bot.get_guild(rl[0]).get_role(rl[1]).name,
                            ),
                        )
                    except AttributeError:
                        pass

    @commands.group(aliases=["rl"])
    @commands.has_guild_permissions(manage_roles=True)
    async def role_link(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @role_link.command(name="add", aliases=["set"])
    async def role_link_add(self, ctx, role: discord.Role, target: int, target_role: int):
        target = bot.get_guild(target)
        if not target:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "role_link")["unknown_server"],
                color=Error,
            )
            return await ctx.reply(embed=e)
        if target.get_member(ctx.author.id):
            if not target.get_member(ctx.author.id).guild_permissions.manage_roles:
                e = discord.Embed(
                    title=get_txt(ctx.guild.id, "role_link")["no_role_perm"],
                    color=Error,
                )
                return await ctx.reply(embed=e)
        else:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "role_link")["not_in_server"],
                color=Error,
            )
            return await ctx.reply(embed=e)
        target_role = target.get_role(target_role)
        if not target_role:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "role_link")["unknown_role"],
                color=Error,
            )
            return await ctx.reply(embed=e)
        elif (
            target.get_member(ctx.author.id).top_role.position <= target_role.position
            and not target.owner_id == ctx.author.id
        ):
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "role_link")["no_role_perm"],
                color=Error,
            )
            return await ctx.reply(embed=e)
        if role.id not in self.bot.guild_settings[ctx.guild.id]["role_link"].keys():
            self.bot.guild_settings[ctx.guild.id]["role_link"][role.id] = []
        self.bot.guild_settings[ctx.guild.id]["role_link"][role.id].append([target.id, target_role.id])
        if target_role.id not in self.bot.guild_settings[target.id]["role_link"].keys():
            self.bot.guild_settings[target.id]["role_link"][target_role.id] = []
        self.bot.guild_settings[target.id]["role_link"][target_role.id].append([ctx.guild.id, role.id])
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "role_link")["add"].format(role.name),
            description=get_txt(ctx.guild.id, "role_link")["add_desc"].format(
                ctx.guild.name,
                role.mention,
                target.name,
                "@" + target_role.name,
            ),
            color=Success,
        )
        return await ctx.reply(embed=e)

    @role_link.command(name="remove", aliases=["del", "delete", "rem"])
    async def role_link_remove(self, ctx, role: discord.Role, target_role: int):
        res = []
        g = 0
        for rl in self.bot.guild_settings[ctx.guild.id]["role_link"][role.id]:
            if rl[1] != target_role:
                res.append(rl)
            else:
                g = rl[0]
        if g == 0:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "role_link")["remove_fail"],
                color=Error,
            )
            return
        self.bot.guild_settings[ctx.guild.id]["role_link"][role.id] = res.copy()
        res = []
        for rl in self.bot.guild_settings[g]["role_link"][target_role]:
            if rl[1] != role.id:
                res.append(rl)
            else:
                g = rl[0]
        self.bot.guild_settings[g]["role_link"][role.id] = res.copy()
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "role_link")["remove"].format(role.name),
            color=Success,
        )
        return await ctx.reply(embed=e)

    @role_link.command(name="update")
    async def role_link_update(self, ctx):
        for m in ctx.guild.members:
            for r in m.roles:
                if r.id in self.bot.guild_settings[m.guild.id]["role_link"].keys():
                    for rl in self.bot.guild_settings[m.guild.id]["role_link"][r.id]:
                        try:
                            await self.bot.get_guild(rl[0]).get_member(m.id).add_roles(
                                self.bot.get_guild(rl[0]).get_role(rl[1]),
                                reason=get_txt(m.guild.id, "role_link")["reason"].format(
                                    self.bot.get_guild(rl[0]).name,
                                    self.bot.get_guild(rl[0]).get_role(rl[1]).name,
                                ),
                            )
                        except (NotFound, AttributeError):
                            pass
        e = discord.Embed(title=get_txt(ctx.guild.id, "role_link")["update"], color=Success)
        return await ctx.reply(embed=e)

    @role_link.command(name="list")
    async def role_link_list(self, ctx):
        g = ctx.guild.id

        gs = self.bot.guild_settings[g]
        if gs["role_link"] == {}:
            e = discord.Embed(
                title="登録されていません。",
                description="`sb#role_link add`で登録してください。",
                color=Error,
            )
            return await ctx.reply(embed=e)
        else:
            table = Texttable()
            table.set_deco(Texttable.HEADER)
            table.set_cols_dtype(["t", "t", "t"])
            table.set_cols_align(["c", "l", "c"])
            res = [["ロール", "サーバー", "ロール"]]
            for k, v in gs["role_link"].items():
                for v2 in v:
                    if ctx.guild.get_role(k) is None:
                        continue
                    elif self.bot.get_guild(v2[0]) is None:
                        continue
                    elif self.bot.get_guild(v2[0]).get_role(v2[1]) is None:
                        continue
                    res.append(
                        [
                            "@" + remove_emoji(ctx.guild.get_role(k).name),
                            remove_emoji(self.bot.get_guild(v2[0]).name),
                            "@" + remove_emoji(self.bot.get_guild(v2[0]).get_role(v2[1]).name),
                        ]
                    )
            table.add_rows(res)
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "role_link")["list"],
                description=f"```asciidoc\n{table.draw()}```",
                color=Info,
            )
            return await ctx.reply(embed=e)


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(RoleLinkCog(_bot), override=True)
