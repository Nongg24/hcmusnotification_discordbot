import os
import discord
from discord.ext import commands, tasks
import asyncio
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# ============ Load Environment Variables ============
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_IDS = os.getenv("CHANNEL_IDS")

if not TOKEN:
    raise ValueError("❌ DISCORD_TOKEN not found in .env")

if CHANNEL_IDS:
    CHANNEL_IDS = [int(cid.strip()) for cid in CHANNEL_IDS.split(",")]
else:
    CHANNEL_IDS = []
    print("⚠️ No CHANNEL_IDS set — bot won't send notifications.")

# ============ URLs ============
URL_HCMUS = "https://hcmus.edu.vn/thong-tin-danh-cho-nguoi-hoc/"
URL_EXAM = "http://ktdbcl.hcmus.edu.vn/index.php/cong-tac-kh-o-thi/l-ch-thi-h-c-ky"
URL_FIT = "https://www.fit.hcmus.edu.vn/tin-tuc"
URL_STUDENT_AFFAIRS = "https://hcmus.edu.vn/phong-cong-tac-sinh-vien/"

# ============ Discord Setup ============
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

latest_posts = {}

# ============ Scraper Functions ============
def fetch_hcmus_common(url, name, limit=1):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        a_tags = soup.select("a.vc_gitem-link.vc-zone-link")
        posts = [(a.get("title") or a.text.strip(), a.get("href")) for a in a_tags[:limit]]
        return posts[0] if posts else None
    except Exception as e:
        print(f"❌ Error scraping {name}: {e}")
        return None


def fetch_hcmus_main(limit=1):
    return fetch_hcmus_common(URL_HCMUS, "HCMUS Main", limit)


def fetch_student_affairs(limit=1):
    return fetch_hcmus_common(URL_STUDENT_AFFAIRS, "Student Affairs", limit)


def fetch_exam_schedule(limit=1):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(URL_EXAM, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        links = soup.select("div.contentpaneopen a") or soup.select("a[href*='index.php']")
        for a in links[:limit]:
            title = a.text.strip()
            href = a.get("href")
            if not href.startswith("http"):
                href = f"http://ktdbcl.hcmus.edu.vn/{href.lstrip('/')}"
            return title, href
    except Exception as e:
        print(f"❌ Error scraping Exam Schedule: {e}")
    return None


def fetch_fit_news(limit=1):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(URL_FIT, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        links = soup.select("div.col-lg-9 a") or soup.select("a[href*='/tin-tuc/']")
        for a in links[:limit]:
            title = a.text.strip()
            href = a.get("href")
            if not href.startswith("http"):
                href = f"https://www.fit.hcmus.edu.vn/{href.lstrip('/')}"
            return title, href
    except Exception as e:
        print(f"❌ Error scraping FIT News: {e}")
    return None


# ============ Background Task ============
@tasks.loop(minutes=10)
async def check_new_post():
    global latest_posts
    loop = asyncio.get_event_loop()

    sources = {
        "HCMUS Main": fetch_hcmus_main,
        "Exam Schedule": fetch_exam_schedule,
        "FIT News": fetch_fit_news,
        "Student Affairs": fetch_student_affairs,
    }

    for name, func in sources.items():
        new_post = await loop.run_in_executor(None, func)
        if not new_post:
            print(f"⚠️ No posts found for {name}")
            continue

        title, link = new_post
        if latest_posts.get(name) != link:
            latest_posts[name] = link
            print(f"🆕 New post detected from {name}: {title}")
            for channel_id in CHANNEL_IDS:
                channel = bot.get_channel(channel_id)
                if channel:
                    try:
                        await channel.send(f"@everyone 📰 | **{title}**\n{name}: {link}")
                    except Exception as e:
                        print(f"❌ Failed to send message to {channel_id}: {e}")


# ============ Event Handlers ============
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    if not check_new_post.is_running():
        check_new_post.start()


@bot.event
async def on_disconnect():
    print("⚠️ Bot disconnected from Discord!")
    for channel_id in CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send("⚠️ **Bot has disconnected from Discord!**")
            except Exception as e:
                print(f"❌ Failed to send disconnect message: {e}")


@bot.event
async def on_resumed():
    print("✅ Bot reconnected to Discord!")
    for channel_id in CHANNEL_IDS:
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send("✅ **Bot has reconnected to Discord!**")
            except Exception as e:
                print(f"❌ Failed to send reconnect message: {e}")


# ============ Run Bot ============
bot.run(TOKEN)
