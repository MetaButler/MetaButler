import logging
import os
import sys
import time
from typing import List
import spamwatch
import telegram.ext as tg
from telethon import TelegramClient
from telethon.sessions import MemorySession
from configparser import ConfigParser
from ptbcontrib.postgres_persistence import PostgresPersistence
from logging.config import fileConfig
from SibylSystem import PsychoPass

StartTime = time.time()

def get_user_list(key):
    # Import here to evade a circular import
    from MetaButler.modules.sql import metas_sql
    metas = metas_sql.get_metas(key)
    return [a.user_id for a in metas]

# enable logging

fileConfig('logging.ini')

#print(flag)
log = logging.getLogger('[MetaButler]')
logging.getLogger('ptbcontrib.postgres_persistence.postgrespersistence').setLevel(logging.WARNING)
log.info("[META] METABUTLER is starting.")

# if version < 3.6, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 7:
    log.error(
        "[META] You MUST have a python version of at least 3.7! Multiple features depend on this. Bot quitting."
    )
    quit(1)

parser = ConfigParser()
parser.read("config.ini")
metaconfig = parser["metaconfig"]

class MetaINIT:
    def __init__(self, parser: ConfigParser):
        self.parser = parser
        self.OWNER_ID: int = self.parser.getint('OWNER_ID')
        self.OWNER_USERNAME: str = self.parser.get('OWNER_USERNAME', None)
        self.APP_ID: str = self.parser.getint("APP_ID")
        self.API_HASH: str = self.parser.get("API_HASH")
        self.WEBHOOK: bool = self.parser.getboolean('WEBHOOK', False)
        self.URL: str = self.parser.get('URL', None)
        self.CERT_PATH: str = self.parser.get('CERT_PATH', None)
        self.PORT: int = self.parser.getint('PORT', None)
        self.INFOPIC: bool = self.parser.getboolean('INFOPIC', False)
        self.DEL_CMDS: bool = self.parser.getboolean("DEL_CMDS", False)
        self.STRICT_GBAN: bool = self.parser.getboolean("STRICT_GBAN", False)
        self.ALLOW_EXCL: bool = self.parser.getboolean("ALLOW_EXCL", False)
        self.CUSTOM_CMD: List[str] = ['/', '!']
        self.BAN_STICKER: str = self.parser.get("BAN_STICKER", None)
        self.TOKEN: str = self.parser.get("TOKEN")
        self.DB_URI: str = self.parser.get("SQLALCHEMY_DATABASE_URI")
        self.LOAD = self.parser.get("LOAD").split()
        self.LOAD: List[str] = list(map(str, self.LOAD))
        self.MESSAGE_DUMP: int = self.parser.getint('MESSAGE_DUMP', None)
        self.GBAN_LOGS: int = self.parser.getint('GBAN_LOGS', None)
        self.NO_LOAD = self.parser.get("NO_LOAD").split()
        self.NO_LOAD: List[str] = list(map(str, self.NO_LOAD))
        self.spamwatch_api: str = self.parser.get('spamwatch_api', None)
        self.CASH_API_KEY: str = self.parser.get('CASH_API_KEY', None)
        self.TIME_API_KEY: str = self.parser.get('TIME_API_KEY', None)
        self.bot_id = 0 #placeholder
        self.WEATHER_API = self.parser.get("WEATHER_API", None)
        self.bot_name = "MetaButler" #placeholder
        self.bot_username = "MetaButlerbot" #placeholder
        self.DEBUG: bool = self.parser.getboolean("IS_DEBUG", False)
        self.DROP_UPDATES: bool = self.parser.getboolean("DROP_UPDATES", True)
        self.BOT_API_URL: str = self.parser.get('BOT_API_URL', "https://api.telegram.org/bot")
        self.BOT_API_FILE_URL: str = self.parser.get('BOT_API_FILE_URL', "https://api.telegram.org/file/bot")
        self.PRIVATEBIN_INSTANCE: str = self.parser.get('PRIVATEBIN_INSTANCE', 'https://bin.0xfc.de/')
        self.USERGE_ANTISPAM_API_KEY = self.parser.get('USERGE_ANTISPAM_API_KEY', None)
        self.SIBYL_KEY = self.parser.get('SIBYL_KEY', None)


    def init_sw(self):
        if self.spamwatch_api is None:
            log.warning("SpamWatch API key is missing! Check your config.ini")
            return None
        else:
            try:
                sw = spamwatch.Client(spamwatch_api)
                return sw
            except:
                sw = None
                log.warning("Can't connect to SpamWatch!")
                return sw

        
    def init_sibyl_client(self):
        if self.SIBYL_KEY is None:
            log.warning("SibylSystem module is NOT loaded!")
            return None
        else:
            try:
                sibylClient: PsychoPass = None
                sibylClient = PsychoPass(self.SIBYL_KEY)
                log.info('Connected to @SibylSystem')
            except Exception as e:
                sibylClient = None
                log.error(
                    f"Failed to load SibylSystem due to {e.with_traceback(e.__traceback__)}",
                )
            return sibylClient


