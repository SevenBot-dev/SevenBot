import discord
from discord.ext import commands
from sembed import SEmbed

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (
    Activate_aliases,
    Deactivate_aliases,
    Error,
    Info,
    Success,
)


class AutoTextCog(commands.Cog):
    def __init__(self, bot):
        global Texts, Auto_text_channels
        global get_txt
        self.bot: commands.Bot = bot
        self.bot.guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt
        if self.bot.consts.get("atc"):
            Auto_text_channels = self.bot.consts["atc"]
        else:
            Auto_text_channels = {}
            self.bot.consts["atc"] = Auto_text_channels

    @commands.group(aliases=["at"], invoke_without_command=True)
    async def auto_text(self, ctx):
        await self.bot.send_subcommands(ctx)

    @auto_text.command("activate", aliases=Activate_aliases)
    async def auto_text_activate(self, ctx, channel: discord.VoiceChannel):
        if channel.category is None:
            return await ctx.reply(embed=SEmbed("VCが条件を満たしていません。", "VCはカテゴリに入っている必要があります。", color=Error))
        elif channel.id in self.bot.guild_settings[ctx.guild.id]["auto_text"]:
            return await ctx.reply(
                embed=SEmbed(
                    "VCはすでに有効です。",
                    f"無効化するには`sb#auto_text deactivate #{channel.name}`を使用して下さい。",
                    color=Error,
                )
            )
        self.bot.guild_settings[ctx.guild.id]["auto_text"].append(channel.id)
        await ctx.reply(
            embed=SEmbed(
                "自動TCを有効にしました。",
                f"無効化するには`sb#auto_text deactivate #{channel.name}`を使用して下さい。",
                color=Success,
            )
        )

    @auto_text.command("deactivate", aliases=Deactivate_aliases)
    async def auto_text_deactivate(self, ctx, channel: discord.VoiceChannel):
        if channel.id not in self.bot.guild_settings[ctx.guild.id]["auto_text"]:
            return await ctx.reply(
                embed=SEmbed(
                    "VCはすでに無効です。",
                    f"有効化するには`sb#auto_text activate #{channel.name}`を使用して下さい。",
                    color=Error,
                )
            )
        self.bot.guild_settings[ctx.guild.id]["auto_text"].remove(channel.id)
        await ctx.reply(
            embed=SEmbed(
                "自動TCを無効にしました。",
                f"有効化するには`sb#auto_text activate #{channel.name}`を使用して下さい。",
                color=Success,
            )
        )

    @commands.Cog.listener()
    async def on_voice_channel_update(
        self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ):
        if before is not None and (not before.members) and before in Auto_text_channels:
            try:
                await Auto_text_channels[before].delete()
            except discord.NotFound:
                pass
            del Auto_text_channels[before]
        if (
            after is not None
            and after.channel.id in self.bot.guild_settings[member.guild.id]["auto_text"]
            and after.channel.id not in Auto_text_channels
        ):
            ntc = await after.category.create_text_channel(
                after.name,
                topic=f"このチャンネルは{after.channel.mention}に誰もいなくなったら自動的に消去されます。",
            )
            Auto_text_channels[after] = ntc
            await ntc.send(
                member.mention,
                embed=SEmbed(
                    "",
                    f"このチャンネルは{after.channel.mention}に誰もいなくなったら自動的に消去されます。",
                    color=Info,
                ),
            )


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(AutoTextCog(_bot), override=True)
