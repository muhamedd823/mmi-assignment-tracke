def fetch_data(chat_id=None):
    try:
        # Added more headers to mimic a real browser perfectly
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://lms.mersamedia.org/",
            "Connection": "keep-alive"
        }
        
        # Increase timeout to 60 to give SiteGround time to process
        r = requests.get(API_URL, impersonate="chrome", headers=headers, timeout=60)
        
        if r.status_code == 200:
            return r.json()
        else:
            if chat_id: bot.send_message(chat_id, f"❌ SiteGround Error: {r.status_code}")
            return None
    except Exception as e:
        if chat_id: bot.send_message(chat_id, f"⚠️ Timeout: SiteGround is ignoring Render.")
        return None
