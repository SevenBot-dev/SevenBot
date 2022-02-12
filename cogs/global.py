# -*- ignore_on_debug -*-
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
import websockets
from discord.errors import Forbidden, NotFound
from discord.ext import commands, components, tasks
from sembed import SAuthor, SEmbed, SField  # , SField, SAuthor, SFooter

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (
    Activate_aliases,
    Chat,
    Deactivate_aliases,
    Error,
    Info,
    Official_discord_id,
    Owner_ID,
    Process,
    Success,
)
from common_resources.tokens import wsgc_token, emergency
from common_resources.tools import flatten

SGC_ID = 707158257818664991
SGC_ID2 = 799184205316751391
SGC_STOP = False
Gc_last_users = {}
Image_exts = ["gif", "jpg", "jpeg", "jpe", "jfif", "png", "bmp", "ico"]
Cant_image = "https://i.imgur.com/UuhmAUG.png"
INVITE_PATTERN = re.compile(r"(https?://)?((ptb|canary)\.)?(discord\.(gg|io)|discord(app)?.com/invite)/[0-9a-zA-Z]+")
Private_chat_info = {}


class GlobalCog(commands.Cog):
    def __init__(self, bot):
        global Global_chat, Global_mute, Private_chat_info
        global get_txt, is_command
        self.bot: commands.Bot = bot
        self.bot.guild_settings = bot.guild_settings
        Global_chat = bot.raw_config["gc"]
        Global_mute = bot.raw_config["gm"]
        get_txt = bot.get_txt
        is_command = bot.is_command
        if self.bot.consts.get("pci"):
            Private_chat_info = self.bot.consts["pci"]
        else:
            raw_info = self.bot.sync_db.private_chat.find({}, {"_id": False})
            for info in raw_info:
                Private_chat_info[info["name"]] = info
            self.bot.consts["pci"] = Private_chat_info
        self.sync_pc_data.start()
        self.bot.loop.create_task(self.get_pc_data())
        self.bot.loop.create_task(self.keep_websocket())
        self.websocket_flag = False
        self.register_flag = False

    def make_rule_embed(self, channel):
        owner = self.bot.get_user(Private_chat_info[channel]["owner"])
        return SEmbed(
            f"`{channel}`のルール",
            fields=[SField(*r, False) for r in Private_chat_info[channel]["rule"].items()],
            author=SAuthor(str(owner) + f"(ID:{owner.id})", str(owner.display_avatar.url)),
            color=Info,
        )

    @commands.Cog.listener("on_message")
    async def on_message_sgc(self, message):
        if message.channel.id in [SGC_ID, SGC_ID2] and message.author.id != self.bot.user.id and not SGC_STOP:
            loop = asyncio.get_event_loop()
            loop.create_task(message.add_reaction(self.bot.oemojis["network"]))
            try:
                data = json.loads(message.content)
            except json.JSONDecodeError:
                return
            await self.handle_sgc(data, message.author.id, "sgc")
            loop.create_task(message.remove_reaction(self.bot.oemojis["network"], self.bot.user))
            loop.create_task(message.add_reaction(self.bot.oemojis["check8"]))
            return

    async def handle_sgc(self, data, from_id, channel):
        from_user = self.bot.get_user(from_id)
        ga = []
        deletes = []
        whname = f"sevenbot-private-webhook-{channel}"
        each = Private_chat_info[channel]["channels"]
        # print(data)
        if data.get("isBot", False):
            return
        if data.get("type", "message") == "message":
            async with aiohttp.ClientSession() as s:

                async def single_send(cn):
                    ch_webhooks = await cn.webhooks()
                    webhook = discord.utils.get(ch_webhooks, name=whname)
                    if webhook is None:
                        g = self.bot.get_guild(Official_discord_id)
                        a = g.icon
                        webhook = await cn.create_webhook(name=whname, avatar=await a.read())
                    un = data["userName"] + "#" + data["userDiscriminator"]
                    un += "("
                    if data.get("sb-tag", {}).get("type"):
                        un = "[" + data.get("sb-tag", {}).get("emoji") + "]" + un
                    un += f"ID:{data['userId']}, From:{from_user})"
                    files = []
                    for a in data.get("attachmentsUrl", []):
                        u = urllib.parse.unquote(a)
                        fio = io.BytesIO()
                        async with s.get(u) as r:
                            fio.write(await r.read())
                        fio.seek(0)
                        files.append(discord.File(fio, filename=u.split("/")[-1]))
                        fio.close()
                    embed = None
                    if reference_id := data.get("reference"):
                        gms = self.bot.consts["gcm"][channel]
                        if references := gms.get(int(reference_id)):
                            reference = references[0]
                            embed = discord.Embed(description=reference.content, color=Chat)
                            avatar = reference.author.display_avatar.url.removeprefix("('")
                            embed.set_author(
                                name=reference.author.name,
                                icon_url=avatar,
                            )
                    return await webhook.send(
                        content=data["content"],  # content.replace("@", "@​")
                        username=un,
                        allowed_mentions=discord.AllowedMentions.none(),
                        avatar_url="https://media.discordapp.net/avatars/"
                        f"{data['userId']}/{data['userAvatar']}."
                        f"{'gif' if data['userAvatar'].startswith('a_') else 'webp'}?size=1024",
                        files=files,
                        embed=embed,
                        wait=True,
                    )

                for c in each:
                    cn = self.bot.get_channel(c)
                    if cn is None:
                        deletes.append(c)
                        continue
                    else:
                        if cn.permissions_for(cn.guild.me).manage_webhooks:
                            ga.append(single_send(cn))
                self.bot.consts["gcm"][channel][int(data["messageId"])] = await asyncio.gather(*ga)
                if len(list(self.bot.consts["gcm"][channel].keys())) > 30:
                    del self.bot.consts["gcm"][channel][list(self.bot.consts["gcm"][channel].keys())[0]]
        elif data.get("type", "message") == "edit":
            ga = []
            for m in self.bot.consts["gcm"][channel].get(int(data["messageId"]), []):
                ga.append(m.edit(content=data["content"]))
            await asyncio.gather(*ga)
        elif data.get("type", "message") == "delete":
            ga = []
            for m in self.bot.consts["gcm"][channel].get(int(data["messageId"]), []):
                ga.append(m.delete())
            await asyncio.gather(*ga)

    async def send_mute(self, message):
        await message.delete()
        e2 = discord.Embed(title="あなたはミュートされています。", color=Error)
        await message.author.send(embed=e2)

    async def send_emergency(self, message):
        await message.delete()
        e2 = discord.Embed(title="現在Emergencyモードのためグローバルチャットは使用できません。", color=Error)
        await message.author.send(embed=e2)

    def short_line(self, data, length):
        res = ""
        count = 0
        for c in data:
            if ord(c) > 256:
                count += 2
            else:
                count += 1
            if count > length:
                res = res[:-2] + "..."
                break
            res += c
        return res

    def process_spam(self, content):
        if len(content.splitlines()) > 10:
            content = "\n".join(content.splitlines()[:10]) + "\n..."
        content = "\n".join([self.short_line(li, 200) for li in content.splitlines()])
        if len(content) > 500:
            content = content[:500]
            if content.count("```") % 2 != 0:
                content += "\n```"
            content += "..."
        return content

    async def keep_websocket(self):
        while not self.websocket_flag:
            try:
                async with websockets.connect("wss://wsgc-gw1.cyberrex.jp/v1") as websocket:
                    self.websocket = websocket
                    while not self.websocket_flag:
                        msg = await websocket.recv()
                        json_msg = json.loads(msg)
                        if json_msg.get("t", "") == "ERROR":
                            if json_msg["type"] == "ALREADY_REGISTERED":
                                self.register_flag = True
                            else:
                                await self.bot.get_channel(763877469928554517).send(json_msg)
                        elif json_msg["t"] == "HELLO":
                            if not self.register_flag:
                                await websocket.send(
                                    json.dumps({"t": "CONNECT", "d": {"id": str(self.bot.user.id), "token": wsgc_token}})
                                )
                        elif json_msg["t"] in ("HEARTBEAT", "CONNECTED"):
                            pass
                        elif json_msg.get("f"):
                            await self.handle_sgc(json_msg["d"], int(json_msg["f"]["id"]), "wsgc")
                        else:
                            await self.bot.get_channel(763877469928554517).send(json_msg)
                    await websocket.send(json.dumps({"t": "CLOSE", "d": None}))
            except websockets.ConnectionClosed:
                pass

    async def send_messages(self, message, *, username=None, embed=None):
        e = discord.Embed(
            description=message.content,
            timestamp=message.created_at,
            color=Chat,
        )
        if message.attachments != []:
            u = message.attachments[0].url
            if "".join(os.path.splitext(os.path.basename(message.attachments[0].filename))[1:])[1:] not in Image_exts:
                u = Cant_image
            e.set_image(url=u)
        e.set_author(
            name=f"{message.author}(ID:{message.author.id})",
            icon_url=message.author.display_avatar.url,
        )
        e.set_footer(
            text=f"{message.guild.name}(ID:{message.guild.id})",
            icon_url=message.guild.icon.url,
        )
        loop = asyncio.get_event_loop()
        ga = []
        if message.channel.id in flatten([c["channels"] for c in Private_chat_info.values()]):
            for pk, pv in Private_chat_info.items():
                if message.channel.id in pv["channels"]:
                    channel = pk
                    each = pv["channels"]
                    break
            whname = f"sevenbot-private-webhook-{channel}"
            if not self.bot.consts["gcm"].get(channel):
                self.bot.consts["gcm"][channel] = {}
            gms = self.bot.consts["gcm"][channel]
            # print(Private_chat_info[channel]["mute"])
            if message.author.id in Private_chat_info[channel]["mute"]:
                return await self.send_mute(message)
        else:
            whname = "sevenbot-global-webhook"
            if not self.bot.consts["gcm"].get(None):
                self.bot.consts["gcm"][None] = {}
            gms = self.bot.consts["gcm"][None]
            channel = None
            each = Global_chat
        deletes = []
        gms[message.id] = []
        content = (
            re.sub(INVITE_PATTERN, "[Invite link]", message.content)
            if whname == "sevenbot-global-webhook"
            else message.content
        )
        if whname == "sevenbot-global-webhook" or Private_chat_info[channel]["antispam"]:
            content = self.process_spam(content)
        if channel == "sgc":
            loop.create_task(self.send_sgc(message, content))
        elif channel == "wsgc":
            loop.create_task(self.send_wsgc(message, content))
        for c in each:
            cn = self.bot.get_channel(c)
            if cn is None:
                deletes.append(c)
                continue
            else:
                # print(cn)
                try:
                    if cn.permissions_for(cn.guild.me).manage_webhooks:
                        if not c == message.channel.id:
                            ch_webhooks = await cn.webhooks()
                            webhook = discord.utils.get(ch_webhooks, name=whname)
                            if webhook is None:
                                g = self.bot.get_guild(Official_discord_id)
                                a = g.icon
                                webhook = await cn.create_webhook(name=whname, avatar=await a.read())
                            fl = []
                            for at in message.attachments:
                                fl.append(await at.to_file())
                            if username is None:
                                un_prefix = ""
                                if message.author.id == Owner_ID:
                                    un_prefix = "[👑]"
                                elif self.bot.get_guild(Official_discord_id).get_member(message.author.id) is not None:
                                    m = self.bot.get_guild(Official_discord_id).get_member(message.author.id)
                                    if self.bot.get_guild(Official_discord_id).get_role(741837982012538910) in m.roles:
                                        un_prefix = "[🛠️]"
                                    elif self.bot.is_premium(message.author):
                                        un_prefix = "[💎]"
                                    elif (
                                        self.bot.get_guild(Official_discord_id).get_role(747555900092580030) in m.roles
                                    ):
                                        un_prefix = "[✔️]"
                                un_suffix = "("
                                un_suffix += f"ID:{message.author.id}, "
                                un_suffix += f"From:{message.guild.name}"
                                un_suffix += ")"
                                un = un_prefix + str(message.author) + un_suffix
                                if len(un) > 80:
                                    length = 80 - len(un_prefix + un_suffix) - 5
                                    un = (
                                        un_prefix
                                        + message.author.name[:length]
                                        + "#"
                                        + message.author.discriminator
                                        + un_suffix
                                    )
                            else:
                                un = username
                            rem = None
                            if message.reference:
                                try:
                                    rmsg = await message.channel.fetch_message(message.reference.message_id)
                                    rem = discord.Embed(description=rmsg.content, color=Chat)
                                    rem.set_author(
                                        name=rmsg.author.name,
                                        icon_url=rmsg.author.display_avatar.url,
                                    )
                                except discord.NotFound:
                                    rem = None
                            ga.append(
                                webhook.send(
                                    content=content,  # content.replace("@", "@​")
                                    username=un,
                                    allowed_mentions=discord.AllowedMentions.none(),
                                    avatar_url=message.author.display_avatar.replace(static_format="png").url,
                                    files=fl,
                                    embed=embed or rem,
                                    wait=True,
                                )
                            )
                            # await
                            # webhook.edit(avater_url="https://i.imgur.com/JffqEAl.png")
                    else:
                        embeds = [e]
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
                            embeds.append(e3)
                        ga.append(cn.send(embeds=embeds))
                except discord.HTTPException:
                    pass
        if not message.channel.permissions_for(message.guild.me).manage_webhooks:
            await message.delete()
        for d in deletes:
            each.remove(d)
        r = await asyncio.gather(*ga)
        # print(r)
        gms[message.id] = r
        if len(list(gms.keys())) > 30:
            del gms[list(gms.keys())[0]]

    async def send_sgc(self, message: discord.Message, content: str):
        rjson = self.create_sgc_payload(message, content)
        await self.bot.get_channel(SGC_ID).send(
            json.dumps(rjson, ensure_ascii=False), allowed_mentions=discord.AllowedMentions.none()
        )

    async def send_wsgc(self, message: discord.Message, content: str):
        rjson = self.create_sgc_payload(message, content)
        await self.websocket.send(json.dumps({"t": "SGC_MESSAGE", "d": rjson}, ensure_ascii=False))

    def create_sgc_payload(self, message, content):
        rjson = {
            "type": "message",
            "userId": str(message.author.id),
            "userName": message.author.name,
            "userDiscriminator": message.author.discriminator,
            "userAvatar": message.author.display_avatar.key,
            "isBot": message.author.bot,
            "guildId": str(message.guild.id),
            "guildName": message.guild.name,
            "guildIcon": message.guild.icon and message.guild.icon.key,
            "channelId": str(message.channel.id),
            "channelName": message.channel.name,
            "messageId": str(message.id),
            "content": content.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere"),
            "sb-tag": {"type": None},
            "sb-rawContent": message.content,
            "version": "2.1.7",
        }
        if message.attachments:
            rjson["attachmentsUrl"] = [a.url for a in message.attachments]
        if message.author.id == Owner_ID:
            rjson["sb-tag"] = {"type": "admin", "emoji": "👑"}
        elif self.bot.get_guild(Official_discord_id).get_member(message.author.id) is not None:
            m = self.bot.get_guild(Official_discord_id).get_member(message.author.id)
            if self.bot.get_guild(Official_discord_id).get_role(741837982012538910) in m.roles:
                rjson["sb-tag"] = {"type": "moderator", "emoji": "🛠️"}
            elif self.bot.is_premium(message.author):
                rjson["sb-tag"] = {"type": "premium", "emoji": "💎"}
            elif self.bot.get_guild(Official_discord_id).get_role(747555900092580030) in m.roles:
                rjson["sb-tag"] = {"type": "special", "emoji": "✔️"}
        if message.reference:
            gms = self.bot.consts["gcm"]["sgc"]
            data = gms.get(message.reference.message_id)
            if data:
                rjson["reference"] = message.reference.message_id
            else:
                msg = discord.utils.find(lambda k: message.reference.message_id in [m.id for m in gms[k]], gms.keys())
                if msg:
                    rjson["reference"] = msg

        return rjson

    @commands.Cog.listener("on_message")
    async def on_message_global(self, message):
        if (
            message.channel.id in self.bot.global_chats
            and message.author.id != self.bot.user.id
            and not message.webhook_id
            and message.author.bot
        ):
            await message.delete()
        if (message.channel.id in self.bot.global_chats) and (not message.author.bot and not message.webhook_id):
            if is_command(message):
                pass
            else:
                if message.author.id in Global_mute:
                    await self.send_mute(message)
                elif emergency:
                    await self.send_emergency(message)
                else:
                    if message.channel.id in Global_chat:
                        slow = 5
                    else:
                        for pv in Private_chat_info.values():
                            if message.channel.id in pv["channels"]:
                                slow = pv["slow"]
                                break
                    if (
                        message.author.id in Gc_last_users.keys()
                        and time.time() - Gc_last_users[message.author.id] < slow
                    ):
                        await message.add_reaction(self.bot.oemojis["queue"])
                        await asyncio.sleep(slow)
                        await message.remove_reaction(self.bot.oemojis["queue"], self.bot.user)
                    Gc_last_users[message.author.id] = time.time()
                    await message.add_reaction(self.bot.oemojis["network"])
                    try:
                        await self.send_messages(message)
                        try:
                            await message.remove_reaction(self.bot.oemojis["network"], message.guild.me)
                            await message.add_reaction(self.bot.oemojis["check8"])
                            await asyncio.sleep(2)
                            await message.remove_reaction(self.bot.oemojis["check8"], message.guild.me)
                        except NotFound:
                            pass
                    except discord.HTTPException:
                        pass

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if (
            message.channel.id in Global_chat
            or message.channel.id in flatten([c["channels"] for c in Private_chat_info.values()])
        ) and not message.author.bot:
            # mi = 0
            dga = []
            if message.channel.id in Global_chat:
                e = None
            else:
                for pck, pc in Private_chat_info.items():
                    if message.channel.id in pc["channels"]:
                        e = pck
                        break
            if e == "sgc":
                await self.bot.get_channel(SGC_ID2).send(
                    json.dumps(
                        {"type": "delete", "messageId": str(message.id)},
                        ensure_ascii=False,
                    )
                )
            elif e == "wsgc":
                await self.wsgc_event_send({"type": "delete", "messageId": str(message.id)})
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
        if (
            after.channel.id in Global_chat
            or after.channel.id in flatten([c["channels"] for c in Private_chat_info.values()])
        ) and not after.author.bot:
            # mi = 0
            dga = []
            if after.channel.id in Global_chat:
                e = None
            else:
                for pck, pc in Private_chat_info.items():
                    if after.channel.id in pc["channels"]:
                        e = pck
                        break
            if (not e) or Private_chat_info[e]["antispam"]:
                content = self.process_spam(after.content)
            else:
                content = after.content
            if e == "sgc":
                await self.bot.get_channel(SGC_ID2).send(
                    json.dumps(
                        {
                            "type": "edit",
                            "messageId": str(after.id),
                            "content": content,
                        },
                        ensure_ascii=False,
                    )
                )
            elif e == "wsgc":
                await self.wsgc_event_send(
                    {
                        "type": "edit",
                        "messageId": str(after.id),
                        "content": content,
                    }
                )

            for ml in self.bot.consts["gcm"][e].get(after.id, []):
                try:
                    dga.append(ml.edit(content=content))
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

    async def wsgc_event_send(self, payload):
        await self.websocket.send(
            json.dumps(
                {"t": "SGC_EVENT", "d": payload},
                ensure_ascii=False,
            )
        )

    @gchat.command(name="activate", aliases=Activate_aliases + ["join", "connect"])
    @commands.has_permissions(manage_channels=True)
    async def activate_global(self, ctx, channel=None):
        if ctx.channel.id in Global_chat or ctx.channel.id in flatten(
            [c["channels"] for c in Private_chat_info.values()]
        ):
            e = discord.Embed(
                title="既に有効です。",
                description="グローバルチャットではないチャンネルで使用してください。",
                color=Error,
            )
            await ctx.reply(embed=e)
        else:
            if channel is None:
                e2 = discord.Embed(
                    title="グローバルチャットに仲間が入ってきた!",
                    description=f"{ctx.guild.name}がグローバルチャットに参加しました！",
                    timestamp=ctx.message.created_at,
                    color=Chat,
                )
                e2.set_thumbnail(url=ctx.guild.icon.url)
                e2.set_footer(text=f"現在のチャンネル数：{len(Global_chat)+1}")
                loop = asyncio.get_event_loop()

                async def send_webhook(webhook, *args, **kwargs):
                    try:
                        await webhook.send(*args, **kwargs)
                    except discord.InvalidArgument:
                        pass

                for c in Global_chat:
                    cn = self.bot.get_channel(c)
                    if cn is None:
                        Global_chat.remove(c)
                    else:
                        try:
                            ch_webhooks = await cn.webhooks()
                        except Forbidden:
                            continue
                        webhook = discord.utils.get(ch_webhooks, name="sevenbot-global-webhook")
                        if webhook is None:
                            g = self.bot.get_guild(Official_discord_id)
                            a = g.icon
                            webhook = await cn.create_webhook(
                                name="sevenbot-global-webhook",
                                avatar=await a.read(),
                            )
                        fl = []
                        un = "SevenBot Global"
                        loop.create_task(
                            send_webhook(
                                webhook,
                                embed=e2,  # content.replace("@", "@​")
                                username=un,
                                avatar_url="https://i.imgur.com/eaXHbTe.png",
                                files=fl,
                            )
                        )
                        # https://i.imgur.com/eaXHbTe.png
                e = discord.Embed(
                    title="グローバルチャット参加",
                    description="グローバルチャットに参加しました。",
                    color=Success,
                )
                await ctx.reply(embed=e)
                e3 = discord.Embed(title="グローバルチャットのルールについて", color=Info)
                e3.add_field(name="宣伝禁止", value="宣伝はしないで下さい。", inline=False)
                e3.add_field(
                    name="暴言・エロ画像など、不快に感じる行為禁止",
                    value="不快に感じる行為はしないで下さい。",
                    inline=False,
                )
                e3.add_field(
                    name="ルール違反を発見した場合",
                    value="`sb#global_report <メッセージID>`で報告して下さい。",
                    inline=False,
                )
                r = await ctx.send(embed=e3)
                await r.pin()
                Global_chat.append(ctx.channel.id)
            else:

                def check(c):
                    return c.channel.id == ctx.author.dm_channel.id and not c.author.bot

                if channel in list(Private_chat_info.keys()):
                    if Private_chat_info[channel]["pass"] == "":
                        e4 = discord.Embed(
                            title=f"個人グローバルチャット参加 - `{channel}`",
                            description="個人グローバルチャットに参加しました。",
                            color=Success,
                        )
                        e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        Private_chat_info[channel]["channels"].append(ctx.channel.id)
                        await ctx.reply(embed=e4)
                        if channel == "sgc":
                            await self.bot.get_channel(SGC_ID2).send(
                                json.dumps(
                                    {
                                        "type": "sb-guildJoin",
                                        "guildName": ctx.guild.name,
                                        "guildId": str(ctx.guild.id),
                                        "guildIcon": ctx.guild.icon.key,
                                        "channelName": ctx.channel.name,
                                        "channelID": ctx.channel.id,
                                    },
                                    ensure_ascii=False,
                                )
                            )
                        elif channel == "wsgc":
                            await self.wsgc_event_send(
                                {
                                    "type": "sb-guildJoin",
                                    "guildName": ctx.guild.name,
                                    "guildId": str(ctx.guild.id),
                                    "guildIcon": ctx.guild.icon.key,
                                    "channelName": ctx.channel.name,
                                    "channelID": ctx.channel.id,
                                },
                            )
                    else:
                        e2 = discord.Embed(
                            title=f"個人グローバルチャット参加 - `{channel}`",
                            description="DMを確認してください。",
                            color=Process,
                        )
                        fm = await ctx.reply(embed=e2)
                        e3 = discord.Embed(
                            title=f"個人グローバルチャット参加 - `{channel}`",
                            description="30秒以内にパスワードを送信して下さい。",
                            color=Process,
                        )
                        e3.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        m = await ctx.author.send(embed=e3)
                        try:
                            msg = await self.bot.wait_for("message", check=check, timeout=30)
                            if Private_chat_info[channel]["pass"] == hashlib.sha256(msg.content.encode()).hexdigest():
                                e4 = discord.Embed(
                                    title=f"個人グローバルチャット参加 - `{channel}`",
                                    description="パスワードを確認しました。",
                                    color=Success,
                                )
                                e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                                Private_chat_info[channel]["channels"].append(ctx.channel.id)
                                await m.edit(embed=e4)
                                await fm.edit(embed=e4)
                            else:
                                e4 = discord.Embed(
                                    title=f"個人グローバルチャット参加 - `{channel}`",
                                    description="パスワードが違います。",
                                    color=Error,
                                )
                                e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                                await m.edit(embed=e4)
                                return
                        except asyncio.TimeoutError:
                            e4 = discord.Embed(
                                title=f"個人グローバルチャット参加 - `{channel}`",
                                description="タイムアウトしました。",
                                color=Error,
                            )
                            e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                            await m.edit(embed=e4)
                            return
                    e2 = discord.Embed(
                        title="グローバルチャットに仲間が入ってきた!",
                        description=f"{ctx.guild.name}がグローバルチャットに参加しました！",
                        timestamp=ctx.message.created_at,
                        color=Chat,
                    )
                    e2.set_thumbnail(url=ctx.guild.icon.url)
                    e2.set_footer(text=f"現在のチャンネル数：{len(Private_chat_info[channel]['channels'])}")
                    r = await ctx.send(embed=self.make_rule_embed(channel))
                    await r.pin()
                    loop = asyncio.get_event_loop()
                    for c in Private_chat_info[channel]["channels"]:
                        if c == ctx.channel.id:
                            continue
                        cn = self.bot.get_channel(c)
                        if cn is None:
                            Private_chat_info[channel]["channels"].remove(c)
                        else:
                            try:
                                ch_webhooks = await cn.webhooks()
                            except Forbidden:
                                continue
                            webhook = discord.utils.get(
                                ch_webhooks,
                                name="sevenbot-private-webhook-" + channel,
                            )
                            if webhook is None:
                                g = self.bot.get_guild(Official_discord_id)
                                a = g.icon
                                webhook = await cn.create_webhook(
                                    name="sevenbot-private-webhook-" + channel,
                                    avatar=await a.read(),
                                )
                            fl = []
                            un = "SevenBot Personal Global"
                            loop.create_task(
                                webhook.send(
                                    embed=e2,  # content.replace("@", "@​")
                                    username=un,
                                    avatar_url="https://i.imgur.com/eaXHbTe.png",
                                    files=fl,
                                )
                            )
                else:
                    e2 = discord.Embed(
                        title=f"個人グローバルチャット作成 - `{channel}`",
                        description="DMを確認してください。",
                        color=Process,
                    )
                    fm = await ctx.reply(embed=e2)
                    e3 = discord.Embed(
                        title=f"個人グローバルチャット作成 - `{channel}`",
                        description="30秒以内にパスワードを送信して下さい。",
                        color=Process,
                    )
                    e3.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                    buttons = [
                        components.Button(
                            "パスワード無し",
                            "no_pass",
                            components.ButtonType.secondary,
                        ),
                        components.Button("キャンセル", "cancel", components.ButtonType.danger),
                    ]
                    msg = await components.send(ctx.author, embed=e3, components=buttons)
                    try:
                        loop = asyncio.get_event_loop()
                        wait_msg = loop.create_task(
                            self.bot.wait_for(
                                "message",
                                check=lambda m: m.channel == msg.channel and not m.author.bot,
                                timeout=30,
                            ),
                            name="wait_pass",
                        )
                        wait_button = loop.create_task(
                            self.bot.wait_for(
                                "button_click",
                                check=lambda c: c.channel == msg.channel and c.message == msg,
                                timeout=30,
                            ),
                            name="wait_button",
                        )
                        done_tasks, pending_tasks = await asyncio.wait(
                            {wait_msg, wait_button},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        done_task = done_tasks.pop()
                        for task in pending_tasks:
                            task.cancel()
                        if done_task.get_name() == "wait_pass":
                            password = hashlib.sha256(done_task.result().content.encode()).hexdigest()
                        elif done_task.get_name() == "wait_button":
                            await done_task.result().defer_update()
                            if done_task.result().custom_id == "cancel":
                                e4 = discord.Embed(
                                    title=f"個人グローバルチャット作成 - `{channel}`",
                                    description="キャンセルされました。",
                                    color=Error,
                                )
                                e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                                for b in buttons:
                                    b.enabled = False
                                await components.edit(msg, embed=e4, components=buttons)
                                await fm.edit(embed=e4)
                                return
                            else:
                                password = ""
                        Private_chat_info[channel] = {
                            "channels": [ctx.channel.id],
                            "owner": ctx.author.id,
                            "pass": password,
                            "mute": [],
                            "rule": {},
                            "slow": 5,
                            "antispam": False,
                        }
                        e4 = discord.Embed(
                            title=f"個人グローバルチャット作成 - `{channel}`",
                            description="パスワードを確認しました。",
                            color=Success,
                        )
                        e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        for b in buttons:
                            b.enabled = False
                        await components.edit(msg, embed=e4, components=buttons)
                        await fm.edit(embed=e4)
                    except asyncio.TimeoutError:
                        e4 = discord.Embed(
                            title=f"個人グローバルチャット作成 - `{channel}`",
                            description="タイムアウトしました。",
                            color=Error,
                        )
                        e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                        for b in buttons:
                            b.enabled = False
                        await components.edit(msg, embed=e4, components=buttons)
                        await fm.edit(embed=e4)

    @gchat.command(name="deactivate", aliases=Deactivate_aliases + ["leave", "disconnect"])
    @commands.has_permissions(manage_channels=True)
    async def deactivate_global(self, ctx):
        if ctx.channel.id in Global_chat:
            Global_chat.remove(ctx.channel.id)
            e = discord.Embed(
                title="グローバルチャット退出",
                description="グローバルチャットから退出しました。",
                color=Success,
            )
            await ctx.reply(embed=e)
            e2 = discord.Embed(
                title="グローバルチャットの仲間が抜けちゃった…",
                description=f"{ctx.guild.name}がグローバルチャットから退出しました。",
                timestamp=ctx.message.created_at,
                color=Chat,
            )
            e2.set_thumbnail(url=ctx.guild.icon.url)
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
                    webhook = discord.utils.get(ch_webhooks, name="sevenbot-global-webhook")
                    if webhook is None:
                        g = self.bot.get_guild(Official_discord_id)
                        a = g.icon
                        webhook = await cn.create_webhook(
                            name="sevenbot-global-webhook",
                            avatar=await a.read(),
                        )
                    fl = []
                    un = "SevenBot Global"
                    loop.create_task(
                        webhook.send(
                            embed=e2,  # content.replace("@", "@​")
                            username=un,
                            avatar_url="https://i.imgur.com/orLneWh.png",
                            files=fl,
                        )
                    )
                    # https://i.imgur.com/eaXHbTe.png
        elif ctx.channel.id in flatten([c["channels"] for c in Private_chat_info.values()]):
            for pk, pv in Private_chat_info.items():
                if ctx.channel.id in pv["channels"]:
                    pn = pk
                    # each = pv
                    break
            Private_chat_info[pn]["channels"].remove(ctx.channel.id)
            e = discord.Embed(
                title=f"個人グローバルチャット`{pn}`退出",
                description=f"個人グローバルチャット`{pn}`から退出しました。",
                color=Success,
            )
            await ctx.reply(embed=e)
            if Private_chat_info[pn]["channels"] == []:
                del Private_chat_info[pn]
                return
            e2 = discord.Embed(
                title="グローバルチャットの仲間が抜けちゃった…",
                description=f"{ctx.guild.name}がグローバルチャットから退出しました。",
                timestamp=ctx.message.created_at,
                color=Chat,
            )
            e2.set_thumbnail(url=ctx.guild.icon.url)
            e2.set_footer(text=f"現在のチャンネル数：{len(Private_chat_info[pk]['channels'])}")
            if pk == "sgc":
                await self.bot.get_channel(SGC_ID2).send(
                    json.dumps(
                        {
                            "type": "sb-guildLeft",
                            "guildName": ctx.guild.name,
                            "guildId": str(ctx.guild.id),
                            "guildIcon": ctx.guild.icon.key,
                            "channelName": ctx.channel.name,
                            "channelID": ctx.channel.id,
                        },
                        ensure_ascii=False,
                    )
                )
            elif pk == "wsgc":
                await self.wsgc_event_send(
                    {
                        "type": "sb-guildLeft",
                        "guildName": ctx.guild.name,
                        "guildId": str(ctx.guild.id),
                        "guildIcon": ctx.guild.icon.key,
                        "channelName": ctx.channel.name,
                        "channelID": ctx.channel.id,
                    }
                )
            loop = asyncio.get_event_loop()
            for c in Private_chat_info[pk]["channels"]:
                cn = self.bot.get_channel(c)
                if cn is None:
                    Private_chat_info[pk]["channels"].remove(c)
                else:
                    try:
                        ch_webhooks = await cn.webhooks()
                    except Forbidden:
                        continue
                    webhook = discord.utils.get(ch_webhooks, name="sevenbot-private-webhook-" + pk)
                    if webhook is None:
                        g = self.bot.get_guild(Official_discord_id)
                        a = g.icon
                        webhook = await cn.create_webhook(
                            name="sevenbot-private-webhook-" + pk,
                            avatar=await a.read(),
                        )
                    fl = []
                    un = "SevenBot Personal Global"
                    loop.create_task(
                        webhook.send(
                            embed=e2,  # content.replace("@", "@​")
                            username=un,
                            avatar_url="https://i.imgur.com/orLneWh.png",
                            files=fl,
                        )
                    )
                    # https://i.imgur.com/eaXHbTe.png
        else:
            e = discord.Embed(
                title="ここはグローバルチャットではありません。",
                description="グローバルチャットで使用してください。",
                color=Error,
            )
            await ctx.reply(embed=e)

    @gchat.group(name="private", aliases=["p", "pr"], invoke_without_command=True)
    async def private_global(self, ctx):
        await self.bot.send_subcommands(ctx)

    @private_global.command(name="password", aliases=["pass"])
    async def changepass_private_global(self, ctx, channel):
        if await self.only_owner(ctx, channel, "パスワード編集"):
            return
        e2 = discord.Embed(
            title=f"パスワード編集 - `{channel}`",
            description="DMを確認してください。",
            color=Process,
        )
        fm = await ctx.reply(embed=e2)
        e3 = discord.Embed(
            title=f"パスワード編集 - `{channel}`",
            description="30秒以内にパスワードを送信して下さい。\n`none`と送信するとパスワードが無効になります。",
            color=Process,
        )
        e3.set_footer(text=f"チャンネルID: {ctx.channel.id}")

        buttons = [
            components.Button("パスワード無し", "no_pass", components.ButtonType.secondary),
            components.Button("キャンセル", "cancel", components.ButtonType.danger),
        ]
        msg = await components.send(ctx.author, embed=e3, components=buttons)
        try:
            loop = asyncio.get_event_loop()
            wait_msg = loop.create_task(
                self.bot.wait_for(
                    "message",
                    check=lambda m: m.channel == msg.channel and not m.author.bot,
                    timeout=30,
                ),
                name="wait_pass",
            )
            wait_button = loop.create_task(
                self.bot.wait_for(
                    "button_click",
                    check=lambda c: c.channel == msg.channel and c.message == msg,
                    timeout=30,
                ),
                name="wait_button",
            )
            done_tasks, pending_tasks = await asyncio.wait({wait_msg, wait_button}, return_when=asyncio.FIRST_COMPLETED)
            done_task = done_tasks.pop()
            for task in pending_tasks:
                task.cancel()
            if done_task.get_name() == "wait_pass":
                Private_chat_info[channel]["pass"] = hashlib.sha256(msg.content.encode()).hexdigest()
            elif done_task.get_name() == "wait_button":
                await done_task.result().defer_update()
                if done_task.result().custom_id == "no_pass":
                    Private_chat_info[channel]["pass"] = ""
                else:
                    e4 = discord.Embed(
                        title=f"パスワード編集 - `{channel}`",
                        description="キャンセルされました。",
                        color=Error,
                    )
                    e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
                    for b in buttons:
                        b.enabled = False
                    await components.edit(msg, embed=e4, components=buttons)
                    await fm.edit(embed=e4)
                    return
            e4 = discord.Embed(
                title=f"パスワード編集 - `{channel}`",
                description="パスワードを確認しました。",
                color=Success,
            )
            e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
            for b in buttons:
                b.enabled = False
            await components.edit(msg, embed=e4, components=buttons)
            await fm.edit(embed=e4)
        except asyncio.TimeoutError:
            e4 = discord.Embed(
                title=f"パスワード編集 - `{channel}`",
                description="タイムアウトしました。",
                color=Error,
            )
            e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
            await components.edit(msg, embed=e4, components=buttons)
            await fm.edit(embed=e4)

    @private_global.command(name="slowmode", aliases=["slow"])
    async def changeslow_private_global(self, ctx, channel, seconds: int):
        if await self.only_owner(ctx, channel, "低速モード編集"):
            return
        if not (5 <= seconds <= 600):
            e4 = discord.Embed(
                title=f"低速モード編集 - `{channel}`",
                description="低速モードは5~600秒でなければなりません。",
                color=Error,
            )
            await ctx.reply(embed=e4)
        e4 = discord.Embed(
            title=f"低速モード編集 - `{channel}`",
            description=f"{seconds}秒に設定しました。",
            color=Success,
        )
        await ctx.reply(embed=e4)

    @private_global.group(name="rule", aliases=["r"], invoke_without_command=True)
    async def rule_private_global(self, ctx):
        await self.bot.send_subcommands(ctx)

    @rule_private_global.command(name="add")
    async def add_rule_private_global(self, ctx, channel, name, *, value):
        if await self.only_owner(ctx, channel, "ルール設定"):
            return
        if name not in Private_chat_info[channel]["rule"].keys():
            if len(Private_chat_info[channel]["rule"]) >= 10:
                e = discord.Embed(
                    title=f"ルール設定 - `{channel}`",
                    description="ルールが多すぎます。\n`sb#gchat private rule remove` で削除して下さい。",
                    color=Error,
                )
                return await ctx.reply(embed=e)
            Private_chat_info[channel]["rule"][name] = value
            e = discord.Embed(
                title=f"ルール設定 - `{channel}`",
                description="ルールを追加しました。",
                color=Success,
            )
        else:
            Private_chat_info[channel]["rule"][name] = value
            e = discord.Embed(
                title=f"ルール設定 - `{channel}`",
                description="ルールを設定しました。",
                color=Success,
            )
        await ctx.reply(embed=e)
        await ctx.send("プレビュー", embed=self.make_rule_embed(channel))

    @rule_private_global.command(name="remove", aliases=["del", "delete", "rem"])
    async def remove_rule_private_global(self, ctx, channel, name):
        if await self.only_owner(ctx, channel, "ルール設定"):
            return
        if Private_chat_info[channel]["rule"].get(name):
            del Private_chat_info[channel]["rule"][name]
            e = discord.Embed(
                title=f"ルール設定 - `{channel}`",
                description="ルールを削除しました。",
                color=Success,
            )
            await ctx.reply(embed=e)
            await ctx.send("プレビュー", embed=self.make_rule_embed(channel))
        else:
            e = discord.Embed(
                title=f"ルール設定 - `{channel}`",
                description="ルールが見付かりませんでした。",
                color=Error,
            )
            await ctx.reply(embed=e)

    @rule_private_global.command(name="view", aliases=["show", "preview", "check"])
    async def view_rule_private_global(self, ctx, channel):
        await ctx.send(
            f"`{channel}`のルール",
            embed=self.make_rule_embed(channel),
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @private_global.command(name="mute")
    async def mute_private_global(self, ctx, channel, uid: int):
        if await self.only_owner(ctx, channel, "ミュート"):
            return
        user = await self.bot.fetch_user(uid)
        e = discord.Embed(title=f"`{user}`をGMuteしますか？", color=Process)
        msg = await ctx.reply(embed=e)
        await msg.add_reaction(self.bot.oemojis["check5"])
        await msg.add_reaction(self.bot.oemojis["check6"])

        def check(r, u):
            if u.id == ctx.author.id:
                return r.message.id == msg.id
            else:
                return False

        try:
            r, _ = await self.bot.wait_for("reaction_add", check=check, timeout=10)
            if r.emoji.name == "check5":
                Private_chat_info[channel]["mute"].append(uid)
                e = discord.Embed(
                    title=f"ミュート - `{channel}`",
                    description=f"`{user}`をミュートしました。",
                    color=Success,
                )
                msg = await msg.edit(embed=e)
            else:
                e = discord.Embed(title="キャンセルしました。", description="", color=Success)
                msg = await msg.edit(embed=e)

        except asyncio.TimeoutError:
            e = discord.Embed(title="タイムアウトしました。", description="", color=Error)
            msg = await msg.edit(embed=e)

    @private_global.command(name="kick")
    async def kick_private_global(self, ctx, channel):
        if await self.only_owner(ctx, channel, "キック"):
            return
        e2 = discord.Embed(
            title=f"キック - `{channel}`",
            description="DMを確認してください。",
            color=Process,
        )
        fm = await ctx.reply(embed=e2)
        e3 = discord.Embed(
            title=f"キック - `{channel}`",
            description="30秒以内に以下の番号を入力してください。スペース区切りで複数入力できます。`cancel`でキャンセルします。",
            color=Process,
        )
        m = await ctx.author.send(embed=e3)
        index = 0
        desc = ""
        for c in Private_chat_info[channel]["channels"]:
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
            return c.channel.id == ctx.author.dm_channel.id and not c.author.bot

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            if msg.content.lower() == "cancel":
                return await ctx.author.send(embed=SEmbed(f"キック - `{channel}`", "キャンセルしました。", color=Success))
            else:
                dl = set()
                for n in msg.content.split():
                    try:
                        i = int(n)
                        dl.add(Private_chat_info[channel]["channels"][i - 1])
                    except (ValueError, IndexError):
                        pass
            Private_chat_info[channel]["channels"] = list(set(Private_chat_info[channel]["channels"]) - dl)
            e4 = discord.Embed(
                title=f"キック - `{channel}`",
                description=f"{len(dl)}チャンネルをキックしました。",
                color=Success,
            )
            await m.edit(embed=e4)
            await fm.edit(embed=e4)
        except asyncio.TimeoutError:
            e4 = discord.Embed(
                title=f"キック - `{channel}`",
                description="タイムアウトしました。",
                color=Error,
            )
            e4.set_footer(text=f"チャンネルID: {ctx.channel.id}")
            await m.edit(embed=e4)

    @commands.command()
    async def sgc(self, ctx):
        res = ""
        for m in self.bot.get_guild(706905953320304772).get_role(773868241713627167).members:
            if m.status == discord.Status.offline:
                res += str(self.bot.oemojis["offline"])
            elif m.status == discord.Status.dnd:
                res += str(self.bot.oemojis["dnd"])
            elif m.status == discord.Status.idle:
                res += str(self.bot.oemojis["idle"])
            elif m.status == discord.Status.online:
                res += str(self.bot.oemojis["online"])
            else:
                res += str(self.bot.oemojis["unknown"])
            res += str(m) + "\n"
        e = discord.Embed(title="スーパーグローバルチャット情報", description=res, color=Info)
        e.set_footer(text="sb#gchat activate sgcでグローバルチャットに参加できます。")
        return await ctx.reply(embed=e)

    async def only_owner(self, ctx, channel, name):
        if not Private_chat_info.get(channel):
            e2 = discord.Embed(
                title=f"{name} - `{channel}`",
                description="不明なチャンネルIDです。",
                color=Error,
            )
            await ctx.reply(embed=e2)
            return True
        if ctx.author.id != Private_chat_info[channel]["owner"]:
            e2 = discord.Embed(
                title=f"{name} - `{channel}`",
                description=f"あなたは`{channel}`のオーナーではありません。",
                color=Error,
            )
            await ctx.reply(embed=e2)
            return True
        return False

    @tasks.loop(minutes=5)
    async def sync_pc_data(self):
        async for c in self.bot.db.private_chat.find({}, {"_id": False}):
            if Private_chat_info.get(c["name"]) is None:
                await self.bot.db.private_chat.delete_one({"name": c["name"]})
                continue
            if c != Private_chat_info.get(c["name"]):
                await self.bot.db.private_chat.update_one(
                    {"name": c["name"]}, {"$set": Private_chat_info[c["name"]]}, upsert=True
                )

    async def get_pc_data(self):
        async with self.bot.db.private_chat.watch() as change_stream:
            async for change in change_stream:
                if change["operationType"] == "update":
                    pcd = await self.bot.db.guild_settings.find_one(change["documentKey"])
                    Private_chat_info[pcd["name"]] = pcd

    def cog_unload(self):
        self.sync_pc_data.stop()
        self.websocket_flag = True


def setup(_bot):
    global bot
    bot = _bot
    #     logging.info("cog.py reloaded")
    _bot.add_cog(GlobalCog(_bot), override=True)
