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

# Suppress the InsecureRequestWarning for websites with certificate issues
warnings.simplefilter('ignore', InsecureRequestWarning)

# --- Configuration (environment variables) ---
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
APP_PASSWORD = os.environ.get("APP_PASSWORD")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", SENDER_EMAIL)

# Directory to store tender JSON files
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


# A list of all websites to track. Add or remove entries as needed.
WEBSITES = [
    {
        "name": "GIZ",
        "url": "https://www.giz.de/en/live-tenders-giz-india#live-tenders",
        "dynamic": False
    },
    {
        "name": "GEDA",
        "url": "https://geda.gujarat.gov.in/geda/2018/5/30/Live%20Tenders/6207",
        "dynamic": False
    },
    {
        "name": "MAHAURJA",
        "url": "https://www.mahaurja.com/meda/en/tender",
        "dynamic": False
    },
    {
        "name": "HPPCL",
        "url": "https://hppcl.in/content/650_1_tender.aspx",
        "dynamic": False
    },
    {
        "name": "HAREDA",
        "url": "https://hareda.gov.in/tenders/",
        "dynamic": False
    },
    {
        "name": "BREDA",
        "url": "https://breda.co.in/livetender.aspx",
        "dynamic": False
    },
    {
        "name": "TGREDCO",
        "url": "https://tgredco.telangana.gov.in/Default.aspx",
        "dynamic": False
    },
    {
        "name": "SECI",
        "url": "https://www.seci.co.in/tenders",
        "dynamic": False
    },
    {
        "name": "NIWE",
        "url": "https://niwe.res.in/Tenders/tender_data/",
        "dynamic": False
    },
    {
        "name": "IREDA",
        "url": "https://www.ireda.in/tender",
        "dynamic": False
    },
    {
        "name": "NISE",
        "url": "https://nise.res.in/notices/",
        "dynamic": False
    },
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
    # --- New Website Entry for MAHAPREIT ---
    {
        "name": "MAHAPREIT",
        "url": "https://mahapreit.in/page/tender",
        "dynamic": False
    }
]

# --- Scraping Functions (BeautifulSoup) ---

def get_giz_tenders(url):
    """Scrapes the GIZ tenders page for all tender details."""
    tender_list = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the GIZ URL: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    tender_list_element = soup.find('h2', string='Live Tenders').find_next_sibling('ul')
    if tender_list_element:
        tender_items = tender_list_element.find_all('li')
        for item in tender_items:
            link = item.find('a')
            if link:
                tender_list.append({
                    'title': link.get_text(strip=True),
                    'url': link.get('href')
                })
    return tender_list

def get_geda_tenders(url):
    """Scrapes the GEDA tenders page for all tender details."""
    tender_list = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the GEDA URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    content_block = soup.find('div', class_='content-block')
    if content_block:
        tender_paragraphs = content_block.find_all('p')
        for p in tender_paragraphs:
            link = p.find('a')
            if link and link.get('href'):
                href = link.get('href')
                base_url = "https://geda.gujarat.gov.in"
                full_url = href if href.startswith(('http://', 'https://')) else f"{base_url}{href}"
                tender_list.append({
                    'title': link.get_text(strip=True),
                    'url': full_url
                })
    return tender_list

