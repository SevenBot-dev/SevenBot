import datetime
import time

import discord
from discord.ext import commands, components
from sembed import SEmbed

import _pathmagic  # type: ignore # noqa
from cogs.moderation import delta_to_text
from common_resources.consts import (  # Activate_aliases,; Deactivate_aliases,; Info,; Success,
    Error,
    Widget,
)
from common_resources.tools import convert_timedelta


class TicketCog(commands.Cog):
    def __init__(self, bot):
        global Texts
        global get_txt
        self.bot: commands.Bot = bot
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, pl: discord.RawReactionActionEvent):
        if pl.user_id == self.bot.user.id:
            return
        channel = self.bot.get_channel(pl.channel_id)
        try:
            message = await channel.fetch_message(pl.message_id)
        except (discord.errors.NotFound, discord.errors.Forbidden):
            return
        guild = self.bot.get_guild(pl.guild_id)
        user = guild.get_member(pl.user_id)
        if message.embeds == []:
            return
        if message.author.id != self.bot.user.id:
            return

        m0 = message.embeds[0]
        if m0.footer.text == "下の南京錠ボタンを押して終了":
            if await self.bot.db.tickets.find_one({"message": message.id}) is not None:
                await message.remove_reaction(pl.emoji, user)
                if pl.emoji.name == "lock":
                    await self.close_ticket(message, user, guild)
        if message.embeds[0].title == "チケット作成":
            await message.remove_reaction(pl.emoji, user)
            if pl.emoji.name == "add":
                success, status, data = await self.create_ticket(message, user, guild)
                if not success:
                    if status == "in_cooldown":
                        await message.channel.send(
                            user.mention,
                            embed=SEmbed(
                                color=Error,
                                description=f"作成の上限を超えています。<t:{int(data)}:R>に再度お試しください。",
                                footer="このメッセージは5秒後に削除されます。",
                            ),
                            delete_after=5,
                        )

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, com: components.ButtonResponse):
        if com.custom_id == "ticket_lock":
            await com.defer_update()
            await self.close_ticket(com.message, com.guild)
        elif com.custom_id == "ticket_create":
            success, status, data = await self.create_ticket(com.message, com.fired_by, com.guild)
            if not success:
                if status == "in_cooldown":
                    await com.send(
                        com.fired_by.mention,
                        embed=SEmbed(color=Error, description=f"作成の上限を超えています。<t:{int(data)}:R>に再度お試しください。"),
                        hidden=True,
                    )

    @commands.command(name="ticket")
    @commands.has_guild_permissions(manage_guild=True, manage_channels=True)
    async def ticket(self, ctx, subject, description, cooldown: convert_timedelta = datetime.timedelta(hours=1)):
        if self.bot.guild_settings[ctx.guild.id]["ticket_category"] == 0:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            cat = await ctx.guild.create_category("チケット", overwrites=overwrites)
            self.bot.guild_settings[ctx.guild.id]["ticket_category"] = cat.id
        else:
            cat = self.bot.get_channel(self.bot.guild_settings[ctx.guild.id]["ticket_category"])
        e = discord.Embed(title="チケット作成", description=subject, color=Widget)
        e.set_footer(text=f"{delta_to_text(cooldown, ctx)}に1回")
        m = await components.send(
            ctx,
            embed=e,
            components=[
                components.Button(
                    label="作成",
                    style=components.ButtonType.secondary,
                    custom_id="ticket_create",
                ),
            ],
        )
        await self.bot.db.tickets.insert_one(
            {
                "message": m.id,
                "subject": subject,
                "description": description,
                "count": 0,
                "cooldown": cooldown.total_seconds(),
            }
        )

    async def create_ticket(self, message: discord.Message, user: discord.User, guild: discord.Guild):
        ticket_data = await self.bot.db.tickets.find_one({"message": message.id})
        if ticket_time := self.bot.consts["ticket_time"].get(f"{guild.id}-{user.id}"):
            if time.time() - ticket_time < ticket_data["cooldown"]:
                return (
                    False,
                    "in_cooldown",
                    self.bot.consts["ticket_time"][f"{guild.id}-{user.id}"] + ticket_data["cooldown"],
                )

        self.bot.consts["ticket_time"][f"{guild.id}-{user.id}"] = time.time()
        cat = self.bot.get_channel(self.bot.guild_settings[guild.id]["ticket_category"])
        if cat is None:
            ow = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            cat = await guild.create_category_channel(name="チケット", overwrites=ow)
            self.bot.guild_settings[guild.id]["ticket_category"] = cat.id
        ow = cat.overwrites
        ow[user] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        await self.bot.db.tickets.update_one(
            {"message": message.id},
            {"$inc": {"count": 1}},
        )
        tc = await guild.create_text_channel(
            category=cat,
            name=f"チケット#{str(ticket_data['count']+1).zfill(4)}-アクティブ",
            overwrites=ow,
        )
        e = discord.Embed(title=ticket_data["subject"], description=ticket_data["description"], color=Widget)
        e.set_footer(text="下のボタンを押して終了")
        message = await components.send(
            tc,
            user.mention,
            embed=e,
            components=[components.Button("終了", "ticket_lock", components.ButtonType.danger)],
        )
        return True, message, tc

    async def close_ticket(self, message: discord.Message, guild: discord.Guild):
        if message.channel.name.endswith("-クローズ"):
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        await message.channel.edit(overwrites=overwrites, name=message.channel.name[0:-5] + "クローズ")
        await message.channel.send("チケットをクローズしました。")
        return True


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(TicketCog(_bot), override=True)
