import os
import discord
from discord.ext import commands, tasks
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
URL = "https://hcmus.edu.vn/thong-tin-danh-cho-nguoi-hoc/"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

latest_post = None  # store the newest post link to avoid duplicates


def fetch_latest_post(limit=1):
    """Scrape the latest announcement title + URL from HCMUS."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    post_links = soup.select("a.vc_gitem-link.vc-zone-link")

    posts = []
    for a in post_links[:limit]:
        title = a.get("title") or a.get_text(strip=True)
        link = a.get("href")
        posts.append((title, link))

    return posts[0] if posts else None


@tasks.loop(minutes=10)  # check every 10 minutes
async def check_new_post():
    global latest_post
    new_post = fetch_latest_post()

    if not new_post:
        print("⚠️ Không tìm thấy bài viết nào.")
        return

    title, link = new_post
    if latest_post != link:
        latest_post = link
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            # 🔔 Send notification and ping everyone
            message = f"@everyone 📰 | **{title}**\n{link}"
            await channel.send(message)
            print(f"✅ Sent new post: {title}")
        else:
            print("❌ Không tìm thấy channel. Kiểm tra CHANNEL_ID trong .env")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    check_new_post.start()


bot.run(TOKEN)
