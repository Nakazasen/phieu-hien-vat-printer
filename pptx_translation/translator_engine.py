"""
Robust Multi-Tier Japanese-to-Vietnamese Translation Engine.
Features local disk caching, domain glossary prioritization, online translation fallback,
and CJK character detection.
"""

import os
import re
import json
import time
import urllib.request
import urllib.parse
import hashlib
from typing import Dict, Optional, List
from .glossary import MANUFACTURING_GLOSSARY, translate_with_glossary


class PPTXTranslatorEngine:
    """
    Translates Japanese text to Vietnamese with paragraph-level semantics,
    domain glossary injection, persistent caching, and network retries.
    """

    CJK_REGEX = re.compile(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff66-\uff9f]')

    def __init__(self, cache_file: Optional[str] = None):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cache_file = cache_file or os.path.join(project_root, "output", "translation_cache.json")
        self.cache: Dict[str, str] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Loads cached translations from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save_cache(self) -> None:
        """Saves cached translations to disk."""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    @classmethod
    def contains_japanese(cls, text: str) -> bool:
        """Checks if text contains Japanese/CJK characters."""
        if not text:
            return False
        return bool(cls.CJK_REGEX.search(text))

    def translate_text(self, text: str) -> str:
        """
        Translates a Japanese text string or paragraph to Vietnamese.
        If no Japanese characters are detected, returns original text.
        """
        if not text or not text.strip():
            return text

        cleaned_text = text.strip()
        if not self.contains_japanese(cleaned_text):
            return text

        cache_key = hashlib.md5(cleaned_text.encode("utf-8")).hexdigest()
        if cache_key in self.cache and not self.contains_japanese(self.cache[cache_key]):
            return self._preserve_outer_whitespace(text, self.cache[cache_key])

        # Step 1: Direct exact match in glossary
        if cleaned_text in MANUFACTURING_GLOSSARY:
            translated = MANUFACTURING_GLOSSARY[cleaned_text]
            self.cache[cache_key] = translated
            self._save_cache()
            return self._preserve_outer_whitespace(text, translated)

        # Step 2: Attempt online high-quality translation
        translated = self._online_translate(cleaned_text)
        
        # Step 3: If online translation failed or left untranslated Japanese, apply glossary mapping
        if not translated or self.contains_japanese(translated):
            translated = translate_with_glossary(cleaned_text)

        # Step 4: Final glossary polish to ensure consistent terminology
        translated = self._apply_glossary_enforcement(translated)

        # Step 5: Normalize Japanese punctuation, prolonged sound marks and dashes
        translated = self._normalize_japanese_symbols(translated)

        # Step 6: Guarantee zero residual CJK
        if self.contains_japanese(translated):
            translated = self._apply_glossary_enforcement(translated)
            translated = translate_with_glossary(translated)
            translated = self._normalize_japanese_symbols(translated)

        self.cache[cache_key] = translated
        self._save_cache()
        return self._preserve_outer_whitespace(text, translated)

    def _online_translate(self, text: str, retries: int = 3) -> Optional[str]:
        """
        Translates text via Google Translate and MyMemory API endpoints with fallback.
        """
        # 1. Google Translate Single API
        google_url = "https://translate.googleapis.com/translate_a/single"
        google_params = {
            "client": "gtx",
            "sl": "ja",
            "tl": "vi",
            "dt": "t",
            "q": text,
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }

        for attempt in range(retries):
            try:
                encoded_params = urllib.parse.urlencode(google_params)
                full_url = f"{google_url}?{encoded_params}"
                req = urllib.request.Request(full_url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    raw_data = response.read().decode("utf-8")
                    data = json.loads(raw_data)
                    
                    if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                        translated_parts = [segment[0] for segment in data[0] if segment and segment[0]]
                        res = "".join(translated_parts).strip()
                        if res and not self.contains_japanese(res):
                            return res
            except Exception:
                time.sleep(0.4 * (attempt + 1))

        # 2. MyMemory Fallback
        try:
            mm_url = f"https://api.mymemory.translated.net/get?{urllib.parse.urlencode({'q': text, 'langpair': 'ja|vi'})}"
            req = urllib.request.Request(mm_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data and "responseData" in data and "translatedText" in data["responseData"]:
                    res = data["responseData"]["translatedText"]
                    if res and not res.startswith("MYMEMORY WARNING") and not self.contains_japanese(res):
                        return res.strip()
        except Exception:
            pass

        return None

    def _normalize_japanese_symbols(self, text: str) -> str:
        """Converts Japanese punctuation and prolonged sound marks to standard equivalents."""
        if not text:
            return text
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
        res = text
        for k, v in replacements.items():
            res = res.replace(k, v)
        return res

    def _apply_glossary_enforcement(self, text: str) -> str:
        """
        Ensures all key technical terms strictly conform to the engineering glossary.
        """
        enforced = text
        for ja_term, vi_term in sorted(MANUFACTURING_GLOSSARY.items(), key=lambda x: len(x[0]), reverse=True):
            if ja_term in enforced:
                enforced = enforced.replace(ja_term, vi_term)
        return enforced

    @staticmethod
    def _preserve_outer_whitespace(original: str, translated: str) -> str:
        """Preserves leading and trailing whitespace/newlines from original string."""
        leading = original[:len(original) - len(original.lstrip())]
        trailing = original[len(original.rstrip()):]
        return f"{leading}{translated}{trailing}"
