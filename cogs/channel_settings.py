import discord
from discord.ext import commands

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (
    Activate_aliases,
    Deactivate_aliases,
    Success,
    Error,
)


class ChannelSettingCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        self.bot.guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.group(name="channel_settings", aliases=["ch"])
    @commands.has_permissions(manage_channels=True)
    async def channel_setting(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @channel_setting.command(name="slowmode", aliases=["cooldown"])
    @commands.has_permissions(manage_channels=True)
    async def ch_slowmode(self, ctx, sec: int):
        await ctx.channel.edit(slowmode_delay=sec)
        e = discord.Embed(
            title=get_txt(ctx.guild.id, "ch")["slowmode"][0].format(sec),
            color=Success,
        )
        return await ctx.reply(embed=e)

    @channel_setting.group(name="commands", aliases=["cmd"])
    @commands.has_permissions(manage_channels=True)
    async def ch_commands(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @channel_setting.group(name="auto_parse")
    @commands.has_permissions(manage_channels=True)
    async def ch_auto_parse(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_auto_parse.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_auto_parse(self, ctx):
        if ctx.channel.id not in self.bot.guild_settings[ctx.guild.id]["auto_parse"]:
            e = discord.Embed(
                title="既に無効化されています。",
                description="",
                color=Error
            )
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["auto_parse"].remove(ctx.channel.id)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`での自動パースを無効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)

    @ch_auto_parse.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_auto_parse(self, ctx):
        if ctx.channel.id not in self.bot.guild_settings[ctx.guild.id]["auto_parse"]:
            self.bot.guild_settings[ctx.guild.id]["auto_parse"].append(ctx.channel.id)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`での自動パースを有効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="2ch_link")
    @commands.has_permissions(manage_channels=True)
    async def ch_2ch_link(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_2ch_link.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_2ch_link(self, ctx):
        if ctx.channel.id not in self.bot.guild_settings[ctx.guild.id]["2ch_link"]:
            e = discord.Embed(
                title="既に無効化されています。",
                description="",
                color=Error
            )
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["2ch_link"].remove(ctx.channel.id)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`での2ch風メッセージリンクを無効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)

    @ch_2ch_link.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_2ch_link(self, ctx):
        if ctx.channel.id not in self.bot.guild_settings[ctx.guild.id]["2ch_link"]:
            self.bot.guild_settings[ctx.guild.id]["2ch_link"].append(ctx.channel.id)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`での2ch風メッセージリンクを有効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="lainan_talk", invoke_without_command=True)
    @commands.has_permissions(manage_channels=True)
    async def ch_lainan_talk(self, ctx):
        await self.bot.send_subcommands(ctx)

    @ch_lainan_talk.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_lainan_talk(self, ctx):
        if ctx.channel.id not in self.bot.guild_settings[ctx.guild.id]["lainan_talk"]:
            e = discord.Embed(title="既に無効化されています。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["lainan_talk"].remove(ctx.channel.id)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`でのLainan APIの返信を無効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)

    @ch_lainan_talk.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_lainan_talk(self, ctx):
        if ctx.channel.id not in self.bot.guild_settings[ctx.guild.id]["lainan_talk"]:
            self.bot.guild_settings[ctx.guild.id]["lainan_talk"].append(ctx.channel.id)
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`でのLainan APIの返信を有効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @ch_commands.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_command(self, ctx):
        if ctx.channel.id in self.bot.guild_settings[ctx.guild.id]["deactivate_command"]:
            e = discord.Embed(title="既に無効化されています。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["deactivate_command"].append(
                ctx.channel.id
            )
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`での管理者以外のコマンドを無効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)

    @ch_commands.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_command(self, ctx):
        if ctx.channel.id in self.bot.guild_settings[ctx.guild.id]["deactivate_command"]:
            self.bot.guild_settings[ctx.guild.id]["deactivate_command"].remove(
                ctx.channel.id
            )
            e = discord.Embed(
                title=f"`#{ctx.channel.name}`でのコマンドを有効にしました。",
                description="",
                color=Success,
            )
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(title="既に有効です。", description="", color=Error)
            return await ctx.reply(embed=e)

    @channel_setting.group(name="level")
    @commands.has_permissions(manage_channels=True)
    async def ch_level(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_level.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def ch_level_activate(self, ctx):
        if (
            ctx.channel.id
            not in self.bot.guild_settings[ctx.guild.id]["level_ignore_channel"]
        ):
            e = discord.Embed(title="既に有効です。", color=Error)
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["level_ignore_channel"].remove(
                ctx.channel.id
            )
            e = discord.Embed(
                title="このチャンネルでのレベリングが有効になりました。", description="", color=Success
            )
            return await ctx.reply(embed=e)

    @ch_level.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def ch_level_deactivate(self, ctx):
        if (
            ctx.channel.id
            in self.bot.guild_settings[ctx.guild.id]["level_ignore_channel"]
        ):
            e = discord.Embed(title="既に無効です。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["level_ignore_channel"].append(
                ctx.channel.id
            )
            e = discord.Embed(
                title="このチャンネルでのレベリングが無効になりました。", description="", color=Success
            )
            return await ctx.reply(embed=e)

    @channel_setting.group(name="translate", aliases=["trans"])
    @commands.has_permissions(manage_channels=True)
    async def ch_trans(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_trans.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_translate(self, ctx, lang):
        if ctx.channel.id in list(
            self.bot.guild_settings[ctx.guild.id]["trans_channel"].keys()
        ):
            e = discord.Embed(title="既に有効です。", color=Error)
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["trans_channel"][ctx.channel.id] = lang
            e = discord.Embed(
                title="自動翻訳が有効になりました。", description="", color=Success
            )
            return await ctx.reply(embed=e)

    @ch_trans.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_translate(self, ctx):
        if ctx.channel.id not in list(
            self.bot.guild_settings[ctx.guild.id]["trans_channel"].keys()
        ):
            e = discord.Embed(title="既に無効です。", description="", color=Error)
            return await ctx.reply(embed=e)
        else:
            del self.bot.guild_settings[ctx.guild.id]["trans_channel"][ctx.channel.id]
            e = discord.Embed(
                title="自動翻訳が無効になりました。", description="", color=Success
            )
            return await ctx.reply(embed=e)

    @channel_setting.group(name="auto_publish")
    @commands.has_permissions(manage_channels=True)
    async def ch_autopub(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)
        else:
            pass

    @ch_autopub.command(name="activate", aliases=Activate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def activate_autopub(self, ctx):
        if ctx.channel.id in self.bot.guild_settings[ctx.guild.id]["autopub"]:
            e = discord.Embed(title="既に有効です。", color=Error)
            return await ctx.reply(embed=e)
        elif ctx.channel.type == discord.ChannelType.news:
            self.bot.guild_settings[ctx.guild.id]["autopub"].append(ctx.channel.id)
            e = discord.Embed(title="自動公開が有効になりました。", color=Success)
            return await ctx.reply(embed=e)
        else:
            e = discord.Embed(title="自動公開はアナウンスチャンネルでのみ使用できます。", color=Error)
            return await ctx.reply(embed=e)

    @ch_autopub.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_channels=True)
    async def deactivate_autopub(self, ctx):
        if ctx.channel.id not in self.bot.guild_settings[ctx.guild.id]["autopub"]:
            e = discord.Embed(title="既に無効です。", color=Error)
            return await ctx.reply(embed=e)
        else:
            self.bot.guild_settings[ctx.guild.id]["autopub"].remove(ctx.channel.id)
            e = discord.Embed(title="自動公開が無効になりました。", color=Success)
            return await ctx.reply(embed=e)


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(ChannelSettingCog(_bot), override=True)
