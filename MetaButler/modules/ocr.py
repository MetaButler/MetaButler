import os
from PIL import Image
import pytesseract

from MetaButler.modules.helper_funcs.decorators import metacmd
from telegram import ParseMode, Update
from telegram.ext import CallbackContext


@metacmd(command='ocr', pass_args=True)
def ocr(update: Update, context: CallbackContext):
    message = update.effective_message
    if message.reply_to_message.photo:
        try:
            file_info = context.bot.get_file(
                message.reply_to_message.photo.file_id)
            path = file_info.download(out=file)
            text = pytesseract.image_to_string(Image.open(path))
            if text:
                update.message.reply_text(f"{str(text)}\n\nImage to Text Generated using @MetaButlerBot")
            else:
                update.message.reply_text("No Text Found")
        except Exception as e:
            update.message.reply_text(f"Error Occured: {e}")
        finally:        
            os.remove(path)        

    else:
        message.reply_text('What am I supposed to do with this?')
        return


