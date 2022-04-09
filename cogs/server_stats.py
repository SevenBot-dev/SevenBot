import asyncio

import discord
from discord import CategoryChannel
from discord.errors import Forbidden, NotFound
from discord.ext import commands, tasks

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (
    Activate_aliases,
    Deactivate_aliases,
    Error,
    Stat_dict,
    Success,
)


class ServerStatCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        self.bot.guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt
        self.batch_update_stat_channel.start()

    @commands.group()
    @commands.has_permissions(manage_guild=True)
    async def server_stat(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @server_stat.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_guild=True)
    async def ss_activate(self, ctx, *stats):
        cat = None
        if not stats:
            e = discord.Embed(
                title="統計が指定されていません。",
                description="`sb#help server_stat`で確認してください。",
                color=Error,
            )
            return await ctx.reply(embed=e)
        for stat in stats:
            if stat not in Stat_dict.keys():
                e = discord.Embed(
                    title=f"統計{stat}が見付かりませんでした。",
                    description="`sb#help server_stat`で確認してください。",
                    color=Error,
                )
                return await ctx.reply(embed=e)
        if self.bot.guild_settings[ctx.guild.id]["do_stat_channels"]:
            for sc in self.bot.guild_settings[ctx.guild.id]["stat_channels"].values():
                c = self.bot.get_channel(sc)
                if isinstance(c, CategoryChannel):
                    cat = c
                    continue
                if c is not None:
                    await c.delete()
        else:
            overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(connect=False)}
            cat = await ctx.guild.create_category("統計", overwrites=overwrites)
        for stat in stats:
            n = await ctx.guild.create_voice_channel(f"{Stat_dict[stat]}： --", category=cat)
            self.bot.guild_settings[ctx.guild.id]["stat_channels"][stat] = n.id
        self.bot.guild_settings[ctx.guild.id]["stat_channels"]["category"] = cat.id
        self.bot.guild_settings[ctx.guild.id]["do_stat_channels"] = True
        e = discord.Embed(
            title="統計チャンネルが有効になりました。",
            description="無効化するには`sb#server_stat deactivate`を実行してください。",
            color=Success,
        )
        return await ctx.reply(embed=e)

    @server_stat.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_guild=True)
    async def ss_deactivate(self, ctx):
        if self.bot.guild_settings[ctx.guild.id]["do_stat_channels"]:
            for sc in self.bot.guild_settings[ctx.guild.id]["stat_channels"].values():
                c = self.bot.get_channel(sc)
                if c is not None:
                    await c.delete()
            self.bot.guild_settings[ctx.guild.id]["stat_channels"] = {}
            self.bot.guild_settings[ctx.guild.id]["do_stat_channels"] = False
            e = discord.Embed(
                title="統計チャンネルが無効になりました。",
                description="もう一度有効にするには`sb#server_stat activate`を使用してください。",
                color=Success,
            )
            return await ctx.reply(embed=e)

    @tasks.loop(minutes=5, seconds=10)
    async def batch_update_stat_channel(self):
        for g in self.bot.guilds:
            try:
                if self.bot.guild_settings[g.id]["do_stat_channels"]:
                    for sck, scv in self.bot.guild_settings[g.id]["stat_channels"].items():
                        if sck == "category":
                            continue
                        s = self.bot.get_channel(scv)
                        if s is None:
                            continue

                        val = "--"
                        if sck == "members":
                            val = g.member_count
                        elif sck == "humans":
                            val = len(list(filter(lambda m: not m.bot, g.members)))
                        elif sck == "bots":
                            val = len(list(filter(lambda m: m.bot, g.members)))
                        elif sck == "channels":
                            val = (
                                len(g.text_channels)
                                + len(g.voice_channels)
                                - len(self.bot.guild_settings[g.id]["stat_channels"].keys())
                                + 1
                            )
                        elif sck == "text_channels":
                            val = len(g.text_channels)
                        elif sck == "voice_channels":
                            val = len(g.voice_channels) - len(self.bot.guild_settings[g.id]["stat_channels"].keys()) + 1
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

    def cog_unload(self):
        self.batch_update_stat_channel.stop()


async def setup(_bot):
    global bot
    bot = _bot
    await _bot.add_cog(ServerStatCog(_bot), override=True)
