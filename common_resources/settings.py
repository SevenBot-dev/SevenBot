from __future__ import annotations

import re
import typing
from typing import Literal, NewType, TypedDict, Union

Snowflake = NewType("Snowflake", int)


class GuildSettings(TypedDict):
    autoreply: dict[str, list[str, str]]
    muted: dict[Snowflake, int]
    deactivate_command: list[Snowflake]
    auth_role: Snowflake
    trans_channel: dict[Snowflake, str]
    event_messages: EventMessages
    event_message_channel: Snowflake
    level_counts: dict[Snowflake, int]
    levels: dict[Snowflake, int]
    level_roles: dict[int, Snowflake]
    level_active: bool
    level_channel: False | Snowflake
    level_ignore_channel: list[Snowflake]
    level_boosts: dict[Snowflake, float]
    do_bump_alert: False | Snowflake
    bump_role: False | Snowflake
    do_dissoku_alert: False | Snowflake
    dissoku_role: False | Snowflake
    prefix: None | str
    autopub: list[Snowflake]
    anchor_link: list[Snowflake]
    role_link: dict[Snowflake, list[list[Snowflake, Snowflake]]]
    archive_category: Snowflake
    ww_role: WWRole
    ticket_category: Snowflake
    warns: dict[Snowflake, int]
    warn_settings: WarnSettings
    timed_role: dict[Snowflake, int]
    gban_enabled: bool
    lock_message_content: dict[Snowflake, LockMessageContent]
    lock_message_id: dict[Snowflake, Snowflake | None]


def _get_int_keys():
    def convert_union(txt: re.Match):
        return "Union[" + txt[0].replace(" | ", ", ") + "]"

    def pass_arg(arg: typing.ForwardRef):
        arg_str = arg.__forward_arg__
        arg_str = (
            re.sub(r"(\w+ \| )+(\w+)", convert_union, arg_str)
            .replace("False", "Literal[False]")
            .replace("True", "Literal[True]")
            .replace("Snowflake", "int")
        )
        return eval(arg_str)

    settings = dict(map(lambda a: [a[0], pass_arg(a[1])], GuildSettings.__annotations__.items()))
    int_keys = []

    def get_key_type(k, v):
        if isinstance(v, typing._TypedDictMeta):
            val_types = dict(map(lambda a: [a[0], pass_arg(a[1])], v.__annotations__.items()))
            for k2, v2 in val_types.items():
                get_key_type(k + "." + k2, v2)
            return
        if not hasattr(v, "__origin__"):
            return
        if v.__origin__ is dict:
            if v.__args__[0] is int:
                int_keys.append(k)
            if isinstance(v.__args__[1], typing._TypedDictMeta):
                val_types = dict(map(lambda a: [a[0], pass_arg(a[1])], v.__args__[1].__annotations__.items()))
                for k2, v2 in val_types.items():
                    get_key_type(k + "." + k2, v2)

    for k, v in settings.items():
        get_key_type(k, v)
    return int_keys


DEFAULT_SETTINGS: GuildSettings = {
    "autoreply": {},
    "muted": {},
    "deactivate_command": [],
    "last_everyone": {},
    "everyone_count": {},
    "hasnt_admin": "権限がありません。",
    "do_announce": True,
    "announce_channel": False,
    "auth_role": 0,
    "trans_channel": {},
    "event_messages": {"join": False, "leave": False},
    "event_message_channel": 0,
    "alarm_channels": 0,
    "level_counts": {},
    "levels": {},
    "level_roles": {},
    "level_active": False,
    "level_channel": False,
    "level_ignore_channel": [],
    "bump_role": False,
    "do_dissoku_alert": False,
    "dissoku_role": False,
    "do_stat_channels": False,
    "stat_channels": {},
    "stat_update_counter": 0,
    "ticket_category": 0,
    "auto_parse": [],
    "do_everyone_alert": True,
    "lang": "ja",
    "expand_message": False,
    "do_bump_alert": True,
    "invites": [],
    "prefix": None,
    "autopub": [],
    "alarms": {},
    "2ch_link": [],
    "role_link": {},
    "role_keep": False,
    "timezone": 0,
    "archive_category": 0,
    "ww_role": {"alive": None, "dead": None},
    "kana_talk": [],
    "auth_channel": {
        "type": None,
        "channel": 0,
    },
    "starboards": {},
    "level_boosts": {},
    "warns": {},
    "warn_settings": {"punishments": {}, "auto": 0},
    "economy": {},
    "timed_role": {},
    "auto_text": [],
    "gban_enabled": False,
    "lock_message_content": {},
    "lock_message_id": {},
}


class EventMessages(TypedDict):
    join: Union[False, str]
    leave: Union[False, str]


class WWRole(TypedDict):
    alive: None | Snowflake
    dead: None | Snowflake


class WarnSettings(TypedDict):
    punishments: dict[int, WarnSettingsAction]


class WarnSettingsAction(TypedDict):
    action: Literal["mute", "kick", "ban", "role_add", "role_remove"]


class WarnSettingsActionMute(WarnSettingsAction, total=False):
    length: int


class WarnSettingsActionRole(WarnSettingsAction, total=False):
    role: Snowflake


class LockMessageContent(TypedDict):
    content: str
    author: Snowflake


class AutoMod(TypedDict):
    token_spam: AutoModItem
    invite_spam: AutoModItem


class AutoModItem(TypedDict, total=False):
    enabled: bool
    warn: int | None
    disabled_channels: list[Snowflake]


class AutoModGlobal(TypedDict):
    warn: int
    disabled_channels: list[Snowflake]


DEFAULT_AUTOMOD_ITEM: AutoModItem = {
    "enabled": False,
    "warn": 0,
    "disabled_channels": [],
}

DEFAULT_AUTOMOD_GLOBAL: AutoModGlobal = {
    "warn": 1,
    "disabled_channels": [],
}

GuildSettings.int_keys = _get_int_keys()
