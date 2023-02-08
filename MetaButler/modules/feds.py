import ast
import csv
from email import message
import html
import json
import os
import re
import time
import uuid
from io import BytesIO
from typing import Optional

import MetaButler.modules.sql.feds_sql as sql
from MetaButler import OWNER_ID, SUDO_USERS, WHITELIST_USERS, dispatcher, log
from MetaButler.modules.helper_funcs.alternate import (send_action,
                                                       typing_action)
from MetaButler.modules.helper_funcs.chat_status import (is_user_admin,
                                                         is_user_creator)
from MetaButler.modules.helper_funcs.decorators import metacallback, metacmd
from MetaButler.modules.helper_funcs.extraction import (extract_unt_fedban,
                                                        extract_user,
                                                        extract_user_fban)
from MetaButler.modules.helper_funcs.string_handling import markdown_parser
from MetaButler.modules.log_channel import loggable
from telegram import (Chat, ChatAction, ChatMember, InlineKeyboardButton,
                      InlineKeyboardMarkup, MessageEntity, ParseMode, Update,
                      User)
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram.ext import CallbackContext
from telegram.utils.helpers import mention_html, mention_markdown

# Hello bot owner, I spent many hours of my life for feds, Please don't remove this if you still respect MrYacha and peaktogoo and AyraHikari too
# Federation by MrYacha 2018-2019
# Federation rework by Mizukito Akito 2019
# Federation update v2 by Ayra Hikari 2019
#
# These comments are being kept simply out of respect, even after the refactor of the federations module
#
# Time spended on feds = 10h by #MrYacha
# Time spended on reworking on the whole feds = 22+ hours by @peaktogoo
# Time spended on updating version to v2 = 26+ hours by @AyraHikari
#
# Total spended for making this features is 68+ hours

log.info("Original federation module by MrYacha, reworked by Mizukito Akito (@peaktogoo) on Telegram. Refactored by @Cooldude69_420")

FBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Peer_id_invalid",
    "Group chat was deactivated",
    "Need to be inviter of a user to kick it from a basic group",
    "Chat_admin_required",
    "Only the creator of a basic group can kick group administrators",
    "Channel_private",
    "Not in the chat",
    "Have no rights to send a message",
}

UNFBAN_ERRORS = {
    "User is an administrator of the chat",
    "Chat not found",
    "Not enough rights to restrict/unrestrict chat member",
    "User_not_participant",
    "Method is available for supergroup and channel chats only",
    "Not in the chat",
    "Channel_private",
    "Chat_admin_required",
    "Have no rights to send a message",
}


