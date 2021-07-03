import importlib

import discord

from . import lang_en, lang_ja

importlib.reload(lang_en)
importlib.reload(lang_ja)
Texts = {"ja": lang_ja.JA_TEXTS, "en": lang_en.EN_TEXTS}
Info = discord.Color.blue()
Attention = discord.Color.orange()
Level = discord.Color.gold()
Error = discord.Color.red()
Widget = discord.Color.darker_grey()
Gaming = discord.Color.greyple()
Alert = discord.Color.dark_orange()
Success = discord.Color.green()
Process = discord.Color.dark_green()
Premium_color = 0xF76FF2
Bot_info = 0x00CCFF
Chat = discord.Color.lighter_grey()
Time_format = "%Y-%m-%d %H:%M:%S"
Activate_aliases = ["on", "active", "true"]
Deactivate_aliases = ["off", "disable", "false"]
Event_dict = lang_ja.Event_dict
Stat_dict = lang_ja.Stat_dict
Official_discord_id = 715540925081714788
Sub_discord_id = 723276556629442590
Owner_ID = 686547120534454315
