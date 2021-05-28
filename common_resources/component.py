from dataclasses import dataclass
from typing import Union

import discord
from discord import File, AllowedMentions
from discord import utils
from discord.emoji import Emoji
from discord.errors import InvalidArgument
from discord.http import Route


@dataclass
class Button:
    label: str
    name: str = None
    color: int = 1
    url: str = None
    emoji: Union[Emoji, str] = None
    enabled: bool = True

    def to_dict(self):
        res = {
            "type": 2,
            "style": self.color,
            "label": self.label,
            "disabled": not self.enabled
        }
        if self.emoji:
            if isinstance(self.emoji, str):
                res["emoji"] = {"name": self.emoji}
            else:
                res["emoji"] = {
                    "id": self.emoji.id,
                    "name": self.emoji.name,
                    "animated": self.emoji.animated
                }
        if self.name:
            res["custom_id"] = self.name
        if self.url:
            res["url"] = self.url
        return res


async def _send_files(self, channel_id, *, files, content=None, tts=False, embed=None, nonce=None, allowed_mentions=None, message_reference=None, components=None):
    r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel_id)
    form = []

    payload = {'tts': tts}
    if content:
        payload['content'] = content
    if embed:
        payload['embed'] = embed
    if nonce:
        payload['nonce'] = nonce
    if allowed_mentions:
        payload['allowed_mentions'] = allowed_mentions
    if message_reference:
        payload['message_reference'] = message_reference
    if components:
        payload['components'] = components
    form.append({'name': 'payload_json', 'value': utils.to_json(payload)})
    if len(files) == 1:
        file = files[0]
        form.append({
            'name': 'file',
            'value': file.fp,
            'filename': file.filename,
            'content_type': 'application/octet-stream'
        })
    else:
        for index, file in enumerate(files):
            form.append({
                'name': 'file%s' % index,
                'value': file.fp,
                'filename': file.filename,
                'content_type': 'application/octet-stream'
            })

    return self.request(r, form=form, files=files)


async def send_with_components(channel, content=None, *, tts=False, embed=None, file=None,
                               files=None, delete_after=None, nonce=None,
                               allowed_mentions=None, reference=None,
                               mention_author=None, components=[]):

    channel = await channel._get_channel()
    state = channel._state
    components2 = []
    if isinstance(components[0], list):
        components2 = [{
            "type": 1,
            "components": list(map(lambda b: b.to_dict(), c)),
        }
            for c in components]
    else:
        components2 = [{
            "type": 1,
            "components": list(map(lambda b: b.to_dict(), components)),
        }]
    content = str(content) if content is not None else None
    if embed is not None:
        embed = embed.to_dict()

    if allowed_mentions is not None:
        if state.allowed_mentions is not None:
            allowed_mentions = state.allowed_mentions.merge(allowed_mentions).to_dict()
        else:
            allowed_mentions = allowed_mentions.to_dict()
    else:
        allowed_mentions = state.allowed_mentions and state.allowed_mentions.to_dict()

    if mention_author is not None:
        allowed_mentions = allowed_mentions or AllowedMentions().to_dict()
        allowed_mentions['replied_user'] = bool(mention_author)

    if reference is not None:
        try:
            reference = reference.to_message_reference_dict()
        except AttributeError:
            raise InvalidArgument('reference parameter must be Message or MessageReference') from None

    if file is not None and files is not None:
        raise InvalidArgument('cannot pass both file and files parameter to send()')

    if file is not None:
        if not isinstance(file, File):
            raise InvalidArgument('file parameter must be File')

        try:
            data = await _send_files(channel.id, files=[file], allowed_mentions=allowed_mentions,
                                     content=content, tts=tts, embed=embed, nonce=nonce,
                                     message_reference=reference, components=components2)
        finally:
            file.close()

    elif files is not None:
        if len(files) > 10:
            raise InvalidArgument('files parameter must be a list of up to 10 elements')
        elif not all(isinstance(file, File) for file in files):
            raise InvalidArgument('files parameter must be a list of File')

        try:
            data = await _send_files(channel.id, files=files, content=content, tts=tts,
                                     embed=embed, nonce=nonce, allowed_mentions=allowed_mentions,
                                     message_reference=reference, components=components2)
        finally:
            for f in files:
                f.close()
    else:
        r = Route('POST', '/channels/{channel_id}/messages', channel_id=channel.id)
        payload = {}

        if content:
            payload['content'] = content

        if tts:
            payload['tts'] = True

        if embed:
            payload['embed'] = embed

        if nonce:
            payload['nonce'] = nonce

        if allowed_mentions:
            payload['allowed_mentions'] = allowed_mentions

        if reference:
            payload['message_reference'] = reference

        if components2:
            payload['components'] = components2

        data = await state.http.request(r, json=payload)

    ret = state.create_message(channel=channel, data=data)

    if delete_after is not None:
        await ret.delete(delay=delete_after)
    return ret


async def edit_with_components(message, **fields):
    try:
        content = fields['content']
    except KeyError:
        pass
    else:
        if content is not None:
            fields['content'] = str(content)

    try:
        embed = fields['embed']
    except KeyError:
        pass
    else:
        if embed is not None:
            fields['embed'] = embed.to_dict()

    try:
        suppress = fields.pop('suppress')
    except KeyError:
        pass
    else:
        flags = discord.MessageFlags._from_value(message.flags.value)
        flags.suppress_embeds = suppress
        fields['flags'] = flags.value

    delete_after = fields.pop('delete_after', None)

    try:
        allowed_mentions = fields.pop('allowed_mentions')
    except KeyError:
        if message._state.allowed_mentions is not None and message.author.id == message._state.self_id:
            fields['allowed_mentions'] = message._state.allowed_mentions.to_dict()
    else:
        if allowed_mentions is not None:
            if message._state.allowed_mentions is not None:
                allowed_mentions = message._state.allowed_mentions.merge(allowed_mentions).to_dict()
            else:
                allowed_mentions = allowed_mentions.to_dict()
            fields['allowed_mentions'] = allowed_mentions

    try:
        attachments = fields.pop('attachments')
    except KeyError:
        pass
    else:
        fields['attachments'] = [a.to_dict() for a in attachments]

    components2 = []
    components = fields.get("components")
    if components:
        if isinstance(components[0], list):
            components2 = [{
                "type": 1,
                "components": list(map(lambda b: b.to_dict(), c)),
            }
                for c in components]
        else:
            components2 = [{
                "type": 1,
                "components": list(map(lambda b: b.to_dict(), components)),
            }]
        fields["components"] = components2

    if fields:
        data = await message._state.http.edit_message(message.channel.id, message.id, **fields)
        message._update(data)

    if delete_after is not None:
        await message.delete(delay=delete_after)
