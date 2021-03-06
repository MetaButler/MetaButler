from telegram.ext import run_async, CommandHandler, Filters
from MetaButler import updater, OWNER_ID, CHANNEL_ID
import logging
import requests
import random
import os
import ctypes
import shutil

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

logger = logging.getLogger(__name__)

def post(context):
    url = "https://wallhaven.cc/api/v1/search?sorting=random&categories=100&atleast=1920x1080"
    r = requests.get(url).json()
    num = random.randint(0, 23)
    pic_response = r['data'][num]
    pic_path = pic_response['path']
    pic_id = pic_response['id']
    os.mkdir("wallpaper")
    os.chdir("wallpaper")
    filename = "@wall_heaven.jpg"
    r = requests.get(pic_path)
    file = open(filename, "wb")
    file.write(r.content)
    file.close()
    logging.info("File downloaded")
    id_url = "https://wallhaven.cc/api/v1/w/" + pic_id
    id_req = requests.get(id_url).json()
    tags_dict = id_req['data']['tags']
    caption = ""
    for tag in tags_dict:
          caption += "#" + tag['name'] + " "
    caption += "\n🖥@wall_heaven"
    caption.strip()
    logging.info(caption)
    msg = context.bot.sendPhoto(CHANNEL_ID, open(filename, "rb"), caption=caption, timeout=5000)
    msg_doc = context.bot.sendDocument(CHANNEL_ID, open(filename, "rb"), timeout=500)
    if msg is not None and msg_doc is not None:
        logging.info("Document and image sent")
    else:
        logger.info("Failed to send")
    os.chdir("..")
    shutil.rmtree("wallpaper")

j = updater.job_queue
j.run_repeating(post, 14400, 60)
