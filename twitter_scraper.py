import requests
import json
import sys
import os
import re
from urllib.parse import urlparse, parse_qs

def download_file(url, folder):
    """دانلود فایل از یک URL"""
    os.makedirs(folder, exist_ok=True)
    local_filename = url.split('/')[-1].split('?')[0]
    file_path = os.path.join(folder, local_filename)
    
    if not os.path.exists(file_path):
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    return file_path

def get_tweet_details(tweet_url):
    """دریافت اطلاعات توییت و عکس/فیلم‌ها با استفاده از FxTwitter (بدون نیاز به API)"""
    tweet_id = tweet_url.strip().split('/')[-1]
    api_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    
    # FxTwitter API بدون هیچ احراز هویتی پاسخ می‌دهد
    response = requests.get(api_url)
    if response.status_code != 200:
        raise Exception(f"خطا در اتصال به FxTwitter: {response.status_code}")
    
    data = response.json()
    tweet_data = data.get('tweet', {})
    
    return tweet_data

def get_replies(tweet_url):
    """دریافت ریپلای‌های یک توییت با استفاده از Nitter (بدون نیاز به API)"""
    # استخراج username و tweet_id از URL توییتر
    parts = tweet_url.strip().split('/')
    username = parts[3]
    tweet_id = parts[5]
    
    # لیستی از چند نمونه عمومی Nitter
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.1d4.us",
        "https://nitter.kavin.rocks"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for instance in nitter_instances:
        try:
            nitter_url = f"{instance}/{username}/status/{tweet_id}"
            response = requests.get(nitter_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # استخراج کامنت‌ها با استفاده از regex
                pattern = r'<div class="tweet-content media-body">(.*?)</div>\s*<div class="tweet-footer">'
                comments = re.findall(pattern, response.text, re.DOTALL)
                
                cleaned_comments = [re.sub(r'<[^>]+>', '', c).strip() for c in comments]
                return cleaned_comments
        except:
            continue
    
    return [] # اگر هیچ نمونه‌ای در دسترس نبود، لیست خالی برمی‌گرداند

# ورودی: URL توییت را از آرگومان می‌گیریم
if __name__ == "__main__":
    tweet_url = sys.argv[1]
    username = tweet_url.strip().split('/')[3]
    
    # 1. دریافت اطلاعات توییت اصلی
    tweet = get_tweet_details(tweet_url)
    text = tweet.get('text', '')
    author = tweet.get('author', {}).get('screen_name', '')
    
    # 2. ساخت پوشه‌ها
    base_folder = f"downloads/twitter_{author}"
    media_folder = os.path.join(base_folder, "media")
    os.makedirs(media_folder, exist_ok=True)

    # 3. نوشتن فایل متنی
    summary = []
    summary.append(f"تاریخ: {tweet.get('created_at', '')}")
    summary.append(f"نویسنده: @{author}")
    summary.append(f"متن توییت:\n{text}")
    summary.append("-" * 50)
    
    # 4. دانلود عکس‌ها و ویدیوها
    for media in tweet.get('media', {}).get('all', []):
        media_url = media.get('url')
        if media_url:
            path = download_file(media_url, media_folder)
            summary.append(f"مدیا: {os.path.basename(path)}")
    
    # 5. دریافت و اضافه کردن کامنت‌ها
    replies = get_replies(tweet_url)
    if replies:
        summary.append("\nکامنت‌ها (تا ۱۰۰ مورد):\n" + "=" * 40)
        for i, reply_text in enumerate(replies, 1):
            summary.append(f"\n{i}. {reply_text}")
            if i >= 100:
                break
    
    # 6. ذخیره‌سازی نهایی
    with open(os.path.join(base_folder, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
