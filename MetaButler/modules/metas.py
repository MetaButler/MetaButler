import html
import json
import os
from typing import List, Optional

from telegram import Update, ParseMode, TelegramError
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from MetaButler import (
    dispatcher,
    WHITELIST_USERS,
    SUPPORT_USERS,
    SUDO_USERS,
    DEV_USERS,
    OWNER_ID,
)
from MetaButler.modules.helper_funcs.chat_status import whitelist_plus, dev_plus, sudo_plus
from MetaButler.modules.helper_funcs.extraction import extract_user
from MetaButler.modules.log_channel import gloggable
from MetaButler.modules.sql import metas_sql as sql
from MetaButler.modules.helper_funcs.decorators import metacmd

def check_user_id(user_id: int, context: CallbackContext) -> Optional[str]:
    bot = context.bot
    if not user_id:
        return "That...is a chat!"

    elif user_id == bot.id:
        return "This does not work that way."

    else:
        return None

@metacmd(command='addsudo')
@dev_plus
@gloggable
def addsudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        message.reply_text("This member is already a Sudo user")
        return ""

    if user_id in SUPPORT_USERS:
        rt += "Requested MetaButler to promote a Support user to Sudo."
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        rt += "Requested MetaButler to promote a Whitelist user to Sudo."
        WHITELIST_USERS.remove(user_id)

    # will add or update their role
    sql.set_meta_role(user_id, "sudos")
    SUDO_USERS.append(user_id)

    update.effective_message.reply_text(
        rt
        + "\nSuccessfully promoted {} to Sudo!".format(
            user_member.first_name
        )
    )

    log_message = (
        f"#SUDO\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@metacmd(command='addsupport')
@sudo_plus
@gloggable
def addsupport(
    update: Update,
    context: CallbackContext,
) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "Requested MetaButler to demote this Sudo to Support"
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        message.reply_text("This user is already a Support user.")
        return ""

    if user_id in WHITELIST_USERS:
        rt += "Requested MetaButler to promote this Whitelist user to Support"
        WHITELIST_USERS.remove(user_id)

    sql.set_meta_role(user_id, "supports")
    SUPPORT_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\n{user_member.first_name} was added as a Support user!"
    )

    log_message = (
        f"#SUPPORT\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message


@metacmd(command='addwhitelist')
@sudo_plus
@gloggable
def addwhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)
    rt = ""

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        rt += "This member is a Sudo user, Demoting to Whitelisted user."
        SUDO_USERS.remove(user_id)

    if user_id in SUPPORT_USERS:
        rt += "This user is already a Support user, Demoting to Whitelisted user."
        SUPPORT_USERS.remove(user_id)

    if user_id in WHITELIST_USERS:
        message.reply_text("This user is already a Whitelist user.")
        return ""

    sql.set_meta_role(user_id, "whitelists")
    WHITELIST_USERS.append(user_id)

    update.effective_message.reply_text(
        rt + f"\nSuccessfully promoted {user_member.first_name} to a Whitelist user!"
    )

    log_message = (
        f"#WHITELIST\n"
        f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))} \n"
        f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
    )

    if chat.type != "private":
        log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

    return log_message

@metacmd(command='removesudo')
@dev_plus
@gloggable
def removesudo(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUDO_USERS:
        message.reply_text("Requested MetaButler to demote this user to Civilian")
        SUDO_USERS.remove(user_id)
        sql.remove_meta(user_id)

        log_message = (
            f"#UNSUDO\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = "<b>{}:</b>\n".format(html.escape(chat.title)) + log_message

        return log_message

    else:
        message.reply_text("This user is not a Sudo user!")
        return ""


@metacmd(command='removesupport')
@sudo_plus
@gloggable
def removesupport(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in SUPPORT_USERS:
        message.reply_text("Requested MetaButler to demote this user to Civilian")
        SUPPORT_USERS.remove(user_id)
        sql.remove_meta(user_id)

        log_message = (
            f"#UNSUPPORT\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message

    else:
        message.reply_text("This user is not a Support user!")
        return ""


@metacmd(command='removewhitelist')
@sudo_plus
@gloggable
def removewhitelist(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    bot, args = context.bot, context.args
    user_id = extract_user(message, args)
    user_member = bot.getChat(user_id)

    reply = check_user_id(user_id, bot)
    if reply:
        message.reply_text(reply)
        return ""

    if user_id in WHITELIST_USERS:
        message.reply_text("Demoting to normal user")
        WHITELIST_USERS.remove(user_id)
        sql.remove_meta(user_id)

        log_message = (
            f"#UNWHITELIST\n"
            f"<b>Admin:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(user_member.id, html.escape(user_member.first_name))}"
        )

        if chat.type != "private":
            log_message = f"<b>{html.escape(chat.title)}:</b>\n" + log_message

        return log_message
    else:
        message.reply_text("This user is not a Whitelist user!")
        return ""


def send_metas(update):
    update.effective_message.reply_text(
        metas, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
    )

@metacmd(command='removesardegna')
@whitelist_plus
def whitelistlist(update: Update, context: CallbackContext):
    bot = context.bot
    reply = "<b>Known Whitelisted :</b>\n"
    for each_user in WHITELIST_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)

            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@metacmd(command=["supportlist"])
@whitelist_plus
def supportlist(update: Update, context: CallbackContext):
    bot = context.bot
    reply = "<b>Known Support :</b>\n"
    for each_user in SUPPORT_USERS:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@metacmd(command=["sudolist"])
@whitelist_plus
def sudolist(update: Update, context: CallbackContext):
    bot = context.bot
    true_sudo = list(set(SUDO_USERS) - set(DEV_USERS))
    reply = "<b>Known Sudos :</b>\n"
    for each_user in true_sudo:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)

@metacmd(command=["devlist"])
@whitelist_plus
def devlist(update: Update, context: CallbackContext):
    bot = context.bot
    true_dev = list(set(DEV_USERS) - {OWNER_ID})
    reply = "<b>Dev Members :</b>\n"
    for each_user in true_dev:
        user_id = int(each_user)
        try:
            user = bot.get_chat(user_id)
            reply += f"• {mention_html(user_id, user.first_name)}\n"
        except TelegramError:
            pass
    update.effective_message.reply_text(reply, parse_mode=ParseMode.HTML)


from MetaButler.modules.language import gs

__mod_name__ = "Metas"
