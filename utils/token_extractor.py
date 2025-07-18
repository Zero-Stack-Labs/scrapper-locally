#!/usr/bin/env python3
import time
import json
import random
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
    print("⚠️ Para mejor evasión, instala: pip install undetected-chromedriver")


class AntiDetectionExtractor:
    def __init__(self, use_undetected=True, headless=True):
        self.use_undetected = use_undetected and UNDETECTED_AVAILABLE
        self._captured_token = None
        self.driver = self.setup_driver(headless=headless)

    def setup_driver(self, headless: bool):
        if self.use_undetected:
            print("🔧 Usando undetected-chromedriver...")
            options = uc.ChromeOptions()
            options.add_argument('--incognito')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--window-size=1920,1080')
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Set Chrome binary path for containerized environments
            import os
            chrome_binary = os.environ.get('CHROME_BIN') or os.environ.get('CHROME_PATH')
            if chrome_binary:
                options.binary_location = chrome_binary
                print(f"   - usando Chrome binary: {chrome_binary}")
            
            try:
                driver = uc.Chrome(options=options, headless=headless)
                if headless:
                    print("   - en modo headless.")
            except Exception as e:
                print(f"❌ Error con undetected-chromedriver: {e}")
                print("🔄 Fallback a ChromeDriver normal...")
                self.use_undetected = False
                return self.setup_driver(headless)
        else:
            print("🔧 Usando ChromeDriver normal con evasión avanzada...")
            options = Options()
            options.add_argument('--incognito')
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")
            options.add_argument("--window-size=1920,1080")
            
            if headless:
                print("   - en modo headless.")
                options.add_argument('--headless=new')
            
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
            options.add_argument("--accept-language=en-US,en;q=0.9,es-US;q=0.8,es;q=0.7")
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Set Chrome binary path for containerized environments
            import os
            chrome_binary = os.environ.get('CHROME_BIN') or os.environ.get('CHROME_PATH')
            if chrome_binary:
                options.binary_location = chrome_binary
                print(f"   - usando Chrome binary: {chrome_binary}")
            
            # Use system chromedriver if available, otherwise download
            chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
            if chromedriver_path and os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
                print(f"   - usando chromedriver del sistema: {chromedriver_path}")
            else:
                service = Service(ChromeDriverManager().install())
                print("   - descargando chromedriver...")
            driver = webdriver.Chrome(service=service, options=options)
        return driver

    def _click_element(self, element):
        try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(element))
            element.click()
            print("✅ Click ejecutado.")
            return True
        except Exception as e:
            print(f"⚠️ Error al hacer click: {e}")
            return False

    def find_and_click_pagination(self, page_number=3):
        print(f"🔍 Buscando el enlace de paginación para la página {page_number}...")
        try:
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "nav.Pagination, nav[aria-label*='Pagination']")))
            strategy = f"//nav[contains(@class, 'Pagination')]//a[text()='{page_number}' and not(@aria-current='true')]"
            element = self.driver.find_element(By.XPATH, strategy)
            print(f"✅ Enlace encontrado: '{element.text}'")
            return self._click_element(element)
        except (NoSuchElementException, TimeoutException):
            print(f"❌ No se encontró el enlace para la página {page_number}.")
            return False
        except Exception as e:
            print(f"⚠️ Error inesperado en paginación: {e}")
            return False
            
    def _wait_for_search_token(self, timeout=15):
        print("🕵️‍♂️ Escuchando el tráfico de red en busca del token...")
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
                                print("✅✅ Token 'x-kpsdk-ct' encontrado.")
                                return True
            except Exception:
                pass
            time.sleep(0.5)
        
        print("⚠️ No se encontró la petición de búsqueda con el token en los logs de red.")
        return False

    def get_token(self, target_url: str):
        try:
            print(f"🚀 Iniciando extracción rápida de token desde: {target_url}")
            
            self.driver.get(target_url)
            
            try:
                agree_button = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "touAgreeBtn")))
                print("✅ Botón de consentimiento encontrado. Haciendo click...")
                self._click_element(agree_button)
            except TimeoutException:
                print("INFO: No se encontró el botón de consentimiento (o no fue necesario).")

            print("🧹 Limpiando logs de red antes de la acción...")
            self.driver.get_log('performance')
            
            if self.find_and_click_pagination(page_number=3):
                if not self._wait_for_search_token(timeout=15):
                    print("❌ No se capturó el token después del click de paginación.")
            else:
                print("❌ La acción de paginación falló. No se pudo generar la petición.")

        except Exception as e:
            print(f"❌ Error catastrófico durante la extracción: {e}")
        
        return self._captured_token

    def close(self):
        if self.driver:
            self.driver.quit()
            print("✅ Navegador cerrado.")