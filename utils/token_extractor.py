#!/usr/bin/env python3
"""
Extractor anti-detección avanzado para obtener tokens de seguridad de FootLocker.
Requiere: pip install selenium webdriver-manager undetected-chromedriver
"""

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
    """
    Una clase para extraer el token de seguridad 'x-kpsdk-ct' de sitios
    protegidos por Akamai, como FootLocker.
    """
    def __init__(self, use_undetected=True, headless=True):
        self.use_undetected = use_undetected and UNDETECTED_AVAILABLE
        self._captured_token = None
        self.driver = self.setup_driver(headless=headless)

    def setup_driver(self, headless: bool):
        """Configura y devuelve un driver de Selenium con opciones de evasión."""
        if self.use_undetected:
            print("🔧 Usando undetected-chromedriver...")
            options = uc.ChromeOptions()
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            driver = uc.Chrome(options=options, headless=headless)
            if headless:
                print("   - en modo headless.")
        else:
            print("🔧 Usando ChromeDriver normal con evasión avanzada...")
            options = Options()
            if headless:
                print("   - en modo headless.")
                options.add_argument('--headless=new')
                options.add_argument('--disable-gpu')
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36")
            options.add_argument("--accept-language=en-US,en;q=0.9,es-US;q=0.8,es;q=0.7")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        return driver

    def human_like_delay(self, min_seconds=0.5, max_seconds=2.0):
        """Pausa la ejecución con un tiempo de espera de aspecto humano."""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def simulate_page_browsing(self):
        """Simula una navegación realista haciendo scroll suave por la página."""
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            self.human_like_delay(0.5, 1.0)
            
            scroll_increment = 300
            current_position = 0
            max_scroll = self.driver.execute_script("return document.body.scrollHeight")
            
            while current_position < max_scroll:
                self.driver.execute_script(f"window.scrollBy(0, {scroll_increment});")
                current_position += scroll_increment
                self.human_like_delay(0.4, 0.8)
                max_scroll = self.driver.execute_script("return document.body.scrollHeight")

            self.human_like_delay(1.5, 2.5)
            self.driver.execute_script("window.scrollTo(0, 0);")
            self.human_like_delay(1.0, 2.0)
        except Exception as e:
            print(f"⚠️ Error en navegación de scroll: {e}")

    def realistic_click(self, element):
        """Realiza un click realista sobre un elemento, con validaciones."""
        try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(element))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", element)
            self.human_like_delay(1.0, 2.0)
            element.click()
            print("✅ Click realista ejecutado")
            return True
        except Exception as e:
            print(f"⚠️ Error en click: {e}")
            try:
                self.human_like_delay(0.5, 1.0)
                self.driver.execute_script("arguments[0].click();", element)
                print("✅ Click JavaScript como fallback")
                return True
            except Exception as e2:
                print(f"❌ Error en fallback de click: {e2}")
                return False

    def find_and_click_pagination(self, page_number=3):
        """Encuentra y hace clic en un número de página específico."""
        print(f"🔍 Buscando el enlace de paginación para la página {page_number}...")
        try:
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "nav.Pagination, nav[aria-label*='Pagination']")))
            strategy = f"//nav[contains(@class, 'Pagination')]//a[text()='{page_number}' and not(@aria-current='true')]"
            element = self.driver.find_element(By.XPATH, strategy)
            print(f"✅ Enlace encontrado: '{element.text}' -> {element.get_attribute('href')}")
            return self.realistic_click(element)
        except (NoSuchElementException, TimeoutException):
            print(f"❌ No se encontró el enlace para la página {page_number}.")
            return False
        except Exception as e:
            print(f"⚠️ Error inesperado en paginación: {e}")
            return False
            
    def _wait_for_search_token(self, timeout=20):
        """Escucha el tráfico de red y extrae el header 'x-kpsdk-ct' de la petición de búsqueda."""
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
                                print(f"✅✅ Token 'x-kpsdk-ct' encontrado.")
                                return True
            except Exception:
                pass # Ignorar errores de parsing de logs
            self.human_like_delay(0.5, 0.5)
        
        print("⚠️ No se encontró la petición de búsqueda con el token en los logs de red.")
        return False

    def obtener_token_kpsdk(self, target_url: str):
        """
        Método principal que orquesta el proceso de extracción del token 'x-kpsdk-ct'.

        Args:
            target_url (str): La URL de la categoría de la que se extraerá el token.

        Returns:
            str | None: El valor del token 'x-kpsdk-ct' o None si no se encontró.
        """
        try:
            print(f"🚀 Iniciando extracción de token desde: {target_url}")
            
            self.driver.get(target_url)
            self.human_like_delay(2.0, 3.0)
            try:
                agree_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "touAgreeBtn")))
                print("✅ Botón 'OK' encontrado. Haciendo click...")
                self.realistic_click(agree_button)
            except TimeoutException:
                print("⚠️ No se encontró el botón de consentimiento o no fue necesario.")

            print("⏳ Pausa estratégica y calentamiento de la sesión...")
            self.human_like_delay(4.0, 6.0)
            self.simulate_page_browsing()
            
            print("🧹 Limpiando logs de red antes de la acción...")
            self.driver.get_log('performance')
            
            if self.find_and_click_pagination(page_number=3):
                self.human_like_delay(3.0, 5.0)
                self._wait_for_search_token(timeout=20)
            else:
                print("❌ La acción de paginación falló. No se pudo generar la petición.")

        except Exception as e:
            print(f"❌ Error catastrófico durante la extracción: {e}")
        
        return self._captured_token

    def close(self):
        """Cierra el driver de Selenium y guarda los logs de red."""
        if self.driver:
            try:
                print("💾 Guardando logs de red en 'network_log.json'...")
                logs = self.driver.get_log('performance')
                with open('network_log.json', 'w') as f:
                    json.dump(logs, f, indent=2)
                print("   - Logs guardados con éxito.")
            except Exception as e:
                print(f"⚠️ No se pudieron guardar los logs de red: {e}")
            
            self.driver.quit()
            print("✅ Navegador cerrado.")


