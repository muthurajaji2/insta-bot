"""
Facebook Auto-Poster for iLovekaraikudi.
4 posts per day at peak hours.
All posts are engaging questions to followers about Karaikudi.
Never uses words: Nagarathar, Chettinad
"""
import os, sys, json, requests
from datetime import datetime, timezone

FB_PAGE_ID    = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PEXELS_KEY    = os.environ.get("PEXELS_API_KEY", "")
POST_SLOT     = os.environ.get("POST_SLOT", "1")

BASE_FB  = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}"
LOG_FILE = "post_log.json"

# 4 slots — peak hours IST
# Slot 1: 8:00 AM  (morning peak)
# Slot 2: 12:00 PM (lunch peak)
# Slot 3: 6:00 PM  (evening peak)
# Slot 4: 9:00 PM  (night peak)

SLOT_THEMES = {
    "1": {
        "time": "8:00 AM",
        "topic": "morning question about Karaikudi food, daily routine or childhood memory",
        "image_query": "South Indian breakfast food morning",
        "example_questions": [
            "What is your favourite Karaikudi breakfast? 🍽️",
            "Which street in Karaikudi holds your best childhood memory?",
            "Name one food from Karaikudi you miss the most!",
        ],
    },
    "2": {
        "time": "12:00 PM",
        "topic": "lunchtime question about Karaikudi famous places, landmarks or hidden gems",
        "image_query": "Tamil Nadu India heritage landmark famous place",
        "example_questions": [
            "Which is your favourite spot in Karaikudi?",
            "Best place to eat in Karaikudi — drop your recommendation!",
            "Which Karaikudi landmark makes you proud?",
        ],
    },
    "3": {
        "time": "6:00 PM",
        "topic": "evening question about Karaikudi culture, festivals, traditions or temples",
        "image_query": "South India temple festival culture evening",
        "example_questions": [
            "Which Karaikudi festival is closest to your heart?",
            "Share one tradition from Karaikudi that you love!",
            "Which temple in Karaikudi do you visit first when you come home?",
        ],
    },
    "4": {
        "time": "9:00 PM",
        "topic": "night question about Karaikudi pride, memories, people or Kollywood connections",
        "image_query": "Tamil Nadu India night culture pride",
        "example_questions": [
            "What makes you proud to be from Karaikudi?",
            "Tag someone from Karaikudi who inspires you!",
            "Which Tamil movie shot in Karaikudi is your all-time favourite?",
        ],
    },
}

BANNED_WORDS = {
    "Nagarathar": "Karaikudi community",
    "nagarathar": "Karaikudi community",
    "NAGARATHAR": "KARAIKUDI COMMUNITY",
    "Chettinad": "Karaikudi",
    "chettinad": "Karaikudi",
    "CHETTINAD": "KARAIKUDI",
}

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")

def clean_text(text):
    for word, replacement in BANNED_WORDS.items():
        text = text.replace(word, replacement)
    return text

def generate_question_post(slot):
    theme = SLOT_THEMES.get(slot, SLOT_THEMES["1"])
    log(f"Generating question post for slot {slot} ({theme['time']} IST)")

    examples = "\n".join([f"- {q}" for q in theme["example_questions"]])

    prompt = f"""You are the content creator for 'iLovekaraikudi' Facebook page.

Your job: Write ONE highly engaging QUESTION post for Karaikudi followers.

Time of post: {theme['time']} IST
Topic: {theme['topic']}

Example question styles (do NOT copy exactly, write something fresh and different):
{examples}

STRICT RULES:
- NEVER use the word "Nagarathar" — forbidden
- NEVER use the word "Chettinad" — forbidden
- Use "Karaikudi" instead always

Post format:
- Start with a fun emoji + attention-grabbing opening line
- Ask ONE clear engaging question that locals will want to answer
- Add a fun prompt like "Comment below 👇" or "Tag a friend!" or "Drop your answer!"
- 2-3 emojis total
- End with 3-4 hashtags: #Karaikudi #iLoveKaraikudi #KaraikudiLovers #TamilCulture
- Keep it SHORT — max 4 lines total
- Sound like a fun local friend, not a brand

After the post on a NEW LINE write:
PEXELS_SEARCH: [3-4 words for a relevant image]

Example output:
☀️ Rise and shine Karaikudi family! What is the one breakfast dish that takes you straight back home? Drop your answer below 👇
#Karaikudi #iLoveKaraikudi #KaraikudiLovers

PEXELS_SEARCH: South Indian breakfast idli dosa"""

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

    full_text = r.json()["content"][0]["text"].strip()

    if "PEXELS_SEARCH:" in full_text:
        parts = full_text.split("PEXELS_SEARCH:")
        caption = parts[0].strip()
        search_query = parts[1].strip()
    else:
        caption = full_text
        search_query = theme["image_query"]

    caption = clean_text(caption)
    search_query = clean_text(search_query)

    log(f"Post: {caption[:100]}...")
    log(f"Image search: {search_query}")
    return caption, search_query

def get_pexels_image(query, slot):
    log(f"Searching Pexels: {query}")
    for search_term in [query, SLOT_THEMES.get(slot, {}).get("image_query", "India culture")]:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": search_term, "per_page": 10, "orientation": "landscape", "size": "large"},
                timeout=15,
            )
            if r.status_code == 200:
                photos = r.json().get("photos", [])
                if photos:
                    day = int(datetime.now(timezone.utc).strftime("%j"))
                    photo = photos[day % len(photos)]
                    url = photo["src"]["large2x"]
                    log(f"Image by {photo.get('photographer','Pexels')}: {url[:60]}...")
                    return url
        except Exception as e:
            log(f"Pexels error: {e}")
    raise RuntimeError("Could not get image from Pexels")

def post_to_facebook(caption, image_url):
    log("Posting to Facebook...")
    r = requests.post(
        f"{BASE_FB}/photos",
        data={"url": image_url, "message": caption, "access_token": FB_PAGE_TOKEN},
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

def save_log(slot, status, post_id="", caption="", query="", error=""):
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
        "image_query": query,
        "error": error,
    })
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)

def main():
    print(f"\n{'='*60}")
    print(f"  iLoveKaraikudi  |  Slot {POST_SLOT}  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"{'='*60}\n")

    missing = [k for k, v in {
        "FB_PAGE_ID": FB_PAGE_ID,
        "FB_PAGE_TOKEN": FB_PAGE_TOKEN,
        "ANTHROPIC_API_KEY": ANTHROPIC_KEY,
        "PEXELS_API_KEY": PEXELS_KEY,
    }.items() if not v]
    if missing:
        log(f"ERROR: Missing secrets: {', '.join(missing)}")
        sys.exit(1)

    try:
        caption, query = generate_question_post(POST_SLOT)
        image_url = get_pexels_image(query, POST_SLOT)
        post_id = post_to_facebook(caption, image_url)
        save_log(POST_SLOT, "success", post_id, caption, query)
        print(f"\n✅  Slot {POST_SLOT} posted!\n")
    except Exception as e:
        log(f"FAILED: {e}")
        save_log(POST_SLOT, "error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
