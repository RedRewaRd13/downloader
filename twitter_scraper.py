import requests, json, sys, os, re, xml.etree.ElementTree as ET

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

def get_latest_tweet_url_fxtwitter(username):
    """تلاش با چند نقطه‌ی پایانی مختلف FxTwitter"""
    endpoints = [
        f"https://api.fxtwitter.com/tweets/{username}?count=1",
        f"https://api.fxtwitter.com/user/{username}/tweets?count=1",
        f"https://api.fxtwitter.com/profile/{username}/tweets?count=1",
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                tweets = data.get('tweets') or data.get('data')
                if tweets and len(tweets) > 0:
                    tweet = tweets[0]
                    tid = tweet.get('id')
                    author = tweet.get('author', {}).get('screen_name', username)
                    if tid:
                        return f"https://x.com/{author}/status/{tid}"
        except Exception:
            continue
    return None

def get_latest_tweet_url_rss(username):
    """تلاش با RSS رسمی توییتر و شبیه‌سازی کامل مرورگر"""
    rss_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'application/xml, text/xml, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://twitter.com/',
    }
    try:
        resp = requests.get(rss_url, headers=headers, timeout=10)
        if resp.status_code == 200 and resp.text.strip().startswith('<?xml'):
            root = ET.fromstring(resp.content)
            for item in root.iter('item'):
                link = item.find('link')
                if link is not None and link.text:
                    return link.text.strip()
    except Exception:
        pass
    return None

def get_latest_tweet_url_from_profile(username):
    """آخرین شانس: استخراج شناسه از صفحه‌ی پروفایل به عنوان Googlebot"""
    profile_url = f"https://twitter.com/{username}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
    }
    try:
        resp = requests.get(profile_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            # Twitter in its static version embeds the latest tweet ID in a script tag
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                # --- navigating the JSON structure ---
                # This is brittle but commonly points to the first tweet in the timeline
                try:
                    timeline = data['props']['pageProps']['timelineResponse']['timeline']['instructions']
                    for instruction in timeline:
                        if 'addEntries' in instruction:
                            entries = instruction['addEntries']['entries']
                            for entry in entries:
                                if entry['entryId'].startswith('tweet-'):
                                    tid = entry['entryId'].split('-')[1]
                                    return f"https://x.com/{username}/status/{tid}"
                except (KeyError, IndexError):
                    pass
    except Exception:
        pass
    return None

def get_latest_tweet_url(username):
    """تلاش ترکیبی برای یافتن لینک آخرین توییت"""
    url = get_latest_tweet_url_fxtwitter(username)
    if url:
        print("✅ یافت شد با FxTwitter")
        return url
    url = get_latest_tweet_url_rss(username)
    if url:
        print("✅ یافت شد با RSS")
        return url
    url = get_latest_tweet_url_from_profile(username)
    if url:
        print("✅ یافت شد با استخراج از صفحه پروفایل")
        return url
    return None

def get_tweet_details(tweet_url):
    tweet_id = tweet_url.strip().split('/')[-1]
    api_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    resp = requests.get(api_url)
    if resp.status_code != 200:
        raise Exception(f"خطا در FxTwitter: {resp.status_code}")
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
            resp = requests.get(nitter_url, headers=headers, timeout=15)
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
            print("❌ بعد از چند تلاش نتوانستم آخرین توییت را پیدا کنم.")
            print("💡 می‌توانید لینک مستقیم توییت را به عنوان ورودی بدهید.")
            sys.exit(1)
        print(f"🔗 آخرین توییت: {tweet_url}")

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
        summary.append("\nکامنتی پیدا نشد (نمونه‌های Nitter ممکن است در دسترس نباشند).")

    with open(os.path.join(base_folder, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    print("✅ عملیات با موفقیت انجام شد!")

if __name__ == "__main__":
    main()
