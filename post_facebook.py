"""
Facebook Auto-Poster for iLovekaraikudi.
Uses Pexels API for content-matched images.
"""
import os, sys, json, time, requests
from datetime import datetime, timezone

FB_PAGE_ID    = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PEXELS_KEY    = os.environ.get("PEXELS_API_KEY", "")
POST_SLOT     = os.environ.get("POST_SLOT", "1")

BASE_FB  = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}"
LOG_FILE = "post_log.json"

SLOT_THEMES = {
    "1": {"topic": "Karaikudi morning and daily life culture", "image_query": "Tamil Nadu India morning village"},
    "2": {"topic": "Karaikudi heritage architecture and Chettinad mansions", "image_query": "India heritage palace mansion architecture"},
    "3": {"topic": "Karaikudi famous food and Chettinad cuisine", "image_query": "South Indian food spices curry"},
    "4": {"topic": "Notable person or celebrity connected to Karaikudi Chettinad", "image_query": "Tamil Nadu India culture heritage"},
    "5": {"topic": "Fun interactive question for Karaikudi locals and fans", "image_query": "India street food market local"},
    "6": {"topic": "Karaikudi temples art and cultural festivals", "image_query": "South India Hindu temple festival"},
    "7": {"topic": "Kollywood Tamil cinema connection to Karaikudi Chettinad", "image_query": "India vintage cinema culture"},
    "8": {"topic": "Inspirational quote and pride post about Karaikudi Tamil culture", "image_query": "Tamil Nadu India sunset landscape"},
}

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")

def generate_caption_and_keywords(slot):
    theme = SLOT_THEMES.get(slot, SLOT_THEMES["1"])
    log(f"Generating caption for slot {slot}: {theme['topic']}")

    prompt = f"""You are the content creator for 'iLovekaraikudi' Facebook page celebrating Karaikudi, Chettinad and Tamil culture.

Write ONE engaging Facebook post about: {theme['topic']}

Requirements:
- English with 1-2 Tamil words (with meaning) where natural
- 3-5 sentences, warm and proud tone
- 2-3 relevant emojis
- End with 4-6 hashtags: #Karaikudi #Chettinad #TamilCulture #iLoveKaraikudi
- Include a specific fact, name or detail about Karaikudi
- Do NOT start with "Here is" or any preamble

After the post on a NEW LINE write:
PEXELS_SEARCH: [3-4 English words to search a relevant photo]

Example:
Good morning Karaikudi! ☀️ ...post...
#Karaikudi #Chettinad

PEXELS_SEARCH: Tamil Nadu temple morning"""

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-opus-4-5",
            "max_tokens": 500,
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

    log(f"Caption: {caption[:80]}...")
    log(f"Pexels search: {search_query}")
    return caption, search_query

def get_pexels_image(query, slot):
    log(f"Searching Pexels for: {query}")

    # Try with the AI-generated query first
    for search_term in [query, SLOT_THEMES.get(slot, {}).get("image_query", "India culture")]:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={
                    "query": search_term,
                    "per_page": 10,
                    "orientation": "landscape",
                    "size": "large",
                },
                timeout=15,
            )
            if r.status_code == 200:
                photos = r.json().get("photos", [])
                if photos:
                    # Pick different photo each day using day of year
                    day = int(datetime.now(timezone.utc).strftime("%j"))
                    photo = photos[day % len(photos)]
                    image_url = photo["src"]["large2x"]
                    photographer = photo.get("photographer", "Pexels")
                    log(f"Got Pexels image by {photographer}: {image_url[:70]}...")
                    return image_url
        except Exception as e:
            log(f"Pexels attempt failed: {e}")
            continue

    raise RuntimeError("Could not get image from Pexels — check PEXELS_API_KEY secret")

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
    print(f"  iLoveKaraikudi FB Poster  |  Slot {POST_SLOT}  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
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
        caption, query = generate_caption_and_keywords(POST_SLOT)
        image_url = get_pexels_image(query, POST_SLOT)
        post_id = post_to_facebook(caption, image_url)
        save_log(POST_SLOT, "success", post_id, caption, query)
        print(f"\n✅  Slot {POST_SLOT} posted to iLoveKaraikudi!\n")
    except Exception as e:
        log(f"FAILED: {e}")
        save_log(POST_SLOT, "error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
