import datetime
from typing import Optional

import discord
from discord.ext import commands

import _pathmagic  # type: ignore # noqa
from common_resources.consts import Error, Success, Widget
from common_resources.tools import convert_timedelta


class PanelCog(commands.Cog):
    def __init__(self, bot):
        global Texts, Number_emojis
        global get_txt
        self.bot: commands.Bot = bot
        self.bot.guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt
        Number_emojis = []
        for i in range(11):
            Number_emojis.append(self.bot.oemojis["b" + str(i)])

    @commands.command(aliases=["poll"])
    async def vote(
        self,
        ctx,
        title,
        time: Optional[convert_timedelta],
        multi: Optional[bool],
        *select,
    ):
        if multi is None:
            multi = True
        if time is None:
            time = datetime.timedelta(hours=1)
        if len(select) > 10:
            g = ctx.guild
            e = discord.Embed(
                title=get_txt(g.id, "vote_error")[0],
                description=get_txt(g.id, "vote_error")[0],
                color=Error,
            )
            return await ctx.reply(embed=e)
        dt = discord.utils.utcnow()
        g = ctx.guild
        dt += time
        e = discord.Embed(
            title=get_txt(g.id, "voting")[0], color=Widget, timestamp=dt
        )
        e.add_field(
            name=Texts[self.bot.guild_settings[g.id]["lang"]]["voting"][1],
            value=title,
            inline=False,
        )
        e.add_field(
            name=get_txt(g.id, "voting")[2],
            value=(
                Texts[self.bot.guild_settings[g.id]["lang"]]["voting"][3][0]
                if multi
                else get_txt(g.id, "voting")[3][1]
            ),
            inline=False,
        )
        s = ""
        for sfi, sf in enumerate(select):
            em = self.bot.oemojis["b" + str(sfi + 1)]
            s += f":black_small_square:｜{em}：{sf}\n"
        e.add_field(
            name=Texts[self.bot.guild_settings[g.id]["lang"]]["voting"][4],
            value=s,
            inline=False,
        )
        e.set_author(
            name=f"{ctx.author.display_name}(ID:{ctx.author.id})",
            icon_url=ctx.author.display_avatar.url,
        )
        e.set_footer(text=get_txt(ctx.guild.id, "voting")[5])
        m = await ctx.reply(embed=e)
        for sfi in range(len(select)):
            await m.add_reaction(Number_emojis[sfi + 1])

    @commands.command(aliases=["recruit", "apply"])
    async def party(
        self, ctx, title, time: Optional[convert_timedelta], max: int
    ):
        if time is None:
            time = datetime.timedelta(hours=1)
        dt = discord.utils.utcnow()
        dt += time
        e = discord.Embed(title="募集", color=Widget, timestamp=dt)
        e.add_field(name="タイトル", value=title, inline=False)
        e.add_field(name="最大人数", value=f"{max}人", inline=False)
        e.add_field(name="参加者(現在0人)", value="現在参加者はいません", inline=False)
        e.set_author(
            name=f"{ctx.author}(ID:{ctx.author.id})",
            icon_url=ctx.author.display_avatar.url,
        )
        e.set_footer(text=get_txt(ctx.guild.id, "voting")[5])
        m = await ctx.reply(embed=e)
        await m.add_reaction(self.bot.oemojis["check5"])
        await m.add_reaction(self.bot.oemojis["check6"])

    @commands.command(name="lang")
    @commands.has_guild_permissions(manage_guild=True)
    async def change_lang(self, ctx, lang_to):
        if lang_to not in Texts.keys():
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "change_lang")[0][0],
                description=get_txt(ctx.guild.id, "change_lang")[0][1].format(
                    lang_to
                ),
                color=Error,
            )
            return await ctx.reply(embed=e)
        self.bot.guild_settings[ctx.guild.id]["lang"] = lang_to
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "change_lang")[1][0],
            description=get_txt(ctx.guild.id, "change_lang")[1][1].format(
                lang_to
            ),
            color=Success,
        )
        return await ctx.reply(embed=e)


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(PanelCog(_bot), override=True)
