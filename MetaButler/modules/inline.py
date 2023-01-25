import html
import json
from datetime import datetime
from platform import python_version
from typing import List
from uuid import uuid4

import requests
from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent, Update, InlineKeyboardMarkup, \
    InlineKeyboardButton
from telegram import __version__
from telegram.error import BadRequest
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

import MetaButler.modules.sql.users_sql as sql
from MetaButler import (
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    DEV_USERS,
    WHITELIST_USERS,
    sw, log
)
from MetaButler.modules.helper_funcs.misc import article
from MetaButler.modules.helper_funcs.decorators import metainline


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        text = text.replace(prefix, "", 1)
    return text

@metainline()
def inlinequery(update: Update, _) -> None:
    """
    Main InlineQueryHandler callback.
    """
    query = update.inline_query.query
    user = update.effective_user

    results: List = []
    inline_help_dicts = [
        {
            "title": "Account info on MetaButler",
            "description": "Look up a Telegram account in MetaButler database",
            "message_text": "Click the button below to look up a person in MetaButler database using their Telegram ID",
            "thumb_urL": "https://telegra.ph/file/888b20d2f85e53d692ebd.jpg",
            "keyboard": ".info ",
        },
        {
            "title": "About",
            "description": "Know about MetaButler",
            "message_text": "Click the button below to get to know about MetaButler.",
            "thumb_urL": "https://telegra.ph/file/888b20d2f85e53d692ebd.jpg",
            "keyboard": ".about ",
        },
    ]

    inline_funcs = {
        ".info": inlineinfo,
        ".about": about,
    }

    if (f := query.split(" ", 1)[0]) in inline_funcs:
        inline_funcs[f](remove_prefix(query, f).strip(), update, user)
    else:
        for ihelp in inline_help_dicts:
            results.append(
                article(
                    title=ihelp["title"],
                    description=ihelp["description"],
                    message_text=ihelp["message_text"],
                    thumb_url=ihelp["thumb_urL"],
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text="Click Here",
                                    switch_inline_query_current_chat=ihelp[
                                        "keyboard"
                                    ],
                                )
                            ]
                        ]
                    ),
                )
            )

        update.inline_query.answer(results, cache_time=5)


def inlineinfo(query: str, update: Update, context: CallbackContext) -> None:
    """Handle the inline query."""
    bot = context.bot
    query = update.inline_query.query
    log.info(query)
    user_id = update.effective_user.id

    try:
        search = query.split(" ", 1)[1]
    except IndexError:
        search = user_id

    try:
        user = bot.get_chat(int(search))
    except (BadRequest, ValueError):
        user = bot.get_chat(user_id)

    chat = update.effective_chat
    sql.update_user(user.id, user.username)

    text = (
        f"<b>Information:</b>\n"
        f"• ID: <code>{user.id}</code>\n"
        f"• First Name: {html.escape(user.first_name)}"
    )

    if user.last_name:
        text += f"\n• Last Name: {html.escape(user.last_name)}"

    if user.username:
        text += f"\n• Username: @{html.escape(user.username)}"

    text += f"\n• Permanent user link: {mention_html(user.id, 'link')}"

    try:
        spamwtc = sw.get_ban(int(user.id))
        if spamwtc:
            text += "<b>\n\n• SpamWatched:\n</b> Yes"
            text += f"\n• Reason: <pre>{spamwtc.reason}</pre>"
            text += "\n• Appeal at @SpamWatchSupport"
        else:
            text += "<b>\n\n• SpamWatched:</b> No"
    except:
        pass  # don't crash if api is down somehow...

    num_chats = sql.get_user_num_chats(user.id)
    text += f"\n• <b>Chat count</b>: <code>{num_chats}</code>"




    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Report Error",
                    url=f"https://t.me/MetaProjectsSupport",
                ),
                InlineKeyboardButton(
                    text="Search again",
                    switch_inline_query_current_chat=".info ",
                ),

            ],
        ]
        )

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"User info of {html.escape(user.first_name)}",
            input_message_content=InputTextMessageContent(text, parse_mode=ParseMode.HTML,
                                                          disable_web_page_preview=True),
            reply_markup=kb
        ),
    ]

    update.inline_query.answer(results, cache_time=5)


def about(query: str, update: Update, context: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query
    user_id = update.effective_user.id
    user = context.bot.get_chat(user_id)
    sql.update_user(user.id, user.username)
    about_text = f"""
    MetaButler (@{context.bot.username})
    Maintained by [Destroyer32](t.me/destroyer32)
    Built with ❤️ using python-telegram-bot v{str(__version__)}
    Running on Python {python_version()}
    """
    results: list = []
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Support",
                    url=f"https://t.me/MetaProjectsSupport",
                ),
                InlineKeyboardButton(
                    text="Channel",
                    url=f"https://t.me/metabutlernews",
                ),
                InlineKeyboardButton(
                    text='Ping',
                    callback_data='pingCB'
                ),

            ],
            [
                InlineKeyboardButton(
                    text="GitHub",
                    url="https://github.com/MetaButler/MetaButler",
                ),
            ],
        ])

    results.append(

        InlineQueryResultArticle
            (
            id=str(uuid4()),
            title=f"About MetaButler (@{context.bot.username})",
            input_message_content=InputTextMessageContent(about_text, parse_mode=ParseMode.MARKDOWN,
                                                          disable_web_page_preview=True),
            reply_markup=kb
        )
    )
    update.inline_query.answer(results)
