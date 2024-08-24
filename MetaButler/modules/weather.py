import json
from datetime import datetime
from typing import List

from pytz import country_names as c_n
from pytz import country_timezones as c_tz
from pytz import timezone as tz
from pytz.tzinfo import DstTzInfo, StaticTzInfo
from requests import get
from telegram import (Bot, ChatAction, InlineKeyboardButton,
                      InlineKeyboardMarkup, ParseMode, Update)
from telegram.ext import CallbackContext, CommandHandler, Updater, run_async
from telegram.utils import helpers

from MetaButler import WEATHER_API, dispatcher
from MetaButler.modules.helper_funcs.decorators import metacallback, metacmd
from MetaButler.modules.helper_funcs.misc import delete
from MetaButler.modules.sql.clear_cmd_sql import get_clearcmd


def get_tz(con):
    for c_code in c_n:
        if con == c_n[c_code]:
            return tz(c_tz[c_code][0])
    try:
        if c_n[con]:
            return tz(c_tz[con][0])
    except KeyError:
        return


def fetch_weather_data(weather_data: List[str], day_count: int,
                       ctimezone: DstTzInfo | StaticTzInfo,
                       city_info: List[str]) -> str:
    day = weather_data[day_count]
    day_temp_min = day["temp"]["min"]
    day_temp_max = day["temp"]["max"]
    day_weather = day["weather"][0]
    day_condmain = day_weather["main"]
    day_conddet = day_weather["description"]
    day_icon_id = day_weather["id"]
    day_sunrise = day["sunrise"]
    day_sunset = day["sunset"]
    day_wind_speed = day["wind_speed"]
    day_humidity = day["humidity"]

    # Map weather condition codes to icons
    if day_icon_id <= 232:
        day_icon = "⛈"  # Rain storm
    elif day_icon_id <= 321:
        day_icon = "🌧"  # Drizzle
    elif day_icon_id <= 504:
        day_icon = "🌦"  # Light rain
    elif day_icon_id <= 531:
        day_icon = "⛈"  # Cloudy rain
    elif day_icon_id <= 622:
        day_icon = "❄️"  # Snow
    elif day_icon_id <= 781:
        day_icon = "🌪"  # Atmosphere
    elif day_icon_id == 800:
        day_icon = "☀️"  # Bright
    elif day_icon_id == 801:
        day_icon = "⛅️"  # A little cloudy
    elif day_icon_id <= 804:
        day_icon = "☁️"  # Cloudy

    def celsius(c):
        temp = str((c - 273.15)).split(".")
        return temp[0]

    def sun(unix):
        xx = datetime.fromtimestamp(
            unix,
            tz=ctimezone).strftime("%H:%M").lstrip("0").replace(" 0", " ")
        return xx

    msg = f"*{city_info[0]}, {city_info[1]}*\n\n"
    msg += f"*{datetime.fromtimestamp(day['dt'], tz=ctimezone).strftime('%A, %d %b')}:*\n"
    msg += f"• *Weather Summary:* `{day.get('summary')}`\n"
    msg += f"• *Minimum Temperature:* `{celsius(day_temp_min)}°C`\n"
    msg += f"• *Maximum Temperature:* `{celsius(day_temp_max)}°C`\n"
    msg += f"• *Condition:* `{day_condmain}, {day_conddet}` {day_icon}\n"
    msg += f"• *Humidity:* `{day_humidity}%`\n"
    msg += f"• *Wind:* `{str(day_wind_speed * 3.6).split('.')[0]} km/h`\n"
    msg += f"• *Sunrise:* `{sun(day_sunrise)}`\n"
    msg += f"• *Sunset:* `{sun(day_sunset)}`\n\n"
    return msg


