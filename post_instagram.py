"""
Instagram Auto-Poster with AI-generated captions + images.
Uses Picsum for reliable free images, Claude for captions.
"""
import os, sys, json, time, requests, random
from datetime import datetime, timezone

IG_USER_ID      = os.environ.get("IG_USER_ID", "")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
POST_SLOT       = os.environ.get("POST_SLOT", "1")
NICHE           = os.environ.get("INSTAGRAM_NICHE", "motivational lifestyle")

BASE_IG  = f"https://graph.facebook.com/v19.0/{IG_USER_ID}"
LOG_FILE = "post_log.json"

SLOT_THEMES = {
    "1": "morning motivation and fresh start to the day",
    "2": "productivity tips and mid-morning energy",
    "3": "positive mindset and noon inspiration",
    "4": "lunch break wellness and self-care",
    "5": "afternoon hustle and goal setting",
    "6": "early evening reflection and gratitude",
    "7": "golden hour beauty and lifestyle",
    "8": "night wind-down, rest and tomorrow's mindset",
}

# Curated Picsum photo IDs by mood/theme (always free, always reachable)
SLOT_PHOTO_IDS = {
    "1": [10, 15, 96, 110, 137, 167, 190, 200],   # bright morning
    "2": [20, 42, 56, 103, 153, 175, 211, 240],   # productive desk
    "3": [37, 64, 82, 116, 144, 180, 219, 250],   # positive nature
    "4": [30, 48, 75, 122, 158, 185, 225, 260],   # wellness food
    "5": [25, 55, 88, 130, 163, 192, 230, 270],   # hustle energy
    "6": [45, 68, 92, 135, 170, 198, 235, 280],   # evening city
    "7": [52, 73, 98, 140, 176, 204, 242, 290],   # golden hour
    "8": [60, 80, 105, 148, 182, 210, 248, 300],  # calm night
}

def log(msg):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}")

def generate_caption(slot):
    theme = SLOT_THEMES.get(slot, "daily inspiration")
    log(f"Generating caption for slot {slot}: {theme}")

    prompt = (
        f"You are an Instagram content creator in the '{NICHE}' niche.\n"
        f"Write ONE engaging Instagram caption for the theme: '{theme}'.\n"
        f"Requirements:\n"
        f"- 2-3 sentences max\n"
        f"- Include 2-3 relevant emojis naturally placed\n"
        f"- End with 5-8 hashtags on a new line\n"
        f"- Conversational, authentic tone\n"
        f"- Do NOT include any intro like 'Here is a caption:'\n"
        f"Return ONLY the caption text."
    )

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-opus-4-5",
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30,
    )
    if r.status_code != 200:
        log(f"Anthropic error: {r.status_code} - {r.text}")
        r.raise_for_status()

    caption = r.json()["content"][0]["text"].strip()
    log(f"Caption: {caption[:80]}...")
    return caption

def get_image_url(slot):
    log("Selecting image from Picsum (free, reliable)...")
    # Pick a photo ID based on slot + today's date for variety
    photo_ids = SLOT_PHOTO_IDS.get(slot, list(range(10, 300, 30)))
    day_of_year = int(datetime.now(timezone.utc).strftime("%j"))
    photo_id = photo_ids[day_of_year % len(photo_ids)]

    # Picsum gives a direct 1080x1080 image — always publicly accessible
    image_url = f"https://picsum.photos/id/{photo_id}/1080/1080"

    # Resolve the redirect to get the final direct URL
    log(f"Resolving image URL (Picsum ID: {photo_id})...")
    r = requests.get(image_url, timeout=20, allow_redirects=True)
    if r.status_code != 200:
        raise RuntimeError(f"Image not reachable: {r.status_code}")

    final_url = r.url
    log(f"Image URL ready: {final_url[:80]}...")
    return final_url

def create_container(image_url, caption):
    log("Uploading to Instagram...")
    r = requests.post(f"{BASE_IG}/media", data={
        "image_url": image_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN,
    }, timeout=30)
    if r.status_code != 200:
        log(f"IG container error: {r.status_code} - {r.text}")
        r.raise_for_status()
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"Container failed: {data}")
    log(f"IG container created: {data['id']}")
    return data["id"]

def wait_container(container_id, retries=15, delay=6):
    for i in range(retries):
        r = requests.get(f"{BASE_IG}/media/{container_id}", params={
            "fields": "status_code",
            "access_token": IG_ACCESS_TOKEN,
        }, timeout=15)
        status = r.json().get("status_code", "UNKNOWN")
        log(f"Container status: {status} ({i+1}/{retries})")
        if status == "FINISHED":
            return True
        if status == "ERROR":
            raise RuntimeError("IG container processing error.")
        time.sleep(delay)
    return False

def publish(container_id):
    r = requests.post(f"{BASE_IG}/media_publish", data={
        "creation_id": container_id,
        "access_token": IG_ACCESS_TOKEN,
    }, timeout=30)
    if r.status_code != 200:
        log(f"Publish error: {r.status_code} - {r.text}")
        r.raise_for_status()
    data = r.json()
    if "id" not in data:
        raise RuntimeError(f"Publish failed: {data}")
    log(f"Published! Post ID: {data['id']}")
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
        "caption_preview": caption[:100],
        "error": error,
    })
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)

def main():
    print(f"\n{'='*60}")
    print(f"  Instagram AI AutoPoster  |  Slot {POST_SLOT}  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"  Niche: {NICHE}")
    print(f"{'='*60}\n")

    missing = [k for k, v in {
        "IG_USER_ID": IG_USER_ID,
        "IG_ACCESS_TOKEN": IG_ACCESS_TOKEN,
        "ANTHROPIC_API_KEY": ANTHROPIC_KEY,
    }.items() if not v]
    if missing:
        log(f"ERROR: Missing secrets: {', '.join(missing)}")
        sys.exit(1)

    log(f"API Key loaded: sk-ant-...{ANTHROPIC_KEY[-6:]}")

    try:
        caption   = generate_caption(POST_SLOT)
        image_url = get_image_url(POST_SLOT)
        container_id = create_container(image_url, caption)
        if not wait_container(container_id):
            raise TimeoutError("Container never reached FINISHED state.")
        post_id = publish(container_id)
        save_log(POST_SLOT, "success", post_id, caption)
        print(f"\n✅  Slot {POST_SLOT} posted successfully!\n")
    except Exception as e:
        log(f"FAILED: {e}")
        save_log(POST_SLOT, "error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
