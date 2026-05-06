import requests, json, sys, os, re
from urllib.parse import quote

# پروکسی رایگان که تحریم IP های گیتهاب را دور می‌زند
PROXY = "https://corsproxy.io/?"

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
    ابتدا صفحه پروفایل توییتر را از طریق پروکسی باز می‌کنیم
    و شناسه اولین توییت را از کد JSON-ld استخراج می‌کنیم.
    """
    profile_url = f"https://twitter.com/{username}"
    proxied = PROXY + quote(profile_url, safe='')
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        resp = requests.get(proxied, headers=headers, timeout=20)
        if resp.status_code == 200:
            # توییتر شناسه‌ها را در جاهایی مثل "identifier":"123456" ذخیره می‌کند
            matches = re.findall(r'"identifier":"(\d+)"', resp.text)
            if matches:
                tweet_id = matches[0]
                return f"https://x.com/{username}/status/{tweet_id}"
    except Exception as e:
        print(f"⚠️ روش پروکسی/پروفایل خطا داد: {e}")

    # روش دوم: FxTwitter از طریق پروکسی
    try:
        fx_url = f"https://api.fxtwitter.com/profile/{username}/tweets?count=1"
        proxied_fx = PROXY + quote(fx_url, safe='')
        resp = requests.get(proxied_fx, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            tweets = data.get('tweets', [])
            if tweets:
                tid = tweets[0].get('id')
                author = tweets[0].get('author', {}).get('screen_name', username)
                return f"https://x.com/{author}/status/{tid}"
    except:
        pass
    return None

def get_tweet_details(tweet_url):
    tweet_id = tweet_url.strip().split('/')[-1]
    fx_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    proxied = PROXY + quote(fx_url, safe='')
    resp = requests.get(proxied)
    if resp.status_code != 200:
        raise Exception(f"خطا در دریافت اطلاعات توییت: {resp.status_code}")
    return resp.json().get('tweet', {})

def get_replies(username, tweet_id):
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
            resp = requests.get(nitter_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                pattern = r'<div class="tweet-content media-body">(.*?)</div>'
                comments = re.findall(pattern, resp.text, re.DOTALL)
                return [re.sub(r'<[^>]+>', '', c).strip() for c in comments[:100]]
        except:
            continue
    return []

def main():
    user_input = sys.argv[1].strip()

    if user_input.startswith("http"):
        tweet_url = user_input
        username = tweet_url.split('/')[3]
    else:
        username = user_input
        tweet_url = get_latest_tweet_url(username)
        if not tweet_url:
            print("❌ با وجود پروکسی هم نتوانستم آخرین توییت را پیدا کنم.")
            print("💡 لطفاً لینک مستقیم توییت را وارد کنید.")
            sys.exit(1)
        print(f"✅ آخرین توییت: {tweet_url}")

    tweet = get_tweet_details(tweet_url)
    text = tweet.get('text', '')
    tweet_id = tweet.get('id', '')
    author = tweet.get('author', {}).get('screen_name', username)

    base_folder = f"downloads/twitter_{author}"
    media_folder = os.path.join(base_folder, "media")
    os.makedirs(media_folder, exist_ok=True)

    summary = []
    summary.append(f"کاربر: @{author}")
    summary.append(f"شناسه توییت: {tweet_id}")
    summary.append(f"تاریخ: {tweet.get('created_at', '')}")
    summary.append(f"متن:\n{text}")
    summary.append("-" * 50)

    for media in tweet.get('media', {}).get('all', []):
        url = media.get('url')
        if url:
            path = download_file(url, media_folder)
            summary.append(f"مدیا: {os.path.basename(path)}")

    replies = get_replies(author, tweet_id)
    if replies:
        summary.append("\nکامنت‌ها:\n" + "=" * 40)
        for i, r in enumerate(replies, 1):
            summary.append(f"\n{i}. {r}")
    else:
        summary.append("\nکامنتی پیدا نشد (Nitter در دسترس نبود).")

    with open(os.path.join(base_folder, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    print("✅ عملیات با موفقیت انجام شد!")

if __name__ == "__main__":
    main()
