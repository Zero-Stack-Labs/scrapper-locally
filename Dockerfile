# Start with a stable Python base image
FROM python:3.11-slim-bullseye

WORKDIR /app

# Install dependencies for Chrome and xvfb (virtual display)
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable
RUN curl -sS -o - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get -y update \
    && apt-get -y install google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install a specific version of Chromedriver that matches Chrome Stable
# Find the latest stable version from: https://googlechromelabs.github.io/chrome-for-testing/
# As of mid-2024, a common stable version is 126.x. Adjust if needed.
RUN LATEST_STABLE=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json | jq -r .Stable.version) && \
    curl -sS -o /tmp/chromedriver.zip "https://storage.googleapis.com/chrome-for-testing-public/${LATEST_STABLE}/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver.zip -d /usr/bin/ && \
    mv /usr/bin/chromedriver-linux64/chromedriver /usr/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /usr/bin/chromedriver-linux64

# Set environment variables for your Python script to find the binaries
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV CHROME_PATH=/usr/bin/google-chrome-stable
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create a non-root user for security
RUN useradd -m -s /bin/bash scraper && \
    chown -R scraper:scraper /app
USER scraper

EXPOSE 8080

# Use xvfb-run to provide a virtual display for the application
CMD ["xvfb-run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]