import re
import regex
from telegram import Update, error
from telegram.ext import CallbackContext, Filters

from MetaButler import dispatcher, log
from MetaButler.modules.helper_funcs.decorators import metamsg
from MetaButler.modules.helper_funcs.regex_helper import infinite_loop_check
from MetaButler.modules.language import gs

SED_PATTERN = re.compile(
    r"^/s/((?:\\/|[^/])*)/((?:\\/|[^/])*)(?:/([a-zA-Z]*))?$", re.DOTALL
)


def separate_sed(msg):
    match = SED_PATTERN.match(msg)
    if not match:
        return None

    find = match.group(1)
    replace = match.group(2)
    flags = match.group(3) or ""

    if not find:
        return None

    sed_re = re.compile(r"(\\{1,2})/")
    find = sed_re.sub("/", find)
    replace = sed_re.sub("/", replace)

    count = 0
    if "g" in flags:
        count = 0
    else:
        count = 1

    flags = flags.replace("g", "")

    flag_value = regex.UNICODE
    if "i" in flags:
        flag_value |= regex.IGNORECASE

    try:
        find_re = regex.compile(find, flag_value)
    except re.error:
        return None

    if infinite_loop_check(find):
        return None

    return find_re, replace, count


@metamsg(Filters.regex(r"^/s/"), can_disable=False, group=50, friendly="sed")
def sed(update: Update, context: CallbackContext):
    message = update.effective_message
    if not message.reply_to_message:
        return

    to_parse = message.text
    sed_result = separate_sed(to_parse)

    if not sed_result:
        return

    find_re, replace, count = sed_result

    replied_to = message.reply_to_message
    if replied_to.text:
        original_text = replied_to.text
    elif replied_to.caption:
        original_text = replied_to.caption
    else:
        return

    result = find_re.sub(replace, original_text, count=count)

    if result == original_text:
        return

    try:
        replied_to.reply_text(result)
    except error.BadRequest:
        pass

    try:
        message.delete()
    except error.BadRequest:
        pass


def get_help(chat):
    return gs(chat, "sed_help")


__mod_name__ = "Sed"
