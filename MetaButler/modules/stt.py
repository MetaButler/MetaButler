import os
import sys
import tempfile
import subprocess
import speech_recognition as sr
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from MetaButler.modules.helper_funcs.decorators import metacmd
from MetaButler.modules.helper_funcs.alternate import typing_action
from MetaButler.modules.helper_funcs.misc import has_reply_to_message
from MetaButler.modules.language import gs

def get_help(chat):
    return gs(chat, "stt_help")

__mod_name__ = "Speech-To-Text"

# Supported language codes mapping to SpeechRecognition / Google Speech locales
LANG_MAP = {
    "hi": "hi-IN",
    "mr": "mr-IN",
    "en": "en-US",
    "us": "en-US",
    "uk": "en-GB",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "ru": "ru-RU",
    "pt": "pt-BR",
    "ta": "ta-IN",
    "te": "te-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "ur": "ur-IN",
    "ar": "ar-SA",
    "zh": "zh-CN"
}

DEFAULT_LANG = "en-US"

def convert_to_wav(input_path: str, wav_path: str) -> bool:
    try:
        cmd = ["ffmpeg", "-y", "-i", input_path, "-ac", "1", "-ar", "16000", wav_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        return res.returncode == 0
    except Exception:
        return False

def transcribe_audio_file(audio_path: str, language: str = DEFAULT_LANG) -> str:
    r = sr.Recognizer()
    wav_path = audio_path + ".wav"

    try:
        if not convert_to_wav(audio_path, wav_path):
            wav_path = audio_path

        with sr.AudioFile(wav_path) as source:
            audio_data = r.record(source)

        transcription = r.recognize_google(audio_data, language=language)
        return transcription
    finally:
        if os.path.exists(wav_path) and wav_path != audio_path:
            try:
                os.remove(wav_path)
            except Exception:
                pass

@metacmd(command=["stt", "speechtotext"], pass_args=True, can_disable=True)
@typing_action
def stt(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    bot = context.bot

    if not has_reply_to_message(message):
        message.reply_text(
            "Please reply to a voice note or audio file to transcribe it to text!\n\n"
            "<b>Usage:</b>\n"
            "• Reply to voice message with <code>/stt</code> (Default Hindi/Indian accent)\n"
            "• Reply to voice message with <code>/stt -en</code> (English speech recognition)\n"
            "• Reply to voice message with <code>/stt -mr</code> (Marathi speech recognition)\n\n"
            "<i>Supported language flags: -hi, -mr, -en, -es, -fr, -de, -it, -ja, -ko, -ru, -ta, -te, -bn, -gu, etc.</i>",
            parse_mode=ParseMode.HTML
        )
        return

    reply_msg = message.reply_to_message
    audio_obj = None

    if reply_msg.voice:
        audio_obj = reply_msg.voice
    elif reply_msg.audio:
        audio_obj = reply_msg.audio
    elif reply_msg.video_note:
        audio_obj = reply_msg.video_note
    elif reply_msg.document and reply_msg.document.mime_type and reply_msg.document.mime_type.startswith("audio/"):
        audio_obj = reply_msg.document

    if not audio_obj:
        message.reply_text("The replied message does not contain a voice note or audio file!")
        return

    selected_lang = DEFAULT_LANG
    args = context.args
    if args:
        first_arg = args[0].lower().lstrip("-")
        if first_arg in LANG_MAP:
            selected_lang = LANG_MAP[first_arg]
        elif first_arg in LANG_MAP.values():
            selected_lang = first_arg

    status_msg = message.reply_text("🎧 Transcribing audio...")

    tmp_audio_path = None
    try:
        tg_file = bot.get_file(audio_obj.file_id)
        ext = ".ogg"
        if hasattr(audio_obj, "file_name") and audio_obj.file_name:
            ext = os.path.splitext(audio_obj.file_name)[1] or ".ogg"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_audio_path = tmp_file.name

        tg_file.download(custom_path=tmp_audio_path)

        transcript = transcribe_audio_file(tmp_audio_path, language=selected_lang)

        if transcript:
            reply_text = f"🗣 <b>Transcription:</b>\n\n<code>{transcript}</code>"
        else:
            reply_text = "No speech could be recognized in the audio clip."

        status_msg.edit_text(reply_text, parse_mode=ParseMode.HTML)

    except sr.UnknownValueError:
        status_msg.edit_text("Could not understand the audio speech.")
    except sr.RequestError as e:
        status_msg.edit_text(f"Speech recognition service error: {e}")
    except Exception as e:
        status_msg.edit_text(f"Failed to transcribe audio: {e}")
    finally:
        if tmp_audio_path and os.path.exists(tmp_audio_path):
            try:
                os.remove(tmp_audio_path)
            except Exception:
                pass
