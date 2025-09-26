import os
import json
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- EMAIL CONFIG FROM ENVIRONMENT ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", SENDER_EMAIL)

# Create data directory for JSON files
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# ========== YOUR SCRAPER FUNCTIONS (unchanged except for file paths) ==========

def load_seen_tenders(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

def save_seen_tenders(filename, tenders):
    with open(filename, 'w') as f:
        json.dump(tenders, f)

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print(f"Email sent: {subject}")
    except Exception as e:
        print(f"Error sending email: {e}")

# ----------------------------
# Put your parse_xxx() functions here unchanged
# (parse_giz, parse_geda, parse_mahaurja, parse_hppcl)
# ----------------------------

# Example websites definition (point JSON to data dir):
websites = [
    {
        'name': 'GIZ',
        'url': 'https://www.giz.de/en/live-tenders-giz-india#live-tenders',
        'filename': os.path.join(DATA_DIR, 'giz_tenders.json'),
        'parse_func': 'parse_giz'
    },
    {
        'name': 'GEDA',
        'url': 'https://geda.gujarat.gov.in/tenders.html',
        'filename': os.path.join(DATA_DIR, 'geda_tenders.json'),
        'parse_func': 'parse_geda'
    },
    {
        'name': 'MAHAURJA',
        'url': 'https://www.mahaurja.com/tenders',
        'filename': os.path.join(DATA_DIR, 'mahaurja_tenders.json'),
        'parse_func': 'parse_mahaurja'
    },
    {
        'name': 'HPPCL',
        'url': 'https://www.hppcl.in/page/tenders.aspx',
        'filename': os.path.join(DATA_DIR, 'hppcl_tenders.json'),
        'parse_func': 'parse_hppcl'
    }
]

def scrape_website(website):
    try:
        print(f"Scraping {website['name']}...")
        response = requests.get(website['url'], timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        parse_func = globals()[website['parse_func']]
        current_tenders = parse_func(soup)

        seen_tenders = load_seen_tenders(website['filename'])
        new_tenders = []
        seen_urls = {s['url'] for s in seen_tenders}

        for t in current_tenders:
            if t['url'] not in seen_urls:
                new_tenders.append(t)

        if new_tenders:
            body_lines = [f"{t['title']}\n{t['url']}\n" for t in new_tenders]
            body = "\n".join(body_lines)
            send_email(f"New Tenders from {website['name']}", body)

            updated_tenders = seen_tenders + new_tenders
            save_seen_tenders(website['filename'], updated_tenders)
            print(f"Found {len(new_tenders)} new tenders on {website['name']}")
        else:
            print(f"No new tenders found on {website['name']}")
    except Exception as e:
        print(f"Error scraping {website['name']}: {e}")

def main():
    for website in websites:
        scrape_website(website)

if __name__ == "__main__":
    main()
