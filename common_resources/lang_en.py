import json
import os

Event_dict2 = {
    "join": "On join",
    "leave": "On leave"
}
Stat_dict2 = {
    "members": "Members",
    "humans": "Users",
    "bots": "Bots",
    "onlines": "Onlines",
    "online_per": "Online percent",
    "channels": "Channels",
    "text_channels": "Text channels",
    "voice_channels": "Voice channels",
    "roles": "Roles"
}
en2 = ""
for ek, ev in Event_dict2.items():
    en2 += f"`{ek}`: {ev}\n"
st2 = ""
for ek, ev in Stat_dict2.items():
    st2 += f"`{ek}`: {ev}\n"
with open(os.path.dirname(__file__) + "../translations/en/main.json", "r", encoding="utf8") as f:
    EN_TEXTS = json.load(f)
