import asyncio
import re

from telethon import events
from telethon.tl.functions.channels import EditTitleRequest
from telethon.errors.rpcerrorlist import ChatNotModifiedError

MULTI_EDIT_TIMEOUT = 80
REVERT_TIMEOUT = 2 * 60 * 60
CHANNEL_ID = 1040270887
DEFAULT_TITLE = "Programming & Tech"
rename_lock = asyncio.Lock()
revert_task = None


def fix_title(s):
    # Ideally this would be a state machine, but ¯\_(ツ)_/¯
    def replace(m):
        token = m.group(1)
        if token.lower() == 'and':
            token = '&'
        return token[0].upper() + token[1:] + (' ' if m.group(2) else '')
    return re.sub(r'(\S+)(\s+)?', replace, s)


async def edit_title(title):
    try:
        await borg(EditTitleRequest(
            channel=CHANNEL_ID, title=title
        ))
    except ChatNotModifiedError:
        pass  # Everything is ok


async def wait_for_delete(deleted_fut, timeout):
    try:
        await asyncio.wait_for(deleted_fut, timeout)
        return True
    except asyncio.TimeoutError:
        pass
    return False


async def wait_and_revert(timeout):
    await asyncio.sleep(timeout)
    await edit_title(DEFAULT_TITLE)


@borg.on(events.NewMessage(
    pattern=re.compile(r"(?i)programming (?:&|and) (.+)"), chats=CHANNEL_ID))
async def on_name(event):
    global revert_task
    new_topic = fix_title(event.pattern_match.group(1))
    new_title = f"Programming & {new_topic}"
    if "Tech" not in new_title:
        new_title += " & Tech"

    if len(new_title) > 255 or rename_lock.locked():
        return

    with (await rename_lock):
        await edit_title(new_title)
        await asyncio.sleep(MULTI_EDIT_TIMEOUT)

    if revert_task and not revert_task.done():
        revert_task.cancel()
    revert_task = asyncio.create_task(wait_and_revert(REVERT_TIMEOUT))