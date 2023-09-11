from gpytranslate import SyncTranslator
from MetaButler.modules.language import gs
from .helper_funcs.misc import has_reply_to_message

def get_help(chat):
    return gs(chat, "gtranslate_help")

__mod_name__ = "Translator"

trans = SyncTranslator()

from telegram import ParseMode, Update
from telegram.ext import CallbackContext
from MetaButler.modules.helper_funcs.decorators import metacmd

@metacmd(command=["tr", "tl"])
def translate(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    message = update.effective_message
    reply_msg = message.reply_to_message
    if not has_reply_to_message(message):
        message.reply_text("Reply to a message to translate it!")
        return
    if reply_msg.caption:
        to_translate = reply_msg.caption
    elif reply_msg.text:
        to_translate = reply_msg.text
    else:
        return
    try:
        args = message.text.split()[1].lower()
        if "//" in args:
            source = args.split("//")[0]
            dest = args.split("//")[1]
        else:
            source = trans.detect(to_translate)
            dest = args
    except IndexError:
        source = trans.detect(to_translate)
        dest = "en"
    translation = trans(to_translate,
                        sourcelang=source, targetlang=dest)
    reply = f"<b>Translated from {source} to {dest}</b>:\n" \
        f"<code>{translation.text}</code>"

    bot.send_message(text=reply, chat_id=message.chat.id, parse_mode=ParseMode.HTML)


@metacmd(command='langs')
def languages(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    bot = context.bot
    bot.send_message(
        text="Click [here](https://cloud.google.com/translate/docs/languages) to see the list of supported language codes!",
        chat_id=message.chat.id, disable_web_page_preview=True, parse_mode=ParseMode.MARKDOWN)
