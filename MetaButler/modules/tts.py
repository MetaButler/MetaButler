import io
import asyncio
import edge_tts
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from MetaButler.modules.helper_funcs.decorators import metacmd
from MetaButler.modules.helper_funcs.alternate import typing_action
from MetaButler.modules.helper_funcs.misc import has_reply_to_message
from MetaButler.modules.language import gs

def get_help(chat):
    return gs(chat, "tts_help")

__mod_name__ = "Text-To-Speech"

# Language and dialect shortcuts mapping to edge-tts neural voices
VOICE_MAP = {
    "hi": "hi-IN-SwaraNeural",
    "mr": "mr-IN-AarohiNeural",
    "en": "en-IN-NeerjaNeural",
    "us": "en-US-AriaNeural",
    "uk": "en-GB-SoniaNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "it": "it-IT-ElsaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "pt": "pt-BR-FranciscaNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "bn": "bn-IN-TanishaaNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "ur": "ur-IN-GulNeural",
    "ar": "ar-SA-ZariyahNeural",
    "zh": "zh-CN-XiaoxiaoNeural"
}

import os
import sys
import subprocess
import tempfile

DEFAULT_VOICE = "hi-IN-SwaraNeural"

def generate_speech(text: str, voice: str) -> io.BytesIO:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            sys.executable,
            "-m",
            "edge_tts",
            "--voice",
            voice,
            "--text",
            text,
            "--write-media",
            tmp_path,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "edge-tts process failed")

        with open(tmp_path, "rb") as f:
            audio_data = io.BytesIO(f.read())

        audio_data.name = "tts.mp3"
        audio_data.seek(0)
        return audio_data
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass




@metacmd(command=["tts", "texttospeech"], pass_args=True, can_disable=True)
@typing_action
def tts(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    bot = context.bot
    reply_msg = message.reply_to_message

    target_text = ""
    voice = DEFAULT_VOICE

    args = context.args

    if has_reply_to_message(message):
        if reply_msg.text:
            target_text = reply_msg.text
        elif reply_msg.caption:
            target_text = reply_msg.caption

        if args:
            lang_arg = args[0].lower().lstrip("-")
            if lang_arg in VOICE_MAP:
                voice = VOICE_MAP[lang_arg]
            elif lang_arg in VOICE_MAP.values():
                voice = lang_arg
    else:
        if not args:
            message.reply_text(
                "Please provide text or reply to a message to convert it to speech!\n\n"
                "<b>Usage:</b>\n"
                "• <code>/tts <text></code>\n"
                "• <code>/tts -<lang_code> <text></code>\n"
                "<i>Example: /tts Hello world</i>\n"
                "<i>Example: /tts -hi Namaste dosto</i>\n"
                "<i>Example: /tts -es Hola mundo</i>",
                parse_mode=ParseMode.HTML
            )
            return

        first_arg = args[0].lower()
        if first_arg.startswith("-"):
            clean_arg = first_arg[1:]
            if clean_arg in VOICE_MAP:
                voice = VOICE_MAP[clean_arg]
                target_text = " ".join(args[1:])
            elif clean_arg in VOICE_MAP.values():
                voice = clean_arg
                target_text = " ".join(args[1:])
            else:
                target_text = " ".join(args)
        else:
            target_text = " ".join(args)


    if not target_text.strip():
        message.reply_text("No readable text found to convert to speech!")
        return

    try:
        audio_stream = generate_speech(target_text, voice)
        bot.send_voice(
            chat_id=message.chat.id,
            voice=audio_stream,
            reply_to_message_id=message.message_id
        )
    except Exception as e:
        message.reply_text(f"Failed to generate speech audio: {e}")
