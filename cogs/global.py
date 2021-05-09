import asyncio
import hashlib
import io
import json
import os
import re
import time
import urllib.parse

import aiohttp
import discord
from discord.ext import commands
from discord.errors import Forbidden, NotFound
from sembed import SEmbed  # , SField, SAuthor, SFooter
import _pathmagic  # type: ignore # noqa
from common_resources.consts import (Info, Success, Error, Chat, Official_discord_id, Owner_ID, Activate_aliases, Deactivate_aliases, Process)
from common_resources.tools import (flatten)


SGC_ID = 707158257818664991
SGC_ID2 = 799184205316751391
SGC_STOP = False
Gc_last_users = {}
Image_exts = ["gif", "jpg", "jpeg", "jpe", "jfif", "png", "bmp", "ico"]
Cant_image = "https://i.imgur.com/UuhmAUG.png"
INVITE_PATTERN = re.compile(
    r"(https?://)?((ptb|canary)\.)?(discord.(gg|io)|discord(app)?.com/invite)/[0-9a-zA-Z]+")


class GlobalCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Official_emojis, Private_chats, Global_chat, Global_mute, Private_chat_pass, Private_chat_author
        global get_txt, is_command
        self.bot = bot
        Guild_settings = bot.raw_config["gs"]
        Global_chat = bot.raw_config["gc"]
        Official_emojis = bot.consts["oe"]
        Private_chats = bot.raw_config["pc"]
        Global_mute = bot.raw_config["gm"]
        Private_chat_pass = bot.raw_config["pp"]
        Private_chat_author = bot.raw_config["pa"]
        get_txt = bot.get_txt
        is_command = bot.is_command

    @commands.Cog.listener("on_message")
    async def on_message_global(self, message):
        if message.channel.id in [SGC_ID, SGC_ID2] and message.author.id != self.bot.user.id and not SGC_STOP:
            loop = asyncio.get_event_loop()
            ga = []
            deletes = []
            whname = "sevenbot-private-webhook-sgc"
            each = Private_chats["sgc"]
            # print(message.content)
            try:
                data = json.loads(message.content)
            except json.JSONDecodeError:
                return
            # print(data)
            if data.get("isBot", False):
                return
            loop.create_task(message.add_reaction(Official_emojis["network"]))
            if data.get("type", "message") == "message":

                async def single_send(cn):
                    ch_webhooks = await cn.webhooks()
                    webhook = discord.utils.get(
                        ch_webhooks, name=whname)
                    if webhook is None:
                        g = self.bot.get_guild(
                            Official_discord_id)
                        a = g.icon_url_as(format="png")
                        webhook = await cn.create_webhook(name=whname, avatar=await a.read())
                    fl = []
                    for at in message.attachments:
                        fl.append(await at.to_file())
                    un = data["userName"] + "#" + data["userDiscriminator"]
                    un += "("
                    if message.author.id == Owner_ID:
                        un = "[👑]" + un
                    elif bot.get_guild(Official_discord_id).get_member(message.author.id) is not None:
                        m = bot.get_guild(Official_discord_id).get_member(
                            message.author.id)
                        if self.bot.is_premium(m):
                            un = "[💎]" + un
                        elif bot.get_guild(Official_discord_id).get_role(741837982012538910) in m.roles:
                            un = "[✔️]" + un  # 747555900092580030
                        elif bot.get_guild(Official_discord_id).get_role(747555900092580030) in m.roles:
                            un = "[⭕]" + un

                    un += f"ID:{data['userId']}, From:{message.author})"
                    files = []
                    async with aiohttp.ClientSession() as s:
                        for a in data.get('attachmentsUrl', []):
                            u = urllib.parse.unquote(a)
                            fio = io.BytesIO()
                            async with s.get(u) as r:
                                fio.write(await r.read())

                            fio.seek(0)
                            files.append(discord.File(
                                fio, filename=u.split("/")[-1]))
                            fio.close()
                    return await webhook.send(content=data["content"],  # content.replace("@", "@​")
                                              username=un,
                                              allowed_mentions=discord.AllowedMentions.none(),
                                              avatar_url=f"https://media.discordapp.net/avatars/{data['userId']}/{data['userAvatar']}.{'gif' if data['userAvatar'].startswith('a_') else 'png'}?size=1024",
                                              files=files,
                                              wait=True)
                for c in each:
                    cn = self.bot.get_channel(c)
                    if cn is None:
                        deletes.append(c)
                        continue
                    else:
                        if cn.guild.me.permissions_in(cn).manage_webhooks:
                            if not c == message.channel.id:
                                ga.append(single_send(cn))
                                # await
                                # webhook.edit(avater_url="https://i.imgur.com/JffqEAl.png")
                self.bot.consts["gcm"][data.get("messageId", message.id)] = await asyncio.gather(*ga)
                if len(list(self.bot.consts["gcm"]["sgc"].keys())) > 30:
                    del self.bot.consts["gcm"]["sgc"][list(
                        self.bot.consts["gcm"]["sgc"].keys())[0]]
                loop.create_task(message.remove_reaction(
                    Official_emojis["network"], self.bot.user))
                loop.create_task(message.add_reaction(
                    Official_emojis["check8"]))
            elif data.get("type", "message") == "edit":
                ga = []
                for m in self.bot.consts["gcm"].get(data["messageId"], []):
                    ga.append(m.edit(content=data["content"]))

                await asyncio.gather(*ga)
            elif data.get("type", "message") == "delete":
                ga = []
                for m in self.bot.consts["gcm"].get(data["messageId"], []):
                    ga.append(m.delete())

                await asyncio.gather(*ga)
            elif data.get("type", "message") == "gg-gcconnect":
                async def single_send(cn):
                    ch_webhooks = await cn.webhooks()
                    webhook = discord.utils.get(
                        ch_webhooks, name=whname)
                    if webhook is None:
                        g = self.bot.get_guild(
                            Official_discord_id)
                        a = g.icon_url_as(format="png")
                        webhook = await cn.create_webhook(name=whname, avatar=await a.read())
                    fl = []
                    for at in message.attachments:
                        fl.append(await at.to_file())
                    un = str(message.author)
                    un += "("
                    un += f"ID:{message.author.id})"
                    e = SEmbed("新しいサーバーが参加しました。", data["guildName"])
                    if data['guildIcon']:
                        e.thumbnail_url = f"https://cdn.discordapp.com/icons/{data['guildId']}/{data['guildIcon']}." + (
                            "gif" if data['guildIcon'].startswith("a_") else "png")
                    return await webhook.send(embed=e,  # content.replace("@", "@​")
                                              username=un,
                                              allowed_mentions=discord.AllowedMentions.none(),
                                              avatar_url=message.author.avatar_url_as(
                                                  static_format="png"),
                                              wait=True)
                for c in each:
                    cn = self.bot.get_channel(c)
                    if cn is None:
                        deletes.append(c)
                        continue
                    else:
                        if cn.guild.me.permissions_in(cn).manage_webhooks:
                            if not c == message.channel.id:
                                ga.append(single_send(cn))
                loop.create_task(message.add_reaction(
                    Official_emojis["check8"]))
            return
        if (message.channel.id in Global_chat or message.channel.id in flatten(list(Private_chats.values()))) and (not message.author.bot and not message.webhook_id):
            if is_command(message):
                pass
            else:
                if message.author.id in Global_mute:
                    await message.delete()
                    e2 = discord.Embed(title="あなたはミュートされています。", info=Error)
                    await message.author.send(embed=e2)
                else:
                    if message.author.id in Gc_last_users.keys() and time.time() - Gc_last_users[message.author.id] < 5:
                        await message.add_reaction(Official_emojis["queue"])
                        await asyncio.sleep(5)
                        await message.remove_reaction(Official_emojis["queue"], self.bot.user)
                    Gc_last_users[message.author.id] = time.time()
                    await message.add_reaction(Official_emojis["network"])
                    e = discord.Embed(description=message.content,
                                      timestamp=message.created_at, color=Chat)
                    if message.attachments != []:
                        u = message.attachments[0].url
                        if "".join(os.path.splitext(os.path.basename(message.attachments[0].filename))[1:])[1:] not in Image_exts:
                            u = Cant_image
                        e.set_image(url=u)
                    e.set_author(name=f"{message.author}(ID:{message.author.id})",
                                 icon_url=message.author.avatar_url_as(static_format="png"))
                    e.set_footer(text=f"{message.guild.name}(ID:{message.guild.id})",
                                 icon_url=message.guild.icon_url_as(static_format="png"))
                    # loop = asyncio.get_event_loop()
                    ga = []
                    if message.channel.id in flatten(list(Private_chats.values())):
                        for pk, pv in Private_chats.items():
                            if message.channel.id in pv:
                                pn = pk
                                each = pv
                                break
                        whname = f"sevenbot-private-webhook-{pn}"
                        gms = self.bot.consts["gcm"][pn]
                    else:
                        whname = "sevenbot-global-webhook"
                        gms = self.bot.consts["gcm"][None]
                        each = Global_chat
                    deletes = []
                    gms[message.id] = []
                    content = re.sub(
                        INVITE_PATTERN, "[Invite link]", message.content) if whname == "sevenbot-global-webhook" else message.content
                    if whname == "sevenbot-global-webhook":
                        if len(content.splitlines()) > 10:
                            content = "\n".join(
                                content.splitlines()[:10]) + "\n..."

                        if len(content) > 1000:
                            content = content[:1000] + "..."

                    async def ss(wh, **kwargs):
                        return await wh.send(**kwargs)
                    try:
                        for c in each:
                            cn = self.bot.get_channel(c)
                            if cn is None:
                                deletes.append(c)
                                continue
                            else:
                                # print(cn)
                                try:
                                    if cn.guild.me.permissions_in(cn).manage_webhooks:
                                        if not c == message.channel.id:
                                            ch_webhooks = await cn.webhooks()
                                            webhook = discord.utils.get(
                                                ch_webhooks, name=whname)
                                            if webhook is None:
                                                g = self.bot.get_guild(
                                                    Official_discord_id)
                                                a = g.icon_url_as(format="png")
                                                webhook = await cn.create_webhook(name=whname, avatar=await a.read())
                                            fl = []
                                            for at in message.attachments:
                                                fl.append(await at.to_file())
                                            un = str(message.author)
                                            un += "("

                                            if message.author.id == Owner_ID:
                                                un = "[👑]" + un
                                            elif self.bot.get_guild(Official_discord_id).get_member(message.author.id) is not None:
                                                m = self.bot.get_guild(Official_discord_id).get_member(
                                                    message.author.id)
                                                if self.bot.get_guild(Official_discord_id).get_role(741837982012538910) in m.roles:
                                                    un = "[🛠️]" + un
                                                elif self.bot.is_premium(message.author):
                                                    un = "[💎]" + un
                                                elif self.bot.get_guild(Official_discord_id).get_role(747555900092580030) in m.roles:
                                                    un = "[✔️]" + un

                                            un += f"ID:{message.author.id})"
                                            rem = None
                                            if message.reference:
                                                try:
                                                    rmsg = await message.channel.fetch_message(message.reference.message_id)
                                                    rem = discord.Embed(
                                                        description=rmsg.content, color=Chat)
                                                    rem.set_author(
                                                        name=rmsg.author.name, icon_url=rmsg.author.avatar_url_as(static_format="png"))
                                                except discord.errors.NotFound:
                                                    rem = None
                                            ga.append(ss(webhook, content=content,  # content.replace("@", "@​")
                                                         username=un,
                                                         allowed_mentions=discord.AllowedMentions.none(),
                                                         avatar_url=message.author.avatar_url_as(
                                                             static_format="png"),
                                                         files=fl,
                                                         embed=rem,
                                                         wait=True))
                                            # await
                                            # webhook.edit(avater_url="https://i.imgur.com/JffqEAl.png")
                                    else:
                                        await cn.send(embed=e)
                                        tmp = False
                                        for a in message.attachments:
                                            if not tmp:
                                                tmp = True
                                                continue
                                            e3 = discord.Embed(color=Chat)
                                            u = a.url

                                            if "".join(os.path.splitext(os.path.basename(a.filename))[1:])[1:] not in Image_exts:
                                                u = Cant_image
                                            e3.set_image(url=u)
                                            await cn.send(embed=e3)
                                except discord.HTTPException:
                                    pass
                        if not message.guild.me.permissions_in(message.channel).manage_webhooks:
                            await message.delete()
                        for d in deletes:
                            each.remove(d)
                        r = await asyncio.gather(*ga)
                        # print(r)
                        gms[message.id] = r
                        if len(list(gms.keys())) > 30:
                            del gms[list(gms.keys())[0]]
                        if message.channel.id in flatten(list(Private_chats.values())) and pn == "sgc":
                            rjson = {
                                "type": "message",
                                "userId": message.author.id,
                                "userName": message.author.name,
                                "userDiscriminator": message.author.discriminator,
                                "userAvatar": message.author.avatar,
                                "isBot": message.author.bot,
                                "guildId": message.guild.id,
                                "guildName": message.guild.name,
                                "guildIcon": message.guild.icon,
                                "channelId": message.channel.id,
                                "channelName": message.channel.name,
                                "messageId": message.id,
                                "content": content,
                                "sb-tag": {
                                    "type": None
                                },
                                "sb-rawContent": message.content
                            }
                            if message.attachments:
                                rjson["attachmentsUrl"] = [urllib.parse.quote(
                                    a.url) for a in message.attachments]

                            if message.author.id == Owner_ID:
                                rjson["sb-tag"] = {
                                    "type": "admin",
                                    "emoji": "👑"
                                }
                            elif self.bot.get_guild(Official_discord_id).get_member(message.author.id) is not None:
                                m = self.bot.get_guild(Official_discord_id).get_member(
                                    message.author.id)
                                if self.bot.get_guild(Official_discord_id).get_role(741837982012538910) in m.roles:
                                    rjson["sb-tag"] = {
                                        "type": "moderator",
                                        "emoji": "🛠️"
                                    }
                                elif self.bot.is_premium(message.author):
                                    rjson["sb-tag"] = {
                                        "type": "premium",
                                        "emoji": "💎"
                                    }
                                elif self.bot.get_guild(Official_discord_id).get_role(747555900092580030) in m.roles:
                                    rjson["sb-tag"] = {
                                        "type": "special",
                                        "emoji": "✔️"
                                    }
                            await self.bot.get_channel(SGC_ID).send(json.dumps(rjson, ensure_ascii=False))
                            # await self.bot.get_channel(SGC_ID).send(json.dumps(rjson, ensure_ascii=False))
                        try:
                            await message.remove_reaction(Official_emojis["network"], message.guild.me)

                            await message.add_reaction(Official_emojis["check8"])
                            await asyncio.sleep(2)
                            await message.remove_reaction(Official_emojis["check8"], message.guild.me)
                        except NotFound:
                            pass
                    except discord.HTTPException:
                        pass

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if (message.channel.id in Global_chat or message.channel.id in flatten(list(Private_chats.values()))) and not message.author.bot:
            # mi = 0
            dga = []
            if message.channel.id in Global_chat:
                e = None
            else:
                for pck, pc in Private_chats.items():
                    if message.channel.id in pc:
                        e = pck
                        break
            if e == "sgc":
                await self.bot.get_channel(SGC_ID2).send(json.dumps({"type": "delete", "messageId": message.id}, ensure_ascii=False))
            for ml in self.bot.consts["gcm"][e].get(message.id, []):
                try:
                    dga.append(ml.delete())
                except AttributeError:
                    pass

            # async def single(gcc, ind):
            #     ta = await gcc.history(limit=ind).flatten()
            #     await ta[-1].delete()
            # async for m in message.channel.history(limit=100):
            #     mi += 1
            #     if m.created_at < message.created_at:

            #         for gc2 in e:
            #             if gc2 != message.channel.id:
            #                 gcc = self.bot.get_channel(gc2)
            #                 dga.append(single(gcc, mi))
            #         break
            await asyncio.gather(*dga)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if (after.channel.id in Global_chat or after.channel.id in flatten(list(Private_chats.values()))) and not after.author.bot:
            # mi = 0
            dga = []
            if after.channel.id in Global_chat:
                e = None
            else:
                for pck, pc in Private_chats.items():
                    if after.channel.id in pc:
                        e = pck
                        break
            if e == "sgc":
                await self.bot.get_channel(SGC_ID2).send(json.dumps({"type": "edit", "messageId": after.id, "content": after.content}, ensure_ascii=False))
            for ml in self.bot.consts["gcm"][e].get(after.id, []):
                try:
                    dga.append(ml.edit(content=after.content))
                except AttributeError:
                    pass

            # async def single(gcc, ind):
            #     ta = await gcc.history(limit=ind).flatten()
            #     await ta[-1].delete()
            # async for m in message.channel.history(limit=100):
            #     mi += 1
            #     if m.created_at < message.created_at:

            #         for gc2 in e:
            #             if gc2 != message.channel.id:
            #                 gcc = self.bot.get_channel(gc2)
            #                 dga.append(single(gcc, mi))
            #         break
            await asyncio.gather(*dga)

    @commands.group(aliases=["gc"])
    @commands.has_permissions(manage_channels=True)
    async def gchat(self, ctx):
        if ctx.invoked_subcommand is None:

            await self.bot.send_subcommands(ctx)
        else:
            pass

    @gchat.command(name="activate", aliases=Activate_aliases + ["join", "connect"])
    @commands.has_permissions(manage_channels=True)
    async def activate_global(self, ctx, channel=None):
        global Global_chat, Private_chats, Private_chat_pass, Private_chat_author
        if ctx.channel.id in Global_chat or ctx.channel.id in flatten(list(Private_chats.values())):
            e = discord.Embed(
                title="既に有効です。", description="グローバルチャットではないチャンネルで使用してください。", color=Error)
            await ctx.send(embed=e)
        else:
            if channel is None:
                e2 = discord.Embed(
                    title="グローバルチャットに仲間が入ってきた!", description=f"{ctx.guild.name}がグローバルチャットに参加しました！", timestamp=ctx.message.created_at, color=Chat)
                e2.set_thumbnail(
                    url=ctx.guild.icon_url_as(static_format='png'))
                e2.set_footer(text=f"現在のチャンネル数：{len(Global_chat)+1}")
                loop = asyncio.get_event_loop()
                for c in Global_chat:
                    cn = self.bot.get_channel(c)
                    if cn is None:
                        Global_chat.remove(c)
                    else:
                        try:
                            ch_webhooks = await cn.webhooks()
                        except Forbidden:
                            continue
                        webhook = discord.utils.get(
                            ch_webhooks, name="sevenbot-global-webhook")
                        if webhook is None:
                            g = self.bot.get_guild(
                                Official_discord_id)
                            a = g.icon_url_as(format="png")
                            webhook = await cn.create_webhook(name="sevenbot-global-webhook", avatar=await a.read())
                        fl = []
                        un = "SevenBot Global"
                        loop.create_task(webhook.send(embed=e2,  # content.replace("@", "@​")
                                                      username=un,
                                                      avatar_url="https://i.imgur.com/eaXHbTe.png",
                                                      files=fl))
                        # https://i.imgur.com/eaXHbTe.png
                e = discord.Embed(
                    title="グローバルチャット参加", description="グローバルチャットに参加しました。", color=Success)
                await ctx.send(embed=e)
                e3 = discord.Embed(title="グローバルチャットのルールについて", color=Info)
                e3.add_field(
                    name="宣伝禁止", value="宣伝はしないで下さい。", inline=False)
                e3.add_field(name="暴言・エロ画像など、不快に感じる行為禁止",
                             value="不快に感じる行為はしないで下さい。", inline=False)
                e3.add_field(
                    name="ルール違反を発見した場合", value="`sb#global_report <メッセージID>`で報告して下さい。", inline=False)
                r = await ctx.send(embed=e3)
                await r.pin()
                Global_chat.append(ctx.channel.id)
            else:
                def check(c):
                    return (c.channel.id == ctx.author.dm_channel.id and not c.author.bot)
                if channel in list(Private_chats.keys()):
                    if Private_chat_pass[channel] == "":
                        e4 = discord.Embed(
                            title=f"個人グローバルチャット参加 - `{channel}`", description="個人グローバルチャットに参加しました。", color=Success)
                        e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        Private_chats[channel].append(ctx.channel.id)
                        await ctx.send(embed=e4)
                        if channel == "sgc":
                            await self.bot.get_channel(SGC_ID2).send(json.dumps({
                                "type": "sb-guildJoin",
                                "guildName": ctx.guild.name,
                                "guildId": ctx.guild.id,
                                "guildIcon": ctx.guild.icon,
                                "channelName": ctx.channel.name,
                                "channelID": ctx.channel.id}, ensure_ascii=False))
                        # return
                    else:
                        e2 = discord.Embed(
                            title=f"個人グローバルチャット参加 - `{channel}`", description="DMを確認してください。", color=Process)
                        fm = await ctx.send(embed=e2)
                        e3 = discord.Embed(
                            title=f"個人グローバルチャット参加 - `{channel}`", description="30秒以内にパスワードを送信して下さい。", color=Process)
                        e3.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        m = await ctx.author.send(embed=e3)
                        try:
                            msg = await self.bot.wait_for("message", check=check, timeout=30)
                            if Private_chat_pass[channel] == hashlib.sha256(msg.content.encode()).hexdigest():
                                e4 = discord.Embed(
                                    title=f"個人グローバルチャット参加 - `{channel}`", description="パスワードを確認しました。", color=Success)
                                e4.set_footer(
                                    text=f"チャンネルID: {ctx.channel.id}")
                                Private_chats[channel].append(
                                    ctx.channel.id)
                                await m.edit(embed=e4)
                                await fm.edit(embed=e4)
                            else:
                                e4 = discord.Embed(
                                    title=f"個人グローバルチャット参加 - `{channel}`", description="パスワードが違います。", color=Error)
                                e4.set_footer(
                                    text=f"チャンネルID: {ctx.channel.id}")
                                await m.edit(embed=e4)
                                return
                        except asyncio.TimeoutError:
                            e4 = discord.Embed(
                                title=f"個人グローバルチャット参加 - `{channel}`", description="タイムアウトしました。", color=Error)
                            e4.set_footer(
                                text=f"チャンネルID: {ctx.channel.id}")
                            await m.edit(embed=e4)
                            return
                    e2 = discord.Embed(
                        title="グローバルチャットに仲間が入ってきた!", description=f"{ctx.guild.name}がグローバルチャットに参加しました！", timestamp=ctx.message.created_at, color=Chat)
                    e2.set_thumbnail(
                        url=ctx.guild.icon_url_as(static_format='png'))
                    e2.set_footer(
                        text=f"現在のチャンネル数：{len(Private_chats[channel])+1}")
                    loop = asyncio.get_event_loop()
                    for c in Private_chats[channel]:
                        if c == ctx.channel.id:
                            continue
                        cn = self.bot.get_channel(c)
                        if cn is None:
                            Private_chats[channel].remove(c)
                        else:
                            try:
                                ch_webhooks = await cn.webhooks()
                            except Forbidden:
                                continue
                            webhook = discord.utils.get(
                                ch_webhooks, name="sevenbot-private-webhook-" + channel)
                            if webhook is None:
                                g = self.bot.get_guild(
                                    Official_discord_id)
                                a = g.icon_url_as(format="png")
                                webhook = await cn.create_webhook(name="sevenbot-private-webhook-" + channel, avatar=await a.read())
                            fl = []
                            un = "SevenBot Personal Global"
                            loop.create_task(webhook.send(embed=e2,  # content.replace("@", "@​")
                                                          username=un,
                                                          avatar_url="https://i.imgur.com/eaXHbTe.png",
                                                          files=fl))
                else:
                    e2 = discord.Embed(
                        title=f"個人グローバルチャット作成 - `{channel}`", description="DMを確認してください。", color=Process)
                    fm = await ctx.send(embed=e2)
                    e3 = discord.Embed(
                        title=f"個人グローバルチャット作成 - `{channel}`", description="30秒以内にパスワードを送信して下さい。\n`none`と送信するとパスワードが無効になります。", color=Process)
                    e3.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                    m = await ctx.author.send(embed=e3)
                    try:
                        msg = await self.bot.wait_for("message", check=check, timeout=30)
                        Private_chats[channel] = [ctx.channel.id]
                        if msg.content.lower() == "none":
                            Private_chat_pass[channel] = ""
                        else:
                            Private_chat_pass[channel] = hashlib.sha256(
                                msg.content.encode()).hexdigest()
                        Private_chat_author[channel] = ctx.author.id
                        e4 = discord.Embed(
                            title=f"個人グローバルチャット作成 - `{channel}`", description="パスワードを確認しました。", color=Success)
                        e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        await m.edit(embed=e4)
                        await fm.edit(embed=e4)
                    except asyncio.TimeoutError:
                        e4 = discord.Embed(
                            title=f"個人グローバルチャット作成 - `{channel}`", description="タイムアウトしました。", color=Error)
                        e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        await m.edit(embed=e4)

    @gchat.command(name="deactivate", aliases=Deactivate_aliases + ["leave", "disconnect"])
    @commands.has_permissions(manage_channels=True)
    async def deactivate_global(self, ctx):
        global Global_chat, Private_chats, Private_chat_pass, Private_chat_author
        if ctx.channel.id in Global_chat:
            Global_chat.remove(ctx.channel.id)
            e = discord.Embed(
                title="グローバルチャット退出", description="グローバルチャットから退出しました。", color=Success)
            await ctx.send(embed=e)
            e2 = discord.Embed(title="グローバルチャットの仲間が抜けちゃった…",
                               description=f"{ctx.guild.name}がグローバルチャットから退出しました。", timestamp=ctx.message.created_at, color=Chat)
            e2.set_thumbnail(url=ctx.guild.icon_url)
            e2.set_footer(text=f"現在のチャンネル数：{len(Global_chat)}")
            loop = asyncio.get_event_loop()
            for c in Global_chat:
                cn = self.bot.get_channel(c)
                if cn is None:
                    Global_chat.remove(c)
                else:
                    try:
                        ch_webhooks = await cn.webhooks()
                    except Forbidden:
                        continue
                    webhook = discord.utils.get(
                        ch_webhooks, name="sevenbot-global-webhook")
                    if webhook is None:
                        g = self.bot.get_guild(
                            Official_discord_id)
                        a = g.icon_url_as(format="png")
                        webhook = await cn.create_webhook(name="sevenbot-global-webhook", avatar=await a.read())
                    fl = []
                    un = "SevenBot Global"
                    loop.create_task(webhook.send(embed=e2,  # content.replace("@", "@​")
                                                  username=un,
                                                  avatar_url="https://i.imgur.com/orLneWh.png",
                                                  files=fl))
                    # https://i.imgur.com/eaXHbTe.png
        elif ctx.channel.id in flatten(list(Private_chats.values())):
            for pk, pv in Private_chats.items():
                if ctx.channel.id in pv:
                    # pn = pk
                    # each = pv
                    break
            Private_chats[pk].remove(ctx.channel.id)
            if Private_chats[pk] == []:
                del Private_chats[pk]
                del Private_chat_author[pk]
                del Private_chat_pass[pk]
            e = discord.Embed(
                title=f"個人グローバルチャット`{pk}`退出", description=f"個人グローバルチャット`{pk}`から退出しました。", color=Success)
            await ctx.send(embed=e)
            e2 = discord.Embed(title="グローバルチャットの仲間が抜けちゃった…",
                               description=f"{ctx.guild.name}がグローバルチャットから退出しました。", timestamp=ctx.message.created_at, color=Chat)
            e2.set_thumbnail(url=ctx.guild.icon_url)
            e2.set_footer(text=f"現在のチャンネル数：{len(Private_chats[pk])}")
            if pk == "sgc":
                await self.bot.get_channel(SGC_ID2).send(json.dumps({
                    "type": "sb-guildLeft",
                    "guildName": ctx.guild.name,
                    "guildId": ctx.guild.id,
                    "guildIcon": ctx.guild.icon,
                    "channelName": ctx.channel.name,
                    "channelID": ctx.channel.id}, ensure_ascii=False))
            loop = asyncio.get_event_loop()
            for c in Private_chats[pk]:
                cn = self.bot.get_channel(c)
                if cn is None:
                    Private_chats[pk].remove(c)
                else:
                    try:
                        ch_webhooks = await cn.webhooks()
                    except Forbidden:
                        continue
                    webhook = discord.utils.get(
                        ch_webhooks, name="sevenbot-private-webhook-" + pk)
                    if webhook is None:
                        g = self.bot.get_guild(
                            Official_discord_id)
                        a = g.icon_url_as(format="png")
                        webhook = await cn.create_webhook(name="sevenbot-private-webhook-" + pk, avatar=await a.read())
                    fl = []
                    un = "SevenBot Personal Global"
                    loop.create_task(webhook.send(embed=e2,  # content.replace("@", "@​")
                                                  username=un,
                                                  avatar_url="https://i.imgur.com/orLneWh.png",
                                                  files=fl))
                    # https://i.imgur.com/eaXHbTe.png
        else:
            e = discord.Embed(title="ここはグローバルチャットではありません。",
                              description="グローバルチャットで使用してください。", color=Error)
            await ctx.send(embed=e)

    @gchat.group(name="private", aliases=["pr"], invoke_without_command=True)
    async def private_global(self, ctx):
        await self.bot.send_subcommands(ctx)

    @private_global.command(name="change_pass")
    async def changepass_private_global(self, ctx, channel):
        global Global_chat, Private_chats, Private_chat_pass, Private_chat_author
        if ctx.author.id != Private_chat_author[channel]:
            e2 = discord.Embed(
                title=f"パスワード編集 - `{channel}`", description=f"あなたは`{channel}`のオーナーではありません。", color=Error)
            fm = await ctx.send(embed=e2)
            return
        e2 = discord.Embed(
            title=f"パスワード編集 - `{channel}`", description="DMを確認してください。", color=Process)
        fm = await ctx.send(embed=e2)
        e3 = discord.Embed(
            title=f"パスワード編集 - `{channel}`", description="30秒以内にパスワードを送信して下さい。\n`none`と送信するとパスワードが無効になります。", color=Process)
        e3.set_footer(text=f"チャンネルID: {ctx.channel.id}")
        m = await ctx.author.send(embed=e3)

        def check(c):
            return (c.channel.id == ctx.author.dm_channel.id and not c.author.bot)
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            # Private_chats[channel] = [ctx.channel.id]
            if msg.content.lower() == "none":
                Private_chat_pass[channel] = ""
            else:
                Private_chat_pass[channel] = hashlib.sha256(
                    msg.content.encode()).hexdigest()
            e4 = discord.Embed(
                title=f"パスワード編集 - `{channel}`", description="パスワードを確認しました。", color=Success)
            e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
            await m.edit(embed=e4)
            await fm.edit(embed=e4)
        except asyncio.TimeoutError:
            e4 = discord.Embed(
                title=f"パスワード編集 - `{channel}`", description="タイムアウトしました。", color=Error)
            e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
            await m.edit(embed=e4)

    @private_global.command(name="kick")
    async def kick_private_global(self, ctx, channel):
        global Global_chat, Private_chats, Private_chat_pass, Private_chat_author
        if not Private_chat_author.get(channel):
            e2 = discord.Embed(
                title=f"キック - `{channel}`", description="不明なチャンネルIDです。", color=Error)
            fm = await ctx.send(embed=e2)
            return
        elif ctx.author.id != Private_chat_author[channel]:
            e2 = discord.Embed(
                title=f"キック - `{channel}`", description=f"あなたは`{channel}`のオーナーではありません。", color=Error)
            fm = await ctx.send(embed=e2)
            return
        e2 = discord.Embed(
            title=f"キック - `{channel}`", description="DMを確認してください。", color=Process)
        fm = await ctx.send(embed=e2)
        e3 = discord.Embed(
            title=f"キック - `{channel}`", description="30秒以内に以下の番号を入力してください。スペース区切りで複数入力できます。`cancel`でキャンセルします。", color=Process)
        m = await ctx.author.send(embed=e3)
        index = 0
        desc = ""
        for c in Private_chats[channel]:
            if self.bot.get_channel(c):
                index += 1
                tdesc = desc + ""
                tdesc += f"`{index}`: " + self.bot.get_channel(c).guild.name + "\n"
                if len(tdesc) > 2000:
                    await ctx.author.send(embed=SEmbed("", desc, color=Process))
                    desc = ""
                else:
                    desc = tdesc + ""

        await ctx.author.send(embed=SEmbed("", desc, color=Process))

        def check(c):
            return (c.channel.id == ctx.author.dm_channel.id and not c.author.bot)
        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            if msg.content.lower() == "cancel":
                return await ctx.author.send(embed=SEmbed(f"キック - `{channel}`", "キャンセルしました。", color=Success))
            else:
                dl = set()
                for n in msg.content.split():
                    try:
                        i = int(n)
                        dl.add(Private_chats[channel][i - 1])

                    except (ValueError, IndexError):
                        pass

            Private_chats[channel] = list(set(Private_chats[channel]) - dl)
            e4 = discord.Embed(
                title=f"キック - `{channel}`", description=f"{len(dl)}チャンネルをキックしました。", color=Success)
            await m.edit(embed=e4)
            await fm.edit(embed=e4)
        except asyncio.TimeoutError:
            e4 = discord.Embed(
                title=f"キック - `{channel}`", description="タイムアウトしました。", color=Error)
            e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
            await m.edit(embed=e4)

    @commands.command()
    async def sgc(self, ctx):
        res = ""
        for m in self.bot.get_guild(706905953320304772).get_role(773868241713627167).members:
            if m.status == discord.Status.offline:
                res += str(Official_emojis["offline"])
            elif m.status == discord.Status.dnd:
                res += str(Official_emojis["dnd"])
            elif m.status == discord.Status.idle:
                res += str(Official_emojis["idle"])
            elif m.status == discord.Status.online:
                res += str(Official_emojis["online"])
            else:
                res += str(Official_emojis["unknown"])
            res += str(m) + "\n"
        e = discord.Embed(title="スーパーグローバルチャット情報", description=res, color=Info)
        e.set_footer(text="sb#gchat activate sgcでグローバルチャットに参加できます。")
        return await ctx.send(embed=e)


def setup(_bot):
    global bot
    bot = _bot
#     logging.info("cog.py reloaded")
    _bot.add_cog(GlobalCog(_bot))
