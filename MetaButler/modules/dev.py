import os
import subprocess
import sys
from time import sleep
from MetaButler import dispatcher, telethn, OWNER_ID
from MetaButler.modules.helper_funcs.chat_status import dev_plus
from telegram import TelegramError, Update
from telegram.ext import CallbackContext, CommandHandler
import asyncio
from statistics import mean
from time import monotonic as time
from telethon import events

@dev_plus
def leave(update: Update, context: CallbackContext):
    bot = context.bot
    args = context.args
    if args:
        chat_id = str(args[0])
        try:
            bot.leave_chat(int(chat_id))
            update.effective_message.reply_text("Left chat.")
        except TelegramError:
            update.effective_message.reply_text("Failed to leave chat for some reason.")
    else:
        update.effective_message.reply_text("Send a valid chat ID")

class Store:
    def __init__(self, func):
        self.func = func
        self.calls = []
        self.time = time()
        self.lock = asyncio.Lock()

    def average(self):
        return round(mean(self.calls), 2) if self.calls else 0

    def __repr__(self):
        return f"<Store func={self.func.__name__}, average={self.average()}>"

    async def __call__(self, event):
        async with self.lock:
            if not self.calls:
                self.calls = [0]
            if time() - self.time > 1:
                self.time = time()
                self.calls.append(1)
            else:
                self.calls[-1] += 1
        await self.func(event)

async def nothing(event):
    pass


messages = Store(nothing)
inline_queries = Store(nothing)
callback_queries = Store(nothing)

telethn.add_event_handler(messages, events.NewMessage())
telethn.add_event_handler(inline_queries, events.InlineQuery())
telethn.add_event_handler(callback_queries, events.CallbackQuery())


@telethn.on(events.NewMessage(pattern=r"/getstats", from_users=OWNER_ID))
async def getstats(event):
    await event.reply(
        f"**__META EVENT STATISTICS__**\n**Average messages:** {messages.average()}/s\n**Average Callback Queries:** {callback_queries.average()}/s\n**Average Inline Queries:** {inline_queries.average()}/s", parse_mode='md'
        )


LEAVE_HANDLER = CommandHandler("leave", leave, run_async=True)

dispatcher.add_handler(LEAVE_HANDLER)

__mod_name__ = "Dev"
__handlers__ = [LEAVE_HANDLER]
