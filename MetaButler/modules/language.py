from typing import Union, List, Dict, Callable, Generator, Any
import itertools
from collections.abc import Iterable
from telegram.ext import CommandHandler, CallbackQueryHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from MetaButler import dispatcher
import MetaButler.modules.sql.language_sql as sql
from MetaButler.modules.helper_funcs.chat_status import user_admin, user_admin_no_reply
from MetaButler.langs import get_string, get_languages, get_language



def paginate(
    iterable: Iterable, page_size: int
) -> Generator[List, None, None]:
    while True:
        i1, i2 = itertools.tee(iterable)
        iterable, page = (
            itertools.islice(i1, page_size, None),
            list(itertools.islice(i2, page_size)),
        )
        if len(page) == 0:
            break
        yield page


def mb(chat_id: Union[int, str], string: str) -> str:
    lang = sql.get_chat_lang(chat_id)
    return get_string(lang, string)