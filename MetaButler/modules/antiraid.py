# Raid module by Luke (t.me/itsLuuke)
import html
from typing import Optional
from datetime import timedelta
from pytimeparse.timeparse import timeparse

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html

from .log_channel import loggable
from .helper_funcs.anonymous import user_admin, AdminPerms
from .helper_funcs.chat_status import bot_admin, connection_status, user_admin_no_reply
from .helper_funcs.decorators import metacmd, metacallback
from .. import log, updater

import MetaButler.modules.sql.welcome_sql as sql

j = updater.job_queue

# store job id in a dict to be able to cancel them later
RUNNING_ANTIRAIDS = {}  # {chat_id:job_id, ...}


def get_time(time: str) -> int:
    try:
        return timeparse(time)
    except BaseException:
        return 0


def get_readable_time(time: int) -> str:
    t = f"{timedelta(seconds=time)}".split(":")
    if time == 86400:
        return "1 day"
    return "{} hour(s)".format(t[0]) if time >= 3600 else "{} minutes".format(t[1])


@metacmd(command="antiraid", pass_args=True)
@bot_admin
@connection_status
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def setAntiRaid(update: Update, context: CallbackContext) -> Optional[str]:
    args = context.args
    chat = update.effective_chat
    msg = update.effective_message
    user = update.effective_user
    if chat.type == "private":
        context.bot.sendMessage(chat.id, "This command is not available in PMs.")
        return
    stat, time, acttime = sql.getAntiRaidStatus(chat.id)
    readable_time = get_readable_time(time)
    if len(args) == 0:
        if stat:
            text = 'AntiRaid mode is currently <code>Enabled</code>\nWould you like to <code>Disable</code> AntiRaid?'
            keyboard = [[
                InlineKeyboardButton("Disable AntiRaid Mode", callback_data="disable_antiraid={}={}".format(chat.id, time)),
                InlineKeyboardButton("Cancel Action", callback_data="cancel_antiraid=1"),
            ]]
        else:
            text = f"AntiRaid mode is currently <code>Disabled</code>\nWould you like to <code>Enable</code> " \
                   f"AntiRaid for {readable_time}?"
            keyboard = [[
                InlineKeyboardButton("Enable AntiRaid Mode", callback_data="enable_antiraid={}={}".format(chat.id, time)),
                InlineKeyboardButton("Cancel Action", callback_data="cancel_antiraid=0"),
            ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

    elif args[0] == "off":
        if stat:
            sql.setAntiRaidStatus(chat.id, False, time, acttime)
            j.scheduler.remove_job(RUNNING_ANTIRAIDS.pop(chat.id))
            text = "AntiRaid mode has been <code>Disabled</code>, members that join will no longer be kicked."
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#ANTIRAID\n"
                f"Disabled\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")

    else:
        args_time = args[0].lower()
        if time := get_time(args_time):
            readable_time = get_readable_time(time)
            if 300 <= time < 86400:
                text = f"AntiRaid mode is currently <code>Disabled</code>\nWould you like to <code>Enable</code> " \
                       f"AntiRaid for {readable_time}? "
                keyboard = [[
                    InlineKeyboardButton("Enable AntiRaid", callback_data="enable_antiraid={}={}".format(chat.id, time)),
                    InlineKeyboardButton("Cancel Action", callback_data="cancel_antiraid=0"),
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                msg.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
            else:
                msg.reply_text("You can only set time between 5 minutes and 1 day", parse_mode=ParseMode.HTML)

        else:
            msg.reply_text("Unknown time given, give me something like 5m or 1h", parse_mode=ParseMode.HTML)


@metacallback(pattern="enable_antiraid=")
@connection_status
@user_admin_no_reply
@loggable
def enable_antiraid_cb(update: Update, ctx: CallbackContext) -> Optional[str]:
    args = update.callback_query.data.replace("enable_antiraid=", "").split("=")
    chat = update.effective_chat
    user = update.effective_user
    chat_id = args[0]
    time = int(args[1])
    readable_time = get_readable_time(time)
    _, t, acttime = sql.getAntiRaidStatus(chat_id)
    sql.setAntiRaidStatus(chat_id, True, time, acttime)
    update.effective_message.edit_text(f"AntiRaid mode has been <code>Enabled</code> for {readable_time}.",
                                       parse_mode=ParseMode.HTML)
    log.info("enabled antiraid mode in {} for {}".format(chat_id, readable_time))
    try:
        oldAntiRaid = RUNNING_ANTIRAIDS.pop(int(chat_id))
        j.scheduler.remove_job(oldAntiRaid)  # check if there was an old job
    except KeyError:
        pass

    def disable_antiraid(_):
        sql.setAntiRaidStatus(chat_id, False, t, acttime)
        log.info("disbled antiraid mode in {}".format(chat_id))
        ctx.bot.send_message(chat_id, "AntiRaid mode has been automatically disabled!")

    antiraid = j.run_once(disable_antiraid, time)
    RUNNING_ANTIRAIDS[int(chat_id)] = antiraid.job.id
    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#ANTIRAID\n"
        f"Enabled for {readable_time}\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
    )


@metacallback(pattern="disable_antiraid=")
@connection_status
@user_admin_no_reply
@loggable
def disable_antiraid_cb(update: Update, _: CallbackContext) -> Optional[str]:
    args = update.callback_query.data.replace("disable_antiraid=", "").split("=")
    chat = update.effective_chat
    user = update.effective_user
    chat_id = args[0]
    time = args[1]
    _, _, acttime = sql.getAntiRaidStatus(chat_id)
    sql.setAntiRaidStatus(chat_id, False, time, acttime)
    j.scheduler.remove_job(RUNNING_ANTIRAIDS.pop(int(chat_id)))
    update.effective_message.edit_text(
        'AntiRaid mode has been <code>Disabled</code>, newly joining members will no longer be kicked.',
        parse_mode=ParseMode.HTML,
    )
    logmsg = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#ANTIRAID\n"
        f"Disabled\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
    )
    return logmsg


@metacallback(pattern="cancel_antiraid=")
@connection_status
@user_admin_no_reply
def disable_antiraid_cb(update: Update, _: CallbackContext):
    args = update.callback_query.data.split("=")
    what = args[0]
    update.effective_message.edit_text(
        f"Action cancelled, AntiRaid mode will stay <code>{'Enabled' if what == 1 else 'Disabled'}</code>.",
        parse_mode=ParseMode.HTML)


@metacmd(command="antiraidtime")
@connection_status
@loggable
@user_admin(AdminPerms.CAN_CHANGE_INFO)
def antiraidtime(update: Update, context: CallbackContext) -> Optional[str]:
    what, time, acttime = sql.getAntiRaidStatus(update.effective_chat.id)
    args = context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not args:
        msg.reply_text(
            f"AntiRaid mode is currently set to {get_readable_time(time)}\nWhen toggled, the AntiRaid mode will last "
            f"for {get_readable_time(time)} then turn off automatically",
            parse_mode=ParseMode.HTML)
        return
    args_time = args[0].lower()
    if time := get_time(args_time):
        readable_time = get_readable_time(time)
        if 300 <= time < 86400:
            text = f"AntiRaid mode is currently set to {readable_time}\nWhen toggled, the AntiRaid mode will last for " \
                   f"{readable_time} then turn off automatically"
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            sql.setAntiRaidStatus(chat.id, what, time, acttime)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#ANTIRAID\n"
                    f"Set AntiRaid mode time to {readable_time}\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")
        else:
            msg.reply_text("You can only set time between 5 minutes and 1 day", parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Unknown time given, give me something like 5m or 1h", parse_mode=ParseMode.HTML)


@metacmd(command="antiraidactiontime", pass_args=True)
@connection_status
@user_admin(AdminPerms.CAN_CHANGE_INFO)
@loggable
def antiraidtime(update: Update, context: CallbackContext) -> Optional[str]:
    what, t, time = sql.getAntiRaidStatus(update.effective_chat.id)
    args = context.args
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if not args:
        msg.reply_text(
            f"AntiRaid action time is currently set to {get_readable_time(time)}\nWhen toggled, the members that "
            f"join will be temp banned for {get_readable_time(time)}",
            parse_mode=ParseMode.HTML)
        return
    args_time = args[0].lower()
    if time := get_time(args_time):
        readable_time = get_readable_time(time)
        if 300 <= time < 86400:
            text = f"AntiRaid action time is currently set to {get_readable_time(time)}\nWhen toggled, the members that" \
                   f" join will be temp banned for {readable_time}"
            msg.reply_text(text, parse_mode=ParseMode.HTML)
            sql.setAntiRaidStatus(chat.id, what, t, time)
            return (f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#ANTIRAID\n"
                    f"Set AntiRaid mode action time to {readable_time}\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n")
        else:
            msg.reply_text("You can only set time between 5 minutes and 1 day", parse_mode=ParseMode.HTML)
    else:
        msg.reply_text("Unknown time given, give me something like 5m or 1h", parse_mode=ParseMode.HTML)


from .language import gs


def get_help(chat):
    return gs(chat, "antiraid_help")


__mod_name__ = "AntiRaid"