@metacmd(command='weather', pass_args=True)
def weather(update: Update, context: CallbackContext):
    bot = context.bot
    chat = update.effective_chat
    message = update.effective_message
    city = message.text[len("/weather "):]
    weather_found = False

    if city:
        APPID = WEATHER_API
        result = None
        timezone_countries = {
            timezone: country
            for country, timezones in c_tz.items()
            for timezone in timezones
        }

        if "," in city:
            newcity = city.split(",")
            if len(newcity[1]) == 2:
                city = newcity[0].strip() + "," + newcity[1].strip()
            else:
                country = get_tz((newcity[1].strip()).title())
                try:
                    countrycode = timezone_countries[f"{country}"]
                except KeyError:
                    weather.edit("`Invalid country.`")
                    return
                city = newcity[0].strip() + "," + countrycode.strip()

        # Get the coordinates for the city
        geocode_url = f"https://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={APPID}"
        geocode_request = get(geocode_url)
        geocode_result = json.loads(geocode_request.text)

        if geocode_request.status_code != 200 or not geocode_result:
            msg = "No location information for this city!"
        else:
            lat = geocode_result[0]["lat"]
            lon = geocode_result[0]["lon"]

            # Use API 3.0 to get weather data
            url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={APPID}"
            request = get(url)
            result = json.loads(request.text)

            if request.status_code != 200:
                msg = "No weather information for this location!"
            else:
                weather_found = True
                current = result["current"]
                cityname = geocode_result[0]["name"]
                country = geocode_result[0]["country"]
                longitude = lon
                latitude = lat
                curtemp = current["temp"]
                feels_like = current["feels_like"]
                humidity = current["humidity"]
                sunrise = current["sunrise"]
                sunset = current["sunset"]
                wind_speed = current["wind_speed"]
                weath = current["weather"][0]
                condmain = weath["main"]
                conddet = weath["description"]
                icon_id = weath["id"]

                # Map weather condition codes to icons
                if icon_id <= 232:
                    icon = "⛈"  # Rain storm
                elif icon_id <= 321:
                    icon = "🌧"  # Drizzle
                elif icon_id <= 504:
                    icon = "🌦"  # Light rain
                elif icon_id <= 531:
                    icon = "⛈"  # Cloudy rain
                elif icon_id <= 622:
                    icon = "❄️"  # Snow
                elif icon_id <= 781:
                    icon = "🌪"  # Atmosphere
                elif icon_id == 800:
                    icon = "☀️"  # Bright
                elif icon_id == 801:
                    icon = "⛅️"  # A little cloudy
                elif icon_id <= 804:
                    icon = "☁️"  # Cloudy

                ctimezone = tz(c_tz[country][0])
                time = datetime.now(ctimezone).strftime(
                    "%A %d %b, %H:%M").lstrip("0").replace(" 0", " ")
                fullc_n = c_n[f"{country}"]

                kmph = str(wind_speed * 3.6).split(".")
                mph = str(wind_speed * 2.237).split(".")

                def fahrenheit(f):
                    temp = str(((f - 273.15) * 9 / 5 + 32)).split(".")
                    return temp[0]

                def celsius(c):
                    temp = str((c - 273.15)).split(".")
                    return temp[0]

                def sun(unix):
                    xx = datetime.fromtimestamp(
                        unix,
                        tz=ctimezone).strftime("%H:%M").lstrip("0").replace(
                            " 0", " ")
                    return xx

                # Current weather message
                msg = f"*{helpers.escape_markdown(cityname, version=2)}, {helpers.escape_markdown(fullc_n, version=2)}*\n"
                msg += f"`Longitude: {longitude}`\n"
                msg += f"`Latitude: {latitude}`\n\n"
                msg += f"• *Time:* `{time}`\n"
                msg += f"• *Temperature:* `{celsius(curtemp)}°C`\n"
                msg += f"• *Feels like:* `{celsius(feels_like)}°C`\n"
                msg += f"• *Condition:* `{condmain}, {conddet}` {icon}\n"
                msg += f"• *Humidity:* `{humidity}%`\n"
                msg += f"• *Wind:* `{kmph[0]} km/h`\n"
                msg += f"• *Sunrise:* `{sun(sunrise)}`\n"
                msg += f"• *Sunset:* `{sun(sunset)}`\n\n"
    else:
        msg = "Please specify a city or country"

    if weather_found:
        weather_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "7 Day Forecast",
                callback_data=f'wthr_{update.effective_user.id}_svn')
        ]])
        weather_daily = result["daily"][1:8]
        context.user_data[update.effective_chat.id] = {}
        context.user_data[
            update.effective_chat.id]['current_weather_data_msg'] = msg
        context.user_data[
            update.effective_chat.id]['weather_data'] = weather_daily
        context.user_data[update.effective_chat.id]['ctimezone'] = ctimezone
        context.user_data[update.effective_chat.id]['city_info'] = [
            cityname, fullc_n
        ]
        delmsg = message.reply_text(text=msg,
                                    parse_mode=ParseMode.MARKDOWN_V2,
                                    disable_web_page_preview=True,
                                    reply_markup=weather_keyboard)
    else:
        delmsg = message.reply_text(
            text=msg,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )

    cleartime = get_clearcmd(chat.id, "weather")

    if cleartime:
        context.dispatcher.run_async(delete, delmsg, cleartime.time)


