from __future__ import annotations
from typing import Literal, NewType, TypedDict, Union

Snowflake = NewType("Snowflake", int)


class EventMessages(TypedDict):
    join: Union[False, str]
    leave: Union[False, str]


class WWRole(TypedDict):
    alive: None | Snowflake
    dead: None | Snowflake


class WarnSettings(TypedDict):
    action: Literal["mute", "kick", "ban", "role_add", "role_remove"]


class WarnSettingsMute(WarnSettings, total=False):
    length: int


class WarnSettingsRole(WarnSettings, total=False):
    role: Snowflake


class LockMessageContent(TypedDict):
    content: str
    author: Snowflake


class GuildSettings(TypedDict):
    autoreply: dict[str, list[str, str]]
    muted: dict[Snowflake, int]
    tts_dicts: dict[str, dict[str, str]]
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
    warns: dict[Snowflake, int]
    warn_settings: WarnSettings
    timed_role: dict[Snowflake, int]
    gban_enabled: bool
    lock_message_content: dict[Snowflake, LockMessageContent]
    lock_message_id: dict[Snowflake, Snowflake | None]
