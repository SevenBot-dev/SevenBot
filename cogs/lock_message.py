import time

import discord
import sembed
from common_resources.consts import Activate_aliases, Chat, Deactivate_aliases, Error, Success
from discord.ext import commands

import _pathmagic  # type: ignore # noqa


class LockMessageCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts, Official_emojis
        global get_txt
        self.bot: commands.Bot = bot
        Guild_settings = bot.guild_settings
        Official_emojis = bot.consts["oe"]
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.group(aliases=["lm"], invoke_without_command=True)
    async def lock_message(self, ctx):
        await self.bot.send_subcommands(ctx)

    @lock_message.command(name="activate", aliases=Activate_aliases + ["register"])
    @commands.has_permissions(manage_messages=True)
    async def lock_message_activate(self, ctx, *, content):
        Guild_settings[ctx.guild.id]["lock_message_content"][str(ctx.channel.id)] = {
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
            del Guild_settings[ctx.guild.id]["lock_message_content"][str(ctx.channel.id)]
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
    async def on_message(self, message):
        if message.guild is None:
            return
        if message.author == self.bot.user:
            if embeds := message.embeds:
                if embeds and "?locked" in embeds[0].author.url:
                    return
        if content := Guild_settings[message.guild.id]["lock_message_content"].get(str(message.channel.id)):
            if message_id := Guild_settings[message.guild.id]["lock_message_id"].get(str(message.channel.id)):
                if time.time() - discord.Object(message_id).created_at.timestamp() < 10:
                    return
                try:
                    await discord.PartialMessage(channel=message.channel, id=message_id).delete()
                except discord.NotFound:
                    pass
            author = message.guild.get_member(content["author"])
            if author is None:
                del Guild_settings[message.guild.id]["lock_message_content"][str(message.channel.id)]
                return
            msg = await message.channel.send(
                embed=sembed.SEmbed(
                    description=content["content"],
                    color=Chat,
                    author=sembed.SAuthor(
                        name=author.display_name,
                        icon_url=author.avatar.url + "?locked"
                    ),
                )
            )
            Guild_settings[message.guild.id]["lock_message_id"][str(message.channel.id)] = msg.id


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(LockMessageCog(_bot), override=True)
