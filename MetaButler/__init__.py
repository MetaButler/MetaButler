import logging
import os
import sys
import time
import spamwatch
import telegram.ext as tg
from telethon import TelegramClient
from telethon.sessions import MemorySession
from configparser import ConfigParser
from rich.logging import RichHandler
from ptbcontrib.postgres_persistence import PostgresPersistence

StartTime = time.time()

# enable logging
FORMAT = "[MetaButler] %(message)s"
logging.basicConfig(handlers=[RichHandler()], level=logging.INFO, format=FORMAT, datefmt="[%X]")
log = logging.getLogger("rich")

log.info("[META] Meta is starting. | Licensed under GPLv3.")

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
    def __init__(self, parser):
        self.parser = parser
        self.OWNER_ID = self.parser.getint('OWNER_ID')
        self.OWNER_USERNAME = self.parser.get('OWNER_USERNAME', None)
        self.APP_ID = self.parser.getint("APP_ID")
        self.API_HASH = self.parser.get("API_HASH")
        self.WEBHOOK = self.parser.getboolean('WEBHOOK', False)
        self.URL = self.parser.get('URL', None)
        self.CERT_PATH = self.parser.get('CERT_PATH', None)
        self.PORT = self.parser.getint('PORT', None)
        self.INFOPIC = self.parser.getboolean('INFOPIC', False)
        self.DEL_CMDS = self.parser.getboolean("DEL_CMDS", False)
        self.STRICT_GBAN = self.parser.getboolean("STRICT_GBAN", False)
        self.ALLOW_EXCL = self.parser.getboolean("ALLOW_EXCL", False)
        self.CUSTOM_CMD = ['/', '!']
        self.BAN_STICKER = self.parser.get("BAN_STICKER", None)
        self.TOKEN = self.parser.get("TOKEN")
        self.DB_URI = self.parser.get("SQLALCHEMY_DATABASE_URI")
        self.LOAD = self.parser.get("LOAD").split()
        self.LOAD = list(map(str, self.LOAD))
        self.MESSAGE_DUMP = self.parser.getint('MESSAGE_DUMP', None)
        self.GBAN_LOGS = self.parser.getint('GBAN_LOGS', None)
        self.NO_LOAD = self.parser.get("NO_LOAD").split()
        self.NO_LOAD = list(map(str, self.NO_LOAD))
        self.SUDO_USERS = self.parser.get("SUDO_USERS").split()
        self.SUDO_USERS = list(map(int, self.SUDO_USERS))
        self.SUPPORT_USERS = self.parser.get("SUPPORT_USERS").split()
        self.SUPPORT_USERS = list(map(int, self.SUPPORT_USERS))
        self.SPAMMERS = self.parser.get("SPAMMERS").split()
        self.SPAMMERS = list(map(int, self.SPAMMERS))
        self.DEV_USERS = self.parser.get("DEV_USERS").split()
        self.DEV_USERS = list(map(int, self.DEV_USERS))
        self.WHITELIST_USERS = self.parser.get("WHITELIST_USERS").split()
        self.WHITELIST_USERS =list(map(int, self.WHITELIST_USERS))
        self.spamwatch_api = self.parser.get('spamwatch_api', None)
        self.TIME_API_KEY = self.parser.get('TIME_API_KEY', None)
        self.CF_API_KEY =  self.parser.get("CF_API_KEY", None)
        self.WEATHER_API = self.parser.get("WEATHER_API", None)
        self.bot_id = 0 #placeholder
        self.bot_name = "MetaButler" #placeholder
        self.bot_username = "MetaButlerbot" #placeholder


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
SUDO_USERS = MInit.SUDO_USERS + [OWNER_ID]
DEV_USERS = MInit.DEV_USERS + [OWNER_ID]
SUPPORT_USERS = MInit.SUPPORT_USERS
WHITELIST_USERS = MInit.WHITELIST_USERS
SPAMMERS = MInit.SPAMMERS
spamwatch_api = MInit.spamwatch_api
WEATHER_API = MInit.WEATHER_API
TIME_API_KEY = MInit.TIME_API_KEY
CF_API_KEY = MInit.CF_API_KEY

SPB_MODE = metaconfig.getboolean('SPB_MODE', False)

# SpamWatch
sw = MInit.init_sw()

from MetaButler.modules.sql import SESSION

updater = tg.Updater(TOKEN, workers=min(32, os.cpu_count() + 4), request_kwargs={"read_timeout": 10, "connect_timeout": 10}, persistence=PostgresPersistence(SESSION))
telethn = TelegramClient(MemorySession(), APP_ID, API_HASH)
dispatcher = updater.dispatcher

# Load at end to ensure all prev variables have been set
from MetaButler.modules.helper_funcs.handlers import CustomCommandHandler

if CUSTOM_CMD and len(CUSTOM_CMD) >= 1:
    tg.CommandHandler = CustomCommandHandler


def spamfilters(text, user_id, chat_id):
    # print("{} | {} | {}".format(text, user_id, chat_id))
    if int(user_id) in SPAMMERS:
        print("This user is a spammer!")
        return True
    else:
        return False
