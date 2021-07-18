import urllib

from hurry.filesize import size as sizee, alternative
from telethon import custom
from MetaButler.events import register
from MetaButler.modules.language import gs
from datetime import datetime
from typing import Tuple

from requests import get
import rapidjson as json

def sanitize_data(data: dict, chat_id: int) -> Tuple[str, str, str]:
    for k, v in data.items():
        device_build = k
        device_data = v
        msg = gs(chat_id, "rom_type").format(str(device_build).capitalize())
        download_url = None
        if len(device_data.keys()) == 1 and list(device_data.keys())[0] == 'msg':
            msg += f'**Message:** __{device_data["msg"]}__\n\n'
        else:
            build_date = datetime.utcfromtimestamp(int(device_data['datetime'])).strftime('%Y-%m-%d %H:%M:%S') or None
            file_name = device_data['filename'] or None
            md5_url = device_data['md5url'] or None
            build_size = sizee(int(device_data['size']), system=alternative) or None
            download_url = device_data['url']
            build_version = device_data['version']
            msg += f'**Build Date:** {build_date}\n**Build Size:** {build_size}\n**Build Version:** {build_version}\n**File Name:** [{file_name}]({download_url})\n**File MD5:** {md5_url}\n\n'
    return device_build, msg, download_url

@register(pattern=r'^/bliss(?: |$)(\S*)')
async def bliss(event):
    if event.sender_id is None:
        return
    
    chat_id = event.chat_id
    try:
        device_code__ = event.pattern_match.group(1)
        device_code = urllib.parse.quote_plus(device_code__)
    except Exception:
        device_code = ''
    
    if device_code == '':
        reply_text = gs(chat_id, "cmd_example").format('bliss')
        return await event.reply(reply_text, link_preview=False)
    
    url = 'https://downloads.blissroms.org/api/v1/updater/los/{device_code}/{build}/'
    device_data = list()
    for build in ['vanilla', 'gapps']:
        build_url = url.format(device_code=device_code, build=build)
        req = get(build_url)
        response = {}
        if req.status_code == 404:
            msg = {'msg': req.json()['message']}
            response[build] = msg
        elif req.status_code >= 500:
            msg = {'msg': 'Server error occurred, please retry later!'}
            response[build] = msg
        elif req.status_code == 200:
            response[build] = req.json()['response'][-1] # Get latest build
        else:
            msg = {'msg': f'Unexpected response {req.data}\nPlease report this to bot developers!'}
            response[build] = msg
        device_data.append(response)

    base_msg = ""
    keyboard = []
    for build in device_data:
        device_build, msg, download_url = sanitize_data(build, chat_id)
        base_msg += msg
        if download_url is not None:
            keyboard.append([custom.Button.url(f'Download {str(device_build).capitalize()} build', download_url)])
    base_msg = str(base_msg).strip()
    if len(keyboard) == 0:
        return await event.reply(base_msg)
    return await event.reply(base_msg, buttons=keyboard, link_preview=False)

@register(pattern=r"^/los(?: |$)(\S*)")
async def los(event):
    if event.sender_id is None:
        return

    chat_id = event.chat_id
    try:
        device_ = event.pattern_match.group(1)
        device = urllib.parse.quote_plus(device_)
    except Exception:
        device = ''

    if device == '':
        reply_text = gs(chat_id, "cmd_example").format("los")
        await event.reply(reply_text, link_preview=False)
        return

    fetch = get(f'https://download.lineageos.org/api/v1/{device}/nightly/*')
    if fetch.status_code == 200 and len(fetch.json()['response']) != 0:
        usr = json.loads(fetch.content)
        response = usr['response'][0]
        filename = response['filename']
        url = response['url']
        buildsize_a = response['size']
        buildsize_b = sizee(int(buildsize_a))
        version = response['version']

        reply_text = gs(chat_id, "download").format(filename, url)
        reply_text += gs(chat_id, "build_size").format(buildsize_b)
        reply_text += gs(chat_id, "version").format(version)

        keyboard = [custom.Button.url(gs(chat_id, "btn_dl"), f"{url}")]
        await event.reply(reply_text, buttons=keyboard, link_preview=False)
        return

    else:
        reply_text = gs(chat_id, "err_not_found")
    await event.reply(reply_text, link_preview=False)


