import os
from dotenv import load_dotenv

load_dotenv()

# توکن ربات از فایل .env خونده میشه (BOT_TOKEN=...)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# پروکسی برای وصل شدن به تلگرام (اختیاری)، مثلاً socks5://127.0.0.1:10808
PROXY_URL = os.getenv("PROXY_URL", "")

# آیدی عددی ادمین‌ها (می‌تونی چندتا اضافه کنی)
ADMIN_IDS = [82502565]

# یوزرنیم پشتیبانی (برای نمایش به کاربر)
SUPPORT_USERNAME = "fff16kkk"
