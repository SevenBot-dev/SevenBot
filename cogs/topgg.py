import aiohttp
from discord.ext import commands, tasks

import _pathmagic  # type: ignore # noqa


class TopGG(commands.Cog):
    """
    This example uses dblpy's autopost feature to post guild count to top.gg every 30 minutes.
    """

    def __init__(self, bot):
        self.bot = bot
        # Autopost will post your guild count every 30 minutes
        if not self.bot.debug:
            self.dblpy = self.bot.DBL_client
            self.task = self.update_stats.start()

    @tasks.loop(minutes=30)
    async def update_stats(self):
        """This function runs every 30 minutes to automatically update your server count."""
        await self.bot.wait_until_ready()
        try:
            server_count = len(self.bot.guilds)
            await self.dblpy.post_guild_count(server_count)
        except Exception as e:
            raise e

    @commands.Cog.listener()
    async def on_dbl_vote(self, data):
        async with aiohttp.ClientSession() as s:
            async with s.post("https://canary.discord.com/api/webhooks/773443377147936778/wdDFijmd9G0dVict2qpP-3rOP9i2i3e-LDcAlWSRCVF5WwTJziLoMVETMb8Ldy5qCONP",
                              json={"content": f'<@!{data["user"]}> さんが高評価をしてくれました！', "allowed_mentions": {"parse": []}}) as r:
                r.raise_for_status()

    def cog_unload(self):
        self.upload_stats.stop()


def setup(bot):
    bot.add_cog(TopGG(bot))
