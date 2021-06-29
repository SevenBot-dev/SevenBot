import asyncio
import hashlib
import random
import time

import discord
from discord.ext import commands, components
import re2 as re
from texttable import Texttable

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (Info, Success, Error, Alert)


class AutoreplyCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts, Official_emojis, GBan, SB_Bans
        global get_txt, is_command
        self.bot: commands.Bot = bot
        is_command = self.bot.is_command
        Guild_settings = bot.guild_settings
        Official_emojis = bot.consts["oe"]
        Texts = bot.texts
        get_txt = bot.get_txt
        GBan = bot.raw_config["gb"]
        SB_Bans = bot.raw_config["sbb"]

    async def do_reply(self, ar, message, content):
        m = re.match(r"^([^:]+):([\s\S]*)$", ar[0])
        if m:
            cmd = m[1].lower()
            cnt = m[2]
            if cmd == "re":
                if re.search(cnt, content):
                    return True
            elif cmd == "fullmatch":
                if content.lower() == cnt.lower():
                    return True
            elif cmd == "channel":
                m2 = re.match(r"^([^|]*)\|([^|]*)$", cnt)
                if m2 is not None:
                    ch = m2.group(1).split(",")
                    for c in ch:
                        try:
                            fake_ctx = await self.bot.get_context(message)
                            channel = await commands.converter.TextChannelConverter().convert(fake_ctx, c)
                        except commands.errors.BadArgument:
                            pass
                        else:
                            if message.channel == channel:
                                ar[0] = m2.group(2)
                                return await self.do_reply(ar, message, content)
            elif cmd == "has-image":
                if message.attachments and [a for a in message.attachments if a.content_type.startswith("image")]:
                    ar[0] = cnt
                    return await self.do_reply(ar, message, content)
            else:
                return ar[0].lower() in content.lower()
        elif ar[0].lower() in content.lower():
            return True

        return False

    @commands.Cog.listener("on_message")
    async def on_message_ar(self, message):
        global Guild_settings
        if message.author.id in GBan.keys() or message.channel.id in self.bot.global_chats:
            return
        if not self.bot.is_ready():
            return
        if message.author.bot or message.channel.id in Guild_settings[message.guild.id]["lainan_talk"]:
            return
        if message.author.id in SB_Bans.keys() and is_command(message):
            if SB_Bans[message.author.id] > time.time():
                return
        arp = Guild_settings[message.guild.id].get("autoreply")
        random_tmp = []

        async def ar_send(ch, msg_content):
            try:
                m = re.match(r"^([^:]+):([\s\S]*)", msg_content)
                if m:
                    cmd = m[1].lower()
                    cnt = m[2]
                    if cmd == "noreply":
                        await ch.send(cnt)
                    elif cmd == "pingreply":
                        await message.reply(cnt, mention_author=True)
                    elif cmd == "react":
                        try:
                            await message.add_reaction(cnt)
                        except discord.errors.BadRequest:
                            await message.add_reaction(Official_emojis["check2"])
                    elif cmd == "random":
                        random_tmp.append(cnt)
                    else:
                        await message.reply(msg_content)
                else:
                    await message.reply(msg_content)
            except asyncio.TimeoutError:
                pass
        ga = []
        if arp is not None:
            for ar in arp.values():
                if await self.do_reply(ar, message, message.content) and not is_command(message):
                    ga.append(ar_send(message.channel, ar[1]))
        await asyncio.gather(*ga)
        if random_tmp:
            await ar_send(message.channel, random.choice(random_tmp))

    @commands.group(aliases=["ar"])
    async def autoreply(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @autoreply.command(name="add", aliases=["set"])
    @commands.has_guild_permissions(manage_messages=True)
    async def ar_add(self, ctx, base, *, reply):
        global Guild_settings
        dat = base + reply
        rid = hashlib.md5(dat.encode()).hexdigest()[0:8]
        if ctx.guild.id not in Guild_settings:
            await self.reset(ctx)
        if "autoreply" not in Guild_settings[ctx.guild.id]:
            Guild_settings[ctx.guild.id]["autoreply"] = {}
        Guild_settings[ctx.guild.id]["autoreply"][rid] = [base, reply]
        e = discord.Embed(title=f"自動返信に`{base}`を追加しました。",
                          description=f"戻すには`sb#autoreply remove {base}`または`sb#autoreply remove {rid}`を使用してください", color=Success)
        await ctx.reply(embed=e)
        if reply.startswith("!"):
            e = discord.Embed(title="注意！",
                              description="コマンドは`!コマンド名 内容`から`コマンド名:内容`へ移行しました。", color=Alert)
            await ctx.reply(embed=e)

    @autoreply.command(name="remove", aliases=["del", "delete", "rem"])
    @commands.has_guild_permissions(manage_messages=True)
    async def ar_remove(self, ctx, *, txt):
        global Guild_settings
        res = ""
        count = 0
        new = {}
        if txt in Guild_settings[ctx.guild.id]["autoreply"].keys():
            res += "`" + \
                Guild_settings[ctx.guild.id]["autoreply"][txt][1] + "`\n"
            for ark, ar in Guild_settings[ctx.guild.id]["autoreply"].items():
                if ark != txt:
                    new[ark] = ar
            count = 1
        else:
            for ark, ar in Guild_settings[ctx.guild.id]["autoreply"].items():
                if ar[0] == txt:
                    count += 1
                    res += "`" + ar[1] + "`\n"
                else:
                    new[ark] = ar
        if count == 0:
            e = discord.Embed(
                title=f"自動返信に`{txt}`は含まれていません。", description="`sb#autoreply list`で確認してください。", color=Error)
        else:
            e = discord.Embed(
                title=f"{count}個の自動返信を削除しました。", description=res, color=Success)
            Guild_settings[ctx.guild.id]["autoreply"] = new
        return await ctx.reply(embed=e)

    @autoreply.command(name="list")
    async def ar_list(self, ctx):
        g = ctx.guild.id
        if g not in Guild_settings:
            await self.reset(ctx)
        gs = Guild_settings[g]
        if gs["autoreply"] == {}:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "ar_list_no"), description=get_txt(ctx.guild.id, "ar_list_no_desc"), color=Error)
            return await ctx.reply(embed=e)
        else:
            def make_new():
                table = Texttable(max_width=80)
                table.set_deco(Texttable.HEADER)
                table.set_cols_dtype(['t', 't', 't'])
                table.set_cols_align(["l", "l", "l"])
                table.set_cols_width([8, 19, 20])
                table.add_row(get_txt(ctx.guild.id, "ar_list_row"))
                return table
            table = make_new()
            res = []
            for k, v in gs["autoreply"].items():
                b = table.draw()
                table.add_row([k, v[0].replace("\n", get_txt(ctx.guild.id, "ar_list_br")),
                               v[1].replace("\n", get_txt(ctx.guild.id, "ar_list_br"))])
                if len(table.draw()) > 2000:
                    res.append(b)
                    table = make_new()
                    table.add_row([k, v[0].replace("\n", get_txt(ctx.guild.id, "ar_list_br")),
                                   v[1].replace("\n", get_txt(ctx.guild.id, "ar_list_br"))])
            res.append(table.draw())
            e = discord.Embed(title=get_txt(ctx.guild.id, "ar_list")
                              + f" - {1}/{len(res)}", description=f"```asciidoc\n{res[0]}```", color=Info)
            buttons = [
                components.Button("前のページ", "left", style=2),
                components.Button("次のページ", "right", style=2),
                components.Button("終了", "exit", style=4),
            ]
            msg = await components.send(ctx, embed=e, reference=ctx.message.to_reference(), components=buttons)
            page = 0
            while True:
                try:
                    com = await self.bot.wait_for("button_click", check=lambda com: com.message == msg and com.member == ctx.author, timeout=60)
                    await com.defer_update()
                    if com.custom_id == "left":
                        if page > 0:
                            page -= 1
                        buttons[0].enabled = page != 0
                    elif com.custom_id == "right":
                        if page < (len(res) - 1):
                            page += 1
                        buttons[1].enabled = page != (len(res) - 1)
                    elif com.custom_id == "exit":
                        break
                    e = discord.Embed(title=get_txt(
                        ctx.guild.id, "ar_list") + f" - {page+1}/{len(res)}", description=f"```asciidoc\n{res[page]}```", color=Info)
                    await msg.edit(embed=e)
                except asyncio.TimeoutError:
                    break
            for c in buttons:
                c.enabled = False
            await components.edit(msg, components=buttons)


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(AutoreplyCog(_bot), override=True)
