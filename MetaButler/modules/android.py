import urllib

from hurry.filesize import size as sizee
from telethon import custom
from MetaButler.events import register
from MetaButler.modules.language import gs

from requests import get
import rapidjson as json


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

    chat_id = event.chat_id

    url = 'https://raw.githubusercontent.com/topjohnwu/magisk_files/'
    releases = '**Latest Magisk Releases:**\n'
    variant = ['master/stable', 'master/beta', 'canary/canary']
    for variants in variant:
        fetch = get(url + variants + '.json')
        data = json.loads(fetch.content)
        if variants == "master/stable":
            name = "**Stable**"
            cc = 0
            branch = "master"
        elif variants == "master/beta":
            name = "**Beta**"
            cc = 0
            branch = "master"
        elif variants == "canary/canary":
            name = "**Canary**"
            cc = 1
            branch = "canary"

        if variants == "canary/canary":
            releases += f'{name}: [ZIP v{data["magisk"]["version"]}]({url}{branch}/{data["magisk"]["link"]}) | ' \
                        f'[APK v{data["app"]["version"]}]({url}{branch}/{data["app"]["link"]}) | '
        else:
            releases += f'{name}: [ZIP v{data["magisk"]["version"]}]({data["magisk"]["link"]}) | ' \
                        f'[APK v{data["app"]["version"]}]({data["app"]["link"]}) | '
        if cc == 1:
            releases += f'[Uninstaller]({data["uninstaller"]["link"]}) | ' \
                        f'[Changelog]({url}{branch}/notes.md)\n'
        else:
            releases += f'[Uninstaller]({data["uninstaller"]["link"]})\n'

    await event.reply(releases, link_preview=False)

def get_help(chat):
    return gs(chat, "android_help")

__mod_name__ = "Android"