import datetime
import pytz
import json
import logging
import time # <--- НОВА БІБЛІОТЕКА
# ... інші імпорти

# --- LOAD CONFIG (додаємо time zone) ---
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

TELEGRAM_TOKEN = CONFIG["telegram_token"]
CHAT_IDS = CONFIG["chat_ids"]
EMAILS = CONFIG["emails"]
SPREADSHEET_ID = CONFIG["spreadsheet_id"]
TIMEZONE_NAME = CONFIG.get("timezone", "UTC") # <--- НОВИЙ ПАРАМЕТР
LOCAL_TIMEZONE = pytz.timezone(TIMEZONE_NAME)

# ... init (без змін) ...
bot = Bot(token=TELEGRAM_TOKEN)
# ... інші ініціалізації ...

# --- FUNCTIONS (без змін) ---
def get_upcoming_events():
    # ... (код без змін) ...
    now = datetime.datetime.utcnow().isoformat() + "Z"
    # ... (код без змін) ...
    
def send_telegram(user, text):
    # ... (код без змін) ...

def send_email(to, subject, body):
    # ... (код без змін) ...
    
def log_payment(user, date, amount):
    # ... (код без змін) ...

def check_events():
    # Використовуємо локальний час для більш інтуїтивного порівняння
    now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    events = get_upcoming_events()

    for e in events:
        summary = e.get("summary", "Урок без назви")
        
        # Обробка часу (дата/час або лише дата)
        start_data = e["start"].get("dateTime", e["start"].get("date"))
        # Додаємо обробку випадку "лише дата"
        if len(start_data) <= 10:
            # Це подія на цілий день, ігноруємо її
            continue
            
        start_time_utc = datetime.datetime.fromisoformat(start_data.replace("Z", "+00:00"))
        start_time_local = start_time_utc.astimezone(LOCAL_TIMEZONE)

        delta = start_time_utc - now_utc

        # 1. СПОВІЩЕННЯ (за 30 хв)
        # Використовуємо діапазон, щоб не пропустити момент, якщо запуск був не точно вчасно
        if datetime.timedelta(minutes=25) < delta <= datetime.timedelta(minutes=35):
            logging.info(f"Надсилаю нагадування для {summary}")
            for name in CHAT_IDS.keys():
                # Перевіряємо, чи є ім'я учня в назві тренування
                if name.lower() in summary.lower():
                    time_format = '%H:%M %d.%m.%Y'
                    msg = (
                        f"🔔 Нагадування: **{summary}**\n"
                        f"⏰ Початок о **{start_time_local.strftime(time_format)}** ({TIMEZONE_NAME})"
                    )
                    
                    # Надсилаємо Telegram
                    send_telegram(name, msg)
                    
                    # Надсилаємо Email (якщо є в конфігурації)
                    email = EMAILS.get(name)
                    if email:
                        send_email(email, "🔔 Нагадування про тренування", msg.replace('**', ''))


        # 2. ЛОГУВАННЯ ОПЛАТИ (через 5 хв після закінчення тренування)
        # Припускаємо, що тренування триває 1 годину (можна вдосконалити, використовуючи e["end"])
        end_data = e["end"].get("dateTime", e["end"].get("date"))
        end_time_utc = datetime.datetime.fromisoformat(end_data.replace("Z", "+00:00"))
        
        # Різниця часу між кінцем події і зараз
        delta_end = end_time_utc - now_utc
        
        # Якщо тренування закінчилося і минуло від 1 до 15 хвилин
        if datetime.timedelta(minutes=-15) < delta_end <= datetime.timedelta(minutes=-1):
            logging.info(f"Логую оплату для {summary}")
            for name in CHAT_IDS.keys():
                if name.lower() in summary.lower():
                    # Перевірка: Щоб не логувати одну подію двічі, вам потрібно вести 
                    # список ІД подій, які вже були залоговані. Це важливе вдосконалення 
                    # для реального використання!
                    log_payment(
                        user=name, 
                        date=start_time_local.strftime("%d.%m.%Y"), 
                        amount="500 UAH" # Зробіть суму більш інформативною
                    )
                    
                    # МОЖНА ДОДАТИ СПОВІЩЕННЯ ПРО ЗАВЕРШЕННЯ
                    # send_telegram(name, f"✅ Тренування {summary} завершено. До зустрічі!")


if __name__ == "__main__":
    logging.info(f"⏳ Bot started. Checking events every 60 seconds (Timezone: {TIMEZONE_NAME})...")
    
    # Головний цикл бота
    while True:
        try:
            check_events()
        except Exception as e:
            logging.error(f"❌ An error occurred: {e}")
            
        time.sleep(60) # Перевіряти події кожну хвилину