def get_mahaurja_tenders(url):
    """
    Scrapes the MahaUrja tenders page, including all paginated pages,
    and returns a complete list of tender details.
    """
    tender_list = []
    page_url = url
    while page_url:
        print(f"Scraping page: {page_url}")
        try:
            response = requests.get(page_url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error during page scrape: {e}")
            break
        
        soup = BeautifulSoup(response.content, 'html.parser')
        first_title_tag = soup.find('th', class_='text-align-justify')

        if not first_title_tag:
            print("Could not find any tender title elements on the page.")
            break

        main_table = first_title_tag.find_parent('table')
        if main_table:
            for row in main_table.find_all('tr'):
                try:
                    title_tag = row.find('th', class_='text-align-justify')
                    link_tag = row.find('a', href=re.compile(r'\.pdf$', re.IGNORECASE))
                    if title_tag and link_tag and link_tag.get('href'):
                        title = title_tag.get_text(strip=True)
                        href = link_tag.get('href')
                        base_url = "https://www.mahaurja.com"
                        full_url = requests.compat.urljoin(base_url, href)
                        tender_list.append({
                            'title': title,
                            'url': full_url
                        })
                except (AttributeError, IndexError):
                    continue
        else:
            print("Could not find the main tender table on the page.")
            break

        next_link = soup.find('a', string=re.compile('Next', re.IGNORECASE))
        if next_link and next_link.get('href'):
            page_url = requests.compat.urljoin(url, next_link.get('href'))
        else:
            page_url = None
            print("Pagination complete. No more pages to scrape.")
    
    return tender_list

def get_hppcl_tenders(url):
    """Fetches the HPPCL webpage and extracts all tenders."""
    tender_list = []
    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the HPPCL URL: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    tenders_table = soup.find('table', {'id': 'cphmain_grdTenders'})
    if tenders_table:
        for row in tenders_table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) > 2:
                try:
                    title = cells[2].text.strip()
                    tender_list.append({'title': title, 'url': url})
                except IndexError:
                    continue
    return tender_list

def get_hareda_tenders(url):
    """
    Scrapes the HAREDA tenders page for all tender details.
    """
    tender_list = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the HAREDA URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    tenders_table = None
    for table in soup.find_all('table'):
        header = table.find('th', string=re.compile('Title', re.I))
        if header:
            tenders_table = table
            break
    
    if not tenders_table:
        print("HAREDA: Could not find the tenders table on the page.")
        return []
    
    for row in tenders_table.find_all('tr')[1:]:
        cells = row.find_all('td')
        if len(cells) > 1:
            try:
                title_cell = cells[0] if cells[0].get_text(strip=True) else cells[1]
                title = title_cell.get_text(strip=True)
                link_element = row.find('a', href=True)
                href = link_element.get('href') if link_element else '#'
                base_url = "https://hareda.gov.in"
                full_url = href if href.startswith(('http://', 'https://')) else f"{base_url}{href}"
                tender_list.append({
                    'title': title,
                    'url': full_url
                })
            except (IndexError, AttributeError):
                continue
    return tender_list

def get_breda_tenders(url):
    """
    Scrapes the BREDA website for all tender details.
    This site uses ASP.NET and displays tenders in a table.
    """
    tender_list = []
    try:
        response = requests.get(url, verify=False, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the BREDA URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    tenders_table = soup.find('table', {'id': 'ContentPlaceHolder1_GridView1'})

    if tenders_table:
        for row in tenders_table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) > 2:
                try:
                    title = cells[2].get_text(strip=True)
                    download_link_element = None
                    for cell in cells[2:]:
                        link = cell.find('a', href=re.compile(r'\.pdf$', re.I))
                        if link:
                            download_link_element = link
                            break
                    
                    href = download_link_element.get('href') if download_link_element else '#'
                    
                    base_url = "https://breda.co.in/"
                    full_url = href if href.startswith(('http://', 'https://')) else f"{base_url}{href}"
                    
                    tender_list.append({
                        'title': title,
                        'url': full_url
                    })
                except (IndexError, AttributeError):
                    continue
    return tender_list

def get_tgredco_tenders(url):
    """
    Scrapes the TGREDCO tenders page for all tender details.
    """
    tender_list = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the TGREDCO URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    tenders_container = soup.find('div', id='tenders')
    
    if not tenders_container:
        print("Tenders container not found. The website structure may have changed.")
        return []
        
    tender_cards = tenders_container.find_all('div', class_='col-lg-12 tenders')
    
    if not tender_cards:
        print("No tender cards found with the specified class.")
        return []
        
    for card in tender_cards:
        main_title_tag = card.find('p', class_='text-black font-size-14px mt-lg-3 mb-lg-0 mt-3')
        link_tags = card.find_all('a', href=re.compile(r'updates?|tenders?|circulars?|doc|pdf|word', re.IGNORECASE))
        tender_id_tag = card.find('h6', class_='small text-black')
        
        # The logic to combine the title pieces
        main_title = main_title_tag.get_text(strip=True) if main_title_tag else ""
        tender_id = tender_id_tag.get_text(strip=True) if tender_id_tag else ""
        
        # Remove any "new-gif" alt text that might appear
        if "new-gif.gif" in main_title:
            main_title = main_title.replace("new-gif", "").strip()

        # Construct a more descriptive base title
        if main_title and tender_id:
            base_title = f"{main_title} ({tender_id})"
        elif main_title:
            base_title = main_title
        elif tender_id:
            base_title = f"Tender ID: {tender_id}"
        else:
            base_title = "No Title Found"

        if not link_tags:
            continue

        for link in link_tags:
            href = link.get('href')
            full_url = requests.compat.urljoin(url, href)
            
            # Use the link text as the title if it's not a generic phrase.
            link_text = link.get_text(strip=True)
            if link_text and link_text.lower() not in ["click here", "read more"]:
                final_title = link_text
            else:
                # Fallback: use the base title and add the filename for uniqueness.
                filename = os.path.basename(href)
                final_title = f"{base_title} - {filename}"
                
            tender_list.append({
                'title': final_title,
                'url': full_url
            })
    
    return tender_list

