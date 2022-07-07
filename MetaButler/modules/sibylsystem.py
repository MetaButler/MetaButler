import logging
from enum import Enum
from typing import Optional, Tuple

from SibylSystem import GeneralException
from telegram import (Bot, Chat, InlineKeyboardButton, InlineKeyboardMarkup,
                      Message, MessageEntity, Update, User)
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CallbackQueryHandler
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.filters import Filters
from telegram.ext.messagehandler import MessageHandler
from telegram.parsemode import ParseMode
from telegram.utils import helpers
from telegram.utils.helpers import mention_html

from . import ALL_MODULES
from .helper_funcs.chat_status import (connection_status, is_user_admin,
                                       user_admin)
from .helper_funcs.extraction import extract_user
from .log_channel import loggable
from .sql.users_sql import get_user_com_chats

try:
    from .disable import DisableAbleCommandHandler
except:
    DisableAbleCommandHandler = CommandHandler

import MetaButler.modules.sql.sibyl_sql as sql
from MetaButler import SIBYL_KEY, sibylClient, log
from MetaButler.modules.helper_funcs.decorators import metacmd, metamsg, metacallback

from .. import dispatcher

log.info(
    "For support reach out to @PublicSafetyBureau on Telegram | Powered by Kaizoku")

SIBYLBAN_SETTINGS = sql.SIBYLBAN_SETTINGS


def get_sibyl_setting(chat_id):
    try:
        log_stat = SIBYLBAN_SETTINGS[f'{chat_id}'][0]
        act = SIBYLBAN_SETTINGS[f'{chat_id}'][1]
    except KeyError:  # set default
        log_stat = True
        act = 1
    return log_stat, act


@loggable
def sibyl_ban(update: Update, context: CallbackContext) -> Optional[str]:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not user:
        return
    bot = context.bot
    if not sql.does_chat_sibylban(chat.id):
        return

    mem = chat.get_member(user.id)
    if mem.status not in ["member", "left"]:
        return

    if sibylClient:
        log_stat, act = get_sibyl_setting(chat.id)
        try:
            data = sibylClient.get_info(user.id)
        except GeneralException:
            return

        except BaseException as e:
            logging.error(e)
            return

        if data.banned and act in {1, 2}:
            try:
                bot.ban_chat_member(chat_id=chat.id, user_id=user.id)
            except BadRequest:
                return
            except BaseException as e:
                logging.error(
                    f"Failed to ban {user.id} in {chat.id} due to {e}")

            txt = '''{} has a <a href="https://t.me/SibylSystem/3">Crime Coefficient</a> of {}\n'''.format(
                user.mention_html(), data.crime_coefficient,
            )
            txt += "<b>Enforcement Mode:</b> {}".format(
                "Lethal Eliminator" if not data.is_bot else "Destroy Decomposer",
            )
            log_msg = "#SIBYL_BAN #{}".format(", #".join(
                data.ban_flags)) if data.ban_flags else "#SIBYL_BAN"
            log_msg += f"\n • <b>User:</b> {user.mention_html()}\n"
            log_msg += f" • <b>Reason:</b> <code>{data.reason}</code>\n" if data.reason else ""
            log_msg += f" • <b>Ban time:</b> <code>{data.date}</code>" if data.date else ""

            if act == 1:
                message.reply_html(text=txt, disable_web_page_preview=True)

            if log_stat:
                return log_msg

            handle_sibyl_banned(user, data)


@loggable
def sibyl_ban_alert(update: Update, context: CallbackContext) -> Optional[str]:
    message = update.effective_message
    chat = update.effective_chat
    users = update.effective_message.new_chat_members
    bot = context.bot
    if not users:
        return

    if not sql.does_chat_sibylban(chat.id):
        return

    if sibylClient:
        log_stat, act = get_sibyl_setting(chat.id)
        if act != 3:  # just for alert mode
            return

        for user in users:
            try:
                data = sibylClient.get_info(user.id)
            except GeneralException:
                return
            except BaseException as e:
                logging.error(e)
                return

            if data.banned:
                txt = '''{} has a <a href="https://t.me/SibylSystem/3">Crime Coefficient</a> of {}\n'''.format(
                    user.mention_html(), data.crime_coefficient,
                )
                txt += "<b>Enforcement Mode:</b> None"
                url = helpers.create_deep_linked_url(
                    bot.username, f"sibyl_banned-{user.id}")

                keyboard = [[InlineKeyboardButton(text="More Info", url=url)]]

                reply_markup = InlineKeyboardMarkup(keyboard)
                log_msg = "#SIBYL_BAN #{}".format(", #".join(
                    data.ban_flags)) if data.ban_flags else "#SIBYL_BAN"
                log_msg += f"\n • <b>User:</b> {user.mention_html()}\n"
                log_msg += f" • <b>Reason:</b> <code>{data.reason}</code>\n" if data.reason else ""
                log_msg += f" • <b>Ban time:</b> <code>{data.date}</code>\n" if data.date else ""
                log_msg += " • <b>Enforcement Mode:</b> None"
                message.reply_html(
                    text=txt, disable_web_page_preview=True, reply_markup=reply_markup)

                if log_stat:
                    return log_msg

                handle_sibyl_banned(user, data)


