"""
Instagram Auto-Poster with AI-generated captions + images.
"""
import os, sys, json, time, requests
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

    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    log(f"Calling Anthropic API...")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if r.status_code != 200:
        log(f"Anthropic API error: {r.status_code} - {r.text}")
        r.raise_for_status()

    caption = r.json()["content"][0]["text"].strip()
    log(f"Caption generated: {caption[:80]}...")
    return caption

def generate_image_prompt(caption, slot):
    theme = SLOT_THEMES.get(slot, "daily inspiration")
    log("Generating image prompt...")

    prompt = (
        f"Create a short image generation prompt (max 20 words) for an Instagram post.\n"
        f"Theme: {theme}\n"
        f"Style: photorealistic, bright, aesthetic, Instagram-worthy.\n"
        f"Return ONLY the image prompt, nothing else."
    )

    headers = {
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers=headers,
        json={
            "model": "claude-opus-4-5",
            "max_tokens": 80,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=20,
    )

    if r.status_code != 200:
        log(f"Anthropic API error: {r.status_code} - {r.text}")
        r.raise_for_status()

    img_prompt = r.json()["content"][0]["text"].strip()
    log(f"Image prompt: {img_prompt}")
    return img_prompt

def generate_image_url(img_prompt, slot):
    log("Generating image via Pollinations.ai...")
    safe_prompt = requests.utils.quote(img_prompt)
    seed = int(slot) * 1000 + int(datetime.now(timezone.utc).strftime("%j"))
    image_url = (
        f"https://image.pollinations.ai/prompt/{safe_prompt}"
        f"?width=1080&height=1080&seed={seed}&nologo=true&enhance=true"
    )
    log(f"Verifying image URL...")
    check = requests.head(image_url, timeout=30, allow_redirects=True)
    if check.status_code != 200:
        raise RuntimeError(f"Image URL not reachable: {check.status_code}")
    log(f"Image URL ready!")
    return image_url

def create_container(image_url, caption):
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

def save_log(slot, status, post_id="", caption="", image_url="", error=""):
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

    log(f"API Key loaded: sk-ant-...{ANTHROPIC_KEY[-6:] if len(ANTHROPIC_KEY) > 6 else '???'}")

    try:
        caption = generate_caption(POST_SLOT)
        img_prompt = generate_image_prompt(caption, POST_SLOT)
        image_url = generate_image_url(img_prompt, POST_SLOT)
        container_id = create_container(image_url, caption)
        if not wait_container(container_id):
            raise TimeoutError("Container never reached FINISHED state.")
        post_id = publish(container_id)
        save_log(POST_SLOT, "success", post_id, caption, image_url)
        print(f"\n✅  Slot {POST_SLOT} posted successfully!\n")
    except Exception as e:
        log(f"FAILED: {e}")
        save_log(POST_SLOT, "error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
