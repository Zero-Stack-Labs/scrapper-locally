#!/usr/bin/env python3
import time
import json
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

try:
    import undetected_chromedriver as uc
    UNDETECTED_AVAILABLE = True
except ImportError:
    UNDETECTED_AVAILABLE = False
    print("⚠️ For better evasion, install: pip install undetected-chromedriver")


class GKEAntiDetectionExtractor:
    def __init__(self, use_undetected=True, headless=True):
        self.use_undetected = use_undetected and UNDETECTED_AVAILABLE
        self._captured_token = None
        self.driver = self.setup_driver(headless=headless)

    def setup_driver(self, headless: bool):
        if self.use_undetected:
            print("🔧 Using undetected-chromedriver for GKE...")
            options = uc.ChromeOptions()
            options.add_argument('--incognito')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_argument('--disable-javascript')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            driver = uc.Chrome(options=options, headless=headless, version_main=None)
            if headless:
                print("   - in headless mode optimized for GKE.")
        else:
            print("🔧 Using normal ChromeDriver with GKE optimizations...")
            options = Options()
            options.add_argument('--incognito')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            options.add_argument('--disable-images')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            if headless:
                print("   - in headless mode optimized for GKE.")
                options.add_argument('--headless=new')
            
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            realistic_user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
            
            options.add_argument(f"--user-agent={random.choice(realistic_user_agents)}")
            options.add_argument("--accept-language=en-US,en;q=0.9")
            options.add_argument("--accept-encoding=gzip, deflate, br")
            options.add_argument("--accept=text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8")
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        
        self._add_stealth_scripts(driver)
        return driver

    def _add_stealth_scripts(self, driver):
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        window.chrome = {
            runtime: {}
        };
        
        Object.defineProperty(navigator, 'permissions', {
            get: () => ({
                query: () => Promise.resolve({ state: 'granted' }),
            }),
        });
        """
        
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': stealth_js
        })

    def _human_like_delay(self, min_delay=0.5, max_delay=2.0):
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def _click_element(self, element):
        try:
            self._human_like_delay(0.3, 0.8)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(element))
            
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            self._human_like_delay(0.2, 0.5)
            
            element.click()
            print("✅ Click executed with human-like behavior.")
            return True
        except Exception as e:
            print(f"⚠️ Error clicking: {e}")
            return False

    def find_and_click_pagination(self, page_number=3):
        print(f"🔍 Looking for pagination link for page {page_number}...")
        try:
            wait = WebDriverWait(self.driver, 15)
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "nav.Pagination, nav[aria-label*='Pagination']")))
            
            self._human_like_delay(1.0, 2.0)
            
            strategy = f"//nav[contains(@class, 'Pagination')]//a[text()='{page_number}' and not(@aria-current='true')]"
            element = self.driver.find_element(By.XPATH, strategy)
            print(f"✅ Link found: '{element.text}'")
            return self._click_element(element)
        except (NoSuchElementException, TimeoutException):
            print(f"❌ Link not found for page {page_number}.")
            return False
        except Exception as e:
            print(f"⚠️ Unexpected error in pagination: {e}")
            return False
            
    def _wait_for_search_token(self, timeout=25):
        print("🕵️‍♂️ Listening to network traffic for token (extended timeout for GKE)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                logs = self.driver.get_log('performance')
                for log_entry in logs:
                    log = json.loads(log_entry['message'])['message']
                    
                    if log['method'] == 'Network.requestWillBeSent':
                        url = log['params'].get('request', {}).get('url', '')
                        if '/products/v3/search' in url:
                            headers = log['params'].get('request', {}).get('headers', {})
                            if 'x-kpsdk-ct' in headers:
                                self._captured_token = headers['x-kpsdk-ct']
                                print("✅✅ Token 'x-kpsdk-ct' found.")
                                return True
            except Exception:
                pass
            time.sleep(0.5)
        
        print("⚠️ Search request with token not found in network logs.")
        return False

    def _handle_consent_with_retries(self, max_retries=3):
        for attempt in range(max_retries):
            try:
                agree_button = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((By.ID, "touAgreeBtn"))
                )
                print(f"✅ Consent button found on attempt {attempt + 1}. Clicking...")
                if self._click_element(agree_button):
                    return True
            except TimeoutException:
                if attempt == 0:
                    print("INFO: Consent button not found (or not necessary).")
                return True
            except Exception as e:
                print(f"⚠️ Error handling consent on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    self._human_like_delay(1.0, 2.0)
        return False

    def get_token(self, target_url: str, max_retries=3):
        for attempt in range(max_retries):
            try:
                print(f"🚀 Starting GKE token extraction attempt {attempt + 1} from: {target_url}")
                
                self.driver.get(target_url)
                self._human_like_delay(2.0, 4.0)
                
                self._handle_consent_with_retries()
                self._human_like_delay(1.0, 2.0)

                print("🧹 Clearing network logs before action...")
                self.driver.get_log('performance')
                
                if self.find_and_click_pagination(page_number=3):
                    if self._wait_for_search_token(timeout=25):
                        print(f"✅ Token successfully extracted on attempt {attempt + 1}")
                        return self._captured_token
                    else:
                        print(f"❌ Token not captured on attempt {attempt + 1}")
                else:
                    print(f"❌ Pagination action failed on attempt {attempt + 1}")

                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 3-5 seconds...")
                    self._human_like_delay(3.0, 5.0)

            except Exception as e:
                print(f"❌ Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 3-5 seconds...")
                    self._human_like_delay(3.0, 5.0)
        
        print("❌ All attempts failed to extract token")
        return self._captured_token

    def close(self):
        if self.driver:
            self.driver.quit()
            print("✅ Browser closed.") 