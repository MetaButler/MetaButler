from MetaButler import dispatcher
from telegram import Update
from telegram.ext import CallbackContext
from MetaButler.modules.helper_funcs.decorators import metacmd

@metacmd(command='shout')
def shout(update: Update, context: CallbackContext):
    args = context.args
    text = " ".join(args)
    result = []
    result.append(" ".join(list(text)))
    for pos, symbol in enumerate(text[1:]):
        result.append(symbol + " " + "  " * pos + symbol)
    result = list("\n".join(result))
    result[0] = text[0]
    result = "".join(result)
    msg = "```\n" + result + "```"
    return update.effective_message.reply_text(msg, parse_mode="MARKDOWN")
