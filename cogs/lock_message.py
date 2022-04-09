import time

import discord
import sembed
from discord.ext import commands

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (
    Activate_aliases,
    Chat,
    Deactivate_aliases,
    Error,
    Success,
)


class LockMessageCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        self.working = set()
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.group(aliases=["lm"], invoke_without_command=True)
    async def lock_message(self, ctx):
        await self.bot.send_subcommands(ctx)

    @lock_message.command(name="activate", aliases=Activate_aliases + ["register"])
    @commands.has_permissions(manage_messages=True)
    async def lock_message_activate(self, ctx, *, content):
        self.bot.guild_settings[ctx.guild.id]["lock_message_content"][ctx.channel.id] = {
            "content": content,
            "author": ctx.author.id,
        }
        await ctx.reply(
            embed=discord.Embed(
                title="メッセージを固定しました。",
                description=f"```\n{content}\n``` が最下部に表示されます。",
                color=Success,
            )
        )

    @lock_message.command(name="deactivate", aliases=Deactivate_aliases)
    @commands.has_permissions(manage_messages=True)
    async def lock_message_deactivate(self, ctx):
        try:
            del self.bot.guild_settings[ctx.guild.id]["lock_message_content"][ctx.channel.id]
        except KeyError:
            await ctx.reply(
                embed=discord.Embed(
                    title="固定されているメッセージはありません。",
                    color=Error,
                )
            )
        else:
            await ctx.reply(
                embed=discord.Embed(
                    title="メッセージの固定を解除しました。",
                    color=Success,
                )
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        if message.channel.id in self.working:
            return
        if message.author == self.bot.user:
            if embeds := message.embeds:
                if embeds[0].author.url and "?locked" in embeds[0].author.url:
                    return
        if content := self.bot.guild_settings[message.guild.id]["lock_message_content"].get(message.channel.id):
            self.working.add(message.channel.id)
            if message_id := self.bot.guild_settings[message.guild.id]["lock_message_id"].get(message.channel.id):
                if time.time() - discord.Object(message_id).created_at.timestamp() < 10:
                    return self.working.remove(message.channel.id)
                try:
                    await discord.PartialMessage(channel=message.channel, id=message_id).delete()
                except discord.NotFound:
                    pass
            author = message.guild.get_member(content["author"])
            if author is None:
                del self.bot.guild_settings[message.guild.id]["lock_message_content"][message.channel.id]
                self.working.remove(message.channel.id)
                return
            msg = await message.channel.send(
                embed=sembed.SEmbed(
                    description=content["content"],
                    color=Chat,
                    author=sembed.SAuthor(name=author.display_name, icon_url=author.display_avatar.url + "?locked"),
                )
            )
            self.bot.guild_settings[message.guild.id]["lock_message_id"][message.channel.id] = msg.id
            self.working.remove(message.channel.id)


async def setup(_bot):
    global bot
    bot = _bot
    await _bot.add_cog(LockMessageCog(_bot), override=True)