@register(pattern=r"^/evo(?: |$)(\S*)")
async def evo(event):
    if event.sender_id is None:
        return

    chat_id = event.chat_id
    try:
        device_ = event.pattern_match.group(1)
        device = urllib.parse.quote_plus(device_)
    except Exception:
        device = ''

    if device == "example":
        reply_text = gs(chat_id, "err_example_device")
        await event.reply(reply_text, link_preview=False)
        return

    if device == "x00t":
        device = "X00T"

    if device == "x01bd":
        device = "X01BD"

    if device == '':
        reply_text = gs(chat_id, "cmd_example").format("evo")
        await event.reply(reply_text, link_preview=False)
        return

    fetch = get(
        f'https://raw.githubusercontent.com/Evolution-X-Devices/official_devices/master/builds/{device}.json'
    )

    if fetch.status_code in [500, 504, 505]:
        await event.reply(
            "It seem like Github User Content is down"
        )
        return

    if fetch.status_code == 200:
        try:
            usr = json.loads(fetch.content)
            filename = usr['filename']
            url = usr['url']
            version = usr['version']
            maintainer = usr['maintainer']
            maintainer_url = usr['telegram_username']
            size_a = usr['size']
            size_b = sizee(int(size_a))

            reply_text = gs(chat_id, "download").format(filename, url)
            reply_text += gs(chat_id, "build_size").format(size_b)
            reply_text += gs(chat_id, "android_version").format(version)
            reply_text += gs(chat_id, "maintainer").format(
                f"[{maintainer}](https://t.me/{maintainer_url})")

            keyboard = [custom.Button.url(gs(chat_id, "btn_dl"), f"{url}")]
            await event.reply(reply_text, buttons=keyboard, link_preview=False)
            return

        except ValueError:
            reply_text = gs(chat_id, "err_json")
            await event.reply(reply_text, link_preview=False)
            return

    elif fetch.status_code == 404:
        reply_text = gs(chat_id, "err_not_found")
        await event.reply(reply_text, link_preview=False)
        return

@register(pattern=r"^/phh$")
async def phh(event):
    if event.sender_id is None:
        return

    chat_id = event.chat_id

    fetch = get(
        "https://api.github.com/repos/phhusson/treble_experimentations/releases/latest"
    )
    usr = json.loads(fetch.content)
    reply_text = gs(chat_id, "phh_releases")
    for i in range(len(usr)):
        try:
            name = usr['assets'][i]['name']
            url = usr['assets'][i]['browser_download_url']
            reply_text += f"[{name}]({url})\n"
        except IndexError:
            continue
    await event.reply(reply_text)

@register(pattern=r"^/bootleggers(?: |$)(\S*)")
async def bootleggers(event):
    if event.sender_id is None:
        return

    chat_id = event.chat_id
    try:
        codename_ = event.pattern_match.group(1)
        codename = urllib.parse.quote_plus(codename_)
    except Exception:
        codename = ''

    if codename == '':
        reply_text = gs(chat_id, "cmd_example").format("bootleggers")
        await event.reply(reply_text, link_preview=False)
        return

    fetch = get('https://bootleggersrom-devices.github.io/api/devices.json')
    if fetch.status_code == 200:
        nestedjson = json.loads(fetch.content)

        if codename.lower() == 'x00t':
            devicetoget = 'X00T'
        else:
            devicetoget = codename.lower()

        reply_text = ""
        devices = {}

        for device, values in nestedjson.items():
            devices.update({device: values})

        if devicetoget in devices:
            for oh, baby in devices[devicetoget].items():
                dontneedlist = ['id', 'filename', 'download', 'xdathread']
                peaksmod = {
                    'fullname': 'Device name',
                    'buildate': 'Build date',
                    'buildsize': 'Build size',
                    'downloadfolder': 'SourceForge folder',
                    'mirrorlink': 'Mirror link',
                    'xdathread': 'XDA thread'
                }
                if baby and oh not in dontneedlist:
                    if oh in peaksmod:
                        oh = peaksmod[oh]
                    else:
                        oh = oh.title()

                    if oh == 'SourceForge folder':
                        reply_text += f"\n**{oh}:** [Here]({baby})\n"
                    elif oh == 'Mirror link':
                        if not baby == "Error404":
                            reply_text += f"\n**{oh}:** [Here]({baby})\n"
                    else:
                        reply_text += f"\n**{oh}:** `{baby}`"

            reply_text += gs(chat_id, "xda_thread").format(
                devices[devicetoget]['xdathread'])
            reply_text += gs(chat_id, "download").format(
                devices[devicetoget]['filename'],
                devices[devicetoget]['download'])
        else:
            reply_text = gs(chat_id, "err_not_found")

    elif fetch.status_code == 404:
        reply_text = gs(chat_id, "err_api")
    await event.reply(reply_text, link_preview=False)


@register(pattern=r"^/magisk$")
async def magisk(event):
    if event.sender_id is None:
        return

    magisk_dict = {
        "Stable":
        "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/stable.json",
        "Beta":
        "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/beta.json",
        "Canary":
        "https://raw.githubusercontent.com/topjohnwu/magisk-files/master/canary.json",
    }

    releases = "**Latest Magisk Releases:**\n"

    for name, release_url in magisk_dict.items():
        try:
            fetch = get(release_url, timeout=5)
        except Timeout:
            await event.reply(
                "MetaButler have been trying to connect to Github User Content, It seem like Github User Content is down"
            )
            return

        data = json.loads(fetch.content)
        releases += (
            f'**{name}:** [APK {data["magisk"]["version"]}]({data["magisk"]["link"]}) | '
            f'[Changelog]({data["magisk"]["note"]})\n')
    await event.reply(releases, link_preview=False)

def get_help(chat):
    return gs(chat, "android_help")

__mod_name__ = "Android"