# ... (rest of the code remains the same) ...

def get_seci_tenders(url):
    """
    Scrapes the SECI tenders page for all tender details.
    """
    tender_list = []
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the SECI URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    tenders_table = soup.find('table', {'id': 'tender-list'})

    if tenders_table:
        for row in tenders_table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) > 4:
                try:
                    title = cells[4].get_text(strip=True)
                    link = cells[-1].find('a')
                    href = link.get('href') if link else None
                    
                    if href:
                        full_url = requests.compat.urljoin(url, href)
                        tender_list.append({
                            'title': title,
                            'url': full_url
                        })
                except (IndexError, AttributeError):
                    continue
    return tender_list


def get_ireda_tenders(url):
    """Scrapes the IREDA tenders page for all tender details."""
    tender_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the URL for IREDA: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    tender_header = soup.find('th', string=re.compile('Title', re.I))
    
    if tender_header:
        tenders_table = tender_header.find_parent('table')
        if tenders_table:
            for row in tenders_table.find_all('tr')[1:]:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    try:
                        title = cells[1].get_text(strip=True)
                        link = cells[2].find('a')
                        href = link.get('href') if link else None
                        
                        if href:
                            full_url = requests.compat.urljoin(url, href)
                            tender_list.append({
                                'title': title,
                                'url': full_url
                            })
                    except (IndexError, AttributeError):
                        continue
    return tender_list

