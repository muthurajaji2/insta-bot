"""
Facebook Auto-Poster for iLovekaraikudi.
Claude generates caption + search keyword.
Unsplash finds a relevant matching image.
Posts to Facebook Page via Graph API.
"""
import os, sys, json, time, requests
from datetime import datetime, timezone

FB_PAGE_ID    = os.environ.get("FB_PAGE_ID", "")
FB_PAGE_TOKEN = os.environ.get("FB_PAGE_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
POST_SLOT     = os.environ.get("POST_SLOT", "1")

BASE_FB  = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}"
LOG_FILE = "post_log.json"

SLOT_THEMES = {
    "1": {
        "topic": "Karaikudi morning and daily life culture",
        "image_search": "Tamil Nadu village morning temple",
    },
    "2": {
        "topic": "Karaikudi heritage architecture and Chettinad mansions",
        "image_search": "Chettinad mansion palace architecture heritage",
    },
    "3": {
        "topic": "Karaikudi famous food and Chettinad cuisine",
        "image_search": "Chettinad food spices South Indian cuisine",
    },
    "4": {
        "topic": "Notable person or celebrity born in or connected to Karaikudi or Chettinad",
        "image_search": "Tamil Nadu heritage culture famous landmark",
    },
    "5": {
        "topic": "Fun interactive question for Karaikudi locals and fans to answer",
        "image_search": "Karaikudi street market Tamil Nadu local life",
    },
    "6": {
        "topic": "Karaikudi temples art and cultural festivals",
        "image_search": "South India Hindu temple festival Tamil Nadu",
    },
    "7": {
        "topic": "Kollywood Tamil cinema connection to Karaikudi and Chettinad",
        "image_search": "Tamil cinema vintage film South India",
    },
    "8": {
        "topic": "Inspirational quote and pride post about Karaikudi Tamil culture",
        "image_search": "Tamil Nadu sunset landscape heritage pride",
    },
}

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")

def generate_caption_and_keywords(slot):
    theme = SLOT_THEMES.get(slot, SLOT_THEMES["1"])
    log(f"Generating post for slot {slot}: {theme['topic']}")

    prompt = f"""You are the content creator for the Facebook page 'iLovekaraikudi' — celebrating Karaikudi, Chettinad, and Tamil culture.

Write ONE engaging Facebook post about: {theme['topic']}

Requirements:
- Write in English (include 1-2 Tamil words with meaning where natural)
- 3-5 sentences, warm and proud tone
- Include 2-3 relevant emojis
- End with 4-6 hashtags like #Karaikudi #Chettinad #TamilCulture #iLoveKaraikudi
- Include a specific fact, name, or detail about Karaikudi
- Feel authentic like a local who deeply loves Karaikudi
- Do NOT start with "Here is" or any preamble

After the post, on a NEW LINE write exactly:
IMAGE_KEYWORDS: [3-5 specific keywords for finding a relevant photo for this post]

Example format:
Good morning from Karaikudi! ☀️ ...post text...
#Karaikudi #Chettinad

IMAGE_KEYWORDS: Chettinad temple morning Tamil Nadu"""

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

    # Split caption and image keywords
    if "IMAGE_KEYWORDS:" in full_text:
        parts = full_text.split("IMAGE_KEYWORDS:")
        caption = parts[0].strip()
        keywords = parts[1].strip()
    else:
        caption = full_text
        keywords = theme["image_search"]

    log(f"Caption: {caption[:80]}...")
    log(f"Image keywords: {keywords}")
    return caption, keywords

def get_relevant_image(keywords, slot):
    """
    Fetch a relevant image from Unsplash using keywords.
    Unsplash source gives a direct image URL matching the search term.
    """
    log(f"Fetching relevant image for: {keywords}")

    # Unsplash Source API — free, no key needed, returns topic-matched image
    safe_keywords = requests.utils.quote(keywords)
    seed = int(slot) * 100 + int(datetime.now(timezone.utc).strftime("%j"))

    # Try Unsplash source first (free, topic-matched)
    unsplash_url = f"https://source.unsplash.com/1200x630/?{safe_keywords}&sig={seed}"

    try:
        r = requests.get(unsplash_url, timeout=20, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            log(f"Got Unsplash image: {r.url[:80]}...")
            return r.url
    except Exception as e:
        log(f"Unsplash failed: {e}, trying fallback...")

    # Fallback: Picsum with slot-based seed
    fallback_ids = [10, 15, 20, 25, 30, 37, 42, 48]
    pid = fallback_ids[int(slot) - 1]
    fallback_url = f"https://picsum.photos/id/{pid}/1200/630"
    r = requests.get(fallback_url, timeout=20, allow_redirects=True)
    if r.status_code == 200:
        log(f"Using fallback image: {r.url[:80]}...")
        return r.url

    raise RuntimeError("Could not get any image")

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

def save_log(slot, status, post_id="", caption="", keywords="", error=""):
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
        "image_keywords": keywords,
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

    try:
        caption, keywords = generate_caption_and_keywords(POST_SLOT)
        image_url = get_relevant_image(keywords, POST_SLOT)
        post_id = post_to_facebook(caption, image_url)
        save_log(POST_SLOT, "success", post_id, caption, keywords)
        print(f"\n✅  Slot {POST_SLOT} posted to iLoveKaraikudi!\n")
    except Exception as e:
        log(f"FAILED: {e}")
        save_log(POST_SLOT, "error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
