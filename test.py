import discord
from discord.ext import commands
from common_resources.tokens import TOKEN
bot= commands.Bot(["sbt#", "sbt. ", "sbt."], intents=discord.Intents.all())

bot.load_extension("jishaku")
bot.run(TOKEN)
