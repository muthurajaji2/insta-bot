"""
Facebook Auto-Poster for iLovekaraikudi page.
Posts 8x daily about Karaikudi culture, history, heritage,
famous people, Kollywood stars, quotes, food, and local pride.
"""
import os, sys, json, time, requests, random
from datetime import datetime, timezone

FB_PAGE_ID    = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
POST_SLOT     = os.environ.get("POST_SLOT", "1")

BASE_FB  = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}"
LOG_FILE = "post_log.json"

# 8 different content themes for each slot
SLOT_THEMES = {
    "1": {
        "topic": "Karaikudi morning and daily life",
        "style": "warm morning greeting celebrating Karaikudi culture",
        "example": "Good morning from the heart of Chettinad! Start your day with the pride of Karaikudi.",
    },
    "2": {
        "topic": "Karaikudi heritage architecture and Chettinad mansions",
        "style": "informative and proud post about the famous Chettinad palatial homes and their architecture",
        "example": "The grand Chettinad mansions of Karaikudi are a testament to the prosperity and artistry of our ancestors.",
    },
    "3": {
        "topic": "Karaikudi famous food and Chettinad cuisine",
        "style": "mouth-watering celebration of Chettinad food — Kavuni Arisi, Chettinad Chicken, Paniyaram, Kalkandu Pongal",
        "example": "Chettinad cuisine is world-famous for its bold spices and unique flavors that you can only truly taste in Karaikudi.",
    },
    "4": {
        "topic": "Notable person or celebrity born in or connected to Karaikudi or Chettinad region",
        "style": "celebratory tribute post — choose from: Raja Sir Annamalai Chettiar, M.A. Chidambaram, Sivaji Ganesan connection, filmmaker K. Balachander, cricketer WV Raman, or other Chettinad personalities",
        "example": "Did you know? The legendary cricketer WV Raman has roots in our beloved Chettinad region!",
    },
    "5": {
        "topic": "Fun interactive question for Karaikudi locals and fans to answer in comments",
        "style": "highly engaging question post that makes people from Karaikudi feel nostalgic and comment — ask about favourite food, childhood memories, best places, local experiences, hidden gems, or fun facts about Karaikudi",
        "example": "What is the one Karaikudi dish you could eat every single day and never get tired of? Drop your answer below! 👇",
    },
    "6": {
        "topic": "Karaikudi temples, art, and cultural festivals",
        "style": "devotional and cultural post about local temples like Pillaiyarpatti, festivals, Kolam art, Villu Pattu",
        "example": "The Pillaiyarpatti Karpaga Vinayagar temple is not just a place of worship — it is the soul of Karaikudi.",
    },
    "7": {
        "topic": "Kollywood or Tamil cinema connection to Karaikudi or Chettinad",
        "style": "fun and engaging post about Tamil movies filmed in Karaikudi, actors with Chettinad roots, or cinema references",
        "example": "Karaikudi's stunning Chettinad mansions have been the backdrop for countless Tamil blockbusters!",
    },
    "8": {
        "topic": "Inspirational quote or pride post about Karaikudi",
        "style": "motivational evening post celebrating Karaikudi identity and Tamil pride, with a powerful quote or thought",
        "example": "To be from Karaikudi is to carry centuries of culture, resilience, and greatness in your heart.",
    },
}

# Beautiful Chettinad/Tamil Nadu related Picsum images
SLOT_PHOTO_IDS = {
    "1": [168, 200, 110, 167, 190, 137, 15, 96],
    "2": [401, 402, 403, 404, 405, 406, 407, 408],
    "3": [292, 312, 326, 337, 351, 360, 374, 387],
    "4": [91, 103, 119, 141, 160, 177, 193, 213],
    "5": [230, 244, 258, 271, 283, 295, 308, 321],
    "6": [334, 347, 361, 375, 389, 392, 398, 412],
    "7": [420, 433, 447, 461, 475, 488, 502, 516],
    "8": [529, 543, 557, 571, 585, 598, 612, 626],
}

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")

