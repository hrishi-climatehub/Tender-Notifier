import requests
from bs4 import BeautifulSoup
import smtplib
import os
import json
import re
import warnings
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib3.exceptions import InsecureRequestWarning

# --- Selenium imports ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

# Suppress the InsecureRequestWarning for websites with certificate issues
warnings.simplefilter('ignore', InsecureRequestWarning)

# --- Configuration ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", SENDER_EMAIL)
APP_PASSWORD = os.environ.get("APP_PASSWORD")
TENDERS_DATA_FILE = "all_tenders_data.json"

# A list of all websites to track. Add or remove entries as needed.
WEBSITES = [
    {"name": "GIZ", "url": "https://www.giz.de/en/live-tenders-giz-india#live-tenders", "dynamic": False},
    {"name": "GEDA", "url": "https://geda.gujarat.gov.in/geda/2018/5/30/Live%20Tenders/6207", "dynamic": False},
    {"name": "MAHAURJA", "url": "https://www.mahaurja.com/meda/en/tender", "dynamic": False},
    {"name": "HPPCL", "url": "https://hppcl.in/content/650_1_tender.aspx", "dynamic": False},
    {"name": "HAREDA", "url": "https://hareda.gov.in/tenders/", "dynamic": False},
    {"name": "BREDA", "url": "https://breda.co.in/livetender.aspx", "dynamic": False},
    {"name": "TGREDCO", "url": "https://tgredco.telangana.gov.in/Default.aspx", "dynamic": False},
    {"name": "SECI", "url": "https://www.seci.co.in/tenders", "dynamic": False},
    {"name": "NIWE", "url": "https://niwe.res.in/Tenders/tender_data/", "dynamic": False},
    {"name": "IREDA", "url": "https://www.ireda.in/tender", "dynamic": False},
    {"name": "NISE", "url": "https://nise.res.in/notices/", "dynamic": False},
    {
        "name": "ADB",
        "url": "https://www.adb.org/projects/tenders/country/india/sector/energy-1059",
        "dynamic": True,
        "wait_selector": "div.item.linked",
        "title_selector": "div.item-title",
        "link_selector": "a"
    },
    {
        "name": "GTAI",
        "url": "https://www.gtai.de/en/meta/search/66080!search;eNqVkUFOw0AMRe_idZCARaXmAFwAdoiF47hlqokd7JlCqHp3JiBYgEBm5xk9-_t_n2CHxMWhP8FQPQm7X6Axrh_OmanwCP39Qwf8QvmjIjlADygLnDuwOliibzhst5vNNfzeRVql2BJW8YaoeZjP-ByfPTMlzGGeSUWnH57_MFu96BRffpcEhdjCDfMjOsfX0Wlu5U07wYglqcSdH1nK3TLzP-5miePOvQ6HRsWTUpuwROevSeGeb9NrM3B12cET9FJzbrpqTRSc1Bg6aLG8W2QZPwlD2fMXXnDl18f5_Ab6yBAMM?facets%5Bcountry%5D.tf=3120",
        "dynamic": True,
        "wait_selector": "li.result-item",
        "title_selector": "div.content > a",
        "link_selector": "a"
    },
    {
        "name": "RRECL",
        "url": "https://energy.rajasthan.gov.in/rrecl/#/pages/sm/tender-list/49147/197/0",
        "dynamic": True,
        "wait_selector": "a.tender-link",
        "title_selector": "a.tender-link",
        "link_selector": "a.tender-link"
    },
    {"name": "MAHAPREIT", "url": "https://mahapreit.in/page/tender", "dynamic": False}
]

# --- Selenium Chrome driver helper ---
def get_chrome_driver(options):
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- Scraping Functions ---
# (⚠️ To save space, I won’t re-explain each, but they are the same as your colleague’s version.
# I’ve only changed driver instantiations to use get_chrome_driver(options).)

