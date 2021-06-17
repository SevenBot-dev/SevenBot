import datetime
from typing import Optional

import discord
from discord.ext import commands, tasks

import _pathmagic  # type: ignore # noqa
from common_resources.consts import Time_format, Activate_aliases, Error, Success, Deactivate_aliases

Bump_id = 302050872383242240
Dissoku_id = 761562078095867916
Bump_color = 0x24b8b8
Dissoku_color = 0x7289da


class BumpCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts, Official_emojis, Dissoku_alerts, Bump_alerts
        global get_txt
        self.bot = bot
        Guild_settings = bot.guild_settings
        Official_emojis = bot.consts["oe"]
        Dissoku_alerts = bot.raw_config["da"]
        Bump_alerts = bot.raw_config["ba"]
        Texts = bot.texts
        get_txt = bot.get_txt
        self.batch_bump_alert.start()

    @commands.Cog.listener("on_message")
    async def on_message_bumps(self, message):

        if message.author.id == Bump_id and Guild_settings[message.guild.id]["do_bump_alert"]:
            try:
                if message.embeds[0].image != discord.Embed().Empty:
                    if "disboard.org/images/bot-command-image-bump.png" in str(message.embeds[0].image.url):
                        dt = datetime.datetime.utcnow()
                        dt += datetime.timedelta(hours=2)
                        sdt = dt.strftime(Time_format)
                        Bump_alerts[message.guild.id] = [
                            sdt, message.channel.id]
                        e = discord.Embed(title=get_txt(message.guild.id, "bump_detected"),
                                          description=get_txt(message.guild.id, "bump_detected_desc"), color=Bump_color)
                        await message.channel.send(embed=e)
            except IndexError:
                pass
        elif message.author.id == Dissoku_id and Guild_settings[message.guild.id]["do_dissoku_alert"]:
            try:
                if message.embeds[0].fields:
                    if message.guild.name in message.embeds[0].fields[0].name:
                        dt = datetime.datetime.utcnow()
                        dt += datetime.timedelta(hours=1)
                        sdt = dt.strftime(Time_format)
                        Dissoku_alerts[message.guild.id] = [
                            sdt, message.channel.id]
                        e = discord.Embed(title=get_txt(message.guild.id, "dissoku_detected"),
                                          description=get_txt(message.guild.id, "dissoku_detected_desc"), color=Dissoku_color)
                        await message.channel.send(embed=e)
            except IndexError:
                pass
        return

    @tasks.loop(seconds=10)
    async def batch_bump_alert(self):

        for rg in self.bot.guilds:
            gi = rg.id
            if gi not in Bump_alerts.keys():
                continue
            try:
                bt = datetime.datetime.strptime(
                    Bump_alerts[gi][0], Time_format)
                nt = datetime.datetime.utcnow()
                if bt < nt:
                    e = discord.Embed(title=get_txt(gi, "bump_alert"),
                                      description=get_txt(gi, "bump_alert_desc"), color=Bump_color)
                    c = self.bot.get_channel(Bump_alerts[gi][1])
                    m = ""
                    if Guild_settings[c.guild.id]["bump_role"]:
                        r = c.guild.get_role(
                            Guild_settings[c.guild.id]["bump_role"])
                        if r:
                            m = r.mention
                    await c.send(content=m, embed=e, allowed_mentions=discord.AllowedMentions(roles=True))
                    del Bump_alerts[gi]

            except BaseException:
                pass
        for gi, gs in Guild_settings.items():
            if gi not in Dissoku_alerts.keys():
                continue
            try:
                bt = datetime.datetime.strptime(
                    Dissoku_alerts[gi][0], Time_format)
                nt = datetime.datetime.utcnow()
                if bt < nt:
                    e = discord.Embed(title=get_txt(gi, "dissoku_alert"),
                                      description=get_txt(gi, "dissoku_alert_desc"), color=Dissoku_color)
                    c = self.bot.get_channel(Dissoku_alerts[gi][1])
                    m = ""
                    if Guild_settings[c.guild.id]["dissoku_role"]:
                        r = c.guild.get_role(
                            Guild_settings[c.guild.id]["dissoku_role"])
                        if r:
                            m = r.mention
                    await c.send(content=m, embed=e, allowed_mentions=discord.AllowedMentions(roles=True))
                    del Dissoku_alerts[gi]

            except Exception:
                pass

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def bump(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @bump.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def bump_activate(self, ctx):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["do_bump_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "activate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_bump_alert"] = True
            e = discord.Embed(title=get_txt(ctx.guild.id, "activate").format(
                "Bump通知"), color=Success)
            return await ctx.reply(embed=e)

    @bump.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def bump_deactivate(self, ctx):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["do_bump_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "deactivate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_bump_alert"] = False
            e = discord.Embed(title=get_txt(ctx.guild.id, "deactivate").format(
                "Bump通知"), color=Success)
            return await ctx.reply(embed=e)

    @bump.command(name="role")
    @commands.has_permissions(manage_messages=True)
    async def bump_role(self, ctx, role: Optional[discord.Role] = None):
        global Guild_settings
        if role:
            Guild_settings[ctx.guild.id]["bump_role"] = role.id
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "bump_role_set"), color=Success)
        else:
            Guild_settings[ctx.guild.id]["bump_role"] = None
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "bump_role_set_none"), color=Success)
        return await ctx.reply(embed=e)

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def dissoku(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @dissoku.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def dissoku_activate(self, ctx):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["do_dissoku_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "activate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_dissoku_alert"] = True
            e = discord.Embed(title=get_txt(ctx.guild.id, "activate").format(
                "ディス速通知"), color=Success)
            return await ctx.reply(embed=e)

    @dissoku.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def dissoku_deactivate(self, ctx):
        global Guild_settings
        if not Guild_settings[ctx.guild.id]["do_dissoku_alert"]:
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "deactivate_fail"), color=Error)
            return await ctx.reply(embed=e)
        else:
            Guild_settings[ctx.guild.id]["do_dissoku_alert"] = False
            e = discord.Embed(title=get_txt(ctx.guild.id, "deactivate").format(
                "ディス速通知"), color=Success)
            return await ctx.reply(embed=e)

    @dissoku.command(name="role")
    @commands.has_permissions(manage_messages=True)
    async def dissoku_role(self, ctx, role: Optional[discord.Role] = None):
        global Guild_settings
        if role:
            Guild_settings[ctx.guild.id]["dissoku_role"] = role.id
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "dissoku_role_set"), color=Success)
        else:
            Guild_settings[ctx.guild.id]["dissoku_role"] = None
            e = discord.Embed(title=get_txt(
                ctx.guild.id, "dissoku_role_set_none"), color=Success)
        return await ctx.reply(embed=e)

    def cog_unload(self):
        self.batch_bump_alert.stop()


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(BumpCog(_bot))