@loggable
def handle_sibyl_banned(user, data):
    bot = dispatcher.bot
    chat = get_user_com_chats(user.id)
    keyboard = [[InlineKeyboardButton(
        "Appeal", url="https://t.me/SibylRobot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        bot.send_message(user.id, "You have been added to Sibyl Database",
                         parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    except BaseException as e:
        logging.error(e)

    for c in chat:
        if sql.does_chat_sibylban(c):
            log_stat, act = get_sibyl_setting(c.id)

            if act in {1, 2}:
                # ban user without spamming chat even if its interactive
                bot.ban_chat_member(chat_id=c, user_id=user.id)

            if log_stat:
                log_msg = "#SIBYL_BAN #{}".format(", #".join(
                    data.ban_flags)) if data.ban_flags else "#SIBYL_BAN"
                log_msg += f" • <b>User</b> {user.mention_html()}\n"
                log_msg += f" • <b>Reason:</b> <code>{data.reason}</code>\n" if data.reason else ""
                log_msg += f" • <b>Ban time:</b> <code>{data.date}</code>\n" if data.date else ""
                log_msg += " • <b>Enforcement Mode:</b> None"


modes_txt = '''
Sibyl System Modes:
 • <b>Interactive</b> - Anti spam with alerts
 • <b>Silent</b> - Silently handling bad users in the background
 • <b>Alerts Only</b> - Only Alerts of bad users, no actions taken

Additional Configuration:
 • <b>Log Channel</b> - Creates a log channel entry (if you have a log channel set) for all sibyl events

Current Settings:'''

connection_txt = '''
Connection to <a href="https://t.me/SibylSystem/2">Sibyl System</a> can be turned off and on using the panel buttons below.
'''


@connection_status
@metacmd('sibyl')
@metacallback(pattern=r'sibyl_connect', run_async=True)
@user_admin
def sibylmain(update: Update, _: CallbackContext):
    chat = update.effective_chat
    message = update.effective_message
    stat = sql.does_chat_sibylban(chat.id)
    user = update.effective_user
    if update.callback_query:
        if update.callback_query.data == "sibyl_connect=toggle":
            if not is_user_admin(update, user.id):
                update.callback_query.answer()
                return

            if stat:
                sql.disable_sibyl(chat.id)
                stat = False
            else:
                sql.enable_sibyl(chat.id)
                stat = True
            update.callback_query.answer(
                f'Sibyl System has been {"Enabled!" if stat else "Disabled!"}')

        elif update.callback_query.data == "sibyl_connect=close":
            if not is_user_admin(update, user.id):
                update.callback_query.answer()
            message.delete()
            return

    text = f'{connection_txt}\n • <b>Current Status:</b> <code>{"Enabled" if stat else "Disabled"}</code>'
    keyboard = [
        [
            InlineKeyboardButton(
                "✤ Disconnect" if stat else "✤ Connect",
                callback_data="sibyl_connect=toggle",
            ),
            InlineKeyboardButton(
                "♡ Modes",
                callback_data='sibyl_toggle=main',
            ),
        ],
        [
            InlineKeyboardButton(
                "❖ API",
                url="https://t.me/PsychoPass/4",
            ),
            InlineKeyboardButton(
                "？What is Sibyl",
                url="https://t.me/SibylSystem/2",
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        message.edit_text(text, reply_markup=reply_markup,
                          parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except BadRequest:
        message.reply_text(text, reply_markup=reply_markup,
                           parse_mode=ParseMode.HTML, disable_web_page_preview=True)


class SibylMode(Enum):
    Interactive = 1
    Silent = 2
    Alerts = 3


@connection_status
@metacallback(pattern=r'sibyl_toggle', run_async=True)
def sibyltoggle(update: Update, _: CallbackContext):
    chat: Chat = update.effective_chat
    message: Message = update.effective_message
    user: User = update.effective_user
    if not is_user_admin(update, user.id):
        update.callback_query.answer("Only admins can toggle this!")
        return

    log_stat, act = get_sibyl_setting(chat.id)
    todo = update.callback_query.data.replace("sibyl_toggle=", "")

    if todo.startswith("log"):
        sql.toggle_sibyl_log(chat.id)
        log_stat = not log_stat

    elif not todo.startswith("main"):
        sql.toggle_sibyl_mode(chat.id, int(todo))
        act = int(todo)

    text = f'{modes_txt}\n • <b>Mode:</b> <code>{SibylMode(act).name}</code>\n'
    text += f' • <b>Logs:</b> <code>{"Enabled" if log_stat else "Disabled"}</code>'
    keyboard = [
        [
            InlineKeyboardButton(
                SibylMode(2).name if act != 2 else SibylMode(1).name,
                callback_data=f"sibyl_toggle={int(2 if not act==2 else 1)}",
            ),
            InlineKeyboardButton(
                SibylMode(3).name + " Only" if act != 3 else SibylMode(1).name,
                callback_data=f'sibyl_toggle={int(3 if act != 3 else 1)}',
            ),
        ],
        [
            InlineKeyboardButton(
                "🔙",
                callback_data="sibyl_connect",
            ),
            InlineKeyboardButton(
                "Disable Log" if log_stat else "Enable Log",
                callback_data="sibyl_toggle=log",
            ),
            InlineKeyboardButton(
                "✖️",
                callback_data="sibyl_connect=close",
            ),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        message.edit_text(text, reply_markup=reply_markup,
                          parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except BadRequest:
        pass


def sibyl_banned(update: Update, ctx: CallbackContext):
    chat: Chat = update.effective_chat
    args = ctx.args
    bot: Bot = ctx.bot

    if not(chat.type == "private" and args):
        return

    if not args[0].startswith("sibyl_banned-"):
        return

    user_id = args[0].split("-")[1]
    user: User = bot.get_chat(user_id)

    if not sibylClient:
        return

    txt, reply_markup = get_sibyl_info(bot, user, True)

    update.effective_message.reply_text(
        txt, parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True,
    )


def sibyl_info(update: Update, context: CallbackContext):
    bot: Bot = context.bot
    args = context.args
    message: Message = update.effective_message
    if user_id := extract_user(update.effective_message, args):
        user: User = bot.get_chat(user_id)

    elif not message.reply_to_message and not args:
        user = message.from_user

    elif not message.reply_to_message and (
            not args
            or (
                len(args) >= 1
                and not args[0].startswith("@")
                and not args[0].isdigit()
                and not message.parse_entities([MessageEntity.TEXT_MENTION])
            )
    ):
        message.reply_text("I can't extract a user from this.")
        return

    else:
        return

    msg = message.reply_text(
        "<code>Performing a Cymatic Scan...</code>",
        parse_mode=ParseMode.HTML,
    )

    txt, reply_markup = get_sibyl_info(bot, user)

    msg.edit_text(text=txt, reply_markup=reply_markup,
                  parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def get_sibyl_info(bot: Bot, user: User, detailed: bool = False) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    reply_markup = None
    txt = "<b>Cymatic Scan Results</b>"
    txt += f"\n • <b>User</b>: {mention_html(user.id, user.first_name)}"
    txt += f"\n • <b>ID</b>: <code>{user.id}</code>"

    try:
        data = sibylClient.get_info(user.id)
    except GeneralException:
        data = None
    except BaseException as e:
        logging.error(e)
        data = None

    if data:
        txt += f"\n • <b>Banned:</b> <code>{'No' if not data.banned else 'Yes'}</code>"
        cc = data.crime_coefficient or "?"
        txt += f"\n • <b>Crime Coefficient:</b> <code>{cc}</code> [<a href='https://t.me/SibylSystem/3'>?</a>]"
        hue = data.hue_color or "?"
        txt += f"\n • <b>Hue Color:</b> <code>{hue}</code> [<a href='https://t.me/SibylSystem/5'>?</a>]"
        if data.ban_flags:
            txt += f"\n • <b>Flagged For:</b> <code>{', '.join(data.ban_flags)}</code>"
        if data.date:
            txt += f"\n • <b>Date:</b> <code>{data.date}</code>"
        if data.is_bot:
            txt += "\n • <b>Bot:</b> <code>Yes</code>"

        if data.crime_coefficient < 10:
            txt += "\n • <b>Status:</b> <code>Inspector</code>"
        elif 10 <= data.crime_coefficient < 80:
            txt += "\n • <b>Status:</b> <code>Civilian</code>"
        elif 81 <= data.crime_coefficient <= 100:
            txt += "\n • <b>Status:</b> <code>Restored</code>"
        elif 101 <= data.crime_coefficient <= 150:
            txt += "\n • <b>Status:</b> <code>Enforcer</code>"

        if detailed:
            if data.reason:
                txt += f"\n • <b>Reason:</b> <code>{data.reason}</code>"
            if data.ban_source_url:
                txt += f"\n • <b>Origin:</b> <a href='{data.ban_source_url}'>link</a> "
            if data.source_group:
                txt += f"\n • <b>Attached Source:</b> <code>{data.source_group}</code>"
            if data.message:
                txt += f"\n • <b>Ban Message:</b> {data.message}"

    else:
        txt += "\n • <b>Banned:</b> <code>No</code>"
        txt += f"\n • <b>Crime Coefficient:</b> <code>?</code> [<a href='https://t.me/SibylSystem/3'>?</a>]"
        txt += f"\n • <b>Hue Color:</b> <code>?</code> [<a href='https://t.me/SibylSystem/5'>?</a>]"

    txt += "\n\nPowered by @SibylSystem | Kaizoku"
    if data and data.banned:
        keyboard = [[]]
        if not detailed:
            url = helpers.create_deep_linked_url(
                bot.username, f"sibyl_banned-{user.id}")
            keyboard[0].append(InlineKeyboardButton("More info", url=url))
        keyboard[0].append(InlineKeyboardButton(
            "Appeal", url="https://t.me/SibylRobot"))
        reply_markup = InlineKeyboardMarkup(keyboard)
    return txt, reply_markup


if SIBYL_KEY and __name__.split(".")[-1] in ALL_MODULES:
    dispatcher.add_handler(
        MessageHandler(filters=Filters.chat_type.groups, callback=sibyl_ban), group=101,
    )
    dispatcher.add_handler(
        MessageHandler(filters=Filters.status_update.new_chat_members, callback=sibyl_ban_alert), group=102,
    )

    dispatcher.add_handler(
        CommandHandler(command="start", callback=sibyl_banned, run_async=True), group=113,
    )
    # dispatcher.add_handler(
    #     CallbackQueryHandler(sibylmain, pattern="sibyl_connect", run_async=True), group=112,
    # )


__help__ = """
[Sibyl System](https://t.me/SibylSystem/14) is an anti-spam module designed off the anime "[PsychoPass]". 
This module is capable of interactively or silently handling bad users that Sibyl has recognised to be maliciuos in nature.

The module is on by default and comes with 2 commands. 

*Available Commands:* 
 • `/sibyl`*:* Run this in a group to control settings
 • `/check`*:* An info command to check if a user exists in Sibyl's database
"""
"""
Other Terminologies 
• [Crime Coefficient](https://t.me/SibylSystem/3)
• [Ban Flags and reasons](https://t.me/SibylSystem/4)
• [Hue Colors explained](https://t.me/SibylSystem/5) 
• [API Help and docs](https://t.me/PsychoPass/5)
• [Support group](https://t.me/PublicSafetyBureau)
• [Report bad users](https://t.me/MinistryOfWelfare/8)
"""


def get_help():
    return [__help__,
            [
                InlineKeyboardButton(text="Crime Coefficient",
                                     url="https://t.me/SibylSystem/3"),
                InlineKeyboardButton(
                    text="Ban Flags", url="https://t.me/SibylSystem/4"),
            ],
            [
                InlineKeyboardButton(
                    text="Hue Colors", url="https://t.me/SibylSystem/5"),
                InlineKeyboardButton(
                    text="API Help", url="https://t.me/SibylSystem/5"),
            ],
            [
                InlineKeyboardButton(
                    text="Support", url="https://t.me/PublicSafetyBureau"),
                InlineKeyboardButton(text="Report Crime",
                                     url="https://t.me/MinistryOfWelfare/8"),
            ],
            ]


__mod_name__ = "SibylSystem"
