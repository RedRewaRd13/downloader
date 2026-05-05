import snscrape.modules.twitter as sntwitter
import json, os, requests, sys

def download_media(url, folder):
    os.makedirs(folder, exist_ok=True)
    fname = url.split("/")[-1].split("?")[0]
    if not fname:
        fname = "media"
    path = os.path.join(folder, fname)
    if not os.path.exists(path):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
    return path

def main(username):
    # ۱. آخرین توییت کاربر را پیدا کن
    query = f"from:{username}"
    tweets = list(sntwitter.TwitterSearchScraper(query).get_items())
    if not tweets:
        print("هیچ توییتی پیدا نشد.")
        return
    latest = tweets[0]
    tweet_id = latest.id
    conv_id = latest.conversationId

    # ۲. دریافت کامنت‌های همان توییت (حداکثر ۱۰۰ تا)
    replies_query = f"conversation_id:{conv_id}"
    replies = list(sntwitter.TwitterSearchScraper(replies_query).get_items())

    comments = []
    for r in replies:
        if r.id != tweet_id:
            comments.append(r)
            if len(comments) >= 100:
                break

    # ۳. ساخت پوشه برای ذخیره‌سازی
    base = f"downloads/twitter_{username}"
    media_dir = os.path.join(base, "media")
    os.makedirs(media_dir, exist_ok=True)

    # ۴. نوشتن فایل متنی
    lines = []
    lines.append(f"کاربر: @{username}")
    lines.append(f"شناسه توییت: {tweet_id}")
    lines.append(f"تاریخ: {latest.date}")
    lines.append(f"متن: {latest.rawContent}")
    lines.append("-" * 50)

    # ۵. دانلود عکس‌ها و ویدیوهای توییت اصلی
    if latest.media:
        for i, m in enumerate(latest.media):
            # سعی می‌کنیم بهترین کیفیت رو بگیریم
            if isinstance(m, sntwitter.Photo):
                url = m.fullUrl + "?format=jpg&name=orig"
            elif hasattr(m, 'variants'):
                best = max([v for v in m.variants if hasattr(v, 'bitrate')], key=lambda v: v.bitrate)
                url = best.url
            else:
                continue
            path = download_media(url, media_dir)
            lines.append(f"مدیا {i+1}: {os.path.basename(path)}")

    lines.append("")
    lines.append("کامنت‌ها:")
    lines.append("=" * 40)

    # ۶. پردازش کامنت‌ها و مدیای آنها
    for idx, c in enumerate(comments, 1):
        lines.append(f"\n{idx}. @{c.user.username} ({c.date}):")
        lines.append(c.rawContent)
        if c.media:
            for j, m in enumerate(c.media):
                if isinstance(m, sntwitter.Photo):
                    url = m.fullUrl + "?format=jpg&name=orig"
                elif hasattr(m, 'variants'):
                    best = max([v for v in m.variants if hasattr(v, 'bitrate')], key=lambda v: v.bitrate)
                    url = best.url
                else:
                    continue
                path = download_media(url, media_dir)
                lines.append(f"  -> مدیا: {os.path.basename(path)}")

    # ۷. ذخیره فایل summary.txt
    with open(os.path.join(base, "summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("روش استفاده: python twitter_scraper.py username")
        sys.exit(1)
    main(sys.argv[1])