def main():
    """Función principal para demostrar el uso del extractor."""
    print("=" * 70)
    print("🛡️ EXTRACTOR DE TOKENS DE SEGURIDAD - FOOTLOCKER")
    print("=" * 70)
    
    use_undetected = UNDETECTED_AVAILABLE
    if use_undetected:
        print("🔧 Se usará 'undetected-chromedriver' para máxima evasión.")
    
    # Se ejecuta en modo headless por defecto. Cambiar a headless=False para ver el navegador.
    extractor = AntiDetectionExtractor(use_undetected=use_undetected, headless=True)
    
    try:
        # Ejemplo de uso:
        target_site_url = "https://www.kidsfootlocker.com/category/brands/nike.html"
        token = extractor.obtener_token_kpsdk(target_url=target_site_url)
        
        print("\n" + "=" * 70)
        print("📊 RESULTADOS FINALES:")
        print("=" * 70)
        
        print(f"📋 Token (x-kpsdk-ct): {'Encontrado' if token else 'No encontrado'}")
        if token:
            print(f"✅ ¡ÉXITO! Se obtuvo el token 'x-kpsdk-ct'.")
            output_filename = "kidsfootlocker_token.json"
            with open(output_filename, 'w') as f:
                json.dump({"token": token}, f, indent=2)
            print(f"💾 Token guardado en '{output_filename}'")
        else:
            print("\n❌ FALLO: No se pudo extraer el token 'x-kpsdk-ct'.")
            print("   Revisa el log para más detalles. El navegador se mantendrá abierto para depuración.")
            input("   Presiona Enter en esta terminal para cerrar el navegador.")

    except Exception as e:
        print(f"\n❌ ERROR INESPERADO EN MAIN: {e}")
        input("   Presiona Enter para cerrar.")
    
    finally:
        extractor.close()

if __name__ == "__main__":
    main()