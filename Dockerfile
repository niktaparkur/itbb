FROM python:3.11-slim
WORKDIR /app

# Обновляем пакеты и устанавливаем системные зависимости для Selenium + Chrome
# wget и unzip нужны для скачивания и распаковки драйвера
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    --no-install-recommends

# Скачиваем и устанавливаем Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install
RUN rm google-chrome-stable_current_amd64.deb

# --- УСТАНОВКА PYTHON-ЗАВИСИМОСТЕЙ ---
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# --- КОПИРОВАНИЕ КОДА ПРОЕКТА И ЗАПУСК ---
COPY . .
CMD ["sh", "-c", "alembic upgrade head && python -m bot.main"]