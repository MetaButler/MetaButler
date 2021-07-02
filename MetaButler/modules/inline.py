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
            "title": "SpamProtection INFO",
            "description": "Look up a person/bot/channel/chat on @Intellivoid SpamProtection API",
            "message_text": "Click the button below to look up a person/bot/channel/chat on @Intellivoid SpamProtection API using "
                            "username or telegram id",
            "thumb_urL": "https://telegra.ph/file/888b20d2f85e53d692ebd.jpg",
            "keyboard": ".spb ",
        },
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
        ".spb": spb,
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
                    url=f"https://t.me/MetaButler",
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
    """
    results: list = []
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Support",
                    url=f"https://t.me/MetaButler",
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
                    url="https://www.github.com/DESTROYER-32/MetaButler",
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


def spb(query: str, update: Update, context: CallbackContext) -> None:
    """Handle the inline query."""
    query = update.inline_query.query
    user_id = update.effective_user.id
    srdata = None
    apst = requests.get(f'https://api.intellivoid.net/spamprotection/v1/lookup?query={context.bot.username}')
    api_status = apst.status_code
    if (api_status != 200):
        stats = f"API RETURNED {api_status}"
    else:
        try:
            search = query.split(" ", 1)[1]
        except IndexError:
            search = user_id

        srdata = search or user_id

        url = f"https://api.intellivoid.net/spamprotection/v1/lookup?query={srdata}"
        r = requests.get(url)
        a = r.json()
        response = a["success"]
        if response is True:
            date = a["results"]["last_updated"]
            stats = f"*◢ Intellivoid• SpamProtection Info*:\n"
            stats += f' • *Updated on*: `{datetime.fromtimestamp(date).strftime("%Y-%m-%d %I:%M:%S %p")}`\n'

            if a["results"]["attributes"]["is_potential_spammer"] is True:
                stats += f" • *User*: `USERxSPAM`\n"
            elif a["results"]["attributes"]["is_operator"] is True:
                stats += f" • *User*: `USERxOPERATOR`\n"
            elif a["results"]["attributes"]["is_agent"] is True:
                stats += f" • *User*: `USERxAGENT`\n"
            elif a["results"]["attributes"]["is_whitelisted"] is True:
                stats += f" • *User*: `USERxWHITELISTED`\n"

            stats += f' • *Type*: `{a["results"]["entity_type"]}`\n'
            stats += (
                f' • *Language*: `{a["results"]["language_prediction"]["language"]}`\n'
            )
            stats += f' • *Language Probability*: `{a["results"]["language_prediction"]["probability"]}`\n'
            stats += f"*Spam Prediction*:\n"
            stats += f' • *Ham Prediction*: `{a["results"]["spam_prediction"]["ham_prediction"]}`\n'
            stats += f' • *Spam Prediction*: `{a["results"]["spam_prediction"]["spam_prediction"]}`\n'
            stats += f'*Blacklisted*: `{a["results"]["attributes"]["is_blacklisted"]}`\n'
            if a["results"]["attributes"]["is_blacklisted"] is True:
                stats += (
                    f' • *Reason*: `{a["results"]["attributes"]["blacklist_reason"]}`\n'
                )
                stats += f' • *Flag*: `{a["results"]["attributes"]["blacklist_flag"]}`\n'
            stats += f'*PTID*:\n`{a["results"]["private_telegram_id"]}`\n'

        else:
            stats = "`cannot reach SpamProtection API`"

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="Report Error",
                    url=f"https://t.me/MetaButler",
                ),
                InlineKeyboardButton(
                    text="Search again",
                    switch_inline_query_current_chat=".spb ",
                ),

            ],
        ])

    a = "the entity was not found"
    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"SpamProtection API info of {srdata or a}",
            input_message_content=InputTextMessageContent(stats, parse_mode=ParseMode.MARKDOWN,
                                                          disable_web_page_preview=True),
            reply_markup=kb
        ),
    ]

    update.inline_query.answer(results, cache_time=5)