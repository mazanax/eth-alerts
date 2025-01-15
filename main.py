import asyncio
import os
import redis
import requests
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Конфигурация
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")
REDIS_KEY = os.getenv("REDIS_KEY", "eth_price")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
ETH_PRICE_API = os.getenv("ETH_PRICE_API", "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и TELEGRAM_CHAT_ID должны быть указаны в переменных окружения")

# Подключение к Redis
redis_client = redis.StrictRedis.from_url(REDIS_URI, decode_responses=True)

# Инициализация Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)

def get_eth_price():
    """Получает текущую цену ETH."""
    response = requests.get(ETH_PRICE_API)
    response.raise_for_status()
    data = response.json()
    return data["ethereum"]["usd"]

def check_and_notify():
    """Проверяет изменения цены ETH и отправляет уведомление при пересечении "круглых" значений."""
    current_price = get_eth_price()
    print(f"Current price: {current_price}")

    current_price_rounded = int(current_price // 100) * 100

    previous_price = redis_client.get(REDIS_KEY)
    if previous_price is not None:
        print(f"Previous price: {previous_price}")
        previous_price = float(previous_price)
        previous_price_rounded = int(previous_price // 100) * 100

        # Проверяем, пересечено ли "круглое" значение
        if current_price_rounded != previous_price_rounded:
            direction = "вверх" if current_price > previous_price else "вниз"
            message = (
                f"Цена ETH изменилась {direction}!\n"
                f"Предыдущая цена: ${previous_price}\n"
                f"Текущая цена: ${current_price}\n"
                f"Пересечено значение: ${current_price_rounded}"
            )
            loop.run_until_complete(bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message))

    # Сохраняем текущую цену в Redis
    redis_client.set(REDIS_KEY, current_price)

if __name__ == "__main__":
    try:
        check_and_notify()
    except Exception as e:
        print(f"Ошибка: {e}")
