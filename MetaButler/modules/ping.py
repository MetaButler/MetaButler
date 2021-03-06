import time
from typing import List

import requests
from telegram import ParseMode, Update, Bot
from telegram.ext import  run_async

from MetaButler import StartTime, dispatcher
from MetaButler.modules.helper_funcs.chat_status import user_admin
from MetaButler.modules.disable import DisableAbleCommandHandler

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        if count < 3:
            remainder, result = divmod(seconds, 60)
        else:
            remainder, result = divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time

@user_admin
def ping(update: Update, context):
    msg = update.effective_message

    start_time = time.time()
    message = msg.reply_text("Just A Sec...")
    end_time = time.time()
    telegram_ping = str(round((end_time - start_time) * 1000, 3)) + " ms"
    uptime = get_readable_time((time.time() - StartTime))

    message.edit_text(
        "<b>Ping:</b> <code>{}</code>\n"
        "<b>Bot Uptime:</b> <code>{}</code>".format(telegram_ping, uptime),
        parse_mode=ParseMode.HTML,
    )

PING_HANDLER = DisableAbleCommandHandler("uptime", ping, run_async=True)

dispatcher.add_handler(PING_HANDLER)
