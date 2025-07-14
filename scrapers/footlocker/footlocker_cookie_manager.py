from typing import Optional, Dict
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from utils.logging_config import get_logger

logger = get_logger(__name__)

class FootlockerCookieManager:
    
    def __init__(self):
        self.footlocker_url = "https://www.footlocker.com/category/brands/nike.html?currentPage=1"
        
    def get_fresh_cookies(self, timeout: int = 30000, debug_mode: bool = False) -> Optional[Dict[str, str]]:
        """
        Obtiene cookies frescas visitando la página principal de Footlocker usando sync_playwright
        """
        try:
            logger.info("Navegando a Footlocker (página Nike) para obtener cookies...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=not debug_mode,  # False para debugging, True para producción
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-blink-features=AutomationControlled',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-extensions-file-access-check',
                        '--disable-extensions',
                        '--disable-plugins-discovery',
                        '--disable-default-apps'
                    ]
                )
                
                # Configuración más realista del contexto
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US',
                    timezone_id='America/New_York',
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1'
                    }
                )
                
                page = context.new_page()
                
                # Ejecutar JavaScript para ocultar rastros de automatización
                page.add_init_script("""
                    // Remover propiedades de webdriver
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    // Sobrescribir plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    // Sobrescribir languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    // Remover chrome runtime
                    delete window.chrome.runtime;
                    
                    // Mockear permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                """)
                
                logger.info(f"Navegando a: {self.footlocker_url}")
                page.goto(self.footlocker_url, timeout=timeout, wait_until='domcontentloaded')
                
                # Simular comportamiento humano
                logger.info("Simulando comportamiento humano...")
                page.wait_for_timeout(2000)
                
                # Scroll suave hacia abajo para activar scripts
                page.evaluate("window.scrollTo(0, 500)")
                page.wait_for_timeout(1000)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(2000)
                
                # Esperar más tiempo para que se carguen completamente las cookies
                logger.info("Esperando que se carguen todas las cookies...")
                page.wait_for_timeout(5000)
                
                # Obtener todas las cookies
                cookies = context.cookies()
                
                # Extraer todas las cookies, especialmente ak_bmsc_fl_com-ssn
                cookie_dict = {}
                ak_bmsc_found = False
                
                for cookie in cookies:
                    # Limpiar todas las cookies: eliminar saltos de línea y espacios
                    clean_cookie_value = cookie['value'].replace('\n', '').replace('\r', '').replace(' ', '').strip()
                    cookie_dict[cookie['name']] = clean_cookie_value
                    
                    if cookie['name'] == 'ak_bmsc_fl_com-ssn':
                        ak_bmsc_found = True
                        logger.info(f"Cookie ak_bmsc_fl_com-ssn obtenida y limpia: {clean_cookie_value[:20]}...")
                
                logger.info(f"Total de cookies obtenidas: {len(cookie_dict)} - Nombres: {list(cookie_dict.keys())}")
                
                if not ak_bmsc_found:
                    logger.warning("⚠️ Cookie ak_bmsc_fl_com-ssn no encontrada entre las cookies obtenidas")
                
                browser.close()
                
                if not cookie_dict:
                    logger.warning("No se pudieron obtener cookies")
                    return None
                
                if not ak_bmsc_found:
                    logger.warning("Cookie ak_bmsc_fl_com-ssn no encontrada, pero devolviendo otras cookies disponibles")
                    
                return cookie_dict
                
        except PlaywrightTimeoutError:
            logger.error(f"Timeout al cargar Footlocker después de {timeout}ms")
            return None
        except Exception as e:
            logger.error(f"Error al obtener cookies de Footlocker: {e}")
            return None 