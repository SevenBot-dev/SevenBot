import discord
from discord.http import Route
from discord.ext import commands


class ComponentResponse():
    def __init__(self, bot, data, state):
        self.bot = bot
        self.state = state
        self.id = int(data["id"])
        self.application_id = int(data["application_id"])
        self.guild = bot.get_guild(int(data["guild_id"]))
        self.channel = bot.get_channel(int(data["message"]["channel_id"]))
        self.message = discord.Message(state=bot._get_state(), channel=self.channel, data=data["message"])
        self.member = discord.Member(state=bot._get_state(), guild=self.guild, data=data["member"])
        self.token = data["token"]
        self.custom_id = data["data"]["custom_id"]
        self.defered = False
        self.sent_callback = False

    async def defer_source(self, hidden=False):
        if self.defered:
            raise "Already defered."
        r = Route('POST', '/interactions/{interaction_id}/{interaction_token}/callback', interaction_id=self.id, interaction_token=self.token)
        self.defered = True
        await self.bot.http.request(r, json={"type": 5, "data": {"flags": 64 if hidden else 0}})

    async def defer_update(self):
        if self.defered:
            raise "Already defered."
        r = Route('POST', '/interactions/{interaction_id}/{interaction_token}/callback', interaction_id=self.id, interaction_token=self.token)
        self.defered = True
        await self.bot.http.request(r, json={"type": 6})

    async def send(self, content=None, *, embed=None, embeds=[], allowed_mentions=None, hidden=False, tts=False):

        state = self.state
        content = str(content) if content is not None else None
        if embed is not None:
            if embeds:
                raise ValueError("You mustn't specify embed and embeds same time.")
            else:
                embeds = [embed]

        if allowed_mentions is not None:
            if state.allowed_mentions is not None:
                allowed_mentions = state.allowed_mentions.merge(allowed_mentions).to_dict()
            else:
                allowed_mentions = allowed_mentions.to_dict()
        else:
            allowed_mentions = state.allowed_mentions and state.allowed_mentions.to_dict()
        if self.sent_callback:
            r = Route('POST', "/webhooks/{application_id}/{interaction_token}", application_id=self.application_id, interaction_token=self.token)
            await state.http.request(r, json={
                "content": content,
                "tts": tts,
                "embeds": list(map(lambda e: e.to_dict(), embeds)),
                "allowed_mentions": allowed_mentions,
                "flags": 64 if hidden else 0
            })
        elif self.defered:
            r = Route('PATCH', "/webhooks/{application_id}/{interaction_token}/messages/@original", application_id=self.application_id, interaction_token=self.token)
            await state.http.request(r, json={
                "content": content,
                "tts": tts,
                "embeds": list(map(lambda e: e.to_dict(), embeds)),
                "allowed_mentions": allowed_mentions,
                "flags": 64 if hidden else 0
            })
            self.sent_callback = True
        else:
            r = Route('POST', '/interactions/{interaction_id}/{interaction_token}/callback', interaction_id=self.id, interaction_token=self.token)
            await state.http.request(r, json={
                "type": 4,
                "data": {
                    "content": content,
                    "tts": tts,
                    "embeds": list(map(lambda e: e.to_dict(), embeds)),
                    "allowed_mentions": allowed_mentions,
                    "flags": 64 if hidden else 0
                }
            })
            self.sent_callback = True
        self.defered = True

    async def _get_channel(self):
        return self.channel


class ComponentCog(commands.Cog):
    def __init__(self, bot):
        global Guild_settings, Texts
        global get_txt
        self.bot = bot

    @commands.Cog.listener()
    async def on_socket_response(self, pl):
        if pl["t"] != "INTERACTION_CREATE":
            return
        data = pl["d"]
        if data["type"] != 3:
            return
        self.bot.dispatch("component_click", ComponentResponse(self.bot, data, self.bot._get_state()))


def setup(_bot):
    global bot
    bot = _bot
    _bot.add_cog(ComponentCog(_bot))