@metacallback(pattern=r'^wthr\_\d+(\_\d+)?\_svn$')
def weather_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query_user = query.from_user
    query_data = query.data
    query_data_unpacked = query_data.split('_')

    if int(query_data_unpacked[1]) != query_user.id:
        # Someone else is clicking the button, we don't want it
        query.answer("This button is not meant for you", show_alert=True)
        return

    if len(query_data_unpacked) == 4 and int(
            query_data_unpacked[2]) in [999, 8]:
        # Unwanted button presses, we can just ignore it
        query.answer()
        return

    query.answer("Please wait while we process...")
    context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    try:
        user_data = context.user_data.get(update.effective_chat.id, {})
        weather_data = user_data.get('weather_data')
        ctimezone = user_data.get('ctimezone')
        city_info = user_data.get('city_info')
    except AttributeError:
        query.delete_message()
        return
    except KeyError:
        query.delete_message()
        return

    if not isinstance(weather_data, list):
        query.edit_message_text('Failed to fetch weather data for 7 days...')
        return

    day_count = int(
        query_data_unpacked[2]) if len(query_data_unpacked) == 4 else 0
    day_data = fetch_weather_data(
        weather_data=weather_data,
        day_count=day_count,
        ctimezone=ctimezone,
        city_info=city_info,
    )

    current_day = day_count
    prev_day = current_day - 1
    next_day = current_day + 1

    weather_keyboard = [
        [
            InlineKeyboardButton(f"Day {current_day + 1}",
                                 callback_data=f'wthr_{query_user.id}_999_svn')
        ],
        [
            InlineKeyboardButton(
                "Current Weather",
                callback_data=f'wthr_{query_user.id}_curr_svn')
        ],
    ]

    prev_button = InlineKeyboardButton(
        "«", callback_data=f'wthr_{query_user.id}_{prev_day}_svn')
    next_button = InlineKeyboardButton(
        "»", callback_data=f'wthr_{query_user.id}_{next_day}_svn')

    if current_day == 0:
        prev_button = InlineKeyboardButton(
            "—", callback_data=f'wthr_{query_user.id}_8_svn')
    elif current_day == 6:
        next_button = InlineKeyboardButton(
            "—", callback_data=f'wthr_{query_user.id}_8_svn')

    weather_keyboard[0].insert(0, prev_button)
    weather_keyboard[0].append(next_button)

    query.edit_message_text(
        text=day_data,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(weather_keyboard),
    )


@metacallback(pattern=r'^wthr\_\d+\_curr\_svn$')
def current_weather_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query_user = query.from_user
    query_data = query.data
    query_data_unpacked = query_data.split('_')

    if int(query_data_unpacked[1]) != query_user.id:
        # Someone else is clicking the button, we don't want it
        query.answer("This button is not meant for you", show_alert=True)
        return

    query.answer("Please wait while we process...")
    context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    try:
        current_weather_data = context.user_data.get(
            update.effective_chat.id).get('current_weather_data_msg')
    except AttributeError:
        query.delete_message()
    if not isinstance(current_weather_data, str):
        query.edit_message_text('Failed to fetch current weather data...')

    weather_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "7 Day Forecast",
            callback_data=f'wthr_{update.effective_user.id}_svn')
    ]])

    query.edit_message_text(
        text=current_weather_data,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
        reply_markup=weather_keyboard,
    )
