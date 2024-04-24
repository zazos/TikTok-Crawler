import json
import os
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import random
import time
from fake_useragent import UserAgent
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import traceback

# user agent rotation
ua = UserAgent()
user_agent = ua.random
USER_AGENTS = [ua.random for _ in range(10)]

def save_cookies(driver, path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, 'w') as file:
        json.dump(driver.get_cookies(), file)
        
def load_cookies(driver, path):
    if not os.path.exists(path):
        print("No cookies file found at specified path. Continuing without loading cookies.")
        return
    
    print("Loading cookies..")
    with open(path, 'r') as file:
        cookies = json.load(file)
        for cookie in cookies:
            if 'expiry' in cookie:
                cookie['expiry'] = int(cookie['expiry']) # Selenium expects expiry to be an integer
            driver.add_cookie(cookie)
            
# delays between requests
def human_like_delay(min_delay=6, max_delay=15):
    delay = random.uniform(min_delay, max_delay)
    print(f"Waiting for {delay:.2f} seconds.")
    time.sleep(delay)
    
def get_driver_with_random_user_agent():
    # Set up the Chrome WebDriver with a random User-Agent
    user_agent = random.choice(USER_AGENTS)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument(f'user-agent={user_agent}')
    options.add_argument('--mute-audio')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def check_user_agent():
    driver = get_driver_with_random_user_agent()
    try:
        driver.get("https://www.whatsmyua.info/")
        ua_element = driver.find_element(By.ID, 'custom-ua-string')
        current_ua = ua_element.text
        print(f"Current User-Agent: {current_ua}")
    finally:
        driver.quit()

# check_user_agent()
    
def extract_tiktok_info(container):
    video_info = {}
    # Extract video hashtags
    video_desc_container = container.find('div', attrs={'data-e2e': 'video-desc'})
    if video_desc_container:
        anchor_tags = video_desc_container.find_all('a', attrs={'data-e2e': 'search-common-link'})
        hashtags = [a['href'].split('/')[-1] for a in anchor_tags]
        video_info['hashtags'] = hashtags

    # Extract video engagement metrics
    buttons = container.find_all('button', {'aria-label': True})
    for button in buttons:
        if 'like' in button['aria-label'].lower():
            video_info['likes'] = button.find('strong').text if button.find('strong') else 'N/A'
        elif 'comment' in button['aria-label'].lower():
            video_info['comments'] = button.find('strong').text if button.find('strong') else 'N/A'
        elif 'share' in button['aria-label'].lower():
            video_info['shares'] = button.find('strong').text if button.find('strong') else 'N/A'
            
    return video_info

def manage_request_rate(request_count, request_threshold):
    request_count += 1
    if request_count % request_threshold == 0:
        print(f"Reached {request_threshold} requests, taking a longer break...")
        human_like_delay(30, 60)
    else:
        human_like_delay()
    return request_count
    
        
def scrape_fyp():
    driver = get_driver_with_random_user_agent()
    # load_cookies(driver, 'cookies/cookies.txt')
    video_data = []
    seen_containers = set() # keep track of seen containers to avoid duplicates
    request_count = 0
    request_threshold = 10
    
    try:
        wait = WebDriverWait(driver, 45)
        driver.get('https://www.tiktok.com/foryou')
        
        while len(video_data) < 25:
            # Scroll to the bottom of the page to load more videos
            action = ActionChains(driver)
            action.send_keys(Keys.END).perform()
            action.reset_actions()
            human_like_delay()
            
            wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@data-e2e='recommend-list-item-container']")))
            soup = BeautifulSoup(driver.page_source, 'lxml')
            containers = soup.find_all('div', {'data-e2e': 'recommend-list-item-container'})
            
            for container in containers:
                # Generate a unique identifier for each container (e.g., based on its content)
                container_id = hash(str(container))
                if container_id not in seen_containers:
                    seen_containers.add(container_id)
                    video_info = extract_tiktok_info(container)
                    video_data.append(video_info)
            request_count = manage_request_rate(request_count, request_threshold)
            
            if len(video_data) >= 25:
                break
            print(f"Collected data for {len(video_data)} videos so far.")

            
    except Exception as e:
        print(f"ERROR: ")
        traceback.print_exc()
    finally:
        # save_cookies(driver, 'cookies/cookies.txt')
        driver.quit()
        
    return video_data


engagement_metrics_per_video = scrape_fyp()
for video in engagement_metrics_per_video:
    print(f"Hashtags: {video.get('hashtags')}")
    print(f"Likes: {video.get('likes')}")
    print(f"Comments: {video.get('comments')}")
    print(f"Shares: {video.get('shares')}\n")
