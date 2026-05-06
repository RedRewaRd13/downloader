import requests, sys, os, re

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

def get_tweet_details(tweet_url):
    tweet_id = tweet_url.strip().split('/')[-1]
    fx_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    resp = requests.get(fx_url)
    if resp.status_code != 200:
        raise Exception(f"خطا در دریافت توییت: {resp.status_code}")
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
            url = f"{instance}/{username}/status/{tweet_id}"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                pattern = r'<div class="tweet-content media-body">(.*?)</div>'
                comments = re.findall(pattern, resp.text, re.DOTALL)
                return [re.sub(r'<[^>]+>', '', c).strip() for c in comments[:100]]
        except:
            continue
    return []

def main():
    tweet_url = sys.argv[1].strip()
    if not tweet_url.startswith("http"):
        print("❌ لطفاً لینک کامل توییت را وارد کنید (مثلاً https://x.com/username/status/123)")
        sys.exit(1)

    username = tweet_url.split('/')[3]
    tweet = get_tweet_details(tweet_url)
    text = tweet.get('text', '')
    tweet_id = tweet.get('id', '')

    base_folder = f"downloads/twitter_{username}"
    media_folder = os.path.join(base_folder, "media")
    os.makedirs(media_folder, exist_ok=True)

    summary = []
    summary.append(f"کاربر: @{username}")
    summary.append(f"شناسه توییت: {tweet_id}")
    summary.append(f"تاریخ: {tweet.get('created_at', '')}")
    summary.append(f"متن:\n{text}")
    summary.append("-" * 50)

    for media in tweet.get('media', {}).get('all', []):
        url = media.get('url')
        if url:
            path = download_file(url, media_folder)
            summary.append(f"مدیا: {os.path.basename(path)}")

    replies = get_replies(username, tweet_id)
    if replies:
        summary.append("\nکامنت‌ها:\n" + "=" * 40)
        for i, r in enumerate(replies, 1):
            summary.append(f"\n{i}. {r}")
    else:
        summary.append("\nکامنتی پیدا نشد.")

    with open(os.path.join(base_folder, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))
    print("✅ عملیات با موفقیت انجام شد!")

if __name__ == "__main__":
    main()
