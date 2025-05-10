import logging
import sqlite3
import os
import re
import aiohttp
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.dispatcher.filters import CommandStart, Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetBotCallbackAnswerRequest
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime

API_TOKEN = '7641976092:AAFUp_piifBNoC40LPaONmK_u8f5qOMBu3w'
ADMIN_ID = 5866737498
SOURCE_CHAT_ID = 7074719049
USER_SESSION_STRING = "1ApWapzMBu1_lNFE8FgVmXjuAkY3sGhebjDt-21cYYmJzMriklHfH3IIVYhKHDbSS2geCZERPL4flKRbMONnmNdYHPN9-1tX4Pp7x9KunJ1qjj8qY9DxxId8aFIIkJzUpMYvr0Uo41E-Bj5eUDEoSnKl3cARq8mcwlil-Ff3PvQRLCpdH6YwoFA18785elwv78ZkrPH6xg7-8I8urhGJamcLYHZK_wG4ycu1QaNx4PsuV-H_kXtKMFwlB8mT91-gbA6hYYc5kOfmZ9uCsiEIdcugqk12pQUR-AAHYNGlSiGTNBHILj3u484S8uUQaQf0uWnVIqm0kzUhmC8A-T0Zs4sygYsYejcY="
API_ID = "20105750"
API_HASH = "d29d2bd01c6d1a29fdb4c53161b14073"
MINI_APP_URL = "https://secrexon.vercel.app" # Replace with your hosted Mini App URL

logging.basicConfig(level=logging.INFO)

client = TelegramClient(StringSession(USER_SESSION_STRING), API_ID, API_HASH)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
conn = sqlite3.connect('users.db')
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    approved INTEGER DEFAULT 0
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()

admin_kb = ReplyKeyboardMarkup(resize_keyboard=True)
admin_kb.add(KeyboardButton("👤 Список пользователей"))
admin_kb.add(KeyboardButton("✅ Одобрить"), KeyboardButton("❌ Удалить"))
admin_kb.add(KeyboardButton("📜 Логи"), KeyboardButton("🔍 Поиск"))

user_kb = ReplyKeyboardMarkup(resize_keyboard=True)
user_kb.add(KeyboardButton("🔍 Поиск"))
user_kb.add(KeyboardButton("🌐 Открыть Mini App"))

search_type_kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
search_type_kb.add(KeyboardButton("📱 Номер Телефона"))
search_type_kb.add(KeyboardButton("👤 ФИО"))
search_type_kb.add(KeyboardButton("💬 Телеграм"))
search_type_kb.add(KeyboardButton("🌐 ВКонтакте"))
search_type_kb.add(KeyboardButton("📧 Почта"))
search_type_kb.add(KeyboardButton("⬅ Назад"))

class AdminStates(StatesGroup):
    waiting_for_id_to_approve = State()
    waiting_for_id_to_remove = State()

class SearchState(StatesGroup):
    waiting_for_search_type = State()
    waiting_for_phone = State()
    waiting_for_fio = State()
    waiting_for_telegram = State()
    waiting_for_vk = State()
    waiting_for_email = State()

