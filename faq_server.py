from flask import Flask, request, jsonify
import requests
from datetime import datetime
import pytz
import json
import os

app = Flask(__name__)

from flask_cors import CORS
CORS(app, origins=['*'])

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
WORK_START = 0  # 00:00 по Москве (24 часа для тестирования)
WORK_END = 24    # 24:00 по Москве (24 часа для тестирования)
PENDING_FILE = 'pending_questions.json'

def send_telegram(text):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    resp = requests.post(url, json={'chat_id': CHAT_ID, 'text': text})
    return resp.ok

def save_pending(text):
    if os.path.exists(PENDING_FILE):
        with open(PENDING_FILE, 'r', encoding='utf-8') as f:
            pending = json.load(f)
    else:
        pending = []
    moscow = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow)
    time_str = now.strftime('%d.%m.%Y %H:%M:%S')
    pending.append({'text': text, 'time': time_str})
    with open(PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)

def send_all_pending():
    if not os.path.exists(PENDING_FILE):
        return
    with open(PENDING_FILE, 'r', encoding='utf-8') as f:
        pending = json.load(f)
    sent = []
    for item in pending:
        ok = send_telegram(f"[ОТЛОЖЕННЫЙ ВОПРОС]\n{item['text']}\n(Получен: {item['time']})")
        if ok:
            sent.append(item)
    # Удаляем отправленные
    if sent:
        pending = [item for item in pending if item not in sent]
        with open(PENDING_FILE, 'w', encoding='utf-8') as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

@app.route('/send-to-telegram', methods=['POST', 'OPTIONS'])
def send_to_telegram():
    # Обработка CORS preflight запроса
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        return response
    
    data = request.get_json()
    text = data.get('text', '')
    moscow = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow)
    hour = now.hour
    if WORK_START <= WORK_END:
        # Обычный день (например, 9-18)
        if hour < WORK_START or hour >= WORK_END:
            save_pending(text)
            response = jsonify({'status': 'off_hours', 'message': 'Вопрос сохранён и будет отправлен оператору в рабочее время (10:00–19:00 МСК).'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
    else:
        # Ночная смена (например, 22-6)
        if hour < WORK_START and hour >= WORK_END:
            save_pending(text)
            response = jsonify({'status': 'off_hours', 'message': 'Вопрос сохранён и будет отправлен оператору в рабочее время (10:00–19:00 МСК).'})
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
    ok = send_telegram(text)
    if ok:
        response = jsonify({'status': 'ok', 'message': 'Вопрос отправлен оператору!'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    else:
        save_pending(text)
        response = jsonify({'status': 'fail', 'message': 'Не удалось отправить в Telegram, вопрос сохранён.'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("ОШИБКА: Не установлены переменные окружения TELEGRAM_TOKEN и CHAT_ID")
        exit(1)
    print("Проверяем отложенные вопросы...")
    send_all_pending()
    print("Сервер запущен!")
    app.run(host='0.0.0.0', port=8080)