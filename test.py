import discord
from discord.ext import commands
from common_resources.tokens import TOKEN
bot = commands.Bot(["sbt#", "sbt. ", "sbt."], intents=discord.Intents.all())


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
bot.load_extension("jishaku")
bot.run(TOKEN)
