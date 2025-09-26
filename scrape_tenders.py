import os
import json
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Configuration (environment variables) ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", SENDER_EMAIL)

# Directory to store tender JSON files
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# --- Parser Functions ---
def parse_giz(soup):
    tenders = []
    section = soup.find('section', id='live-tenders')
    if section:
        ul = section.find('ul')
        if ul:
            for li in ul.find_all('li', recursive=False):
                a = li.find('a')
                if a and a.get('href'):
                    href = a.get('href').strip()
                    text = a.get_text(strip=True)
                    if text and not href.startswith('#') and not href.lower().startswith('mailto:'):
                        if href.startswith('/'):
                            href = 'https://www.giz.de' + href
                        tenders.append({'title': text, 'url': href})
    return tenders

def parse_geda(soup):
    tenders = []
    for a in soup.select('table a'):
        href = a.get('href')
        text = a.get_text(strip=True)
        if href and text:
            href = href.strip()
            if not href.startswith('#') and not href.lower().startswith('mailto:'):
                if href.startswith('/'):
                    href = 'https://geda.gujarat.gov.in' + href
                tenders.append({'title': text, 'url': href})
    return tenders

def parse_mahaurja(soup):
    tenders = []
    # try known selectors
    for a in soup.select('table a, div a'):
        href = a.get('href')
        text = a.get_text(strip=True)
        if href and text:
            href = href.strip()
            if not href.startswith('#') and not href.lower().startswith('mailto:'):
                if href.startswith('/'):
                    href = 'https://www.mahaurja.com' + href
                tenders.append({'title': text, 'url': href})
    return tenders

def parse_hppcl(soup):
    tenders = []
    for table in soup.find_all('table'):
        if table.find('a'):
            for a in table.select('a'):
                href = a.get('href')
                text = a.get_text(strip=True)
                if href and text:
                    href = href.strip()
                    if not href.startswith('#') and not href.lower().startswith('mailto:'):
                        if href.startswith('/'):
                            href = 'https://www.hppcl.in' + href
                        tenders.append({'title': text, 'url': href})
    return tenders

# --- Utility Functions ---
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
            body_lines = []
            for tender in new_tenders:
                body_lines.append(f"{tender['title']}\n{tender['url']}\n")
            body = "\n".join(body_lines)
            send_email(f"New Tenders from {website['name']}", body)

            # update seen
            updated_tenders = seen_tenders + new_tenders
            save_seen_tenders(website['filename'], updated_tenders)
            print(f"Found {len(new_tenders)} new tenders on {website['name']}")
        else:
            print(f"No new tenders found on {website['name']}")

    except Exception as e:
        print(f"Error scraping {website['name']}: {e}")

# --- Websites ---
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

def main():
    for website in websites:
        scrape_website(website)

if __name__ == "__main__":
    main()