@dp.message_handler(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "-"
    full_name = message.from_user.full_name

    cursor.execute("SELECT approved FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute("INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
                       (user_id, username, full_name))
        conn.commit()
        await bot.send_message(ADMIN_ID, f"🔔 *Новый пользователь*: _{full_name}_ (@{username})", parse_mode="Markdown")
        await message.answer("🔒 *Доступ ограничен*. Ожидайте одобрения администратора 🕒.", parse_mode="Markdown")
        return

    if user_id == ADMIN_ID:
        await message.answer("Добро пожаловать, *админ*! 🎉", reply_markup=admin_kb, parse_mode="Markdown")
    elif row[0] == 1:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🌐 Открыть Mini App", web_app=WebAppInfo(url=MINI_APP_URL)))
        await message.answer("✅ *Доступ разрешён*. Добро пожаловать! 🌟", reply_markup=user_kb, parse_mode="Markdown")
        await message.answer("Нажмите кнопку ниже, чтобы открыть Mini App:", reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("🔒 *Ваш доступ ещё не одобрен*. Ожидайте ⏳.", parse_mode="Markdown")
    await state.finish()

@dp.message_handler(lambda m: m.text == "🌐 Открыть Mini App")
async def open_mini_app(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT approved FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == 1 or user_id == ADMIN_ID:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🌐 Открыть Mini App", web_app=WebAppInfo(url=MINI_APP_URL)))
        await message.answer("Нажмите кнопку ниже, чтобы открыть Mini App:", reply_markup=kb, parse_mode="Markdown")
    else:
        await message.answer("🔒 *У вас нет доступа к Mini App* 🚫.", parse_mode="Markdown")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and "список" in m.text.lower())
async def list_users(message: types.Message):
    cursor.execute("SELECT user_id, username, full_name, approved FROM users")
    users = cursor.fetchall()
    msg = "👥 *Список пользователей*:\n\n"
    for u in users:
        status = "✅" if u[3] else "❌"
        msg += f"{status} _{u[2]}_ (@{u[1]}) — `{u[0]}`\n"
    await message.answer(msg, parse_mode="Markdown")

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and "одобрить" in m.text.lower())
async def approve_user(message: types.Message):
    await message.answer("✏️ Введите *ID пользователя* для одобрения:", parse_mode="Markdown")
    await AdminStates.waiting_for_id_to_approve.set()

@dp.message_handler(lambda m: m.text.isdigit() and m.from_user.id == ADMIN_ID, state=AdminStates.waiting_for_id_to_approve)
async def get_id_to_approve(msg: types.Message, state: FSMContext):
    uid = int(msg.text.strip())
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    if cursor.fetchone():
        cursor.execute("UPDATE users SET approved = 1 WHERE user_id = ?", (uid,))
        conn.commit()
        await bot.send_message(uid, "✅ *Ваш доступ одобрен*! 🎉", reply_markup=user_kb, parse_mode="Markdown")
        await msg.answer("✔️ *Пользователь одобрен*.", parse_mode="Markdown")
    else:
        await msg.answer("❌ *Пользователь не найден*.", parse_mode="Markdown")
    await state.finish()

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and "удалить" in m.text.lower())
async def remove_user(message: types.Message):
    await message.answer("✏️ Введите *ID пользователя* для удаления:", parse_mode="Markdown")
    await AdminStates.waiting_for_id_to_remove.set()

