import os
import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# ============ URLs ============
URL_HCMUS = "https://hcmus.edu.vn/thong-tin-danh-cho-nguoi-hoc/"
URL_EXAM = "http://ktdbcl.hcmus.edu.vn/index.php/cong-tac-kh-o-thi/l-ch-thi-h-c-ky"
URL_FIT = "https://www.fit.hcmus.edu.vn/tin-tuc"
URL_STUDENT_AFFAIRS = "https://hcmus.edu.vn/phong-cong-tac-sinh-vien/"

# ============ Discord Setup ============
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

latest_posts = {}  # store the latest post per site


# ============ Scrapers ============
def fetch_hcmus_main(limit=1):
    return fetch_hcmus_common(URL_HCMUS, "HCMUS Main", limit)


def fetch_student_affairs(limit=1):
    return fetch_hcmus_common(URL_STUDENT_AFFAIRS, "Student Affairs", limit)


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


def fetch_exam_schedule(limit=1):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(URL_EXAM, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        links = soup.select("div.contentpaneopen a") or soup.select("a[href*='index.php']")
        posts = []
        for a in links[:limit]:
            title = a.text.strip()
            href = a.get("href")
            if not href.startswith("http"):
                href = f"http://ktdbcl.hcmus.edu.vn/{href.lstrip('/')}"
            posts.append((title, href))
        return posts[0] if posts else None
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
        posts = []
        for a in links[:limit]:
            title = a.text.strip()
            href = a.get("href")
            if not href.startswith("http"):
                href = f"https://www.fit.hcmus.edu.vn/{href.lstrip('/')}"
            posts.append((title, href))
        return posts[0] if posts else None
    except Exception as e:
        print(f"❌ Error scraping FIT News: {e}")
        return None


# ============ Background Task ============
@tasks.loop(minutes=10)
async def check_new_post():
    global latest_posts
    sources = {
        "HCMUS Main": fetch_hcmus_main,
        "Exam Schedule": fetch_exam_schedule,
        "FIT News": fetch_fit_news,
        "Student Affairs": fetch_student_affairs,
    }

    for name, func in sources.items():
        new_post = func()
        if not new_post:
            print(f"⚠️ No posts found for {name}")
            continue

        title, link = new_post
        if latest_posts.get(name) != link:
            latest_posts[name] = link
            channel = bot.get_channel(CHANNEL_ID)
            if channel:
                await channel.send(f"@everyone 📰 | **{title}**\n{name}: {link}")
                print(f"✅ New post sent from {name}: {title}")
            else:
                print("❌ Channel not found — check CHANNEL_ID in .env")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_new_post.start()

async def on_disconnect():
    print("⚠️ Bot disconnected from Discord!")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        try:
            await channel.send("⚠️ **Bot has disconnected from Discord!**")
        except Exception as e:
            print(f"❌ Failed to send disconnect message: {e}")

async def on_resumed():
    print("✅ Bot reconnected to Discord!")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        try:
            await channel.send("✅ **Bot has reconnected to Discord!**")
        except Exception as e:
            print(f"❌ Failed to send reconnect message: {e}")


bot.run(TOKEN)
