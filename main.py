
import requests
from bs4 import BeautifulSoup
import json
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

USERNAME = "saif.hallem@uomustansiriyah.edu.iq"
PASSWORD = "Adam@adam15"
LOGIN_URL = "https://asdps.rdd.edu.iq/login"
WORKSHOPS_URL = "https://asdps.rdd.edu.iq/resources/workshops"
WORKSHOP_BASE = "https://asdps.rdd.edu.iq/resources/workshops/"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

session = requests.Session()

def send_telegram(text):
    if not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data)

def send_email(subject, body):
    msg = MIMEText(body, 'plain')
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
        server.quit()
    except Exception as e:
        print("Email sending failed:", e)

def login():
    r = session.get(LOGIN_URL, verify=False)
    soup = BeautifulSoup(r.text, "html.parser")
    token_input = soup.find("input", {"name": "_token"})
    if not token_input:
        print("❌ Could not find _token. Site structure may have changed.")
        return False
    token = token_input["value"]
    payload = {
        "_token": token,
        "email": USERNAME,
        "password": PASSWORD
    }
    res = session.post(LOGIN_URL, data=payload, verify=False)
    return "لوحة التحكم" in res.text

def fetch_workshops():
    r = session.get(WORKSHOPS_URL, verify=False)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.find_all("tr")
    data = {}
    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 10:
            continue
        wid = cols[0].text.strip()
        active = "color: green" in str(cols[0])
        reg_text = cols[5].text.strip()
        data[wid] = {"active": active, "reg": reg_text}
    return data

def get_details(wid):
    url = WORKSHOP_BASE + wid
    r = session.get(url, verify=False)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.find_all("tr")
    info = {"url": url, "id": wid}
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 2:
            k = cols[0].text.strip()
            v = cols[1].text.strip()
            info[k] = v
    info["online"] = info.get("هل الورشة الالكترونية؟", "") == "✓"
    info["place"] = info.get("مكان اقامة الورشة", "")
    info["title"] = info.get("اسم الورشة", "No title")
    info["lecturer"] = info.get("محاضر", "Unknown")
    info["units"] = info.get("الوحدات", "?")
    info["time"] = info.get("تاريخ بدء", "")
    info["registered"] = info.get("المسجلين", "?")
    info["status"] = info.get("التسجيل", "")
    return info

def try_register(wid):
    try:
        url = f"{WORKSHOP_BASE}{wid}/register"
        r = session.post(url, verify=False)
        return r.status_code == 200
    except:
        return False

def notify_all(msg):
    send_telegram(msg)
    send_email("Workshop Update", msg)

def main():
    if not login():
        print("❌ Login failed.")
        return
    print("✅ Logged in. Monitoring started.")
    try:
        with open("state.json", "r") as f:
            old = json.load(f)
    except:
        old = {}

    while True:
        new = fetch_workshops()
        for wid in new:
            if wid not in old or new[wid] != old[wid]:
                details = get_details(wid)
                msg = f"📢 Workshop Update:\n"
                msg += f"🧾 Title: {details['title']}\n"
                msg += f"👤 Lecturer: {details['lecturer']}\n"
                msg += f"📅 Date: {details['time']}\n"
                msg += f"🧮 Units: {details['units']}\n"
                msg += f"📍 Type: {'Online' if details['online'] else 'In-person'}\n"
                msg += f"🔗 Link: {details['url']}\n"
                if details['online']:
                    msg += f"💻 Meet Link: {details['place']}\n"
                if new[wid]["active"] and details["status"] == "ليس مسجلاً بعد" and details["online"]:
                    if try_register(wid):
                        msg += "✅ Auto-registered successfully.\n"
                    else:
                        msg += "⚠️ Could not auto-register.\n"
                notify_all(msg)
        with open("state.json", "w") as f:
            json.dump(new, f)
        time.sleep(600)

if __name__ == "__main__":
    main()