@dp.message_handler(lambda m: m.text.isdigit() and m.from_user.id == ADMIN_ID, state=AdminStates.waiting_for_id_to_remove)
async def process_remove_id(msg: types.Message, state: FSMContext):
    uid = int(msg.text.strip())
    cursor.execute("SELECT approved FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()

    if row is not None:
        prev_approved = row[0]
        if prev_approved == 1:
            await bot.send_message(uid, "❌ *Вас лишили доступа*. Отправьте /start для повторного запроса 🚫.", parse_mode="Markdown")
        else:
            await bot.send_message(uid, "❌ *Вам отказано в доступе* 🚫.", parse_mode="Markdown")

        cursor.execute("DELETE FROM users WHERE user_id = ?", (uid,))
        cursor.execute("DELETE FROM logs WHERE user_id = ?", (uid,))
        conn.commit()
        logging.info(f"Пользователь с ID {uid} удалён из базы данных и логов.")

        await msg.answer("🗑️ *Пользователь удалён* и должен заново запросить доступ.", parse_mode="Markdown")
    else:
        await msg.answer("❌ *Пользователь не найден*.", parse_mode="Markdown")
    await state.finish()

@dp.message_handler(lambda m: m.from_user.id == ADMIN_ID and "логи" in m.text.lower())
async def show_logs(message: types.Message):
    cursor.execute("SELECT DISTINCT user_id, username FROM users")
    users = cursor.fetchall()
    kb = InlineKeyboardMarkup(row_width=2)
    for u in users:
        username = u[1] or f"ID{u[0]}"
        kb.add(InlineKeyboardButton(f"@{username}", callback_data=f"log_{u[0]}"))
    await message.answer("📜 *Выберите пользователя* для просмотра логов:", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data.startswith("log_"))
async def show_user_logs(callback_query: types.CallbackQuery):
    user_id = int(callback_query.data.split("_")[1])
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    username = row[0] if row else str(user_id)
    cursor.execute("SELECT action, timestamp FROM logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20", (user_id,))
    logs = cursor.fetchall()
    if not logs:
        await callback_query.message.edit_text(f"📭 У пользователя *@{username}* пока нет логов.", parse_mode="Markdown")
        return
    text = f"📜 *Логи пользователя* @_{username}_:\n\n"
    for l in logs:
        text += f"🕒 *[{l[1]}]* — _{l[0]}_\n"
    await callback_query.message.edit_text(text, parse_mode="Markdown")

@dp.message_handler(lambda m: m.text == "🔍 Поиск" or m.text.startswith("/search"), state="*")
async def handle_search_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cursor.execute("SELECT approved FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == 1 or user_id == ADMIN_ID:
        await message.answer("🔍 *Выберите тип поиска*:", reply_markup=search_type_kb, parse_mode="Markdown")
        await SearchState.waiting_for_search_type.set()
    else:
        await message.answer("🔒 *У вас нет доступа к поиску* 🚫.", parse_mode="Markdown")
        await state.finish()

@dp.message_handler(lambda m: m.text == "⬅ Назад", state=SearchState.waiting_for_search_type)
async def handle_back_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        await message.answer("↩️ *Возвращаемся в админ-панель*.", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await message.answer("↩️ *Возвращаемся в меню*.", reply_markup=user_kb, parse_mode="Markdown")
    await state.finish()

@dp.message_handler(state=SearchState.waiting_for_search_type)
async def process_search_type(message: types.Message, state: FSMContext):
    search_type = message.text
    if search_type == "📱 Номер Телефона":
        await message.answer("📱 Введите *номер телефона* (например, `79110229894`):", parse_mode="Markdown")
        await SearchState.waiting_for_phone.set()
    elif search_type == "👤 ФИО":
        await message.answer("👤 Введите *ФИО и дату рождения* в формате: _Иванов Иван Иванович 15.05.1990_", parse_mode="Markdown")
        await SearchState.waiting_for_fio.set()
    elif search_type == "💬 Телеграм":
        await message.answer("💬 Введите *Telegram ID* в формате: `tg5866737498`", parse_mode="Markdown")
        await SearchState.waiting_for_telegram.set()
    elif search_type == "🌐 ВКонтакте":
        await message.answer("🌐 Введите *ссылку ВКонтакте* в формате: `vk.com/sherlock`", parse_mode="Markdown")
        await SearchState.waiting_for_vk.set()
    elif search_type == "📧 Почта":
        await message.answer("📧 Введите *email* (например, `example@email.com`):", parse_mode="Markdown")
        await SearchState.waiting_for_email.set()
    else:
        await message.answer("❓ *Пожалуйста, выберите тип поиска из предложенных кнопок*.", parse_mode="Markdown")
        return

@dp.message_handler(state=SearchState.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.isdigit():
        await message.answer("❌ Введите *корректный номер телефона* (только цифры) 📱.", parse_mode="Markdown")
        return
    query = phone
    await process_query_with_query(message, query, "phone")
    await message.answer("🔍 *Выберите тип поиска*:", reply_markup=search_type_kb, parse_mode="Markdown")
    await SearchState.waiting_for_search_type.set()

@dp.message_handler(state=SearchState.waiting_for_fio)
async def process_fio(message: types.Message, state: FSMContext):
    fio_input = message.text.strip()
    fio_pattern = r"^[А-Яа-яЁё\s]+ \d{2}\.\d{2}\.\d{4}$"
    if not re.match(fio_pattern, fio_input):
        await message.answer("❌ Введите *ФИО и дату рождения* в формате: _Иванов Иван Иванович 15.05.1990_ 👤.", parse_mode="Markdown")
        return
    query = fio_input
    await process_fio_query(message, query)
    await message.answer("🔍 *Выберите тип поиска*:", reply_markup=search_type_kb, parse_mode="Markdown")
    await SearchState.waiting_for_search_type.set()

@dp.message_handler(state=SearchState.waiting_for_telegram)
async def process_telegram(message: types.Message, state: FSMContext):
    tg_input = message.text.strip()
    if not tg_input.startswith("tg") or not tg_input[2:].isdigit():
        await message.answer("❌ Введите *Telegram ID* в формате: `tg5866737498` 💬.", parse_mode="Markdown")
        return
    query = tg_input
    await process_query_no_report(message, query, "telegram")
    await message.answer("🔍 *Выберите тип поиска*:", reply_markup=search_type_kb, parse_mode="Markdown")
    await SearchState.waiting_for_search_type.set()

@dp.message_handler(state=SearchState.waiting_for_vk)
async def process_vk(message: types.Message, state: FSMContext):
    vk_input = message.text.strip()
    if not vk_input.startswith("vk.com/"):
        await message.answer("❌ Введите *ссылку ВКонтакте* в формате: `vk.com/sherlock` 🌐.", parse_mode="Markdown")
        return
    query = vk_input
    await process_query_no_report(message, query, "vk")
    await message.answer("🔍 *Выберите тип поиска*:", reply_markup=search_type_kb, parse_mode="Markdown")
    await SearchState.waiting_for_search_type.set()

@dp.message_handler(state=SearchState.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    email = message.text.strip()
    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(email_pattern, email):
        await message.answer("❌ Введите *корректный email* (например, `example@email.com`) 📧.", parse_mode="Markdown")
        return
    query = email
    await process_query_with_query(message, query, "email")
    await message.answer("🔍 *Выберите тип поиска*:", reply_markup=search_type_kb, parse_mode="Markdown")
    await SearchState.waiting_for_search_type.set()

async def download_file(url: str, filename: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(filename, 'wb') as f:
                        f.write(content)
                    return True, filename
                else:
                    logging.error(f"Ошибка при скачивании файла: HTTP {response.status}")
                    return False, None
    except Exception as e:
        logging.error(f"Ошибка при скачивании файла: {str(e)}")
        return False, None

def parse_report_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    sections = []
    current_section = None

    report_cards = soup.find_all('section', class_='report-card')
    if not report_cards:
        logging.warning("Секции 'report-card' не найдены")
        return [{'title': 'Результат', 'items': [['Нет данных', '']]}]

    social_networks = ["TikTok", "Instagram", "Facebook", "Twitter", "VK", "ВКонтакте", "Одноклассники", "YouTube"]

    for card in report_cards:
        title_elem = card.find(['h2', 'h3'])
        if title_elem:
            if current_section:
                sections.append(current_section)
            current_section = {'title': title_elem.get_text(strip=True), 'items': []}
            logging.info(f"Найден заголовок: {current_section['title']}")

        if current_section:
            ul = card.find('ul', class_='report-summary')
            if ul:
                for li in ul.find_all('li'):
                    label = li.find('div', class_='report-card__label')
                    span = li.find('span')
                    if label and span:
                        key = label.get_text(strip=True)
                        value = span.get_text(strip=True).replace('\n', ' ').strip()
                        if span.find('a', class_='__cf_email__'):
                            cf_email = span.find('a', class_='__cf_email__')
                            value = cf_email.get('data-cfemail', cf_email.get_text(strip=True))
                        current_section['items'].append([key, value])
                        logging.info(f"Извлечена пара: {key} -> {value}")

            dl = card.find('dl', class_='report-details')
            if dl:
                for dt, dd in zip(dl.find_all('dt'), dl.find_all('dd')):
                    key = dt.get_text(strip=True)
                    value = dd.get_text(strip=True)
                    current_section['items'].append([key, value])
                    logging.info(f"Извлечена пара: {key} -> {value}")

            tables = card.find_all('table')
            for table in tables:
                for row in table.find('tbody').find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        link = cells[2].find('a')['href'] if len(cells) > 2 and cells[2].find('a') else ''
                        current_section['items'].append([key, value])
                        if link:
                            current_section['items'].append(['Ссылка', link])
                        logging.info(f"Извлечена пара: {key} -> {value}, Ссылка: {link}")

            getcontacts = card.find('div', class_='getcontacts')
            if getcontacts:
                for span in getcontacts.find_all('span'):
                    value = span.get_text(strip=True)
                    current_section['items'].append(['Имя', value])
                    logging.info(f"Извлечено имя: {value}")

            address_list = card.find('ul', class_='report-addresses')
            if address_list:
                for li in address_list.find_all('li'):
                    address = li.get_text(strip=True)
                    current_section['items'].append(['Адрес', address])
                    logging.info(f"Извлечён адрес: {address}")

            email_list = card.find('ul', class_='report-emails')
            if email_list:
                for li in email_list.find_all('li'):
                    email = li.get_text(strip=True)
                    if li.find('a', class_='__cf_email__'):
                        cf_email = li.find('a', class_='__cf_email__')
                        email = cf_email.get('data-cfemail', cf_email.get_text(strip=True))
                    if email != "[email protected]":
                        current_section['items'].append(['Email', email])
                        logging.info(f"Извлечён email: {email}")

            divs = card.find_all('div', recursive=False)
            for div in divs:
                if div.get('class') not in ['getcontacts']:
                    text = div.get_text(strip=True)
                    if text and text not in [item[1] for item in current_section['items']]:
                        if any(social in text for social in social_networks):
                            match = re.match(r'(.+?:)\s*(\S+)\s*\((https?://[^\)]+)\)', text)
                            if match:
                                prefix, username, url = match.groups()
                                formatted_text = f"{prefix} [{username}]({url})"
                                current_section['items'].append(['Социальные сети', formatted_text])
                                logging.info(f"Отформатирована соцсеть: {formatted_text}")
                            else:
                                current_section['items'].append(['Социальные сети', text])
                                logging.info(f"Извлечён текст соцсети: {text}")
                        else:
                            current_section['items'].append(['Дополнительно', text])
                            logging.info(f"Извлечён доп. текст: {text}")

    if current_section:
        sections.append(current_section)

    if not sections:
        sections.append({'title': 'Результат', 'items': [['Нет данных', '']]})

    return sections

async def generate_html_report(query: str, report_url: str = None, search_type: str = "phone", match_info: str = "", sherlock_message: str = ""):
    html_file = None
    sections_html = ""
    if report_url:
        logging.info(f"Скачиваем отчёт по URL: {report_url}")
        success, html_file = await download_file(report_url, "temp_report.html")
        if success:
            with open(html_file, 'r', encoding='utf-8') as f:
                report_html = f.read()
            os.remove(html_file)
            logging.info("HTML отчёт успешно загружен")
            report_sections = parse_report_html(report_html)
            for section in report_sections:
                section_html = f"<div class='section-card'><h2>{section['title']}</h2><ul>"
                for item in section['items']:
                    section_html += "<li>"
                    if isinstance(item, list) and len(item) == 2:
                        key, value = item
                        section_html += f"<span class='key'>{key}:</span> <span class='value'>{value}</span>"
                    else:
                        section_html += f"Неизвестно: {item}"
                    section_html += "</li>"
                section_html += "</ul></div>"
                sections_html += section_html
        else:
            logging.error("Не удалось скачать отчёт")
            sections_html = "<div class='section-card'><h2>Результат</h2><ul><li>Не удалось загрузить данные</li></ul></div>"
    else:
        logging.error(f"URL отчёта не предоставлен. match_info: {match_info}")
        sections_html = f"<div class='section-card'><h2>Результат</h2><ul><li>{match_info if match_info else 'URL отчёта не получен'}</li></ul></div>"

    return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Таинственный Архив</title>
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&family=Montserrat:wght@600&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Roboto', sans-serif;
            background: linear-gradient(180deg, #1C2526 0%, #2E3A3B 100%);
            color: #E5E5E5;
            margin: 0;
            padding: 40px;
            line-height: 1.6;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
        }}
        .header {{
            display: flex;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #D4A017;
        }}
        .header img {{
            width: 80px;
            height: auto;
            margin-right: 20px;
            filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
        }}
        .header-text {{
            display: flex;
            flex-direction: column;
        }}
        .header-text .title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 28px;
            color: #D4A017;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .header-text .subtitle {{
            font-size: 16px;
            color: #A0A0A0;
            font-style: italic;
        }}
        .section-card {{
            background: #FFFFFF;
            color: #2E2E2E;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 12px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        .section-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.25);
        }}
        h2 {{
            font-family: 'Montserrat', sans-serif;
            color: #D4A017;
            font-size: 24px;
            margin-bottom: 20px;
            border-bottom: 2px solid #D4A017;
            padding-bottom: 8px;
            text-transform: uppercase;
        }}
        ul {{
            list-style-type: none;
            padding: 0;
            margin: 0;
        }}
        li {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 15px;
            padding: 12px 15px;
            background: #F8F8F8;
            border-radius: 8px;
            border-bottom: 1px solid #E0E0E0;
            transition: background 0.2s ease;
        }}
        li:last-child {{
            border-bottom: none;
        }}
        li:hover {{
            background: #E8ECEF;
        }}
        .key {{
            font-weight: 700;
            color: #2E2E2E;
            flex: 0 0 30%;
            text-align: right;
            padding-right: 15px;
        }}
        .value {{
            color: #4A4A4A;
            flex: 1;
            text-align: left;
            overflow-wrap: break-word;
            word-wrap: break-word;
            word-break: break-all;
        }}
        @media (max-width: 768px) {{
            body {{
                padding: 20px;
            }}
            .container {{
                padding: 10px;
            }}
            .header img {{
                width: 60px;
            }}
            .header-text .title {{
                font-size: 24px;
            }}
            .section-card {{
                padding: 15px;
            }}
            li {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .key {{
                text-align: left;
                flex: none;
                margin-bottom: 5px;
            }}
            .value {{
                text-align: left;
                font-size: 14px;
            }}
        }}
        @media (max-width: 480px) {{
            body {{
                padding: 15px;
            }}
            .header-text .title {{
                font-size: 20px;
            }}
            .header-text .subtitle {{
                font-size: 14px;
            }}
            .section-card {{
                padding: 10px;
            }}
            h2 {{
                font-size: 20px;
            }}
            .key, .value {{
                font-size: 12px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="file:///C:/Users/User/Bot/TGBOT/logo.png" alt="Таинственный Архив">
            <div class="header-text">
                <span class="title">Таинственный Архив</span>
                <span class="subtitle">Конфиденциальный отчёт</span>
            </div>
        </div>
        {sections_html}
    </div>
</body>
</html>
"""

async def process_query_with_query(aiogram_message: types.Message, query: str, search_type: str):
    user_id = aiogram_message.from_user.id
    html_file = f"report_{user_id}.html"
    cursor.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, f"Поиск ({search_type}): {query}"))
    conn.commit()

    await aiogram_message.answer("⏳ *Обработка запроса...* 🔎", parse_mode="Markdown")
    try:
        async with client:
            source_entity = await client.get_entity("pal3vo_probivbot")
            logging.info(f"Источник данных найден: {source_entity.id}")

            formatted_query = f"/search {query}"
            logging.info(f"Отправка запроса '{formatted_query}'")
            sent_message = await client.send_message(source_entity, formatted_query)
            sent_message_id = sent_message.id
            sent_message_date = sent_message.date
            logging.info(f"Запрос отправлен, ID: {sent_message_id}, Дата: {sent_message_date}")

            timeout = 120
            start_time = asyncio.get_event_loop().time()
            report_url = None
            sherlock_message = ""
            try:
                while asyncio.get_event_loop().time() - start_time < timeout:
                    logging.info(f"Проверка новых сообщений, прошло {asyncio.get_event_loop().time() - start_time:.1f} сек")
                    messages = await client.get_messages(source_entity, limit=10, min_id=sent_message_id)
                    for message in messages:
                        logging.info(f"Получено сообщение ID {message.id}, Дата: {message.date}, Out: {message.out}, Текст: {message.text}")
                        if message.date >= sent_message_date and not message.out:
                            if message.text and not sherlock_message:
                                sherlock_message = message.text
                                sherlock_message = sherlock_message.replace("Интересовались этим: ", "")
                                sherlock_message = re.sub(r'[\*_`\[\]]', '', sherlock_message)
                                sherlock_message = sherlock_message.strip()
                                logging.info(f"Очищенное сообщение от Шерлока: {sherlock_message}")
                                url_match = re.search(r'https://dc6\.sherlock-report\.at/r/[a-f0-9-]+-[a-f0-9]+', sherlock_message)
                                if url_match:
                                    report_url = url_match.group(0)
                                    logging.info(f"Найден URL отчёта в тексте: {report_url}")
                            if message.reply_markup:
                                markup = message.reply_markup
                                if hasattr(markup, 'rows'):
                                    for row in markup.rows:
                                        for button in row.buttons:
                                            if hasattr(button, 'url') and button.url:
                                                report_url = button.url
                                                logging.info(f"Найден URL отчёта: {report_url}")
                                                break
                                        if report_url:
                                            break
                        if report_url:
                            break
                    if report_url:
                        break
                    await asyncio.sleep(5)

                logging.info(f"Итоговый URL отчёта: {report_url}, Сообщение: {sherlock_message}")
                if sherlock_message:
                    formatted_message = f"📢 *Найдено*:\n\n_{sherlock_message}_"
                    await aiogram_message.answer(formatted_message, parse_mode="Markdown")
                if not report_url:
                    logging.warning("URL отчёта не получен в течение 120 секунд")
                    html_content = await generate_html_report(query, search_type=search_type, match_info="URL отчёта не получен")
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    with open(html_file, 'rb') as html_doc:
                        await aiogram_message.answer_document(html_doc, caption="📜 *Отчёт (ошибка)*", parse_mode="Markdown")
                    return

                html_content = await generate_html_report(query, report_url, search_type=search_type)
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                with open(html_file, 'rb') as html_doc:
                    await aiogram_message.answer_document(html_doc, caption="📜 *Отчёт* ✅", parse_mode="Markdown")
            finally:
                if os.path.exists("temp_report.html"):
                    os.remove("temp_report.html")
                if os.path.exists(html_file):
                    os.remove(html_file)
    except Exception as e:
        logging.error(f"Ошибка обработки запроса: {str(e)}")
        html_content = await generate_html_report(query, search_type=search_type, match_info=f"Ошибка: {str(e)}")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        with open(html_file, 'rb') as html_doc:
            await aiogram_message.answer_document(html_doc, caption="📜 *Отчёт (ошибка)*", parse_mode="Markdown")
        if os.path.exists(html_file):
            os.remove(html_file)

async def process_query_no_report(aiogram_message: types.Message, query: str, search_type: str):
    user_id = aiogram_message.from_user.id
    cursor.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, f"Поиск ({search_type}): {query}"))
    conn.commit()

    await aiogram_message.answer("⏳ *Обработка запроса...* 🔎", parse_mode="Markdown")
    try:
        async with client:
            source_entity = await client.get_entity("pal3vo_probivbot")
            logging.info(f"Источник данных найден: {source_entity.id}")

            formatted_query = f"/search {query}"
            logging.info(f"Отправка запроса '{formatted_query}'")
            sent_message = await client.send_message(source_entity, formatted_query)
            sent_message_id = sent_message.id
            sent_message_date = sent_message.date
            logging.info(f"Запрос отправлен, ID: {sent_message_id}, Дата: {sent_message_date}")

            timeout = 120
            start_time = asyncio.get_event_loop().time()
            sherlock_message = ""
            try:
                while asyncio.get_event_loop().time() - start_time < timeout:
                    messages = await client.get_messages(source_entity, limit=10, min_id=sent_message_id)
                    for message in messages:
                        if message.date >= sent_message_date and not message.out:
                            if message.text and not sherlock_message:
                                sherlock_message = message.text
                                sherlock_message = sherlock_message.replace("Интересовались этим: ", "")
                                sherlock_message = re.sub(r'[\*_`\[\]]', '', sherlock_message)
                                sherlock_message = sherlock_message.strip()
                                logging.info(f"Очищенное сообщение от Шерлока: {sherlock_message}")
                                break
                    if sherlock_message:
                        break
                    await asyncio.sleep(5)

                if sherlock_message:
                    formatted_message = f"📢 *Найдено*:\n\n_{sherlock_message}_"
                    await aiogram_message.answer(formatted_message, parse_mode="Markdown")
                else:
                    await aiogram_message.answer("❌ *Данные не получены* 🚫.", parse_mode="Markdown")
            finally:
                if os.path.exists("temp_report.html"):
                    os.remove("temp_report.html")
    except Exception as e:
        logging.error(f"Ошибка обработки запроса: {str(e)}")
        await aiogram_message.answer(f"❌ *Ошибка*: _{str(e)}_ 🚨", parse_mode="Markdown")

async def process_fio_query(aiogram_message: types.Message, query: str):
    user_id = aiogram_message.from_user.id
    html_file = f"report_fio_{user_id}.html"
    cursor.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, f"Поиск (fio): {query}"))
    conn.commit()

    await aiogram_message.answer("⏳ *Обработка запроса по ФИО...* 🔎", parse_mode="Markdown")
    try:
        async with client:
            if not client.is_connected():
                logging.info("Клиент не подключен, пытаемся подключиться...")
                await client.connect()
                if not client.is_connected():
                    logging.error("Не удалось подключиться к клиенту")
                    await aiogram_message.answer("❌ *Ошибка*: Не удалось подключиться к Telegram клиенту 🚨", parse_mode="Markdown")
                    return

            source_entity = await client.get_entity("pal3vo_probivbot")
            logging.info(f"Источник данных найден: {source_entity.id}")

            formatted_query = query
            logging.info(f"Отправка запроса '{formatted_query}'")
            sent_message = await client.send_message(source_entity, formatted_query)
            sent_message_id = sent_message.id
            sent_message_date = sent_message.date
            logging.info(f"Запрос отправлен, ID: {sent_message_id}, Дата: {sent_message_date}")

            timeout = 180
            start_time = asyncio.get_event_loop().time()
            country_selected = False
            report_url = None
            sherlock_message = ""
            try:
                while asyncio.get_event_loop().time() - start_time < timeout:
                    logging.info(f"Проверка новых сообщений, прошло {asyncio.get_event_loop().time() - start_time:.1f} сек")
                    messages = await client.get_messages(source_entity, limit=10, min_id=sent_message_id)
                    for message in messages:
                        logging.info(f"Получено сообщение ID {message.id}, Дата: {message.date}, Out: {message.out}, Текст: {message.text}")
                        if message.date >= sent_message_date and not message.out:
                            if not country_selected and message.reply_markup:
                                markup = message.reply_markup
                                country_button = None
                                if hasattr(markup, 'rows'):
                                    logging.info("Список всех кнопок в reply_markup:")
                                    for row_idx, row in enumerate(markup.rows):
                                        for btn_idx, button in enumerate(row.buttons):
                                            button_text = button.text.strip()
                                            button_data = getattr(button, 'data', None)
                                            logging.info(f"Кнопка [ряд {row_idx}, позиция {btn_idx}]: text='{button_text}', data={button_data}, url={getattr(button, 'url', None)}")
                                            if button_text == "Россия" and button_data:
                                                country_button = button
                                                logging.info(f"Кнопка 'Россия' найдена на ряду {row_idx}, позиция {btn_idx} с данными: {button_data}")
                                                break
                                        if country_button:
                                            break
                                if country_button and country_button.data:
                                    logging.info(f"Попытка нажатия на callback-кнопку 'Россия' с данными: {country_button.data}")
                                    try:
                                        await client(GetBotCallbackAnswerRequest(
                                            peer=source_entity,
                                            msg_id=message.id,
                                            data=country_button.data
                                        ))
                                        logging.info("Запрос на нажатие кнопки отправлен успешно")
                                        country_selected = True
                                        await asyncio.sleep(2)
                                    except Exception as e:
                                        logging.warning(f"Исключение при нажатии на кнопку 'Россия', но продолжаем: {str(e)}")
                                        country_selected = True
                                    continue
                            if message.text and not sherlock_message:
                                sherlock_message = message.text
                                sherlock_message = sherlock_message.replace("Интересовались этим: ", "")
                                sherlock_message = re.sub(r'[\*_`\[\]]', '', sherlock_message)
                                sherlock_message = sherlock_message.strip()
                                logging.info(f"Очищенное сообщение от Шерлока: {sherlock_message}")
                                url_match = re.search(r'https://dc6\.sherlock-report\.at/r/[a-f0-9-]+-[a-f0-9]+', sherlock_message)
                                if url_match and country_selected:
                                    report_url = url_match.group(0)
                                    logging.info(f"Найден URL отчёта в тексте: {report_url}")
                            if country_selected and message.reply_markup:
                                markup = message.reply_markup
                                if hasattr(markup, 'rows'):
                                    for row in markup.rows:
                                        for button in row.buttons:
                                            if hasattr(button, 'url') and button.url:
                                                report_url = button.url
                                                logging.info(f"Найден URL отчёта: {report_url}")
                                                break
                                        if report_url:
                                            break

                        if report_url:
                            break
                    if report_url:
                        break
                    await asyncio.sleep(5)

                logging.info(f"Итоговый URL отчёта: {report_url}, Сообщение: {sherlock_message}")
                if sherlock_message:
                    formatted_message = f"📢 *Найдено:*:\n\n_{sherlock_message}_"
                    await aiogram_message.answer(formatted_message, parse_mode="Markdown")
                if not report_url:
                    logging.warning("URL отчёта не получен в течение 180 секунд")
                    html_content = await generate_html_report(query, search_type="fio", match_info="URL отчёта не получен")
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    with open(html_file, 'rb') as html_doc:
                        await aiogram_message.answer_document(html_doc, caption="📜 *Отчёт (ошибка)*", parse_mode="Markdown")
                    return

                html_content = await generate_html_report(query, report_url, search_type="fio")
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                with open(html_file, 'rb') as html_doc:
                    await aiogram_message.answer_document(html_doc, caption="📜 *Отчёт* ✅", parse_mode="Markdown")
            finally:
                if os.path.exists("temp_report.html"):
                    os.remove("temp_report.html")
                if os.path.exists(html_file):
                    os.remove(html_file)
    except Exception as e:
        logging.error(f"Ошибка обработки запроса по ФИО: {str(e)}")
        html_content = await generate_html_report(query, search_type="fio", match_info=f"Ошибка: {str(e)}")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        with open(html_file, 'rb') as html_doc:
            await aiogram_message.answer_document(html_doc, caption="📜 *Отчёт (ошибка)*", parse_mode="Markdown")
        if os.path.exists(html_file):
            os.remove(html_file)

@dp.message_handler(lambda m: m.from_user.id != ADMIN_ID and m.text not in ["🔍 Поиск", "/search", "⬅ Назад", "🌐 Открыть Mini App"])
async def log_user_messages(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "-"
    full_name = message.from_user.full_name

    cursor.execute("SELECT approved FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        approved = row[0]
        cursor.execute("INSERT INTO logs (user_id, action) VALUES (?, ?)", (user_id, message.text))
        conn.commit()

        if approved:
            await message.answer("✅ *Доступ разрешён*. Добро пожаловать! 🌟", reply_markup=user_kb, parse_mode="Markdown")
        else:
            await message.answer("🔒 *Ваш доступ ещё не одобрен*. Ожидайте ⏳.", parse_mode="Markdown")
    else:
        cursor.execute("INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)", (user_id, username, full_name))
        conn.commit()
        await bot.send_message(ADMIN_ID, f"🔔 *Новый пользователь*: _{full_name}_ (@{username})", parse_mode="Markdown")
        await message.answer("🔒 *Доступ ограничен*. Ожидайте одобрения администратора 🕒.", parse_mode="Markdown")

if __name__ == '__main__':
    print("Бот запущен...")
    client.start()
    print("Клиент подключен")
    executor.start_polling(dp, skip_updates=True)