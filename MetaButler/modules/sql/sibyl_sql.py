import threading

from MetaButler.modules.sql import BASE, SESSION
from sqlalchemy import Boolean, Column, Integer, String


class SibylSettings(BASE):
    __tablename__ = "chat_sibyl_settings"
    chat_id = Column(String(14), primary_key=True)
    setting = Column(Boolean, default=True, nullable=False)
    mode = Column(Integer, default=1)
    do_log = Column(Boolean, default=True)

    def __init__(self, chat_id, disabled, mode=1, does_log=True):
        self.chat_id = str(chat_id)
        self.setting = disabled
        self.mode = int(mode)
        self.log = bool(does_log)

    def __repr__(self):
        return f"<Sibyl setting {self.chat_id} ({self.setting})>"


SibylSettings.__table__.create(checkfirst=True)


SIBYL_SETTING_LOCK = threading.RLock()
SIBYLBAN_LIST = set()
SIBYLBAN_SETTINGS = set()


def toggle_sibyl_log(chat_id):
    with SIBYL_SETTING_LOCK:
        chat = SESSION.query(SibylSettings).get(str(chat_id))
        chat.do_log = not chat.do_log
        SESSION.add(chat)
        SESSION.commit()
        if str(chat_id) in SIBYLBAN_SETTINGS:
            SIBYLBAN_SETTINGS[f'{chat_id}'] = (
                chat.do_log, SIBYLBAN_SETTINGS[f'{chat_id}'][1])
            return
        SIBYLBAN_SETTINGS[f'{chat_id}'] = (True, 1)


def toggle_sibyl_mode(chat_id, mode):
    with SIBYL_SETTING_LOCK:
        chat = SESSION.query(SibylSettings).get(str(chat_id))
        if not chat:
            chat = SibylSettings(chat_id, True, mode)
        chat.mode = mode
        SESSION.add(chat)
        SESSION.commit()
        if str(chat_id) in SIBYLBAN_SETTINGS:
            SIBYLBAN_SETTINGS[f'{chat_id}'] = (
                SIBYLBAN_SETTINGS[f'{chat_id}'][0], mode)
            return
        SIBYLBAN_SETTINGS[f'{chat_id}'] = (True, 1)


def enable_sibyl(chat_id):
    with SIBYL_SETTING_LOCK:
        chat = SESSION.query(SibylSettings).get(str(chat_id))
        if not chat:
            chat = SibylSettings(chat_id, True)

        chat.setting = True
        SESSION.add(chat)
        SESSION.commit()
        if str(chat_id) in SIBYLBAN_LIST:
            SIBYLBAN_LIST.remove(str(chat_id))


def disable_sibyl(chat_id):
    with SIBYL_SETTING_LOCK:
        chat = SESSION.query(SibylSettings).get(str(chat_id))
        if not chat:
            chat = SibylSettings(chat_id, False)

        chat.setting = False
        SESSION.add(chat)
        SESSION.commit()
        SIBYLBAN_LIST.add(str(chat_id))


def __load_sibylban_list():
    global SIBYLBAN_LIST
    try:
        SIBYLBAN_LIST = {
            x.chat_id for x in SESSION.query(SibylSettings).all() if not x.setting
        }
    finally:
        SESSION.close()


def __load_sibylban_settings():
    global SIBYLBAN_SETTINGS
    try:
        SIBYLBAN_SETTINGS = {
            x.chat_id: (x.do_log, x.mode) for x in SESSION.query(SibylSettings).all()
        }
    finally:
        SESSION.close()


def does_chat_sibylban(chat_id):
    return str(chat_id) not in SIBYLBAN_LIST


def chat_sibyl_settings(chat_id):
    return chat_id not in SIBYLBAN_SETTINGS,


# Create in memory to avoid disk access
__load_sibylban_list()
__load_sibylban_settings()
