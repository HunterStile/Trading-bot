FROM python:3.9-slim

# Installa dipendenze di sistema
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installa Google Chrome (OPZIONALE - solo se necessario per scraping)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* \
    || echo "Chrome installation failed - continuing without Chrome"

# Installa ChromeDriver (OPZIONALE)
RUN CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE 2>/dev/null || echo "114.0.5735.90") \
    && wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
    && chmod +x /usr/local/bin/chromedriver \
    && rm /tmp/chromedriver.zip \
    || echo "ChromeDriver installation failed - continuing without ChromeDriver"

# Crea utente non-root per sicurezza
RUN useradd --create-home --shell /bin/bash app

# Crea directory di lavoro
WORKDIR /app

# Copia requirements e installa dipendenze Python
COPY requirements-minimal.txt requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-minimal.txt || \
    pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente
COPY --chown=app:app . .

# Crea directory per dati, log e backup
RUN mkdir -p /app/data /app/logs /app/backups && \
    chown -R app:app /app

# Espone la porta 5000
EXPOSE 5000

# Cambia all'utente non-root
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Comando di avvio
CMD ["python", "frontend/app.py"]