def get_niwe_tenders(url):
    """
    Scrapes the NIWE tenders page for all tender details across all pages.
    """
    tender_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    page_number = 1
    while True:
        page_url = f"{url}?page={page_number}"
        print(f"Scraping page: {page_url}")
        
        try:
            response = requests.get(page_url, timeout=10, headers=headers, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            tenders_table = soup.find('table', class_='tender-table')
            
            current_page_tenders = []
            if tenders_table and tenders_table.find_all('tr'):
                for row in tenders_table.find_all('tr')[1:]:
                    cells = row.find_all('td')
                    if len(cells) >= 5:
                        try:
                            title = cells[1].get_text(strip=True)
                            link = cells[4].find('a')
                            href = link.get('href') if link else None
                            
                            if href:
                                full_url = requests.compat.urljoin(url, href)
                                current_page_tenders.append({
                                    'title': title,
                                    'url': full_url
                                })
                        except (IndexError, AttributeError):
                            continue
            
            if not current_page_tenders:
                print(f"No tenders found on page {page_number}. Ending pagination.")
                break
            
            tender_list.extend(current_page_tenders)
            
            pagination_container = soup.find('ul', class_='pagination-list')
            if pagination_container:
                next_page_link = pagination_container.find('a', string=lambda text: text and text.isdigit() and int(text) > page_number)
                if not next_page_link:
                    print(f"Reached the last page ({page_number}) based on pagination links. Ending pagination.")
                    break
            else:
                print("No pagination container found. Assuming single page. Ending pagination.")
                break
            
            page_number += 1
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching the URL: {e}")
            break
        except Exception as e:
            print(f"An error occurred during scraping: {e}")
            break
            
    return tender_list

def get_nise_tenders(url):
    """
    Scrapes the NISE tenders page for all tender details.
    """
    tender_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    try:
        response = requests.get(url, timeout=10, headers=headers, verify=False)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the NISE URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    tenders_table = soup.find('table', id='exampleTender')
    if tenders_table:
        for row in tenders_table.find('tbody').find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                try:
                    title_cell = cells[2]
                    link = title_cell.find('a')
                    if link and link.get('href'):
                        title = link.get_text(strip=True)
                        href = link.get('href')
                        tender_pattern = re.compile(r'tender|eoi|rfp|bid|quotation|proposal|corrigendum', re.I)
                        if tender_pattern.search(title):
                            full_url = requests.compat.urljoin(url, href)
                            tender_list.append({
                                'title': title,
                                'url': full_url
                            })
                except (IndexError, AttributeError):
                    continue
    return tender_list
    
def get_mahapreit_tenders(url):
    """Scrapes all pages of the MAHAPREIT tenders section for all tender details."""
    tender_list = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    page_url = url
    
    while page_url:
        print(f"Scraping page: {page_url}")
        try:
            response = requests.get(page_url, timeout=10, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching the MAHAPREIT URL: {e}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        tender_blocks = soup.find_all('div', class_='post-item')
        
        for block in tender_blocks:
            try:
                title_tag = block.find('h3').find('a')
                title = title_tag.get_text(strip=True) if title_tag else "No Title Found"
                
                link_tag = block.find('a', string='Download')
                href = link_tag.get('href') if link_tag else None
                
                if href:
                    full_url = requests.compat.urljoin(url, href)
                    tender_list.append({
                        'title': title,
                        'url': full_url
                    })
            except (IndexError, AttributeError):
                continue
        
        pagination_container = soup.find('div', class_='pagination')
        next_link_element = pagination_container.find('a', string=re.compile('Next', re.I)) if pagination_container else None
        
        if next_link_element and next_link_element.get('href'):
            page_url = requests.compat.urljoin(url, next_link_element.get('href'))
        else:
            print("No 'Next' button found. Ending pagination.")
            page_url = None
    
    return tender_list

# --- GTAI Scraper (updated) ---
def get_gtai_tenders(url):
    """
    Scrapes the GTAI search page using Selenium, handling pagination by clicking
    the "next page" button.
    """
    tender_list = []
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    
    try:
        print("Navigating to the initial GTAI URL...")
        driver.get(url)
        
        # Wait for the first page to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'li.result-item'))
        )
        
        while True:
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            tender_items = soup.find_all('li', class_='result-item')
            
            for item in tender_items:
                content_div = item.find('div', class_='content')
                if content_div:
                    link_tag = content_div.find('a', href=True)
                    if link_tag:
                        title = link_tag.get_text(strip=True)
                        href = link_tag['href']
                        base_url = "https://www.gtai.de"
                        full_url = f"{base_url}{href}"
                        
                        tender_list.append({
                            'title': title,
                            'url': full_url
                        })

            # Check for the next page button
            try:
                # Find the 'Next page' link
                next_page_link = driver.find_element(By.CSS_SELECTOR, 'li.result-index-forward a')
                
                # Use JavaScript to click the button to avoid interception issues
                driver.execute_script("arguments[0].click();", next_page_link)
                
                print("Clicked the next page button using JavaScript.")
                
                # Wait for a new result to appear on the new page
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'li.result-item'))
                )
            
            except NoSuchElementException:
                print("No more pages found for GTAI. Reached the end of pagination.")
                break
            except ElementClickInterceptedException as e:
                print(f"Caught an element click interception error for GTAI: {e}. Stopping.")
                break
            except Exception as e:
                print(f"An error occurred while trying to paginate GTAI: {e}")
                break
                
    except Exception as e:
        print(f"An error occurred during GTAI scraping: {e}")
    finally:
        driver.quit()
        
    return tender_list

