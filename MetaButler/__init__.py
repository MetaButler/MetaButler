import logging
import os
import sys
import time
import spamwatch
import telegram.ext as tg
from telethon import TelegramClient
from pyrogram import Client, errors
from pyrogram.errors.exceptions.bad_request_400 import PeerIdInvalid, ChannelInvalid
from pyrogram.types import Chat, User
from configparser import ConfigParser
from rich.logging import RichHandler
StartTime = time.time()

# enable logging
FORMAT = "%(message)s"
logging.basicConfig(handlers=[RichHandler()], level=logging.INFO, format=FORMAT, datefmt="[%X]")
logging.getLogger("pyrogram").setLevel(logging.WARNING)
log = logging.getLogger("rich")

log.info("MetaButler is starting")

# if version < 3.6, stop bot.
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
    log.error(
        "You MUST have a python version of at least 3.6! Multiple features depend on this. Bot quitting."
    )
    quit(1)

parser = ConfigParser()
parser.read("config.ini")
config = parser["config"]


OWNER_ID = config.getint("OWNER_ID")
OWNER_USERNAME = config.get("OWNER_USERNAME")
APP_ID = config.getint("APP_ID")
API_HASH = config.get("API_HASH")
WEBHOOK = config.getboolean("WEBHOOK", False)
URL = config.get("URL", None)
CERT_PATH = config.get("CERT_PATH", None)
PORT = config.getint("PORT", None)
INFOPIC = config.getboolean("INFOPIC", False)
DEL_CMDS = config.getboolean("DEL_CMDS", False)
STRICT_GBAN = config.getboolean("STRICT_GBAN", False)
ALLOW_EXCL = config.getboolean("ALLOW_EXCL", False)
CUSTOM_CMD = config.get("CUSTOM_CMD", None)
BAN_STICKER = config.get("BAN_STICKER", None)
TOKEN = config.get("TOKEN")
DB_URI = config.get("SQLALCHEMY_DATABASE_URI")
LOAD = config.get("LOAD").split()
LOAD = list(map(str, LOAD))
MESSAGE_DUMP = config.getfloat("MESSAGE_DUMP")
GBAN_LOGS = config.getfloat("GBAN_LOGS")
NO_LOAD = config.get("NO_LOAD").split()
NO_LOAD = list(map(str, NO_LOAD))
SUDO_USERS = config.get("SUDO_USERS").split()
SUDO_USERS = list(map(int, SUDO_USERS))
WHITELIST_USERS = config.get("WHITELIST_USERS").split()
WHITELIST_USERS = list(map(int, WHITELIST_USERS))
SPAMMERS = config.get("SPAMMERS").split()
SPAMMERS = list(map(int, SPAMMERS))
spamwatch_api = config.get("spamwatch_api")
CHANNEL_ID = config.get("WALLPOST_CHANNEL_ID")
try:
    CF_API_KEY = config.get("CF_API_KEY")
    log.info("AI antispam powered by Intellivoid.")
except:
    log.info("No Coffeehouse API key provided.")
    CF_API_KEY = None


SUDO_USERS.append(OWNER_ID)

# SpamWatch
if spamwatch_api is None:
    sw = None
    log.warning("SpamWatch API key is missing! Check your config.ini")
else:
    try:
        sw = spamwatch.Client(spamwatch_api)
    except:
        sw = None
        log.warning("Can't connect to SpamWatch!")

updater = tg.Updater(TOKEN, workers=min(32, os.cpu_count() + 4), request_kwargs={"read_timeout": 10, "connect_timeout": 10})
telethn = TelegramClient("MetaButler", APP_ID, API_HASH)
dispatcher = updater.dispatcher

kp = Client("MetaButlerPyro", api_id=APP_ID, api_hash=API_HASH, bot_token=TOKEN, workers=min(32, os.cpu_count() + 4))
apps = []
apps.append(kp)


async def get_entity(client, entity):
    entity_client = client
    if not isinstance(entity, Chat):
        try:
            entity = int(entity)
        except ValueError:
            pass
        except TypeError:
            entity = entity.id
        try:
            entity = await client.get_chat(entity)
        except (PeerIdInvalid, ChannelInvalid):
            for kp in apps:
                if kp != client:
                    try:
                        entity = await kp.get_chat(entity)
                    except (PeerIdInvalid, ChannelInvalid):
                        pass
                    else:
                        entity_client = kp
                        break
            else:
                entity = await kp.get_chat(entity)
                entity_client = kp
    return entity, entity_client


SUDO_USERS = list(SUDO_USERS)
WHITELIST_USERS = list(WHITELIST_USERS)
SPAMMERS = list(SPAMMERS)

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
