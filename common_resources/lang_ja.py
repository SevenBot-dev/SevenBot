import ujson as json
import os

Event_dict = {"join": "参加時", "leave": "退出時"}
Stat_dict = {
    "members": "メンバー数",
    "humans": "ユーザー数",
    "bots": "ボット数",
    "onlines": "オンライン数",
    "online_per": "オンライン割合",
    "channels": "チャンネル",
    "text_channels": "テキストチャンネル",
    "voice_channels": "ボイスチャンネル",
    "roles": "ロール",
}
en = ""
for ek, ev in Event_dict.items():
    en += f"{ek} - {ev}\n"
st = ""
for ek, ev in Stat_dict.items():
    st += f"{ek} - {ev}\n"
with open(
    os.path.dirname(__file__) + "/../translations/ja/main.json",
    "r",
    encoding="utf8",
) as f:
    JA_TEXTS = json.load(f)
