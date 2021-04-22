from asyncio import sleep
from telethon import events
from MetaButler import dispatcher
from MetaButler import telethn as MetaButlerTelethonClient
from MetaButler.modules.sql.clear_cmd_sql import get_clearcmd
from MetaButler.modules.helper_funcs.telethn.chatstatus import user_is_admin
from MetaButler.modules.helper_funcs.misc import delete


@MetaButlerTelethonClient.on(events.NewMessage(pattern=f"^[!/]zombies ?(.*)"))
async def zombies(event):
    chat = await event.get_chat()
    chat_id = event.chat_id
    admin = chat.admin_rights
    creator = chat.creator

    if not await user_is_admin(
        user_id = event.sender_id, message = event
    ):
        delmsg = "Only Admins are allowed to use this command"

    elif not admin and not creator:
        delmsg = "I am not an admin here!"

    else:

        count = 0
        arg = event.pattern_match.group(1).lower()

        if not arg:
                msg = "**Searching for zombies...**\n"
                msg = await event.reply(msg)
                async for user in event.client.iter_participants(event.chat):
                    if user.deleted:
                        count += 1

                if count == 0:
                    delmsg = await msg.edit("No deleted accounts found. Group is clean")
                else:
                    delmsg = await msg.edit(f"Found **{count}** zombies in this group\nClean them by using - `/zombies clean`")
        
        elif arg == "clean":
            msg = "**Cleaning zombies...**\n"
            msg = await event.reply(msg)
            async for user in event.client.iter_participants(event.chat):
                if user.deleted:
                    count += 1
                    await event.client.kick_participant(chat, user)

            if count == 0:
                delmsg = await msg.edit("No deleted accounts found. Group is clean")
            else:
                delmsg = await msg.edit(f"Cleaned `{count}` zombies")
      
        else:
            delmsg = await event.reply("Wrong parameter. You can use only `/zombies clean`")


    cleartime = get_clearcmd(chat_id, "zombies")

    if cleartime:
        await sleep(cleartime.time)
        await delmsg.delete()