@metacmd(command='newfed')
@typing_action
def new_fed(update: Update, _: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat.type != 'private':
        message.reply_text('You can create your federation in my PM, not in a group!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedname = message.text.split(None, 1)
    if len(fedname) >= 2:
        fedname = fedname[1]
        fed_id = str(uuid.uuid4())

        fed = sql.new_fed(message.from_user.id, fedname, fed_id)
        if not fed:
            message.reply_text(
                'Can\'t federate! Please report in @MetaProjectsSupport if the problem persists.')
            return

        message.reply_text(
            "<b>You have successfully created a new federation!</b>\n"
            f"Name: <code>{fedname}</code>\n"
            f"ID: <code>{fed_id}</code>\n\n"
            "Use the command below to join the federation:"
            f"\n<code>/joinfed {fed_id}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        message.reply_text('You need to provide a name for the federation.\nFormat <code>/newfed fedname</code>',
                           parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='delfed', pass_args=True)
@typing_action
def del_fed(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type != 'private':
        message.reply_text('You can delete federations in my PM, not in the group!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if args:
        fed_id = args[0]
        info = sql.get_fed_info(fed_id)
        if info is False:
            message.reply_text('This federation is not found!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if not is_user_fed_owner(fed_id, message.from_user.id):
            message.reply_text('Only federation owners can do this!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        message.reply_text(
            f"Are you sure you want to delete your federation? This action cannot be canceled, you will lose your entire ban list, and <code>{info['fname']}</code> will be permanently lost.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="⚠️ Remove Federation ⚠️", callback_data=f"rmfed_{fed_id}")
                    ],
                    [
                        InlineKeyboardButton(
                            text="Cancel Operation", callback_data="rmfed_cancel")
                    ],
                ]
            ),
            parse_mode=ParseMode.HTML
        )
    else:
        message.reply_text('Whaddya want me to delete?',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return


@metacmd(command='chatfed')
@typing_action
def fed_chat(update: Update, _: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if not is_user_admin(update, message.from_user.id):
        message.reply_text('You must be an admin to execute this command!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This group is not in any federation!')
        return
    fedinfo = sql.get_fed_info(fed_id)
    text = f'This chat is part of the following federation:\n{fedinfo["fname"]} (ID: <code>{fed_id}</code>)'
    message.reply_text(text, parse_mode=ParseMode.HTML,
                       reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='joinfed', pass_args=True)
@typing_action
def join_fed(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    args = context.args
    if not is_user_creator(update, context, message.from_user.id):
        message.reply_text('Only group creators can use this command!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if fed_id:
        message.reply_text('You cannot join two federations from one chat!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if len(args) >= 1:
        fedinfo = sql.search_fed_by_id(args[0])
        if not fedinfo:
            message.reply_text('Please enter a valid federation ID',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fedchat = sql.chat_join_fed(args[0], chat.title, chat.id)
        if not fedchat:
            message.reply_text('Failed to join federation!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fedlog = sql.get_fed_log(args[0])
        if fedlog:
            if ast.literal_eval(fedlog):
                context.bot.send_message(
                    fedlog, f'Chat <b>{chat.title}</b> has joined the federation <b>{fedinfo["fname"]}</b>', parse_mode=ParseMode.HTML)
        message.reply_text(f'This chat has joined the federation {fedinfo["fname"]}',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='leavefed')
@typing_action
def leave_fed(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    fed_info = sql.get_fed_info(fed_id)
    if not is_user_creator(update, context, message.from_user.id):
        message.reply_text('Only group creators can use this command!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if sql.chat_leave_fed(chat.id):
        fedlog = sql.get_fed_log(fed_id)
        if fedlog:
            if ast.literal_eval(fedlog):
                context.bot.send_message(
                    fedlog, f'Chat <b>{chat.title}</b> has left the federation <b>{fed_info["fname"]}</b>', reply_to_message_id=message.message_id, allow_sending_without_reply=True, parse_mode=ParseMode.HTML)
        message.reply_text(f'This chat has left the federation <b>{fed_info["fname"]}</b>!', parse_mode=ParseMode.HTML,
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        message.reply_text('This chat has not joined any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fpromote', pass_args=True)
@typing_action
def user_join_fed(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    user = message.from_user
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if is_user_fed_owner(fed_id, user.id) or user.id in SUDO_USERS:
        to_promote_user_id = extract_user(message, args)
        if to_promote_user_id:
            pass
        elif not message.reply_to_message and (not args or (len(args) >= 1 and not args[0].startswith('@') and not args[0].isdigit() and not message.parse_entities([MessageEntity.TEXT_MENTION]))):
            message.reply_text('I cannot extract an user from this message')
            return
        else:
            log.warning(
                f'Error in user extaction in fpromote for fed ID: {fed_id}')
            message.reply_text('Critical error occurred during user extraction',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        getuser = sql.search_user_in_fed(fed_id, to_promote_user_id)
        fedinfo = sql.get_fed_info(fed_id)
        get_fed_owner = context.bot.get_chat(
            ast.literal_eval(fedinfo["fusers"])["owner"]).id
        if to_promote_user_id == get_fed_owner:
            message.reply_text('You do know that the user is the federation owner, right? RIGHT?',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if getuser:
            message.reply_text('This person is already a federation admin!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if to_promote_user_id == context.bot.id:
            message.reply_text('I am already a federation admin in all federations!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fed_result = sql.user_join_fed(fed_id, to_promote_user_id)
        if fed_result:
            message.reply_text('Successfully promoted in fed!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        else:
            message.reply_text('Failed to promote in fed',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        message.reply_text('Only federation owners can do this',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fdemote', pass_args=True)
@typing_action
def user_demote_fed(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    user = message.from_user
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if is_user_fed_owner(fed_id, user.id):
        to_demote_user_id = extract_user(message, args)
        if to_demote_user_id:
            pass
        elif not message.reply_to_message and (not args or (len(args) >= 1 and not args[0].startswith('@') and not args[0].isdigit() and not message.parse_entities([MessageEntity.TEXT_MENTION]))):
            message.reply_text('I cannot extract an user from this message',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        else:
            log.warning(
                f'Error in user extaction in fpromote for fed ID: {fed_id}')
            message.reply_text('Critical error occurred during user extraction',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        getuser = sql.search_user_in_fed(fed_id, to_demote_user_id)
        fedinfo = sql.get_fed_info(fed_id)
        if to_demote_user_id == context.bot.id:
            message.reply_text('Nope, you cannot demote me!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        get_fed_owner = context.bot.get_chat(
            ast.literal_eval(fedinfo["fusers"])["owner"]).id
        if to_demote_user_id == get_fed_owner:
            message.reply_text('You do know that the user is the federation owner, right? RIGHT?',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if not getuser:
            message.reply_text('I cannot demote people who are not federation admins',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fed_result = sql.user_demote_fed(fed_id, to_demote_user_id)
        if fed_result:
            message.reply_text('Successfully demoted in fed!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        else:
            message.reply_text('Failed to demote in fed!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        message.reply_text('Only federation owners can do this',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fedinfo', pass_args=True)
@typing_action
def fed_info(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if args:
        fed_id = args[0]
    else:
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            message.reply_text('This chat is not a part of any federation!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
    fedinfo = sql.get_fed_info(fed_id)
    if not fedinfo:
        message.reply_text('That is not a valid fed ID',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_admin(fed_id, message.from_user.id):
        message.reply_text('Only a federation admin can use this command!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_owner = context.bot.get_chat(fedinfo['owner'])
    try:
        owner_name = fed_owner.full_name
    except BaseException:
        # Cases where user's name might be blank for some reason
        owner_name = fed_owner.first_name or 'Deleted'
    FEDADMIN = sql.all_fed_users(fed_id)
    FEDADMIN.append(int(fed_owner.id))
    total_admin_fed = len(FEDADMIN)
    text = "<b>ℹ️ Federation Information:</b>"
    text += f"\nFedID: <code>{fed_id}</code>"
    text += f"\nName: {fedinfo['fname']}"
    text += f"\nCreator: {mention_html(fed_owner.id, owner_name)}"
    text += f"\nAll Admins: <code>{total_admin_fed}</code>"
    getfban = sql.get_all_fban_users(fed_id)
    text += f"\nTotal banned users: <code>{len(getfban)}</code>"
    getfchat = sql.all_fed_chats(fed_id)
    text += f"\nNumber of groups in this federation: <code>{len(getfchat)}</code>"
    message.reply_text(text, parse_mode=ParseMode.HTML,
                       reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fedadmins')
@typing_action
def fed_admin(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_admin(fed_id, message.from_user.id):
        message.reply_text('Only federation admins can do this!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    text = f"<b>Federation admins of <u>{fedinfo['fname']}</u>:</b>\n\n"
    text += "👑 Owner:\n"
    fed_owner = context.bot.get_chat(fedinfo["owner"])
    try:
        owner_name = fed_owner.full_name
    except BaseException:
        owner_name = fed_owner.first_name or 'Deleted'
    text += f" • {mention_html(fed_owner.id, owner_name)}\n"

    members = sql.all_fed_members(fed_id)
    if len(members) == 0:
        text += "\n🔱 There is no admin in this federation"
    else:
        text += "\n🔱 Admin:\n"
        for member in members:
            try:
                user = context.bot.get_chat(member)
            except TelegramError:
                # Deleted user
                user = None
            name = user.first_name if user is not None else 'Deleted'
            if user is not None:
                text += f" • {mention_html(user.id, name)}\n"
            else:
                text += '• Deleted User'
    message.reply_text(text, parse_mode=ParseMode.HTML,
                       reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command=['fban', 'fedban'], pass_args=True)
@typing_action
def fed_ban(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This group is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    getfednotify = sql.user_feds_report(fedinfo['owner'])
    if not is_user_fed_admin(fed_id, message.from_user.id):
        message.reply_text('Only federation admins can issue fedbans!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    user_id, reason = extract_unt_fedban(message, args)
    if not user_id:
        message.reply_text('You don\'t seem to be referring to an user!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if user_id == context.bot.id:
        message.reply_text('Can\'t fedban myself!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if is_user_fed_owner(fed_id, user_id):
        message.reply_text('Did you just try to fedban the federation owner?',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if is_user_fed_admin(fed_id, user_id):
        message.reply_text('This person is a federation admin, find someone else!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if user_id == OWNER_ID:
        message.reply_text('Cannot ban the bot owner!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if user_id in SUDO_USERS:
        message.reply_text('I will not a ban a SUDO User!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if user_id in WHITELIST_USERS:
        message.reply_text('This person is whitelisted, cannot be fedbanned!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if user_id in (777000, 1087968824):
        message.reply_text('I\'m not fedbanning Telegram bots.',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fban = sql.get_fban_user(fed_id, user_id)
    try:
        user_chat = context.bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_fname = user_chat.first_name
        fban_user_lname = user_chat.last_name
        fban_user_username = user_chat.username
    except BadRequest as excp:
        if not str(user_id).isdigit():
            message.reply_text(
                excp.message, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        elif not (len(str(user_id)) == 9 or len(str(user_id)) == 10):
            message.reply_text('That\'s so not an user!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        isvalid = False
        fban_user_id = user_id
        fban_user_username = f'user({user_id})'
        fban_user_fname = None
        fban_user_lname = None
    if isvalid and user_chat.type != 'private':
        message.reply_text('That\'s so not an user!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_fname)
    else:
        user_target = fban_user_fname
    fed_name = fedinfo['fname']
    if reason == '':
        reason = 'No reason provided'
    if fban[0]:
        temp = sql.un_fban_user(fed_id, fban_user_id)
        if not temp:
            message.reply_text('Failed to update the reason for fedban!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
    else:
        start_msg = message.reply_text(
            f'Starting a federation ban for {user_target} in the Federation <b>{fed_name}</b>', parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    fedban = sql.fban_user(fed_id, fban_user_id, fban_user_fname,
                           fban_user_lname, fban_user_username, reason, int(time.time()))
    if not fedban:
        message.reply_text('Failed to ban from the federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    start_txt = f"<b>New Federation Ban!</b>\
                \n<b>Federation:</b> {fed_name}\
                \n<b>Federation Admin:</b> {mention_html(message.from_user.id, message.from_user.full_name)}\
                \n<b>User:</b> {user_target}\
                \n<b>User ID:</b> <code>{fban_user_id}</code>\
                \n<b>Reason:</b> {reason}"
    if not fban[0]:
        # Send to fedban originating chat
        start_msg.edit_text(start_txt, parse_mode=ParseMode.HTML)
    else:
        message.reply_text(start_txt.replace("<b>New Federation Ban!</b>", "<b>Federation Ban Updated!</b>"),
                           parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    notify_txt = f"<b>Fedban Reason Updated</b>\
                    \n<b>Federation:</b> {fed_name}\
                    \n<b>Federation Admin:</b> {mention_html(message.from_user.id, message.from_user.full_name)}\
                    \n<b>User:</b> {user_target}\
                    \n<b>User ID:</b> {fban_user_id}\
                    \n<b>Initiated From:</b> <code>{chat.title}</code>\
                    \n<b>Reason:</b> {reason}"
    # Notify fed owner of bans
    if getfednotify:
        if not fban[0]:
            notify_txt = notify_txt.replace(
                '<b>Fedban Reason Updated</b>', '<b>New Federation Ban</b>')
        context.bot.send_message(
            fedinfo['owner'],
            notify_txt,
            parse_mode=ParseMode.HTML
        )
    # If fedlog is set and fedlog is not current chat, notify about ban
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog and int(get_fedlog) != chat.id:
        if not fban[0]:
            notify_txt = notify_txt.replace(
                '<b>Fedban Reason Updated</b>', '<b>New Federation Ban</b>')
        context.bot.send_message(
            get_fedlog,
            notify_txt,
            parse_mode=ParseMode.HTML
        )
    # Ban in all fed chats
    chats_in_fed = 0
    fed_chats = sql.all_fed_chats(fed_id)
    for fedchat in fed_chats:
        try:
            context.bot.ban_chat_member(fedchat, fban_user_id)
            chats_in_fed += 1
        except BadRequest as excp:
            if excp.message in FBAN_ERRORS:
                try:
                    dispatcher.bot.get_chat(fedchat)
                except Unauthorized:
                    sql.chat_leave_fed(fedchat)
                    log.info(
                        f'Chat {fedchat} has left fed {fedinfo["fname"]} because I was kicked')
                    continue
            elif excp.message == 'User_id_invalid':
                break
            else:
                log.warning(
                    f'Could not fban on {fedchat} because: {excp.message}')
        except TelegramError:
            pass
    # Ban for fed subscribers
    subscribers = list(sql.get_subscriber(fed_id))
    if len(subscribers) > 0:
        for fedsid in subscribers:
            all_fedchats = sql.all_fed_chats(fedsid)
            for fedchat in all_fedchats:
                try:
                    context.bot.ban_chat_member(fedchat, fban_user_id)
                except BadRequest as excp:
                    if excp.message in FBAN_ERRORS:
                        try:
                            dispatcher.bot.get_chat(fedchat)
                        except Unauthorized:
                            targetfed_id = sql.get_fed_id(fedchat)
                            sql.unsubs_fed(fed_id, targetfed_id)
                            log.info(
                                f'Chat {fedchat} has unsub fed {fedinfo["fname"]} because I was kicked')
                            continue
                    elif excp.message == 'User_id_invalid':
                        break
                    else:
                        log.warning(
                            f'Could not fban on {fedchat} because: {excp.message}')
                except TelegramError:
                    pass
    if not fban[0]:
        if chats_in_fed == 0:
            context.bot.send_message(
                chat.id, 'Fedban affected 0 chats.')
        else:
            context.bot.send_message(
                chat.id, f'Fedban affected {chats_in_fed} chats.')


@metacmd(command=['unfban', 'rmfedban'], pass_args=True)
def unfban(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This group is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    getfednotify = sql.user_feds_report(fedinfo['owner'])
    if not is_user_fed_admin(fed_id, message.from_user.id):
        message.reply_text('Only federation admins can unfedban users!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    user_id = extract_user_fban(message, args)
    if not user_id:
        message.reply_text('You do not seem to be referring to an user!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    try:
        user_chat = context.bot.get_chat(user_id)
        isvalid = True
        fban_user_id = user_chat.id
        fban_user_fname = user_chat.first_name
    except BadRequest as excp:
        if not str(user_id).isdigit():
            message.reply_text(
                excp.message, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        elif not (len(str(user_id)) == 9 or len(str(user_id)) == 10):
            message.reply_text('That\'s so not an user!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        isvalid = False
        fban_user_id = int(user_id)
        fban_user_fname = f'user({user_id})'
    if isvalid and user_chat.type != 'private':
        message.reply_text('That\'s so not an user!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if isvalid:
        user_target = mention_html(fban_user_id, fban_user_fname)
    else:
        user_target = fban_user_fname
    fban = sql.get_fban_user(fed_id, fban_user_id)
    if not fban[0]:
        message.reply_text('This user is not fbanned')
        return
    start_msg = message.reply_text(f'I\'ll give {user_target} another chance in this federation!', parse_mode=ParseMode.HTML,
                                   reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    chat_list = sql.all_fed_chats(fed_id)
    unfbanned_in_chats = 0
    for fedchat in chat_list:
        try:
            member = context.bot.get_chat_member(fedchat, fban_user_id)
            if member.status == 'kicked':
                context.bot.unban_chat_member(fedchat, fban_user_id)
                unfbanned_in_chats += 1
        except BadRequest as excp:
            if excp.message in UNFBAN_ERRORS:
                try:
                    dispatcher.bot.get_chat(fedchat)
                except Unauthorized:
                    sql.chat_leave_fed(fedchat)
                    log.info(
                        f'Chat {fedchat} has left fed {fedinfo["fname"]} because I was kicked')
                    continue
            elif excp.message == "User_id_invalid":
                break
            else:
                log.warning(
                    f"Could not unfban on {chat} because: {excp.message}")
        except TelegramError:
            pass
    try:
        unfban_res = sql.un_fban_user(fed_id, fban_user_id)
        if not unfban_res:
            context.bot.send_message(
                chat.id, 'Un-fban failed, this user may already be un-fedbanned!')
            return
    except Exception:
        pass
    subscribers = list(sql.get_subscriber(fed_id))
    if len(subscribers) >= 0:
        for fedsid in subscribers:
            all_fedchats = sql.all_fed_chats(fedsid)
            for fedchat in all_fedchats:
                try:
                    context.bot.unban_chat_member(fedchat, fban_user_id)
                except BadRequest as excp:
                    if excp.message in FBAN_ERRORS:
                        try:
                            dispatcher.bot.getChat(fedchat)
                        except Unauthorized:
                            targetfed_id = sql.get_fed_id(fedchat)
                            sql.unsubs_fed(fed_id, targetfed_id)
                            log.info(
                                f"Chat {fedchat} has unsub fed {fedinfo['fname']} because I was kicked")
                            continue
                    elif excp.message == "User_id_invalid":
                        break
                    else:
                        log.warning(
                            f'Unable to unfban on {fedchat} because: {excp.message}')
                except TelegramError:
                    pass
    start_msg.edit_text(
        "<b>Un-FedBan</b>"
        f"\n<b>Federation:</b> {fedinfo['fname']}"
        f"\n<b>Federation Admin:</b> {mention_html(message.from_user.id, message.from_user.full_name)}"
        f"\n<b>User:</b> {user_target}"
        f"\n<b>User ID:</b> <code>{fban_user_id}</code>",
        parse_mode=ParseMode.HTML
    )
    notify_txt = f"<b>Un-FedBan</b>\
                    \n<b>Federation:</b> {fedinfo['fname']}\
                    \n<b>Federation Admin:</b> {mention_html(message.from_user.id, message.from_user.full_name)}\
                    \n<b>User:</b> {user_target}\
                    \n<b>User ID:</b> <code>{fban_user_id}</code>\
                    \n<b>Initiated From:</b> <code>{chat.title}</code>"
    if getfednotify:
        context.bot.send_message(
            fedinfo['owner'],
            notify_txt,
            parse_mode=ParseMode.HTML
        )
    get_fedlog = sql.get_fed_log(fed_id)
    if get_fedlog and int(sql.get_fed_log) != chat.id:
        context.bot.send_message(
            get_fedlog,
            notify_txt,
            parse_mode=ParseMode.HTML
        )
    if unfbanned_in_chats == 0:
        context.bot.send_message(
            chat.id, 'This person has been un-fbanned in 0 chats.')
    else:
        context.bot.send_message(
            chat.id, f'This person has been un-fbanned in {unfbanned_in_chats} chats.')


@metacmd(command='setfrules', pass_args=True)
@typing_action
def set_frules(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This group is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_admin(fed_id, message.from_user.id):
        message.reply_text('Only fed admins can set fed rules!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if len(args) >= 1:
        raw_text = message.text
        args = raw_text.split(None, 1)
        if len(args) == 2:
            txt = args[1]
            offset = len(txt) - len(raw_text)
            markdown_rules = markdown_parser(
                txt, entities=message.parse_entities(), offset=offset)
        x = sql.set_frules(fed_id, markdown_rules)
        if not x:
            message.reply_text('Big F! There has been an error while setting federation rules!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fedinfo = sql.get_fed_info(fed_id)
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog and ast.literal_eval(get_fedlog) and int(get_fedlog) != chat.id:
            context.bot.send_message(
                get_fedlog,
                f'<b>{message.from_user.full_name}</b> has changed federation rules for fed <b>{fedinfo["fname"]}</b>',
                parse_mode=ParseMode.HTML
            )
        if sql.user_feds_report(fedinfo['owner']):
            context.bot.send_message(
                fedinfo['owner'],
                f'<b>{message.from_user.full_name}</b> has changed federation rules for fed <b>{fedinfo["fname"]}</b>',
                parse_mode=ParseMode.HTML
            )
        message.reply_text('Fed rules have been changed!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        message.reply_text('Please write the fed rules to set it up!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='frules')
@typing_action
def get_frules(update: Update, _: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    rules = sql.get_frules(fed_id)
    text = "*Rules in this fed:*\n"
    text += rules
    message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


@metacmd(command='fbroadcast', pass_args=True)
@typing_action
def fed_broadcast(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if args:
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            message.reply_text('This chat is not a part of any federation!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if not is_user_fed_owner(fed_id, message.from_user.id):
            message.reply_text('This command can only be triggered by federation owner!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fedinfo = sql.get_fed_info(fed_id)
        raw_text = message.text
        args = raw_text.split(None, 1)
        txt = args[1]
        offset = len(txt) - len(raw_text)
        text_parser = markdown_parser(
            txt, entities=message.parse_entities(), offset=offset)
        broadcaster = message.from_user.full_name
        text_parser += f'\n\n\- {mention_markdown(message.from_user.id, broadcaster)}'
        chat_list = sql.all_fed_chats(fed_id)
        failed = 0
        for fedchat in chat_list:
            title = f'*New broadcast from Fed {fedinfo["fname"]}*\n'
            try:
                context.bot.send_message(
                    fedchat, title + text_parser, parse_mode=ParseMode.MARKDOWN_V2)
            except TelegramError as excp:
                try:
                    dispatcher.bot.get_chat(fedchat)
                except Unauthorized:
                    failed += 1
                    sql.chat_leave_fed(fedchat)
                    log.info(
                        f'Chat {fedchat} has left fed {fedinfo["fname"]} because I was kicked!')
                    continue
                failed += 1
                log.warning(
                    f'Couldn\'t sent broadcast to {str(fedchat)} because {excp.message}')
        send_text = 'The federation broadcast is complete'
        if failed > 0:
            send_text += f'\nFailed to broadcast in {failed} chats.'
        message.reply_text(
            send_text, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        message.reply_text('Pass me some text to broadcast in fed!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fbanlist', pass_args=True, pass_chat_data=True)
@send_action(ChatAction.UPLOAD_DOCUMENT)
def fed_ban_list(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    user = message.from_user
    args = context.args
    chat_data = context.chat_data
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_owner(fed_id, user.id):
        message.reply_text('Only federation owners can use this command!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    fban_users = sql.get_all_fban_users(fed_id)
    if len(fban_users) == 0:
        message.reply_text(f'The federation ban list of {fedinfo["fname"]} is empty!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if args:
        if args[0] not in ('json', 'csv'):
            message.reply_text(f'Cannot export fedban list as {html.escape(args[0])}. Supported export types are <code>json</code> & <code>csv</code>!',
                               parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        else:
            current_time_30 = time.time() + 1800  # Time 30 minutes in the future
            chat_info = get_chat(chat.id, chat_data)
            if chat_info.get('status'):
                if current_time_30 <= int(chat_info.get('value')):
                    next_backup_time = time.strftime(
                        '%H:%M:%S %d/%m/%Y', time.localtime(chat_info.get('value')))
                    message.reply_text(
                        f'You can backup/import your data once every 30 minutes!\nYou can request fedban export again at <code>{next_backup_time}</code>', reply_to_message_id=message.message_id, allow_sending_without_reply=True, parse_mode=ParseMode.HTML)
                    return
                elif user.id not in SUDO_USERS:
                    put_chat(chat.id, current_time_30, chat_data)
            elif user.id not in SUDO_USERS:
                put_chat(chat.id, current_time_30, chat_data)
            if args[0] == 'json':
                backups = ""
                for fban_user in fban_users:
                    getuserinfo = sql.get_all_fban_users_target(
                        fed_id, fban_user)
                    json_parser = {
                        'user_id': fban_user,
                        'first_name': getuserinfo['first_name'],
                        'last_name': getuserinfo['last_name'],
                        'user_name': getuserinfo['user_name'],
                        'reason': getuserinfo['reason'],
                    }
                    backups += json.dumps(json_parser)
                    backups += '\n'
                backups.strip()
            elif args[0] == 'csv':
                backups = "id,firstname,lastname,username,reason\n"
                for fban_user in fban_users:
                    getuserinfo = sql.get_all_fban_users_target(
                        fed_id, fban_user)
                    backups += (
                        "{user_id},{first_name},{last_name},{user_name},{reason}".format(
                            user_id=fban_user,
                            first_name=getuserinfo["first_name"],
                            last_name=getuserinfo["last_name"],
                            user_name=getuserinfo["user_name"],
                            reason=getuserinfo["reason"],
                        )
                    )
                    backups += '\n'
                backups.strip()
            with BytesIO(str.encode(backups)) as output:
                output.name = f'MetaButler_fbanned_users_{str(fed_id)}.{args[0]}'
                message.reply_document(
                    document=output,
                    filename=f'MetaButler_fbanned_users_{str(fed_id)}.{args[0]}',
                    caption=f'Total {len(fban_users)} users are banned in the Federation {html.escape(fedinfo["fname"])}.',
                    reply_to_message_id=message.message_id,
                    allow_sending_without_reply=True,
                )
    else:
        text = f'<b>{len(fban_users)} users have been banned in the Federation {fedinfo["fname"]}:</b>\n'
        for fban_user in fban_users:
            getuserinfo = sql.get_all_fban_users_target(fed_id, fban_user)
            if not getuserinfo:
                text = f'There are no users banned from the Federation {fedinfo["fname"]}'
                break
            user_name = getuserinfo['first_name']
            if getuserinfo['last_name']:
                user_name += f' {getuserinfo["last_name"]}'
            text += f' • {mention_html(fban_user, user_name)} (<code>{fban_user}</code>)\n'
        try:
            message.reply_text(text, parse_mode=ParseMode.HTML,
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        except:
            current_time_30 = time.time() + 1800  # Time 30 minutes in the future
            chat_info = get_chat(chat.id, chat_data)
            if chat_info.get('status'):
                if current_time_30 <= int(chat_info.get('value')):
                    next_backup_time = time.strftime(
                        '%H:%M:%S %d/%m/%Y', time.localtime(chat_info.get('value')))
                    message.reply_text(
                        f'You can backup your data once every 30 minutes!\nYou can request fedban export again at <code>{next_backup_time}</code>', reply_to_message_id=message.message_id, allow_sending_without_reply=True, parse_mode=ParseMode.HTML)
                    return
                elif user.id not in SUDO_USERS:
                    put_chat(chat.id, current_time_30, chat_data)
            elif user.id not in SUDO_USERS:
                put_chat(chat.id, current_time_30, chat_data)
            cleanr = re.compile("<.*?>")
            cleantext = re.sub(cleanr, "", text)
            with BytesIO(str.encode(cleantext)) as output:
                output.name = f'MetaButler_fbanned_users_{str(fed_id)}.txt'
                message.reply_document(
                    document=output,
                    filename=f'MetaButler_fbanned_users_{str(fed_id)}.txt',
                    caption=f'The following is a list of users who are currently fbanned in the Federation {fedinfo["fname"]}',
                    reply_to_message_id=message.message_id,
                    allow_sending_without_reply=True,
                )


@metacmd(command='fednotif', pass_args=True)
@typing_action
def fed_notify(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_owner(fed_id, message.from_user.id):
        message.reply_text('This command is reserved for the Federation owner only!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if args:
        if args[0].lower() in ('yes', 'on'):
            sql.set_feds_setting(message.from_user.id, True)
            message.reply_text('Done! Every fban/unfban will be notified!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        elif args[0].lower() in ('no', 'off'):
            sql.set_feds_setting(message.from_user.id, False)
            message.reply_text('Done! You will not be notified of fban/unfban!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        getnotify = sql.user_feds_report(message.from_user.id)
        message.reply_text(f'Your current Federation report preferences: `{getnotify}`',
                           parse_mode=ParseMode.MARKDOWN_V2, reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fedchats')
@typing_action
def fed_chats(update: Update, _: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    if not is_user_fed_admin(fed_id, message.from_user.id):
        message.reply_text('Only federation admins can use this command!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    getlist = sql.all_fed_chats(fed_id)
    if len(getlist) == 0:
        message.reply_text(f'No chats have joined the federation <b>{fedinfo["fname"]}</b>!',
                           parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    text = f"<b>Chats in Federation {html.escape(fedinfo['fname'])}:</b>\n"
    for fedchat in getlist:
        try:
            chat_name = dispatcher.bot.get_chat(fedchat).title
        except Unauthorized:
            sql.chat_leave_fed(fedchat)
            log.info(
                f'Chat {fedchat} has left fed {fedinfo["fname"]} because I was kicked!')
            continue
        text += f' • {html.escape(chat_name)} (<code>{fedchat}</code>)\n'
    try:
        message.reply_text(text, parse_mode=ParseMode.HTML,
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    except:
        cleanr = re.compile("<.*?>")
        cleantext = re.sub(cleanr, "", text)
        with BytesIO(str.encode(cleantext)) as output:
            output.name = f'MetaButler_fedchats_{str(fed_id)}.txt'
            message.reply_document(
                document=output,
                filename=f'MetaButler_fedchats_{str(fed_id)}.txt',
                caption=f'Here is a list of all the chats that are under the Federation {fedinfo["fname"]}',
                reply_to_message_id=message.message_id,
                allow_sending_without_reply=True,
            )


@metacmd(command='importfbans', pass_chat_data=True)
@typing_action
def fed_import_bans(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    chat_data = context.chat_data
    if chat.type == 'private':
        message.reply_text('This command is specific to the group!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_owner(fed_id, message.from_user.id):
        message.reply_text('Only federation owners can use this command!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    if message.reply_to_message and message.reply_to_message.document:
        current_time_30 = time.time() + 1800  # Time 30 minutes in the future
        chat_info = get_chat(chat.id, chat_data)
        if chat_info.get('status'):
            if current_time_30 <= int(chat_info.get('value')):
                next_backup_time = time.strftime(
                    '%H:%M:%S %d/%m/%Y', time.localtime(chat_info.get('value')))
                message.reply_text(
                    f'You can backup/import your data once every 30 minutes!\nYou can request fedban import again at <code>{next_backup_time}</code>', reply_to_message_id=message.message_id, allow_sending_without_reply=True, parse_mode=ParseMode.HTML)
                return
            elif message.from_user.id not in SUDO_USERS:
                put_chat(chat.id, current_time_30, chat_data)
        elif message.from_user.id not in SUDO_USERS:
            put_chat(chat.id, current_time_30, chat_data)
        success = 0
        failed = 0
        try:
            file_info = context.bot.get_file(
                message.reply_to_message.document.file_id)
        except BadRequest:
            message.reply_text('Try downloading and re-uploading the file, this one seems broken!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fileformat = message.reply_to_message.document.file_name.split('.')[-1]
        if fileformat not in ('json', 'csv'):
            message.reply_text('Bans can be imported <b>only from</b> JSON/CSV files!', parse_mode=ParseMode.HTML,
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        multi_fed_id = []
        multi_import_userid = []
        multi_import_firstname = []
        multi_import_lastname = []
        multi_import_username = []
        multi_import_reason = []
        if fileformat == 'json':
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                reading = file.read().decode("UTF-8")
                splitting = reading.split("\n")
                for x in splitting:
                    if x == "":
                        continue
                    try:
                        data = json.loads(x)
                    except json.decoder.JSONDecodeError:
                        failed += 1
                        continue
                    try:
                        # Make sure it's int
                        import_userid = int(data["user_id"])
                        import_firstname = str(data["first_name"])
                        import_lastname = str(data["last_name"])
                        import_username = str(data["user_name"])
                        import_reason = str(data["reason"])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == context.bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
        elif fileformat == 'csv':
            file_info.download(
                f'fban_{message.reply_to_message.document.file_id}.csv')
            with open(f'fban_{message.reply_to_message.document.file_id}.csv', 'r', encoding='utf-8') as csv_file:
                reader = csv.reader(csv_file)
                next(reader, None)
                for data in reader:
                    try:
                        import_userid = int(data[0])  # Make sure it int
                        import_firstname = str(data[1])
                        import_lastname = str(data[2])
                        import_username = str(data[3])
                        import_reason = str(data[4])
                    except ValueError:
                        failed += 1
                        continue
                    # Checking user
                    if int(import_userid) == context.bot.id:
                        failed += 1
                        continue
                    if is_user_fed_owner(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if is_user_fed_admin(fed_id, import_userid) is True:
                        failed += 1
                        continue
                    if str(import_userid) == str(OWNER_ID):
                        failed += 1
                        continue
                    if int(import_userid) in SUDO_USERS:
                        failed += 1
                        continue
                    if int(import_userid) in WHITELIST_USERS:
                        failed += 1
                        continue
                    multi_fed_id.append(fed_id)
                    multi_import_userid.append(str(import_userid))
                    multi_import_firstname.append(import_firstname)
                    multi_import_lastname.append(import_lastname)
                    multi_import_username.append(import_username)
                    multi_import_reason.append(import_reason)
                    success += 1
                sql.multi_fban_user(
                    multi_fed_id,
                    multi_import_userid,
                    multi_import_firstname,
                    multi_import_lastname,
                    multi_import_username,
                    multi_import_reason,
                )
            os.remove(f'fban_{message.reply_to_message.document.file_id}.csv')
        text = f'Bans were successfully imported! {success} people are banned.'
        if failed > 0:
            text += f'Failed to import {failed} bans.'
        get_fedlog = sql.get_fed_log(fed_id)
        if get_fedlog and ast.literal_eval(get_fedlog):
            notify_txt = f'Fed *{fedinfo["fname"]}* has successfully imported data. {success} were banned!'
            if failed > 0:
                notify_txt += f'\nFailed to import {failed} bans.'
            context.bot.send_message(
                get_fedlog, notify_txt, parse_mode=ParseMode.MARKDOWN_V2)
        message.reply_text(
            text, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        message.reply_text('No file provided or unsupported file!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return


@metacmd(command='fbanstat', pass_args=True)
@typing_action
def fed_stat_user(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    args = context.args
    if args:
        if args[0].isdigit():
            user_id = args[0]
        else:
            user_id = extract_user(message, args)
    else:
        user_id = extract_user(message, args)
    if user_id:
        if len(args) == 2 and args[0].isdigit():
            fed_id = args[1]
            user_name, fban_reason, fban_time = sql.get_user_fban(
                fed_id, str(user_id))
            if fban_time:
                fban_time = time.strftime(
                    "%d/%m/%Y", time.localtime(fban_time))
            else:
                fban_time = 'Unavailable'
            if not user_name:
                message.reply_text(
                    f'Fed {fed_id} does not exist!', reply_to_message_id=message.message_id, allow_sending_without_reply=True)
                return
            if user_name == "" or user_name is None:
                try:
                    user_name = context.bot.get_chat(user_id).first_name
                except BadRequest:
                    user_name = 'They'
            if not fban_reason:
                message.reply_text(f'{html.escape(user_name)} are not banned in this federation!',
                                   reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            else:
                message.reply_text(f'{html.escape(user_name)} is banned in this federation because:\n<code>{fban_reason}</code>\n<b>Banned at:</b> <code>{fban_time}</code>',
                                   parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        else:
            user_name, fbanlist = sql.get_user_fbanlist(str(user_id))
            if user_name == "" or user_name is None:
                try:
                    user_name = context.bot.get_chat(user_id).first_name
                except BadRequest:
                    user_name = 'They'
            if len(fbanlist) == 0:
                message.reply_text(f'{user_name} are not banned in any federation!',
                                   reply_to_message_id=message.message_id, allow_sending_without_reply=True)
                return
            else:
                text = f'{html.escape(user_name)} have been banned in this/these federation(s):\n'
                for ban in fbanlist:
                    text += f'- <code>{ban[0]}</code>: {ban[1][:20]}\n'
                text += '\nIf you want to find out more about the reason for any fedban specifically, use <code>/fbanstat FedID</code>'
                message.reply_text(text, parse_mode=ParseMode.HTML,
                                   reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    elif not message.reply_to_message and not args:
        user_id = message.from_user.id
        user_name, fbanlist = sql.get_user_fbanlist(user_id)
        if user_name == "":
            user_name = message.from_user.first_name
        if len(fbanlist) == 0:
            message.reply_text(f'{user_name} is not banned in any federation!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        else:
            text = f'{user_name} has been banned in this/these federation(s):\n'
            for fban in fbanlist:
                text += f'- <code>{fban[0]}</code>: {fban[1][:20]}\n'
            text += '\nIf you want to find out more about the reason for any fedban specifically, use <code>/fbanstat FedID</code>'
            message.reply_text(text, parse_mode=ParseMode.HTML,
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
    else:
        fed_id = args[0]
        fedinfo = sql.get_fed_info(fed_id)
        if not fedinfo:
            message.reply_text(f'Fed {fed_id} was not found!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        name, fban_reason, fban_time = sql.get_user_fban(
            fed_id, message.from_user.id)
        if fban_time:
            fban_time = time.strftime("%d/%m/%Y", time.localtime(fban_time))
        else:
            fban_time = 'Unavailable'
        if not name:
            name = message.from_user.first_name
        if not fban_reason:
            message.reply_text(f'{name} is not banned in this federation!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        message.reply_text(f'{name} is banned in this federation because:\n<code>{fban_reason}</code>\n<b>Banned at:</b> <code>{fban_time}</code>',
                           parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='setfedlog', pass_args=True)
@typing_action
def set_fed_log(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not args:
        message.reply_text('You have not provided your Fed ID!\nCorrect usage: <code>/setfedlog FedID</code>',
                           parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    else:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            message.reply_text('This federation does not exist!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if not is_user_fed_owner(args[0], message.from_user.id):
            message.reply_text('Only federation owners can set federation log!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if sql.set_fed_log(args[0], chat.id):
            message.reply_text(f'Federation log of <code>{fedinfo["fname"]}</code> has been set to {chat.title}',
                               parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fedlog', pass_args=True)
@typing_action
def get_fed_log(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if not args:
        fed_id = sql.get_fed_id(chat.id)
        if not fed_id:
            message.reply_text('This chat is not a part of any federation!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if not is_user_fed_owner(fed_id, message.from_user.id):
            message.reply_text('This command is reserved for Federation owners!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        fedinfo = sql.get_fed_info(fed_id)
    else:
        fed_id = args[0]
        fedinfo = sql.get_fed_info(fed_id)
        if not fedinfo:
            message.reply_text('This federation does not exist!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if not is_user_fed_owner(fed_id, message.from_user.id):
            message.reply_text('This command is reserved for Federation owners!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
    fedlog = sql.get_fed_log(fed_id)
    if not fedlog:
        message.reply_text('This federation does not have a federation log set!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    else:
        try:
            fedlogdata = dispatcher.bot.get_chat(int(fedlog))
        except Unauthorized:
            message.reply_text('This federation had a fedlog set, but I have been kicked from the chat!\nUnsetting fedlog!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            sql.set_fed_log(fed_id, None)
            return
        message.reply_text(f'The federation {html.escape(fedinfo["fname"])} has a federation log set: {fedlogdata.title}',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='unsetfedlog', pass_args=True)
@typing_action
def unset_fed_log(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not args:
        message.reply_text('You have not provided your Fed ID!\nCorrect usage: <code>/unsetfedlog FedID</code>',
                           parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    else:
        fedinfo = sql.get_fed_info(args[0])
        if not fedinfo:
            message.reply_text('This federation does not exist!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if not is_user_fed_owner(args[0], message.from_user.id):
            message.reply_text('Only federation owners can unset federation log!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        if sql.set_fed_log(args[0], None):
            message.reply_text(f'Federation log of <code>{fedinfo["fname"]}</code> has been unset!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True, parse_mode=ParseMode.HTML)


@metacmd(command='subfed', pass_args=True)
@typing_action
def subs_feds(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_owner(fed_id, message.from_user.id):
        message.reply_text('This command is reserved for federation owners!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    if args:
        if args[0] == fed_id:
            message.reply_text('How do you plan to subscribe to yourself?!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        getfed = sql.search_fed_by_id(args[0])
        if not getfed:
            message.reply_text('Please enter a valid federation ID to subscribe to!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        subfed = sql.subs_fed(args[0], fed_id)
        if not subfed:
            message.reply_text(f'Federation <code>{html.escape(fedinfo["fname"])}</code> already subscribes to <code>{html.escape(getfed["fname"])}</code>',
                               parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        else:
            message.reply_text(f'Federation <code>{html.escape(fedinfo["fname"])}</code> has subscribed to the federation <code>{html.escape(getfed["fname"])}</code>. Each time there is a fedban in that federation, the person will be banned in this federation too!',
                               parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    context.bot.send_message(
                        int(get_fedlog),
                        f'Federation `{fedinfo["fname"]}` has subscribed to the federation `{getfed["fname"]}`',
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )
    else:
        message.reply_text('You have not provided a federation ID to subscribe to!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='unsubfed', pass_args=True)
@typing_action
def unsubs_feds(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    args = context.args
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_owner(fed_id, message.from_user.id):
        message.reply_text('This command is only for federation owners!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    if not args:
        message.reply_text('You have not provided a federation ID to unsubscribe from!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    else:
        getfed = sql.search_fed_by_id(args[0])
        if not getfed:
            message.reply_text('Please enter a valid federation ID to unsubscribe from!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        unsubfed = sql.unsubs_fed(args[0], fed_id)
        if not unsubfed:
            message.reply_text('How should I unsubscribe from a federation you are not subscribed to?!',
                               reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            return
        else:
            message.reply_text(f'Federation `{fedinfo["fname"]}` has unsubscribed from `{getfed["fname"]}`',
                               parse_mode=ParseMode.MARKDOWN_V2, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
            get_fedlog = sql.get_fed_log(args[0])
            if get_fedlog:
                if int(get_fedlog) != int(chat.id):
                    context.bot.send_message(
                        int(get_fedlog),
                        f'Federation `{fedinfo["fname"]}` has unsubscribed from `{getfed["fname"]}`',
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )


@metacmd(command='fedsubs')
@typing_action
def get_my_fed_subs(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_owner(fed_id, message.from_user.id):
        message.reply_text('This command is only for federation owners!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    mysubs = sql.get_mysubs(fed_id)
    if not mysubs:
        message.reply_text(f'Federation `{fedinfo["fname"]}` is not subscribed to any federation\!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True, parse_mode=ParseMode.MARKDOWN_V2)
        return
    else:
        text = f'Federation `{fedinfo["fname"]}` is subscribed to the following federations:\n'
    for sub in mysubs:
        text += f'\- `{sub}`\n'
    text += '\nTo get federation info: `/fedinfo <FedID>`\. To unsubscribe: `/unsubfed <FedID>`\.'
    message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2,
                       reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='myfeds')
@typing_action
def get_myfeds_list(update: Update, _: CallbackContext) -> None:
    user = update.effective_message.from_user
    message = update.effective_message
    fedowner = sql.get_user_owner_fed_full(user.id)
    if not fedowner:
        text = "<b>You have not created any feds!</b>"
    else:
        text = "<b>You are owner of the following feds:</b>\n"
        for fed in fedowner:
            text += f"- <code>{fed['fed_id']}</code>: <b>{fed['fed']['fname']}</b>\n"
    message.reply_text(text, parse_mode=ParseMode.HTML,
                       reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacmd(command='fedsubbed')
@typing_action
def get_my_subs_list(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    user = message.from_user
    chat = update.effective_chat
    if chat.type == 'private':
        message.reply_text('This command is specific to the group, not to the PM!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fed_id = sql.get_fed_id(chat.id)
    if not fed_id:
        message.reply_text('This chat is not a part of any federation!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    if not is_user_fed_owner(fed_id, user.id):
        message.reply_text('This command is only for federation owners!',
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    fedinfo = sql.get_fed_info(fed_id)
    getsubs = list(sql.get_subscriber(fed_id))
    if len(getsubs) == 0:
        message.reply_text(f'No federations are subscribing to <b>{fedinfo["fname"]}</b>!',
                           parse_mode=ParseMode.HTML, reply_to_message_id=message.message_id, allow_sending_without_reply=True)
        return
    else:
        text = "<b>The following feds have subscribed to your federation:</b>\n"
        for fedid in getsubs:
            text += f"- <code>{fedid}</code>\n"
        message.reply_text(text, parse_mode=ParseMode.HTML,
                           reply_to_message_id=message.message_id, allow_sending_without_reply=True)


@metacallback(pattern=r'rmfed_')
def del_fed_btn_handler(update: Update, _: CallbackContext) -> None:
    query = update.callback_query
    fed_id = query.data.split('_')[1]
    query.answer()
    if fed_id == 'cancel':
        query.edit_message_text('Federation deletion cancelled!')
        return
    fedinfo = sql.get_fed_info(fed_id)
    if fedinfo:
        if sql.del_fed(fed_id):
            query.edit_message_text(
                f"You have deleted your Federation! All the groups that were connected with <code>{fedinfo['fname']}</code> now do not have a federation.", parse_mode=ParseMode.HTML)


def is_user_fed_owner(fed_id: str, user_id: int) -> bool:
    getsql = sql.get_fed_info(fed_id)
    if getsql is False:
        return False
    getfedowner = ast.literal_eval(getsql["fusers"])
    if getfedowner == None or getfedowner == False:
        return False
    getfedowner = getfedowner["owner"]
    if str(user_id) == getfedowner or int(user_id) == OWNER_ID:
        return True
    else:
        return False


def is_user_fed_admin(fed_id: str, user_id: int) -> bool:
    fed_admins = sql.all_fed_users(fed_id)
    if fed_admins is False:
        return False
    if int(user_id) in fed_admins or int(user_id) == OWNER_ID:
        return True
    else:
        return False


def get_chat(chat_id: int, chat_data: Optional[dict]) -> dict:
    try:
        value = chat_data[chat_id]['federation']
        return value
    except KeyError:
        return {'status': False, 'value': False}


def put_chat(chat_id: int, value: bool, chat_data: Optional[dict]) -> None:
    if not value:
        status = False
    else:
        status = True
    chat_data[chat_id] = {"federation": {"status": status, "value": value}}


def __stats__() -> str:
    all_fbanned = sql.get_all_fban_users_global()
    all_feds = sql.get_all_feds_users_global()
    return f"• {len(all_fbanned)} users banned, in {len(all_feds)} federations"


def __user_info__(user_id: int, chat_id: int) -> str:
    fed_id = sql.get_fed_id(chat_id)
    if fed_id:
        fban, fbanreason = sql.get_fban_user(fed_id, user_id)
        info = sql.get_fed_info(fed_id)
        infoname = info["fname"]
        if int(info["owner"]) == user_id:
            text = f"This user is the owner of the current Federation: <b>{infoname}</b>."
        elif is_user_fed_admin(fed_id, user_id):
            text = f"This user is the admin of the current Federation: <b>{infoname}</b>."
        elif fban:
            text = "<b>Banned in current Fed</b>: Yes"
            text += f"\n<b>Reason</b>: {fbanreason}"
        else:
            text = "<b>Banned in current Fed</b>: No"
    else:
        text = ""
    return text


__mod_name__ = "Federations"

from MetaButler.modules.language import gs

def fed_owner_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "FED_OWNER_HELP"),
        parse_mode=ParseMode.MARKDOWN,
    )


def fed_admin_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "FED_ADMIN_HELP"),
        parse_mode=ParseMode.MARKDOWN,
    )



def fed_user_help(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        gs(update.effective_chat.id, "FED_USER_HELP"),
        parse_mode=ParseMode.MARKDOWN,
    )


@metacallback(pattern=r"fed_help_")
def fed_help(update: Update, context: CallbackContext):
    query = update.callback_query
    bot = context.bot
    help_info = query.data.split("fed_help_")[1]
    if help_info == "owner":
        help_text = gs(update.effective_chat.id, "FED_OWNER_HELP")
    elif help_info == "admin":
        help_text = gs(update.effective_chat.id, "FED_ADMIN_HELP")
    elif help_info == "user":
        help_text = gs(update.effective_chat.id, "FED_USER_HELP")
    query.message.edit_text(
        text=help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="Back", callback_data=f"help_module({__mod_name__.replace(' ', '_').lower()})"),
            InlineKeyboardButton(text='Report Error', url='https://t.me/MetaProjectsSupport')]]
        ),
    )
    bot.answer_callback_query(query.id)


def get_help(chat):
    return [gs(chat, "feds_help"),
    [
        InlineKeyboardButton(text="Fedadmins", callback_data="fed_help_admin"),
        InlineKeyboardButton(text="Fedowners", callback_data="fed_help_owner")
    ],
    [
        InlineKeyboardButton(text="Users", callback_data="fed_help_user")
    ],
]