def generate_caption(slot):
    theme = SLOT_THEMES.get(slot, SLOT_THEMES["1"])
    log(f"Generating post for slot {slot}: {theme['topic']}")

    prompt = f"""You are the content creator for the Facebook page 'iLovekaraikudi' — a page celebrating Karaikudi, Chettinad, and Tamil culture.

Write ONE engaging Facebook post about: {theme['topic']}

Style: {theme['style']}

Example tone: {theme['example']}

Requirements:
- Write in English (you can include 1-2 Tamil words with meaning)
- 3-5 sentences, warm and proud tone
- Include 2-3 relevant emojis
- End with 4-6 relevant hashtags like #Karaikudi #Chettinad #TamilCulture #iLoveKaraikudi
- Feel authentic, like a local person who deeply loves Karaikudi
- Include a specific fact, name, or detail about Karaikudi — not generic
- Do NOT start with "Here is" or any preamble

Return ONLY the post text."""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-opus-4-5",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    if r.status_code != 200:
        log(f"Anthropic error: {r.status_code} - {r.text}")
        r.raise_for_status()

    caption = r.json()["content"][0]["text"].strip()
    log(f"Caption: {caption[:100]}...")
    return caption

def get_image_url(slot):
    log("Getting image from Picsum...")
    photo_ids = SLOT_PHOTO_IDS.get(slot, [10, 20, 30])
    day_of_year = int(datetime.now(timezone.utc).strftime("%j"))
    photo_id = photo_ids[day_of_year % len(photo_ids)]

    # Try the selected ID first, fallback to safe IDs if needed
    for pid in [photo_id, 10, 15, 20, 25, 30]:
        image_url = f"https://picsum.photos/id/{pid}/1200/630"
        try:
            r = requests.get(image_url, timeout=20, allow_redirects=True)
            if r.status_code == 200:
                log(f"Image ready (ID: {pid}): {r.url[:70]}...")
                return r.url
        except:
            continue

    raise RuntimeError("Could not get any image from Picsum")

def post_to_facebook(caption, image_url):
    log("Posting to Facebook Page...")
    r = requests.post(
        f"{BASE_FB}/photos",
        data={
            "url": image_url,
            "message": caption,
            "access_token": FB_PAGE_TOKEN,
        },
        timeout=30,
    )
    if r.status_code != 200:
        log(f"FB error: {r.status_code} - {r.text}")
        r.raise_for_status()
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"Post failed: {data}")
    log(f"Posted! ID: {data['id']}")
    return data["id"]

def save_log(slot, status, post_id="", caption="", error=""):
    entries = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            try: entries = json.load(f)
            except: pass
    entries.append({
        "slot": slot,
        "time": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "post_id": post_id,
        "caption_preview": caption[:120],
        "error": error,
    })
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)

def main():
    print(f"\n{'='*60}")
    print(f"  iLoveKaraikudi FB Poster  |  Slot {POST_SLOT}  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"{'='*60}\n")

    missing = [k for k, v in {
        "FB_PAGE_ID": FB_PAGE_ID,
        "FB_PAGE_TOKEN": FB_PAGE_TOKEN,
        "ANTHROPIC_API_KEY": ANTHROPIC_KEY,
    }.items() if not v]
    if missing:
        log(f"ERROR: Missing secrets: {', '.join(missing)}")
        sys.exit(1)

    log(f"Page ID: {FB_PAGE_ID}")
    log(f"API Key: sk-ant-...{ANTHROPIC_KEY[-6:]}")

    try:
        caption   = generate_caption(POST_SLOT)
        image_url = get_image_url(POST_SLOT)
        post_id   = post_to_facebook(caption, image_url)
        save_log(POST_SLOT, "success", post_id, caption)
        print(f"\n✅  Slot {POST_SLOT} posted to iLoveKaraikudi page!\n")
    except Exception as e:
        log(f"FAILED: {e}")
        save_log(POST_SLOT, "error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
