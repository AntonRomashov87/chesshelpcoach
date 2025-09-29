import datetime
import pytz
import json
import logging
from telegram import Bot
from googleapiclient.discovery import build
from google.oauth2 import service_account
from email.mime.text import MIMEText
import base64

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- LOAD CONFIG ---
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

TELEGRAM_TOKEN = CONFIG["telegram_token"]
CHAT_IDS = CONFIG["chat_ids"]  # {"Анна": 123456789, "Олег": 987654321}
EMAILS = CONFIG["emails"]      # {"Анна": "anna@example.com"}
SPREADSHEET_ID = CONFIG["spreadsheet_id"]

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send"
]
SERVICE_ACCOUNT_FILE = "credentials.json"

# --- INIT ---
bot = Bot(token=TELEGRAM_TOKEN)
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
calendar_service = build("calendar", "v3", credentials=creds)
sheets_service = build("sheets", "v4", credentials=creds)
gmail_service = build("gmail", "v1", credentials=creds)

# --- FUNCTIONS ---
def get_upcoming_events():
    now = datetime.datetime.utcnow().isoformat() + "Z"
    events_result = calendar_service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=10,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    return events_result.get("items", [])

def send_telegram(user, text):
    chat_id = CHAT_IDS.get(user)
    if chat_id:
        bot.send_message(chat_id=chat_id, text=text)

def send_email(to, subject, body):
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()

def log_payment(user, date, amount):
    values = [[user, date, amount]]
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="A:C",
        valueInputOption="RAW",
        body={"values": values}
    ).execute()

def check_events():
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
    events = get_upcoming_events()

    for e in events:
        summary = e.get("summary", "Урок без назви")
        start_str = e["start"].get("dateTime", e["start"].get("date"))
        start_time = datetime.datetime.fromisoformat(start_str.replace("Z", "+00:00"))

        delta = start_time - now

        # 30 хв до уроку
        if datetime.timedelta(minutes=29) < delta <= datetime.timedelta(minutes=30):
            for name in CHAT_IDS.keys():
                if name in summary:
                    msg = f"🔔 Нагадування: {summary} о {start_time.strftime('%H:%M %d.%m.%Y')}"
                    send_telegram(name, msg)
                    send_email(EMAILS[name], "Нагадування про урок", msg)

        # після уроку (якщо минуло більше 5 хв)
        if datetime.timedelta(minutes=-5) <= delta <= datetime.timedelta(minutes=0):
            for name in CHAT_IDS.keys():
                if name in summary:
                    log_payment(name, start_time.strftime("%d.%m.%Y"), "500")  # сума умовна

if __name__ == "__main__":
    logging.info("⏳ Bot started...")
    check_events()