# Paste of all scraping functions (get_giz_tenders, get_geda_tenders, ..., get_mahapreit_tenders, get_gtai_tenders, get_adb_tenders, get_dynamic_tenders)
# ... (functions are exactly as in your colleague’s file, except every `webdriver.Chrome(options=options)` is replaced with `get_chrome_driver(options)`)

# --- File and Email Handling ---
def load_seen_tenders(filename, website_name):
    if not os.path.exists(filename) or os.stat(filename).st_size == 0:
        return set()
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            return {t['title'] for t in data.get(website_name, [])}
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading seen tenders from file '{filename}': {e}")
        return set()

def save_seen_tenders(tenders, filename, website_name):
    try:
        if os.path.exists(filename) and os.stat(filename).st_size > 0:
            with open(filename, "r") as f:
                data = json.load(f)
        else:
            data = {}
        data[website_name] = tenders
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
        print("Tenders saved successfully.")
    except IOError as e:
        print(f"Error saving seen tenders to file '{filename}': {e}")

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("Email alert sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

# --- Main Logic ---
def get_all_tenders_for_website(website):
    if website['name'] == "GTAI":
        return get_gtai_tenders(website['url'])
    if website['name'] == "ADB":
        return get_adb_tenders(website['url'])

    if website['dynamic']:
        return get_dynamic_tenders(
            website['url'],
            website['wait_selector'],
            website['title_selector'],
            website['link_selector']
        )
    else:
        if website['name'] == "GIZ":
            return get_giz_tenders(website['url'])
        elif website['name'] == "GEDA":
            return get_geda_tenders(website['url'])
        elif website['name'] == "MAHAURJA":
            return get_mahaurja_tenders(website['url'])
        elif website['name'] == "HPPCL":
            return get_hppcl_tenders(website['url'])
        elif website['name'] == "HAREDA":
            return get_hareda_tenders(website['url'])
        elif website['name'] == "BREDA":
            return get_breda_tenders(website['url'])
        elif website['name'] == "TGREDCO":
            return get_tgredco_tenders(website['url'])
        elif website['name'] == "SECI":
            return get_seci_tenders(website['url'])
        elif website['name'] == "NIWE":
            return get_niwe_tenders(website['url'])
        elif website['name'] == "IREDA":
            return get_ireda_tenders(website['url'])
        elif website['name'] == "MAHAPREIT":
            return get_mahapreit_tenders(website['url'])
        elif website['name'] == "NISE":
            return get_nise_tenders(website['url'])
    return []

def main():
    if not (SENDER_EMAIL and APP_PASSWORD):
        print("Missing SENDER_EMAIL or APP_PASSWORD in environment. Exiting.")
        return

    all_new_tenders_found = False
    email_body = "Hello,\n\nHere is a summary of new tenders:\n\n"

    for website in WEBSITES:
        print(f"Checking for new tenders on {website['name']}...")
        all_tenders = get_all_tenders_for_website(website)

        if not all_tenders:
            email_body += f"--- {website['name']} ---\n"
            email_body += "No tenders were found on the website or an error occurred.\n\n"
            continue

        seen_tenders_titles = load_seen_tenders(TENDERS_DATA_FILE, website['name'])
        new_tenders = [t for t in all_tenders if t['title'] not in seen_tenders_titles]

        email_body += f"--- {website['name']} ---\n"
        if new_tenders:
            all_new_tenders_found = True
            email_body += f"Found {len(new_tenders)} new tender(s):\n"
            for tender in new_tenders:
                email_body += f"- Title: {tender['title']}\n"
                email_body += f"  URL: {tender['url']}\n"
            email_body += "\n"
        else:
            email_body += "No new tenders found.\n\n"

        save_seen_tenders(all_tenders, TENDERS_DATA_FILE, website['name'])

    if all_new_tenders_found:
        send_email(f"Daily Tender Alert: New Tenders Found", email_body)
    else:
        print("No new tenders found across all websites.")

if __name__ == "__main__":
    main()
