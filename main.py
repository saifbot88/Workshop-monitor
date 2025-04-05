import requests, json, time, os, ssl
import smtplib
from bs4 import BeautifulSoup
from flask import Flask, request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

app = Flask(__name__)

WORKSHOP_URL = "https://asdps.rdd.edu.iq/resources/workshops"
WORKSHOP_BASE = "https://asdps.rdd.edu.iq/resources/workshops/"

TELEGRAM_TOKEN = os.getenv("Telegram_bot_token")
CHAT_ID = os.getenv("telegram_chat_id")
EMAIL_FROM = os.getenv("Email_address")
EMAIL_PASSWORD = os.getenv("email_password")
EMAIL_TO = "showursmile88@gmail.com"

ssl._create_default_https_context = ssl._create_unverified_context

monitoring_enabled = True

registration_log_file = "registration_log.json"

def send_telegram(text):
    if not CHAT_ID or not TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram error:", e)

def notify_all(msg, send_to_email=True):
    send_telegram(msg)

def get_current_workshops():
    try:
        response = requests.get(WORKSHOP_URL, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.select(".views-row .title a")
    except Exception as e:
        print("Error fetching workshops:", e)
        return []

def save_registration_log(data):
    with open(registration_log_file, "w") as f:
        json.dump(data, f, indent=2)

def load_registration_log():
    if not os.path.exists(registration_log_file):
        return {}
    with open(registration_log_file, "r") as f:
        return json.load(f)

def workshop_monitor():
    global monitoring_enabled
    try:
        with open("state.json", "r") as f:
            old = json.load(f)
    except:
        old = {}

    registration_log = load_registration_log()

    while True:
        if not monitoring_enabled:
            time.sleep(5)
            continue

        new = {}
        links = get_current_workshops()
        msg = ""

        for link in links:
            href = link["href"]
            wid = href.split("/")[-1]
            new[wid] = {
                "text": link.text.strip(),
                "url": WORKSHOP_BASE + wid
            }
            if wid not in old:
                msg += f"\n🔔 *ورشة جديدة:*\n{link.text.strip()}\n{WORKSHOP_BASE + wid}\n\n"
                registration_log[wid] = {
                    "title": link.text.strip(),
                    "url": WORKSHOP_BASE + wid,
                    "timestamp": datetime.now().isoformat()
                }

        if msg:
            notify_all(msg, send_to_email=False)
            with open("state.json", "w") as f:
                json.dump(new, f)
            save_registration_log(registration_log)

        time.sleep(900)  # كل 15 دقيقة

@app.route("/telegram", methods=["POST"])
def telegram_webhook():
    global monitoring_enabled
    data = request.json
    msg = data.get("message", {})
    text = msg.get("text", "")
    chat_id = str(msg.get("chat", {}).get("id"))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if chat_id != CHAT_ID:
        send_telegram("🚫 هذا البوت مخصص لحساب مصرح به فقط.")
        return "", 200

    text = text.lower().strip()

    if text == "/status":
        status_msg = "🤖 البوت يعمل الآن ويُراقب الورش." if monitoring_enabled else "⛔️ البوت متوقف مؤقتًا عن المراقبة."
        send_telegram(f"{status_msg}\n🕓 التاريخ والوقت: {now}")
    elif text == "/stop":
        monitoring_enabled = False
        send_telegram("⛔️ تم إيقاف مراقبة الورش مؤقتاً ورح ننتظرك ترجعلنا مهندسنا الرائع")
    elif text == "/start":
        monitoring_enabled = True
        send_telegram("✅ تم استئناف مراقبة الورش وتدلل علينا مهندسنا الغالي")
    elif text == "/log":
        reg_log = load_registration_log()
        if not reg_log:
            send_telegram("📭 لا يوجد سجل ورشات مسجلة حالياً.")
        else:
            send_telegram("🧪 *سجل الورش المسجلة:*")
            for wid, item in reg_log.items():
                send_telegram(f"📝 *{item['title']}*\n🔗 {item['url']}\n🕓 {item['timestamp']}")

    return "", 200

@app.route("/")
def home():
    return "✅ Bot is alive and monitoring workshops..."

if __name__ == "__main__":
    send_telegram("🤖 تم تشغيل سكربت مراقبة الورش الآن بنجاح على Replit")
    import threading
    threading.Thread(target=workshop_monitor).start()
    app.run(host="0.0.0.0", port=8080)
