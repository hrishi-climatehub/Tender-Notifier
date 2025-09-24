import requests
from bs4 import BeautifulSoup
import smtplib
import os
import json
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
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Suppress SSL warnings
warnings.simplefilter('ignore', InsecureRequestWarning)

# --- Configuration ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", SENDER_EMAIL)
APP_PASSWORD = os.environ.get("APP_PASSWORD")
TENDERS_DATA_FILE = "all_tenders_data.json"

# --- Helper for webdriver ---
def get_chrome_driver(options):
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- Website List ---
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

# --- Individual Scraper Functions ---
def generic_bs4_scraper(url, site_name):
    tenders = []
    try:
        r = requests.get(url, verify=False, timeout=20)
        soup = BeautifulSoup(r.content, "html.parser")
        for a in soup.find_all("a", href=True):
            tenders.append({"title": a.get_text(strip=True), "url": a["href"]})
    except Exception as e:
        print(f"Error in {site_name}:", e)
    return tenders

def get_giz_tenders(url): return generic_bs4_scraper(url, "GIZ")
def get_geda_tenders(url): return generic_bs4_scraper(url, "GEDA")
def get_mahaurja_tenders(url): return generic_bs4_scraper(url, "MAHAURJA")
def get_hppcl_tenders(url): return generic_bs4_scraper(url, "HPPCL")
def get_hareda_tenders(url): return generic_bs4_scraper(url, "HAREDA")
def get_breda_tenders(url): return generic_bs4_scraper(url, "BREDA")
def get_tgredco_tenders(url): return generic_bs4_scraper(url, "TGREDCO")
def get_seci_tenders(url): return generic_bs4_scraper(url, "SECI")
def get_niwe_tenders(url): return generic_bs4_scraper(url, "NIWE")
def get_ireda_tenders(url): return generic_bs4_scraper(url, "IREDA")
def get_nise_tenders(url): return generic_bs4_scraper(url, "NISE")
def get_mahapreit_tenders(url): return generic_bs4_scraper(url, "MAHAPREIT")

# --- Dynamic Scrapers with safe error handling ---
def get_gtai_tenders(url):
    tenders = []
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = get_chrome_driver(options)
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.result-item"))
            )
        except TimeoutException:
            print(f"Timeout on GTAI ({url}), skipping.")
            return []
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for item in soup.select("li.result-item a[href]"):
            tenders.append({"title": item.get_text(strip=True), "url": f"https://www.gtai.de{item['href']}"})
    except Exception as e:
        print("Error in GTAI:", e)
    finally:
        driver.quit()
    return tenders

def get_adb_tenders(url):
    tenders = []
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = get_chrome_driver(options)
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.item.linked"))
            )
        except TimeoutException:
            print(f"Timeout on ADB ({url}), skipping.")
            return []
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for item in soup.select("div.item.linked div.item-title a[href]"):
            tenders.append({"title": item.get_text(strip=True), "url": f"https://www.adb.org{item['href']}"})
    except Exception as e:
        print("Error in ADB:", e)
    finally:
        driver.quit()
    return tenders

def get_dynamic_tenders(url, wait_selector, title_selector, link_selector):
    tenders = []
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = get_chrome_driver(options)
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
            )
        except TimeoutException:
            print(f"Timeout on dynamic site ({url}), skipping.")
            return []
        soup = BeautifulSoup(driver.page_source, "html.parser")
        for item in soup.select(title_selector):
            link_tag = item if item.name == "a" else item.find("a")
            if link_tag and link_tag.has_attr("href"):
                tenders.append({"title": item.get_text(strip=True), "url": link_tag["href"]})
    except Exception as e:
        print(f"Error in dynamic scraper {url}: {e}")
    finally:
        driver.quit()
    return tenders

# --- File and Email Handling ---
def load_seen_tenders(filename, website_name):
    if not os.path.exists(filename) or os.stat(filename).st_size == 0:
        return set()
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            return {t['title'] for t in data.get(website_name, [])}
    except Exception as e:
        print("Error loading JSON:", e)
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
    except Exception as e:
        print("Error saving JSON:", e)

def send_email(subject, body):
    if not (SENDER_EMAIL and APP_PASSWORD):
        print("Missing email credentials, skipping email.")
        return
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
        print("Error sending email:", e)

# --- Router ---
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
    if website['name'] == "GIZ":
        return get_giz_tenders(website['url'])
    if website['name'] == "GEDA":
        return get_geda_tenders(website['url'])
    if website['name'] == "MAHAURJA":
        return get_mahaurja_tenders(website['url'])
    if website['name'] == "HPPCL":
        return get_hppcl_tenders(website['url'])
    if website['name'] == "HAREDA":
        return get_hareda_tenders(website['url'])
    if website['name'] == "BREDA":
        return get_breda_tenders(website['url'])
    if website['name'] == "TGREDCO":
        return get_tgredco_tenders(website['url'])
    if website['name'] == "SECI":
        return get_seci_tenders(website['url'])
    if website['name'] == "NIWE":
        return get_niwe_tenders(website['url'])
    if website['name'] == "IREDA":
        return get_ireda_tenders(website['url'])
    if website['name'] == "NISE":
        return get_nise_tenders(website['url'])
    if website['name'] == "MAHAPREIT":
        return get_mahapreit_tenders(website['url'])
    return []

# --- Main ---
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
            email_body += f"--- {website['name']} ---\nNo tenders found or error.\n\n"
            continue

        seen_titles = load_seen_tenders(TENDERS_DATA_FILE, website['name'])
        new_tenders = [t for t in all_tenders if t['title'] not in seen_titles]

        email_body += f"--- {website['name']} ---\n"
        if new_tenders:
            all_new_tenders_found = True
            email_body += f"Found {len(new_tenders)} new tender(s):\n"
            for tender in new_tenders:
                email_body += f"- {tender['title']}\n  {tender['url']}\n"
            email_body += "\n"
        else:
            email_body += "No new tenders.\n\n"

        save_seen_tenders(all_tenders, TENDERS_DATA_FILE, website['name'])

    if all_new_tenders_found:
        send_email("Daily Tender Alert: New Tenders Found", email_body)
    else:
        print("No new tenders found across all websites.")

if __name__ == "__main__":
    main()
