import asyncio
import aiohttp
import random
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor

# Telegram Bot Token
TOKEN = "7513398915:AAE4jG9QqX0pQ0oQQ48QnsyIgQpQGofVi8Y"

# Proxy sources
PROXY_SOURCES = [
    "https://api.proxyscrape.com/?request=displayproxies&proxytype=https&timeout=1000",
    "https://api.proxyscrape.com/?request=displayproxies&proxytype=http&timeout=1000",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
]

# User-Agent list to prevent detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.101 Mobile Safari/537.36",
]

# Global proxy list
proxies = []
user_requests = {}

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Fetch fresh proxies
async def fetch_proxies():
    global proxies
    temp_proxies = set()
    async with aiohttp.ClientSession() as session:
        for url in PROXY_SOURCES:
            try:
                async with session.get(url, timeout=5) as resp:
                    text = await resp.text()
                    temp_proxies.update(text.strip().split("\n"))
            except Exception:
                continue

    proxies = await validate_proxies(temp_proxies)
    print(f"[+] {len(proxies)} working proxies loaded.")

# Validate proxies
async def validate_proxies(proxy_list):
    valid_proxies = []
    async with aiohttp.ClientSession() as session:
        tasks = [check_proxy(session, proxy) for proxy in proxy_list]
        results = await asyncio.gather(*tasks)
        valid_proxies = [proxy for proxy, is_valid in zip(proxy_list, results) if is_valid]
    return valid_proxies

# Check if a proxy works
async def check_proxy(session, proxy):
    test_url = "https://www.google.com"
    proxy_url = f"http://{proxy}"
    try:
        async with session.get(test_url, proxy=proxy_url, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False

# Send Telegram view using proxy
async def send_view(session, proxy, channel, msgid):
    url = f"https://t.me/{channel}/{msgid}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    proxy_url = f"http://{proxy}"
    try:
        async with session.get(url, headers=headers, proxy=proxy_url, timeout=5) as resp:
            if resp.status == 200:
                print(f"[+] View sent using {proxy}")
    except Exception:
        pass

# Telegram bot: Start command
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.reply("Send me a Telegram post link (e.g., https://t.me/channel_name/12345).")

# Telegram bot: Receive post link
@dp.message_handler()
async def handle_post_link(message: types.Message):
    if "t.me/" not in message.text:
        await message.reply("Invalid link! Please send a valid Telegram post link.")
        return

    try:
        parts = message.text.split("/")
        channel = parts[3]
        msgid = parts[4]
        user_requests[message.chat.id] = (channel, msgid)
        await message.reply(f"✅ Received post link! Sending views every 6 seconds...\n\nChannel: `{channel}`\nMessage ID: `{msgid}`", parse_mode=ParseMode.MARKDOWN)
    except IndexError:
        await message.reply("Invalid format! Please send a correct Telegram post link.")

# Background task to send views
async def view_sender():
    await fetch_proxies()
    while True:
        if not proxies:
            await fetch_proxies()

        async with aiohttp.ClientSession() as session:
            for chat_id, (channel, msgid) in user_requests.items():
                tasks = [send_view(session, random.choice(proxies), channel, msgid) for _ in range(5)]
                await asyncio.gather(*tasks)
                await bot.send_message(chat_id, f"✅ Views sent to `{channel}/{msgid}`", parse_mode=ParseMode.MARKDOWN)

        print("[+] Refreshing proxies in 6 seconds...")
        await asyncio.sleep(6)

# Run the bot
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(view_sender())
    executor.start_polling(dp, skip_updates=True)
