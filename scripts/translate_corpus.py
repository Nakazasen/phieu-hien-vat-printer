import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
import hashlib

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pptx_translation.glossary import MANUFACTURING_GLOSSARY, translate_with_glossary

CJK_REGEX = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]')

cache_file = os.path.join(PROJECT_ROOT, "output", "translation_cache.json")
cache = {}
if os.path.exists(cache_file):
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        cache = {}

def online_translate_google(text: str) -> str:
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "ja",
        "tl": "vi",
        "dt": "t",
        "q": text,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                parts = [s[0] for s in data[0] if s and s[0]]
                return "".join(parts).strip()
    except Exception as e:
        pass
    return None

def online_translate_mymemory(text: str) -> str:
    url = "https://api.mymemory.translated.net/get"
    params = {
        "q": text,
        "langpair": "ja|vi"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and "responseData" in data and "translatedText" in data["responseData"]:
                res = data["responseData"]["translatedText"]
                if res and not res.startswith("MYMEMORY WARNING"):
                    return res.strip()
    except Exception:
        pass
    return None

def contains_japanese(text: str) -> bool:
    return bool(CJK_REGEX.search(text))

# Load extracted texts
extracted_json = os.path.join(PROJECT_ROOT, "output", "extracted_japanese_texts.json")
with open(extracted_json, "r", encoding="utf-8") as f:
    texts = json.load(f)

print(f"Translating {len(texts)} unique texts...")

for idx, text in enumerate(texts, 1):
    cleaned = text.strip()
    if not cleaned or not contains_japanese(cleaned):
        continue

    cache_key = hashlib.md5(cleaned.encode("utf-8")).hexdigest()
    if cache_key in cache and not contains_japanese(cache[cache_key]):
        continue

    # Attempt Google Translate
    trans = online_translate_google(cleaned)
    if not trans or contains_japanese(trans):
        time.sleep(0.3)
        trans = online_translate_mymemory(cleaned)

    if not trans or contains_japanese(trans):
        trans = translate_with_glossary(cleaned)

    # Post-process with glossary
    for ja, vi in sorted(MANUFACTURING_GLOSSARY.items(), key=lambda x: len(x[0]), reverse=True):
        if ja in trans:
            trans = trans.replace(ja, vi)

    # Normalize symbols
    replacements = {
        "、": ", ",
        "。": ". ",
        "（": " (",
        "）": ") ",
        "【": " [",
        "】": "] ",
        "「": ' "',
        "」": '" ',
        "：": ": ",
        "；": "; ",
        "　": " ",
        "〜": "~",
        "～": "~",
        "ー": "-",
    }
    for k, v in replacements.items():
        trans = trans.replace(k, v)

    cache[cache_key] = trans
    if idx % 20 == 0 or idx == len(texts):
        print(f"[{idx}/{len(texts)}] Progress... (CJK remaining: {contains_japanese(trans)})")
    time.sleep(0.08)

with open(cache_file, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f"Saved {len(cache)} translations to cache.")

# Check for residual CJK in cache
untranslated = []
for k, v in cache.items():
    if contains_japanese(v):
        untranslated.append((k, v))

print(f"Total entries with residual CJK in cache: {len(untranslated)}")
if untranslated:
    for k, v in untranslated[:10]:
        print(f"  * {v}")
