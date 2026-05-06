import requests, sys, os, re, subprocess

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

def get_tweet_with_thread(tweet_url):
    tweet_id = tweet_url.strip().split('/')[-1]
    fx_url = f"https://api.fxtwitter.com/status/{tweet_id}"
    resp = requests.get(fx_url)
    if resp.status_code != 200:
        raise Exception(f"خطا در دریافت توییت: {resp.status_code}")
    data = resp.json()
    return data.get('tweet', {}), data.get('thread', [])

def get_replies_from_nitter(username, tweet_id):
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
    password = sys.argv[2] if len(sys.argv) > 2 else ""

    if not tweet_url.startswith("http"):
        print("❌ لطفاً لینک کامل توییت را وارد کنید")
        sys.exit(1)

    username = tweet_url.split('/')[3]
    tweet, thread = get_tweet_with_thread(tweet_url)

    text = tweet.get('text', '')
    tweet_id = tweet.get('id', '')

    base_folder = os.path.join("twitter", tweet_id)
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

    comments = []
    if thread:
        for t in thread:
            tid = t.get('id')
            if tid and tid != tweet_id:
                author = t.get('author', {}).get('screen_name', 'unknown')
                txt = t.get('text', '')
                comments.append(f"@{author}: {txt}")
        summary.append(f"\nکامنت‌ها (از Thread - {len(comments)} مورد):\n" + "=" * 40)
    else:
        summary.append("\nکامنت‌ها (Thread در دسترس نیست):\n" + "=" * 40)

    if comments:
        for i, c in enumerate(comments, 1):
            summary.append(f"{i}. {c}")
    else:
        nitter_comments = get_replies_from_nitter(username, tweet_id)
        if nitter_comments:
            summary[-1] = "\nکامنت‌ها (از Nitter - %d مورد):\n%s" % (len(nitter_comments), "=" * 40)
            for i, c in enumerate(nitter_comments, 1):
                summary.append(f"{i}. {c}")
        else:
            summary.append("هیچ کامنتی یافت نشد.")

    with open(os.path.join(base_folder, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary))

    # اگه پسورد داده شده، فایل‌ها رو زیپ کن و رمز بذار
    if password:
        zip_filename = f"{base_folder}.zip"
        # حذف زیپ قبلی (در صورت وجود)
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        # ساخت زیپ با پسورد
        subprocess.run(
            ["zip", "-P", password, "-r", zip_filename, base_folder],
            check=True
        )
        print(f"✅ فایل‌های توییت با پسورد در {zip_filename} ذخیره شد.")
        # (اختیاری) حذف پوشه اصلی بدون رمز - اگر می‌خوای پوشه بمونه، این دو خط رو حذف کن
        import shutil
        shutil.rmtree(base_folder)
        print("📁 پوشه اصلی (بدون رمز) حذف شد.")
    else:
        print("✅ فایل‌های توییت بدون پسورد ذخیره شد.")

if __name__ == "__main__":
    main()