MInit = MetaINIT(parser=metaconfig)

OWNER_ID = MInit.OWNER_ID
OWNER_USERNAME = MInit.OWNER_USERNAME
APP_ID = MInit.APP_ID
API_HASH = MInit.API_HASH
WEBHOOK = MInit.WEBHOOK
URL = MInit.URL
CERT_PATH = MInit.CERT_PATH
PORT = MInit.PORT
INFOPIC = MInit.INFOPIC
DEL_CMDS = MInit.DEL_CMDS
ALLOW_EXCL = MInit.ALLOW_EXCL
CUSTOM_CMD = MInit.CUSTOM_CMD
BAN_STICKER = MInit.BAN_STICKER
TOKEN = MInit.TOKEN
DB_URI = MInit.DB_URI
LOAD = MInit.LOAD
MESSAGE_DUMP = MInit.MESSAGE_DUMP
GBAN_LOGS = MInit.GBAN_LOGS
NO_LOAD = MInit.NO_LOAD
SUDO_USERS = [OWNER_ID] + get_user_list("sudos")
DEV_USERS = [OWNER_ID] + get_user_list("devs")
SUPPORT_USERS = get_user_list("supports")
SARDEGNA_USERS = get_user_list("sardegnas")
WHITELIST_USERS = get_user_list("whitelists")
SPAMMERS = get_user_list("spammers")
spamwatch_api = MInit.spamwatch_api
WEATHER_API = MInit.WEATHER_API
TIME_API_KEY = MInit.TIME_API_KEY
PRIVATEBIN_INSTANCE = MInit.PRIVATEBIN_INSTANCE
USERGE_ANTISPAM_API_KEY = MInit.USERGE_ANTISPAM_API_KEY
SIBYL_KEY = MInit.SIBYL_KEY

# SpamWatch
sw = MInit.init_sw()

from MetaButler.modules.sql import SESSION
from MetaButler.modules import ALL_MODULES

# Sibyl Antispam
if 'sibylsystem' in ALL_MODULES:
    sibylClient = MInit.init_sibyl_client()

if not MInit.DROP_UPDATES:
    updater = tg.Updater(token=TOKEN, base_url=MInit.BOT_API_URL, base_file_url=MInit.BOT_API_FILE_URL, workers=min(32, os.cpu_count() + 4), request_kwargs={"read_timeout": 10, "connect_timeout": 10}, persistence=PostgresPersistence(session=SESSION))
    
else:
    updater = tg.Updater(token=TOKEN, base_url=MInit.BOT_API_URL, base_file_url=MInit.BOT_API_FILE_URL, workers=min(32, os.cpu_count() + 4), request_kwargs={"read_timeout": 10, "connect_timeout": 10})
    
telethn = TelegramClient(MemorySession(), APP_ID, API_HASH)
dispatcher = updater.dispatcher



# Load at end to ensure all prev variables have been set
from MetaButler.modules.helper_funcs.handlers import CustomCommandHandler

if CUSTOM_CMD and len(CUSTOM_CMD) >= 1:
    tg.CommandHandler = CustomCommandHandler


def spamfilters(text, user_id, chat_id):
    # print("{} | {} | {}".format(text, user_id, chat_id))
    if int(user_id) not in SPAMMERS:
        return False

    print("This user is a spammer!")
    return True
