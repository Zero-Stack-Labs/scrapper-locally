import json
import shutil
import os
from playwright.sync_api import sync_playwright
import time
import random


def handler(event, context):
    body = json.loads(event.get('body', '{}'))
    url = body.get('url',
                   'https://www.academy.com/c/outdoors/camping--outdoors?&facet=deliveryFilter:inventory_pick%3A78%20OR%20inventory_sts%3A78&bopisEligible=1&isSTS1=1')

    shutil.rmtree('/tmp', ignore_errors=True)
    os.makedirs('/tmp', exist_ok=True)

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/50 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0 Safari/537.36",
    ]

    with sync_playwright() as p:
        browser = p.firefox.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-http2'
            ]
        )

        context_options = {
            "user_agent": random.choice(user_agents),
            "locale": "en-US",
            "viewport": {"width": 1920, "height": 1080},
            "java_script_enabled": True,
            "timezone_id": "America/New_York",
        }

        context = browser.new_context(**context_options)

        context.set_extra_http_headers({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })

        page = context.new_page()

        try:
            page.goto(url, wait_until='load', timeout=120000)
            print(f"Navegando a: {url}")

            num_scrolls = random.randint(1, 3)
            for _ in range(num_scrolls):
                page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {random.uniform(0.2, 0.8)})")
                time.sleep(random.uniform(1, 2))
                page.evaluate("window.scrollBy(0, 150)")
                time.sleep(random.uniform(0.5, 1.5))

            time.sleep(random.uniform(5, 10))

            content = page.content()
            print("Contenido obtenido exitosamente.")

        except Exception as e:
            content = f"Error durante la navegación o recuperación de contenido: {str(e)}"
            print(f"ERROR: {content}")
            try:
                page.screenshot(path="/tmp/captcha_error.png")
                print("Captura de pantalla guardada en /tmp/captcha_error.png")
            except Exception as ss_e:
                print(f"No se pudo guardar la captura de pantalla: {ss_e}")

        browser.close()

    shutil.rmtree('/tmp', ignore_errors=True)

    return {
        'statusCode': 200,
        'body': json.dumps({"content": content}),
        'headers': {'Content-Type': 'application/json'}
    }
