import asyncio
import hashlib
import io
from itertools import product
import random
import time

import aiohttp
import discord
from discord.ext import commands, components
from discord.errors import NotFound, Forbidden
from PIL import Image, ImageDraw, ImageFont
from sembed import SEmbed

import _pathmagic  # type: ignore # noqa
from common_resources.consts import (Process, Success, Error, Widget)
from common_resources.tokens import web_pass


class AuthCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts, Official_emojis
        global get_txt
        self.bot: commands.Bot = bot
        Official_emojis = self.bot.consts["oe"]
        Guild_settings = bot.guild_settings
        Texts = bot.texts
        get_txt = bot.get_txt

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, pl):
        # loop = asyncio.get_event_loop()
        if pl.user_id == self.bot.user.id:
            return
        channel = self.bot.get_channel(pl.channel_id)
        try:
            message = await channel.fetch_message(pl.message_id)
        except (NotFound, Forbidden):
            return
        guild = self.bot.get_guild(pl.guild_id)
        user = guild.get_member(pl.user_id)
        if message.embeds == []:
            return
        elif message.author.id != self.bot.user.id:
            return

        m0 = message.embeds[0]
        if message.embeds[0].title == "認証ボタン" or message.embeds[0].title.startswith("認証ボタン - "):
            await message.remove_reaction(pl.emoji, self.bot.get_user(pl.user_id))
            guild = self.bot.get_guild(pl.guild_id)
            user = guild.get_member(pl.user_id)
            try:
                r = guild.get_role(
                    int(m0.description.splitlines()[1].split(": ")[1][3:-1]))
            except IndexError:
                r = guild.get_role(
                    Guild_settings[pl.guild_id]["auth_role"])
            if message.embeds[0].title == "認証ボタン" or message.embeds[0].title.endswith("リアクション"):
                if pl.emoji.name == "check5":
                    if r not in user.roles:
                        await user.add_roles(r)
                        try:
                            await user.send(f"{guild.name} での認証が完了しました。")
                        except BaseException:
                            pass
            elif message.embeds[0].title.endswith("画像認証") and r not in user.roles:
                url, auth_text = await self.make_image_auth_url(message)
                e = SEmbed(color=Process, title=get_txt(message.guild.id, "img_auth_header"), description=get_txt(message.guild.id, "img_auth_desc") + "\n" + get_txt(message.guild.id, "img_auth_warn"), image_url=url)
                try:
                    msg = await user.send(embed=e)
                    try:
                        await self.bot.wait_for("message", check=lambda message: message.content.lower() == auth_text and message.channel == message.author.dm_channel and message.author == user, timeout=30)
                        await msg.edit(embed=discord.Embed(title=get_txt(guild.id, "img_auth_ok").format(channel.id), color=Success))
                        await user.add_roles(r)
                    except asyncio.TimeoutError:
                        await msg.edit(embed=discord.Embed(title=get_txt(guild.id, "timeout"), color=Error))
                except Forbidden:
                    e = discord.Embed(title=get_txt(
                        guild.id, "dm_fail"), color=Error)
                    e.set_footer(text=get_txt(
                        guild.id, "message_delete").format(5))
                    msg = await self.bot.get_channel(pl.channel_id).send(embed=e)
                    await msg.delete(delay=5)
            elif message.embeds[0].title.endswith("Web認証") and r not in user.roles:
                async with aiohttp.ClientSession() as session:
                    async with session.post('https://captcha.sevenbot.jp/session', json={"password": web_pass, "uid": user.id, "gid": guild.id, "rid": r.id}) as r:
                        r.raise_for_status()
                        session_id = (await r.json())["message"]
                try:
                    await user.send(get_txt(guild.id, "web_auth") + "\nhttps://captcha.sevenbot.jp/verify?id=" + session_id)
                except discord.errors.Forbidden:
                    msg = await channel.send(user.mention + "\n" + get_txt(guild.id, "web_auth_notdm") + "\nhttps://captcha.sevenbot.jp/verify?id=" + session_id)
                    await msg.delete(delay=60)

    @commands.Cog.listener()
    async def on_button_click(self, com):
        print(1)
        if com.message.embeds == []:
            return
        m0 = com.message.embeds[0]
        if m0.title.startswith("認証ボタン - "):
            await com.defer_source(hidden=True)
            guild = com.guild
            user = com.member
            try:
                r = guild.get_role(
                    int(m0.description.splitlines()[1].split(": ")[1][3:-1]))
            except IndexError:
                r = guild.get_role(
                    Guild_settings[com.guild.id]["auth_role"])
            if m0.title.endswith("ワンクリック"):
                if r not in user.roles:
                    await user.add_roles(r)
                    await com.send(f"{guild.name} での認証が完了しました。", hidden=True)
                else:
                    await com.send("すでに認証済みです。", hidden=True)
            elif m0.title.endswith("画像認証"):
                if r not in user.roles:
                    url, auth_text = await self.make_image_auth_url(com.message)
                    await com.send(embed=SEmbed(description=get_txt(com.guild.id, "img_auth_desc2") + "\n" + get_txt(com.guild.id, "img_auth_warn"), image_url=url, color=Process))
                    try:
                        await self.bot.wait_for("message", check=lambda message: message.content.lower() == auth_text and message.channel == message.author.dm_channel and message.author == user, timeout=30)
                        await user.send(get_txt(guild.id, "img_auth_ok").format(com.channel.id))
                        await user.add_roles(r)
                    except asyncio.TimeoutError:
                        await com.send(get_txt(guild.id, "timeout"), hidden=True)
                else:
                    await com.send("すでに認証済みです。", hidden=True)
            elif m0.title.endswith("Web認証"):
                if r not in user.roles:
                    async with aiohttp.ClientSession() as session:
                        async with session.post('https://captcha.sevenbot.jp/session', json={"password": web_pass, "uid": user.id, "gid": guild.id, "rid": r.id, "appid": com.application_id, "token": com.token}) as r:
                            r.raise_for_status()
                            session_id = (await r.json())["message"]
                    await com.send(get_txt(guild.id, "web_auth") + "\nhttps://captcha.sevenbot.jp/verify?id=" + session_id, hidden=True)
                else:
                    await com.send("すでに認証済みです。")

    @commands.group()
    @commands.has_guild_permissions(manage_roles=True)
    async def auth(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_subcommands(ctx)

    @auth.command(name="click")
    @commands.has_guild_permissions(manage_roles=True)
    async def auth_click(self, ctx, role: discord.Role = 0):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["auth_role"] == 0 and role == 0:
            e = discord.Embed(title="ロールが登録されていません",
                              description="初回はロールを登録する必要があります", color=Error)
            await ctx.reply(embed=e)
            return
        if role == 0:
            role = ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"])
        if role.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        elif role.position > ctx.me.top_role.position:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm_bot").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        if role != 0:
            Guild_settings[ctx.guild.id]["auth_role"] = role.id
        e = discord.Embed(
            title="認証ボタン - ワンクリック", description=f'下のボタンを押して認証\nロール: {ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"]).mention}', color=Widget)
        await components.send(ctx, embed=e, components=[components.Button("認証", "auth")])
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

    @auth.command(name="react")
    @commands.has_guild_permissions(manage_roles=True)
    async def auth_react(self, ctx, role: discord.Role = 0):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["auth_role"] == 0 and role == 0:
            e = discord.Embed(title="ロールが登録されていません",
                              description="初回はロールを登録する必要があります", color=Error)
            m = await ctx.reply(embed=e)
            return
        if role == 0:
            role = ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"])
        if role.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        elif role.position > ctx.me.top_role.position:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm_bot").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        if role != 0:
            Guild_settings[ctx.guild.id]["auth_role"] = role.id
        e = discord.Embed(
            title="認証ボタン - リアクション", description=f'下の{Official_emojis["check5"]}を押して認証\nロール: {ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"]).mention}', color=Widget)
        m = await ctx.send(embed=e)
        await m.add_reaction(Official_emojis["check5"])
        await ctx.message.delete()

    @auth.command(name="image", aliases=["img"])
    @commands.has_guild_permissions(manage_roles=True)
    async def auth_image(self, ctx, role: discord.Role = 0):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["auth_role"] == 0 and role == 0:
            e = discord.Embed(title="ロールが登録されていません",
                              description="初回はロールを登録する必要があります", color=Error)
            await ctx.reply(embed=e)
            return
        if role == 0:
            role = ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"])
        if role.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        elif role.position > ctx.me.top_role.position:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm_bot").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        if role != 0:
            Guild_settings[ctx.guild.id]["auth_role"] = role.id
        e = discord.Embed(
            title="認証ボタン - 画像認証", description=f'下の{Official_emojis["check5"]}を押して認証\nロール: {ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"]).mention}', color=Widget)
        await components.send(ctx, embed=e, components=[components.Button("認証", "auth")])
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

    @auth.command(name="react_image", aliases=["react_img"])
    @commands.has_guild_permissions(manage_roles=True)
    async def auth_react_image(self, ctx, role: discord.Role = 0):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["auth_role"] == 0 and role == 0:
            e = discord.Embed(title="ロールが登録されていません",
                              description="初回はロールを登録する必要があります", color=Error)
            m = await ctx.reply(embed=e)
            return
        if role == 0:
            role = ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"])
        if role.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        elif role.position > ctx.me.top_role.position:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm_bot").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        if role != 0:
            Guild_settings[ctx.guild.id]["auth_role"] = role.id
        e = discord.Embed(
            title="認証ボタン - 画像認証", description=f'下の{Official_emojis["check5"]}を押して認証\nロール: {ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"]).mention}', color=Widget)
        m = await ctx.send(embed=e)
        await m.add_reaction(Official_emojis["check5"])
        await ctx.message.delete()

    @auth.command(name="react_web")
    @commands.has_guild_permissions(manage_roles=True)
    async def auth_react_web(self, ctx, role: discord.Role = 0):
        global Guild_settings
        if role == 0:
            role = ctx.guild.get_role(
                Guild_settings[ctx.guild.id]["auth_role"])
        if role == 0:
            role = ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"])
        if role.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        elif role.position > ctx.me.top_role.position:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm_bot").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        if role != 0:
            Guild_settings[ctx.guild.id]["auth_role"] = role.id
        e = discord.Embed(
            title="認証ボタン - Web認証", description=f'下の{Official_emojis["check5"]}を押して認証\nロール: {ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"]).mention}', color=Widget)
        m = await ctx.send(embed=e)
        await m.add_reaction(Official_emojis["check5"])
        await ctx.message.delete()

    @auth.command(name="web")
    @commands.has_guild_permissions(manage_roles=True)
    async def auth_web(self, ctx, role: discord.Role = 0):
        global Guild_settings
        if Guild_settings[ctx.guild.id]["auth_role"] == 0 and role == 0:
            e = discord.Embed(title="ロールが登録されていません",
                              description="初回はロールを登録する必要があります", color=Error)
            await ctx.reply(embed=e)
            return
        elif role.position > ctx.author.top_role.position and not ctx.guild.owner_id == ctx.author.id:
            e = discord.Embed(
                title=get_txt(ctx.guild.id, "no_role_perm").format(role.name), color=Error)
            await ctx.reply(embed=e)
            return
        if role != 0:
            Guild_settings[ctx.guild.id]["auth_role"] = role.id
        e = discord.Embed(
            title="認証ボタン - Web認証", description=f'下のボタンを押して認証\nロール: {ctx.guild.get_role(Guild_settings[ctx.guild.id]["auth_role"]).mention}', color=Widget)
        await components.send(ctx, embed=e, components=[components.Button("認証", "auth")])
        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            pass

    async def make_image_auth_url(self, message):
        im = Image.open("./base_img/text_base.png").convert("RGBA")
        im2 = Image.open("./base_img/text_base_fore.png")
        draw = ImageDraw.Draw(im)
        # fnt = ImageFont.truetype("./fonts/bold.OTF", 32)
        # tfnt = ImageFont.truetype("./fonts/midium.OTF", 32)
        bfnt = ImageFont.truetype("./fonts/bold.OTF", 64)
        auth_text = hashlib.md5(
            str(time.time()).encode()).hexdigest()[0:8]
        w, h = draw.textsize(auth_text, font=bfnt)
        draw.text(((640 - w) / 2, (640 - h) / 2),
                  auth_text, fill="white", font=bfnt)
        im3 = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        for x, y in product(range(im3.size[0]), repeat=2):
            nr = random.randrange(0, 255)
            ng = random.randrange(0, 255)
            nb = random.randrange(0, 255)
            im3.putpixel((x, y), (nr, ng, nb, 128))
        im = Image.alpha_composite(im, im3.resize(im.size))
        draw = ImageDraw.Draw(im)
        im.paste(im2, mask=im2)
        tmpio = io.BytesIO()
        im.save(tmpio, format="png")
        tmpio.seek(0)
        amsg = await self.bot.get_channel(765528694500360212).send(file=discord.File(tmpio, filename="result.png"))
        tmpio.close()
        return amsg.attachments[0].url, auth_text


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(AuthCog(_bot))
