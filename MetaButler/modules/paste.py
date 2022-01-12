from telegram import ParseMode, Update
from telegram.ext import CallbackContext
from MetaButler.modules.helper_funcs.decorators import metacmd
import privatebinapi
from io import BytesIO

@metacmd(command='paste', pass_args=True)
def paste(update: Update, context: CallbackContext):
    args = context.args
    message = update.effective_message
    
    if message.reply_to_message:
        data = message.reply_to_message.text or message.reply_to_message.caption
        if message.reply_to_message.document:
            file_info = context.bot.get_file(message.reply_to_message.document.file_id)
            with BytesIO() as file:
                file_info.download(out=file)
                file.seek(0)
                data = file.read().decode()
                
    elif len(args) >= 1:
        data = message.text.split()[1:]
    else:
        message.reply_text('What am I supposed to do with this?')
        return
    
    txt = ''
    pvt_bin_response = privatebinapi.send('https://bin.nixnet.services', text = data, expiration = '1week', formatting = 'syntaxhighlighting')
    if not pvt_bin_response['full_url']:
        txt = 'Failed to paste data'
    else:
        txt = '<b>Successfully uploaded to PrivateBin:</b> {0}\n<b>Your paste deleting token is:</b> <code>{1}</code>\n<b>Paste Deletion Time: 1 Week</b>'.format(pvt_bin_response["full_url"], pvt_bin_response["deletetoken"])
    
    message.reply_text(txt, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
    
@metacmd(command='delpaste', pass_args=True)
def delpaste(update: Update, context: CallbackContext) -> None:
    args = context.args
    msg = update.effective_message
    
    if len(args) >= 2:
        full_url = msg.text.split()[1]
        del_token = msg.text.split()[2]
    else:
        msg.reply_text('What am I supposed to do with this?')
        return
    
    delete_response = privatebinapi.delete(full_url, del_token)
    if delete_response is not None:
        if int(delete_response['status']) == 0:
            msg.reply_text('<b>Successfully deleted paste!</b>', parse_mode=ParseMode.HTML)
            return
    else:
        msg.reply_text('<b>Paste does not exist or wrong token provided!</b>', parse_mode=ParseMode.HTML)