FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# Install Chrome/Chromium and build dependencies for undetected-chromedriver
RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-chromedriver \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome binary location for undetected-chromedriver
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROME_PATH=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

COPY requirements.txt .
RUN pip install -r requirements.txt

# Install both Playwright and Chrome dependencies
RUN python -m playwright install chromium --with-deps

COPY . .

# Create non-root user for security
RUN useradd -m -s /bin/bash scraper && \
    chown -R scraper:scraper /app
USER scraper

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
