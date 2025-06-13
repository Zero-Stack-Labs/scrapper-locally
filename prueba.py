# [DECISIÓN]: Usar lxml con XPath para extraer productos desde contenedores li con clase product
# [ANÁLISIS]: Encontré una lista de productos en <ul> con múltiples <li> que contienen imágenes, títulos, precios y marcas

import json
import re
from lxml import html

# Read HTML
with open('products.html', 'r', encoding='utf-8') as file:
    content = file.read()

# Parse HTML with lxml
tree = html.fromstring(content)

# Find product containers - looking for li elements that contain product information
product_containers = tree.xpath('//ul/li[.//img and .//h3 and (.//span[contains(text(), "COP")] or .//div[contains(text(), "COP")])][position() <= 60]')

products = []

for container in product_containers:
    try:
        # Extract product ID from various sources
        product_id = "unknown"
        id_sources = [
            container.xpath('.//a/@href'),
            container.xpath('.//@data-id'),
            container.xpath('.//@data-product-id')
        ]
        for source in id_sources:
            if source:
                id_match = re.search(r'/(\d+)(?:[/?]|$)', str(source[0]))
                if id_match:
                    product_id = id_match.group(1)
                    break

        # Extract title
        title_elements = container.xpath('.//h3/text() | .//h3//text()')
        title = ' '.join([t.strip() for t in title_elements if t.strip()]).strip()
        if not title:
            title = "unknown"

        # Extract brand
        brand_elements = container.xpath('.//div[contains(@class, "brand")]//text() | .//a/div[1]//text()')
        brand = "unknown"
        if brand_elements:
            brand = brand_elements[0].strip()
        else:
            brand_from_title = container.xpath('.//a/div[1]/text()')
            if brand_from_title:
                brand = brand_from_title[0].strip()

        # Extract description (same as title)
        description = title

        # Extract price
        price = 0
        price_elements = container.xpath('.//span[contains(text(), "COP")]/text() | .//div[contains(text(), "COP")]/text()')
        for price_text in price_elements:
            price_match = re.search(r'COP\s*([\d,\.]+)', price_text.replace(',', ''))
            if price_match:
                try:
                    price = float(price_match.group(1).replace(',', '').replace('.', ''))
                    break
                except:
                    continue

        # Extract images
        images = []
        img_elements = container.xpath('.//img/@src')
        for img_src in img_elements:
            if img_src and 'http' in img_src and 'svg' not in img_src:
                clean_img = img_src.replace('\\"', '').replace('"', '')
                if clean_img not in images:
                    images.append(clean_img)

        # Extract product URL
        product_url = "unknown"
        url_elements = container.xpath('.//a/@href')
        if url_elements:
            product_url = url_elements[0]

        # Skip if essential data is missing
        if title == "unknown" or not images:
            continue

        product = {
            "id": product_id,
            "title": title,
            "description": description,
            "price": price,
            "images": images,
            "product_url": product_url,
            "variants": [],
            "brand": brand
        }

        products.append(product)

    except Exception as e:
        continue

# Debugging: Print cuántos productos encontraste
print(f"DEBUG: Encontrados {len(products)} productos")

# Show first product as example
if products:
    print(f"DEBUG: Primer producto - {products[0]['title'][:50]}...")
    print(f"DEBUG: Precio: {products[0]['price']}")
    print(f"DEBUG: Imágenes: {len(products[0]['images'])}")

# Output final
print(json.dumps(products, ensure_ascii=False, indent=2))