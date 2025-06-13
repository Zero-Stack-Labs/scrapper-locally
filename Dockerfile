FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

RUN pip install awslambdaric

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Asegura instalación de Chromium de Playwright
RUN python -m playwright install chromium --with-deps

COPY app.py .

ENTRYPOINT ["python", "-m", "awslambdaric"]
CMD ["app.handler"]
