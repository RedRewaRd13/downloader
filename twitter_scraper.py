import requests, json, sys, os, re

def download_file(url, folder):
    os.makedirs(folder, exist_ok=True)
    fname = url.split('/')[-1].split('?')[0]
    path = os.path.join(folder, fname)
    if not os.path.exists(path):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
    return path

def get_latest_tweet_url(username):
    """
    پیدا کردن لینک آخرین توییت با استفاده از API رایگان FxTwitter
    این روش بدون هیچ احراز هویتی کار می‌کند.
    """
    api_url = f"https://api.fxtwitter.com/profile/{username}/tweets?count=1"
    try:
        resp = requests.get(api_url, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # ساختار پاسخ: {'tweets': [ ... ], 'user': ...}
            tweets = data.get('tweets', [])
            if tweets:
                tweet_id = tweets[0].get('id')
                author = tweets[0].get('author', {}).get('screen_name', username)
                return f"https://x.com/{author}/status/{tweet_id}"
    except Exception as e:
        print(f"⚠️ خطا در اتصال به FxTwitter: {e}")
    return None

def get_tweet_details(tweet_url):
    """دریافت اطلاعات توییت و مدیا با FxTwitter"""
    tweet_id = tweet_url.strip().split('/')[-1]
    api_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    resp = requests.get(api_url)
    if resp.status_code != 200:
        raise Exception(f"خطا در FxTwitter: {resp.status_code}")
    return resp.json().get('tweet', {})

def get_replies(username, tweet_id):
    """دریافت متن کامنت‌ها از Nitter (حداکثر ۱۰۰)"""
    nitter_instances = [
        "https://nitter.net",
        "https://nitter.1d4.us",
        "https://nitter.kavin.rocks",
        "https://nitter.privacydev.net"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    for instance in nitter_instances:
        try:
            nitter_url = f"{instance}/{username}/status/{tweet_id}"
            resp = requests.get(nitter_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                pattern = r'<div class="tweet-content media-body">(.*?)</div>'
                comments = re.findall(pattern, resp.text, re.DOTALL)
                return [re.sub(r'<[^>]+>', '', c).strip() for c in comments[:100]]
        except:
            continue
    return []  # اگر هیچ نمونه‌ای در دسترس نبود

def main():
    user_input = sys.argv[1].strip()

    # تشخیص ورودی: لینک کامل یا نام کاربری
    if user_input.startswith("http"):
        tweet_url = user_input
        username = tweet_url.split('/')[3]
    else:
        username = user_input
        tweet_url = get_latest_tweet_url(username)
        if not tweet_url:
            print("❌ نتوانستم آخرین توییت را پیدا کنم. لطفاً لینک مستقیم توییت را وارد کنید.")
            sys.exit(1)
        print(f"✅ آخرین توییت: {tweet_url}")

    tweet = get_tweet_details(tweet_url)
    text = tweet.get('text', '')
    tweet_id = tweet.get('id', '')
    author = tweet.get('author', {}).get('screen_name', username)

    # پوشه‌ها
    base_folder = f"downloads/twitter_{author}"
    media_folder = os.path.join(base_folder, "media")
    os.makedirs(media_folder, exist_ok=True)

    summary = []
    summary.append(f"کاربر: @{author}")
    summary.append(f"شناسه توییت: {tweet_id}")
    summary.append(f"تاریخ: {tweet.get('created_at', '')}")
    summary.append(f"متن:\n{text}")
    summary.append("-" * 50)

    # دانلود عکس‌ها و ویدیوها
    for media in tweet.get('media', {}).get('all', []):
        url = media.get('url')
        if url:
            path = download_file(url, media_folder)
            summary.append(f"مدیا: {os.path.basename(path)}")

    # دریافت کامنت‌ها
    replies = get_replies(author, tweet_id)
    if replies:
        summary.append("\nکامنت‌ها:\n" + "=" * 40)
        for i, r in enumerate(replies, 1):
            summary.append(f"\n{i}. {r}")
    else:
        summary.append("\nکامنتی پیدا نشد (ممکن است نمونه‌های Nitter در دسترس نباشند).")

    # ذخیره فایل
    with open(os.path.join(base_folder, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    print("✅ عملیات با موفقیت انجام شد!")

if __name__ == "__main__":
    main()
