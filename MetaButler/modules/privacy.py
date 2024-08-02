from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext
from MetaButler.modules.helper_funcs.decorators import metacmd, metacallback

PRIVACY_TEXT = """
*Our Contact Details*
- *Name*: MetaButlerBot
- *Telegram*: [SupportChat](https://t.me/MetaProjectsSupport)

The bot is designed to protect your privacy as much as possible. It only collects data necessary for its commands to work.

*Privacy Policy Updates*
- Our privacy policy might change occasionally.
- Any significant changes will be announced on [MetaButler](https://t.me/metabutlernews).
"""

INFORMATION_WE_COLLECT = """
*Information We Collect*
*Types of Personal Information*:
- *Telegram User ID, First Name, Last Name, Username*: These are your public Telegram details. We don’t access your private information.
- *Chat Memberships*: Records of chats you’ve interacted in.
- *Settings and Configurations*: Data from commands you set up (e.g., welcome settings, notes, filters).
"""

WHY_WE_COLLECT_IT = """
*Why We Collect It*
*How and Why We Get Your Information*:
- *Directly from You*:
  - When you message the bot to complete a CAPTCHA, read documentation, etc.
  - When you choose to save messages through the bot.
- *Indirectly*:
  - When you’re part of a group or channel using this bot.
"""

WHAT_WE_DO = """
*What We Do*
*Use of Your Information*:
- *User ID/Username Pairing*: To match usernames with valid user IDs.
- *Chat Memberships*: To help federations decide where bans should apply.
- *Storing Messages*: Only messages you explicitly save (e.g., notes, filters, welcomes).
"""

WHAT_WE_DO_NOT_DO = """
*What We Do Not Do*
*Restrictions on Your Information*:
- *We Do NOT*:
  - Store messages unless you explicitly save them.
  - Use tracking technologies like beacons or unique device identifiers.
  - Collect personal information from children under 13. If we accidentally do, contact us for parental consent or removal of the information.
  - Share any sensitive information with other organizations or individuals.
"""

PRIVACY_BUTTONS = [
    [InlineKeyboardButton("What information we collect", callback_data="info_collect"),
     InlineKeyboardButton("Why we collect it", callback_data="why_collect")],
    [InlineKeyboardButton("What we do", callback_data="what_do"),
     InlineKeyboardButton("What we DO NOT DO", callback_data="what_not_do")],
]

def get_privacy_keyboard(active_button=None):
    buttons = [
        [InlineKeyboardButton("What information we collect", callback_data="info_collect"),
         InlineKeyboardButton("Why we collect it", callback_data="why_collect")],
        [InlineKeyboardButton("What we do", callback_data="what_do"),
         InlineKeyboardButton("What we DO NOT DO", callback_data="what_not_do")],
    ]
    if active_button:
        for row in buttons:
            for button in row:
                if button.callback_data == active_button:
                    button.text = f"➡️ {button.text} ⬅️"
        buttons.append([InlineKeyboardButton("Back", callback_data="privacy")])
    return InlineKeyboardMarkup(buttons)

@metacmd(command="privacy")
def privacy(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        PRIVACY_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(PRIVACY_BUTTONS), disable_web_page_preview=True
    )

@metacallback(pattern=r"^(info_collect|why_collect|what_do|what_not_do|privacy)$")
def privacy_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == "info_collect":
        text = INFORMATION_WE_COLLECT
    elif query.data == "why_collect":
        text = WHY_WE_COLLECT_IT
    elif query.data == "what_do":
        text = WHAT_WE_DO
    elif query.data == "what_not_do":
        text = WHAT_WE_DO_NOT_DO
    else:  # back to privacy
        text = PRIVACY_TEXT

    query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_privacy_keyboard(query.data if query.data != "privacy" else None),
        disable_web_page_preview=True
    )

# Add this to your module's __mod_name__ if necessary
__mod_name__ = "Privacy"
