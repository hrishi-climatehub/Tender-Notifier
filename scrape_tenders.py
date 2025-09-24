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

# (keep your WEBSITES list unchanged)

# -------------------------------------------------
# Replace in every Selenium function:
# driver = webdriver.Chrome(options=options)
# with:
# driver = get_chrome_driver(options)
# -------------------------------------------------

# Example for GTAI:
def get_gtai_tenders(url):
    tender_list = []
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = get_chrome_driver(options)

    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'li.result-item'))
        )
        while True:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_items = soup.find_all('li', class_='result-item')
            for item in tender_items:
                link_tag = item.find('a', href=True)
                if link_tag:
                    tender_list.append({
                        'title': link_tag.get_text(strip=True),
                        'url': f"https://www.gtai.de{link_tag['href']}"
                    })
            try:
                next_page_link = driver.find_element(By.CSS_SELECTOR, 'li.result-index-forward a')
                driver.execute_script("arguments[0].click();", next_page_link)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'li.result-item'))
                )
            except NoSuchElementException:
                break
    finally:
        driver.quit()
    return tender_list

# Do the same replacement for:
# - get_adb_tenders
# - get_dynamic_tenders
# (other BeautifulSoup-only scrapers don’t need changes)

# --- File and Email Handling, Main Logic ---
# (unchanged, except using env vars for email credentials)

def send_email(subject, body):
    if not (SENDER_EMAIL and APP_PASSWORD):
        print("Missing email credentials; skipping email.")
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
        print(f"Error sending email: {e}")

# main() function stays the same
if __name__ == "__main__":
    main()