# --- NEW ADB Scraper ---
def get_adb_tenders(url):
    """
    Scrapes the ADB tenders page using Selenium to handle dynamic content and pagination.
    """
    tender_list = []
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    max_retries = 3

    try:
        print("Navigating to the initial ADB URL...")
        driver.get(url)
        
        print("Waiting for the page to be fully ready...")
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )

        try:
            cookie_accept_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, 'onetrust-accept-btn-handler'))
            )
            cookie_accept_button.click()
            print("Accepted cookies.")
        except (TimeoutException, NoSuchElementException):
            print("No cookie consent banner found or it was already dismissed.")
        except Exception as e:
            print(f"Error handling cookie banner: {e}")
        
        page_number = 1
        
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.item.linked'))
            )
        except TimeoutException:
            print("Initial wait for tender items timed out. The page may not have loaded correctly.")
            return []

        while True:
            if page_number > 20:
                print("Reached page 20. Ending scraper as requested.")
                break
            
            try:
                print(f"Scraping page {page_number}...")
                
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.item.linked'))
                )

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                tender_items = soup.find_all('div', class_='item linked')
                
                if not tender_items:
                    print(f"No tenders found on page {page_number}. Ending pagination.")
                    break

                for item in tender_items:
                    title_tag = item.find('div', class_='item-title')
                    link_tag = item.find('a', href=True)

                    if title_tag and link_tag:
                        title = title_tag.get_text(strip=True)
                        href = link_tag['href']
                        base_url = "https://www.adb.org"
                        full_url = requests.compat.urljoin(base_url, href)
                        
                        tender_list.append({
                            'title': title,
                            'url': full_url
                        })
                
                next_page_link = driver.find_element(By.CSS_SELECTOR, 'a[title="Go to next page"]')
                
                if 'disabled' in next_page_link.find_element(By.XPATH, './..').get_attribute('class'):
                    print("Next button is disabled. Reached the end.")
                    break
                
                print(f"Found next page button. Clicking for page {page_number + 1}...")

                first_item_on_page = driver.find_element(By.CSS_SELECTOR, 'div.item.linked')
                
                driver.execute_script("arguments[0].click();", next_page_link)
                
                WebDriverWait(driver, 20).until(EC.staleness_of(first_item_on_page))
                
                page_number += 1
            
            except NoSuchElementException:
                print("No more pages found. Reached the end of pagination.")
                break
            except Exception as e:
                retries = 0
                while retries < max_retries:
                    print(f"An unexpected error occurred during pagination for page {page_number}: {e}. Retrying... (Attempt {retries + 1}/{max_retries})")
                    try:
                        driver.refresh()
                        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.item.linked')))
                        print(f"Successfully refreshed and re-attempting to scrape page {page_number}.")
                        break
                    except Exception as refresh_error:
                        retries += 1
                        print(f"Refresh failed: {refresh_error}. Retrying...")
                
                if retries == max_retries:
                    print(f"Failed to recover from error after {max_retries} retries on page {page_number}. Ending scraper.")
                    break

    except Exception as e:
        print(f"An error occurred during scraping: {e}")
    finally:
        driver.quit()
        
    return tender_list


# --- Scraping Functions (Selenium) ---

def get_dynamic_tenders(url, wait_selector, title_selector, link_selector):
    """
    Uses Selenium to scrape tenders from a dynamic website.
    """
    tender_list = []
    
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        items = soup.select(wait_selector)
        
        for item in items:
            title_tag = item.select_one(title_selector)
            link_tag = item.select_one(link_selector)

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                href = link_tag.get('href')
                
                full_url = requests.compat.urljoin(url, href)
                
                if "RRECL" in url and title == full_url:
                    continue

                tender_list.append({
                    'title': title,
                    'url': full_url
                })
        
    except Exception as e:
        print(f"An error occurred during Selenium scraping for {url}: {e}")
    finally:
        driver.quit()
        
    return tender_list

# --- File and Email Handling ---

def load_seen_tenders(filename, website_name):
    """Loads previously seen tenders for a specific website from a single file."""
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
    """Saves the current list of tenders for a specific website to a single file."""
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
    """Sends an email using the specified credentials."""
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
    """Helper function to call the correct scraper based on website type."""
    # Special case for websites that need their own tailored function
    if website['name'] == "GTAI":
        return get_gtai_tenders(website['url'])
    if website['name'] == "ADB":
        return get_adb_tenders(website['url'])

    if website['dynamic']:
        # Use the unified Selenium scraper for dynamic sites
        return get_dynamic_tenders(
            website['url'],
            website['wait_selector'],
            website['title_selector'],
            website['link_selector']
        )
    else:
        # Use the specific BeautifulSoup scraper for static sites
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
    """Main function to check for new tenders across all websites."""
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
