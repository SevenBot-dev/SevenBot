import re

import discord
from discord.ext import commands, components

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (
    Activate_aliases,
    Deactivate_aliases,
    Success,
    Error,
    Chat,
)

Message_url_re = re.compile(
    r"(?<!<)https?://(?:(?:ptb|canary)\.)?(?:discord(?:app)?\.com)/channels/(\d+)/(\d+)/(\d+)(?!>)"
)


class MessageExpandCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts, Official_emojis, GBan
        global get_txt
        self.bot: commands.Bot = bot
        Guild_settings = bot.guild_settings
        Official_emojis = bot.consts["oe"]
        GBan = bot.raw_config["gb"]
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.Cog.listener("on_message")
    async def on_message_message_expand(self, message):
        if message.author.id in GBan.keys():
            return
        if not self.bot.is_ready():
            return
        if message.guild is None:
            return
        if message.guild.id not in Guild_settings.keys():
            return
        if message.author.bot:
            return
        if (
            re.match(Message_url_re, message.content) is not None
            and Guild_settings[message.guild.id]["expand_message"]
        ):
            rids = re.match(Message_url_re, message.content)
            ids = [int(i) for i in [rids[1], rids[2], rids[3]]]
            flag = ids[0] == message.guild.id
            if not flag:
                try:
                    flag = bool(
                        self.bot.get_guild(ids[0]).get_member(message.author.id)
                    )
                except AttributeError:
                    flag = False
            if flag:
                c = self.bot.get_channel(ids[1])
                if c is None:
                    e = discord.Embed(
                        title=get_txt(message.guild.id, "expand_message_fail"),
                        description="",
                        color=Error,
                    )
                    await message.channel.send(embed=e)
                try:
                    try:
                        m = await c.fetch_message(ids[2])
                    except (discord.errors.NotFound, discord.errors.Forbidden):
                        return
                    mc = m.content
                    if not (
                        m.guild == message.guild or m.author == message.author
                    ):
                        return
                    if len(mc.splitlines()) > 10:
                        mc = "\n".join(mc.splitlines()[:10]) + "\n..."
                    if len(mc) > 1000:
                        mc = mc[:1000] + "..."
                    em = discord.Embed(
                        color=Chat, description=mc, timestamp=m.created_at
                    )
                    try:
                        em.set_image(url=m.attachments[0].url)
                    except BaseException:
                        pass
                    em.set_author(
                        name=m.author.display_name,
                        icon_url=getattr(
                            m.author.avatar, "url", discord.Embed.Empty
                        ),
                    )
                    footer = Texts[Guild_settings[message.guild.id]["lang"]][
                        "expand_message_footer"
                    ].format(m.channel)
                    if not ids[0] == message.guild.id:
                        footer = (
                            Texts[Guild_settings[message.guild.id]["lang"]][
                                "expand_message_footer3"
                            ].format(m.guild.name)
                            + footer
                        )
                    if m.embeds == []:
                        em.set_footer(
                            text=footer,
                            icon_url=getattr(
                                self.bot.get_guild(ids[0]).icon,
                                "url",
                                discord.Embed.Empty,
                            ),
                        )
                        await message.reply(embed=em)
                    else:
                        em.set_footer(
                            text=footer
                            + Texts[Guild_settings[message.guild.id]["lang"]][
                                "expand_message_footer2"
                            ].format(len(m.embeds)),
                            icon_url=getattr(
                                self.bot.get_guild(ids[0]).icon,
                                "url",
                                discord.Embed.Empty,
                            ),
                        )
                        await components.reply(
                            message, embeds=[em] + m.embeds[:9]
                        )
                except Exception as er:
                    e = discord.Embed(
                        title=get_txt(message.guild.id, "expand_message_fail"),
                        description="",
                        color=Error,
                    )
                    await message.reply(str(er), embed=e)

    @commands.group()
    @commands.has_guild_permissions(manage_messages=True)
    async def expand_message(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @expand_message.command(name="activate", aliases=Activate_aliases)
    @commands.has_guild_permissions(manage_messages=True)
    async def expand_activate(self, ctx):
        global Guild_settings
        gi = ctx.guild.id
        if Guild_settings[ctx.guild.id]["expand_message"]:
            e = discord.Embed(
                title=get_txt(gi, "activate_fail"),
                description=Texts[Guild_settings[gi]["lang"]][
                    "activate_desc"
                ].format("sb#expand_message deactivate"),
                color=Error,
            )
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["expand_message"] = True
            e = discord.Embed(
                title=get_txt(gi, "activate").format("メッセージ展開"),
                description=get_txt(gi, "activate_desc").format(
                    "sb#expand_message deactivate"
                ),
                color=Success,
            )
            return await ctx.reply(embed=e)

    @expand_message.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_guild_permissions(manage_messages=True)
    async def expand_deactivate(self, ctx):
        global Guild_settings
        gi = ctx.guild.id
        if not Guild_settings[ctx.guild.id]["expand_message"]:
            e = discord.Embed(
                title=get_txt(gi, "deactivate_fail"),
                description=get_txt(ctx.guild.id, "deactivate_desc").format(
                    "sb#expand_message activate"
                ),
                color=Error,
            )
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["expand_message"] = False
            e = discord.Embed(
                title=get_txt(gi, "deactivate").format("メッセージ展開"),
                description=get_txt(gi, "deactivate_desc").format(
                    "sb#expand_message activate"
                ),
                color=Success,
            )
            return await ctx.reply(embed=e)


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(MessageExpandCog(_bot), override=True)
