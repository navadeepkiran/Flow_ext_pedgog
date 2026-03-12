"""Code-Mixed Language Normalizer.

Converts Hinglish (Hindi-English) and Tenglish (Telugu-English) code-mixed
text to normalized English. Preserves technical/domain terms while translating
Hindi/Telugu connectors, verbs, and pedagogical cues.
"""

import json
import os
import re

from utils.config import load_config, resolve_path
from utils.helpers import load_json
from utils.logger import get_logger

logger = get_logger(__name__)


def _transliterate_urdu(text: str) -> str:
    """Convert Urdu/Arabic script to Roman/Latin script.

    Handles mixed-script text — only converts Arabic/Urdu range characters,
    everything else passes through unchanged.
    """
    # Urdu letter → Roman mapping
    letter_map = {
        '\u0622': 'aa',   # آ alif madda
        '\u0627': 'a',    # ا alif
        '\u0628': 'b',    # ب
        '\u067E': 'p',    # پ
        '\u062A': 't',    # ت
        '\u0679': 't',    # ٹ
        '\u062B': 's',    # ث
        '\u062C': 'j',    # ج
        '\u0686': 'ch',   # چ
        '\u062D': 'h',    # ح
        '\u062E': 'kh',   # خ
        '\u062F': 'd',    # د
        '\u0688': 'd',    # ڈ
        '\u0630': 'z',    # ذ
        '\u0631': 'r',    # ر
        '\u0691': 'r',    # ڑ
        '\u0632': 'z',    # ز
        '\u0698': 'zh',   # ژ
        '\u0633': 's',    # س
        '\u0634': 'sh',   # ش
        '\u0635': 's',    # ص
        '\u0636': 'z',    # ض
        '\u0637': 't',    # ط
        '\u0638': 'z',    # ظ
        '\u0639': '',     # ع ain — silent in casual romanization
        '\u063A': 'gh',   # غ
        '\u0641': 'f',    # ف
        '\u0642': 'q',    # ق
        '\u0643': 'k',    # ك (Arabic kaf)
        '\u06A9': 'k',    # ک (Urdu kaf)
        '\u06AF': 'g',    # گ
        '\u0644': 'l',    # ل
        '\u0645': 'm',    # م
        '\u0646': 'n',    # ن
        '\u06BA': 'n',    # ں noon ghunna
        '\u0648': 'o',    # و
        '\u06C1': 'h',    # ہ (Urdu he)
        '\u06C3': 'h',    # ۃ (ta marbuta)
        '\u06BE': 'h',    # ھ (do-chashmi he)
        '\u0647': 'h',    # ه (Arabic he)
        '\u06CC': 'i',    # ی (Urdu ye)
        '\u064A': 'y',    # ي (Arabic ye)
        '\u06D2': 'e',    # ے (bari ye)
        '\u0626': '',     # ئ (hamza on ye)
        '\u0621': '',     # ء (hamza)
        '\u0623': 'a',    # أ (hamza on alif)
        '\u0625': 'i',    # إ (hamza below alif)
        '\u0624': 'o',    # ؤ (hamza on waw)
        '\u0670': 'a',    # ٰ (superscript alif)
    }
    # Diacritics (short vowels, etc.)
    diacritic_map = {
        '\u064E': 'a',    # َ fatha / zabar
        '\u0650': 'i',    # ِ kasra / zer
        '\u064F': 'u',    # ُ damma / pesh
        '\u064B': 'an',   # ً tanwin fatha
        '\u064D': 'in',   # ٍ tanwin kasra
        '\u064C': 'un',   # ٌ tanwin damma
        '\u0651': '',     # ّ shadda (handled below)
        '\u0652': '',     # ْ sukun / jazm (silence)
        '\u0654': '',     # ٔ hamza above
        '\u0655': '',     # ٕ hamza below
        '\u0653': '',     # ٓ madda above
        '\u0610': '',     # ؐ sign sallallahu
        '\u0611': '',     # ؑ sign alayhe
        '\u0612': '',     # ؒ sign rahmatullah
        '\u0613': '',     # ؓ sign radi
        '\u0614': '',     # ؔ sign takhallus
        '\u0615': '',     # ؕ small high tah
        '\u0616': '',     # ؖ small high ligature
        '\u0617': '',     # ؗ small high zain
    }
    # Urdu-extended & Arabic digits
    digits_ur = {
        '\u06F0': '0', '\u06F1': '1', '\u06F2': '2', '\u06F3': '3',
        '\u06F4': '4', '\u06F5': '5', '\u06F6': '6', '\u06F7': '7',
        '\u06F8': '8', '\u06F9': '9',
    }
    digits_ar = {
        '\u0660': '0', '\u0661': '1', '\u0662': '2', '\u0663': '3',
        '\u0664': '4', '\u0665': '5', '\u0666': '6', '\u0667': '7',
        '\u0668': '8', '\u0669': '9',
    }
    # Punctuation
    punct_map = {
        '\u061F': '?',    # ؟
        '\u060C': ',',    # ،
        '\u061B': ';',    # ؛
        '\u06D4': '.',    # ۔ (Urdu full stop)
    }

    result = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        # Shadda: repeat the previous consonant
        if ch == '\u0651':
            if result:
                result.append(result[-1])
            i += 1
            continue
        # Diacritics
        if ch in diacritic_map:
            val = diacritic_map[ch]
            if val:
                result.append(val)
            i += 1
            continue
        # Letters (check two-char alif madda first)
        if ch in letter_map:
            result.append(letter_map[ch])
            i += 1
            continue
        # Digits
        if ch in digits_ur:
            result.append(digits_ur[ch])
            i += 1
            continue
        if ch in digits_ar:
            result.append(digits_ar[ch])
            i += 1
            continue
        # Punctuation
        if ch in punct_map:
            result.append(punct_map[ch])
            i += 1
            continue
        # Tatweel (kashida) — decorative, skip
        if ch == '\u0640':
            i += 1
            continue
        # Any other Arabic-block char we missed — skip rather than emit garbage
        if '\u0600' <= ch <= '\u06FF' or '\uFB50' <= ch <= '\uFDFF' or '\uFE70' <= ch <= '\uFEFF':
            i += 1
            continue
        # Everything else (Latin, spaces, etc.) — keep
        result.append(ch)
        i += 1

    return ''.join(result)


def _transliterate_telugu(text: str) -> str:
    """Convert Telugu script (U+0C00-U+0C7F) to Roman/Latin script.

    Handles mixed-script text — only converts Telugu characters,
    everything else passes through unchanged.
    """
    VIRAMA = '\u0C4D'  # ్  (Telugu virama / halant)

    vowels = {
        '\u0C05': 'a',   # అ
        '\u0C06': 'aa',  # ఆ
        '\u0C07': 'i',   # ఇ
        '\u0C08': 'ee',  # ఈ
        '\u0C09': 'u',   # ఉ
        '\u0C0A': 'oo',  # ఊ
        '\u0C0B': 'ru',  # ఋ
        '\u0C0E': 'e',   # ఎ
        '\u0C0F': 'ee',  # ఏ
        '\u0C10': 'ai',  # ఐ
        '\u0C12': 'o',   # ఒ
        '\u0C13': 'oo',  # ఓ
        '\u0C14': 'au',  # ఔ
    }
    matras = {
        '\u0C3E': 'aa',  # ా
        '\u0C3F': 'i',   # ి
        '\u0C40': 'ee',  # ీ
        '\u0C41': 'u',   # ు
        '\u0C42': 'oo',  # ూ
        '\u0C43': 'ru',  # ృ
        '\u0C46': 'e',   # ె
        '\u0C47': 'ee',  # ే
        '\u0C48': 'ai',  # ై
        '\u0C4A': 'o',   # ొ
        '\u0C4B': 'oo',  # ో
        '\u0C4C': 'au',  # ౌ
    }
    consonants = {
        '\u0C15': 'k',   # క
        '\u0C16': 'kh',  # ఖ
        '\u0C17': 'g',   # గ
        '\u0C18': 'gh',  # ఘ
        '\u0C19': 'ng',  # ఙ
        '\u0C1A': 'ch',  # చ
        '\u0C1B': 'chh', # ఛ
        '\u0C1C': 'j',   # జ
        '\u0C1D': 'jh',  # ఝ
        '\u0C1E': 'ny',  # ఞ
        '\u0C1F': 't',   # ట
        '\u0C20': 'th',  # ఠ
        '\u0C21': 'd',   # డ
        '\u0C22': 'dh',  # ఢ
        '\u0C23': 'n',   # ణ
        '\u0C24': 't',   # త
        '\u0C25': 'th',  # థ
        '\u0C26': 'd',   # ద
        '\u0C27': 'dh',  # ధ
        '\u0C28': 'n',   # న
        '\u0C2A': 'p',   # ప
        '\u0C2B': 'ph',  # ఫ
        '\u0C2C': 'b',   # బ
        '\u0C2D': 'bh',  # భ
        '\u0C2E': 'm',   # మ
        '\u0C2F': 'y',   # య
        '\u0C30': 'r',   # ర
        '\u0C31': 'rr',  # ఱ
        '\u0C32': 'l',   # ల
        '\u0C33': 'l',   # ళ
        '\u0C35': 'v',   # వ
        '\u0C36': 'sh',  # శ
        '\u0C37': 'sh',  # ష
        '\u0C38': 's',   # స
        '\u0C39': 'h',   # హ
    }
    digits = {
        '\u0C66': '0', '\u0C67': '1', '\u0C68': '2', '\u0C69': '3',
        '\u0C6A': '4', '\u0C6B': '5', '\u0C6C': '6', '\u0C6D': '7',
        '\u0C6E': '8', '\u0C6F': '9',
    }

    result = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Consonant
        if ch in consonants:
            base = consonants[ch]
            i += 1
            if i < n and text[i] == VIRAMA:
                result.append(base)  # pure consonant, no inherent 'a'
                i += 1
            elif i < n and text[i] in matras:
                result.append(base + matras[text[i]])
                i += 1
            else:
                result.append(base + 'a')  # inherent vowel 'a'
            continue

        # Independent vowel
        if ch in vowels:
            result.append(vowels[ch])
            i += 1
            continue

        # Standalone matra (rare edge case)
        if ch in matras:
            result.append(matras[ch])
            i += 1
            continue

        # Anusvara ం → 'n'
        if ch == '\u0C02':
            result.append('n')
            i += 1
            continue

        # Visarga ః → 'h'
        if ch == '\u0C03':
            result.append('h')
            i += 1
            continue

        # Chandrabindu (rare) ఁ
        if ch == '\u0C01':
            result.append('n')
            i += 1
            continue

        # Stray virama
        if ch == VIRAMA:
            i += 1
            continue

        # Telugu digits
        if ch in digits:
            result.append(digits[ch])
            i += 1
            continue

        # Any other Telugu-block char we missed — skip
        if '\u0C00' <= ch <= '\u0C7F':
            i += 1
            continue

        # Everything else (Latin, spaces, punctuation) — keep
        result.append(ch)
        i += 1

    return ''.join(result)


def transliterate_devanagari(text: str) -> str:
    """Convert Devanagari, Urdu, and/or Telugu script to Roman/Latin script.

    Handles mixed-script text — only converts non-Latin characters,
    everything else passes through unchanged.
    """
    if not text:
        return text
    has_devanagari = any('\u0900' <= c <= '\u097F' for c in text)
    has_urdu = any('\u0600' <= c <= '\u06FF' for c in text)
    has_telugu = any('\u0C00' <= c <= '\u0C7F' for c in text)
    if not has_devanagari and not has_urdu and not has_telugu:
        return text
    # Apply each script transliteration if present
    if has_urdu:
        text = _transliterate_urdu(text)
    if has_telugu:
        text = _transliterate_telugu(text)
    if not has_devanagari:
        return text

    VIRAMA = '\u094D'  # ्
    NUKTA = '\u093C'   # ़

    vowels = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
        'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऋ': 'ri',
    }
    matras = {
        'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
        'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ृ': 'ri',
    }
    consonants = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
        'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    }
    nukta_map = {
        'क': 'q', 'ख': 'kh', 'ग': 'gh', 'ज': 'z',
        'ड': 'r', 'ढ': 'rh', 'फ': 'f',
    }
    digits = {
        '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
        '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    }

    result = []
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        # Nukta consonant (e.g. क़ = क + ़)
        if ch in consonants and i + 1 < n and text[i + 1] == NUKTA:
            base = nukta_map.get(ch, consonants[ch])
            i += 2
            if i < n and text[i] == VIRAMA:
                result.append(base)
                i += 1
            elif i < n and text[i] in matras:
                result.append(base + matras[text[i]])
                i += 1
            else:
                result.append(base + 'a')
            continue

        # Regular consonant
        if ch in consonants:
            base = consonants[ch]
            i += 1
            if i < n and text[i] == VIRAMA:
                result.append(base)
                i += 1
            elif i < n and text[i] in matras:
                result.append(base + matras[text[i]])
                i += 1
            else:
                result.append(base + 'a')
            continue

        # Independent vowel
        if ch in vowels:
            result.append(vowels[ch])
            i += 1
            continue

        # Standalone matra
        if ch in matras:
            result.append(matras[ch])
            i += 1
            continue

        # Anusvara / Chandrabindu
        if ch in ('ं', 'ँ'):
            result.append('n')
            i += 1
            continue

        # Visarga
        if ch == 'ः':
            result.append('h')
            i += 1
            continue

        # Stray virama or nukta
        if ch in (VIRAMA, NUKTA):
            i += 1
            continue

        # Devanagari digits
        if ch in digits:
            result.append(digits[ch])
            i += 1
            continue

        # Danda (।) → period
        if ch in ('।', '॥'):
            result.append('.')
            i += 1
            continue

        # Everything else (Latin, spaces, punctuation) — keep as-is
        result.append(ch)
        i += 1

    return ''.join(result)


class CodeMixedNormalizer:
    """Normalizes code-mixed (Hinglish / Tenglish) transcript text to English."""

    def __init__(self, lexicon_path: str = None):
        """Initialize normalizer with Hinglish + Telugu lexicons.

        Args:
            lexicon_path: Path to hinglish_lexicon.json.
                          Defaults to config value.
        """
        cfg = load_config()
        if lexicon_path is None:
            lexicon_path = cfg["normalizer"]["lexicon_path"]

        raw = load_json(lexicon_path)

        # Build a flat word→translation lookup (skip _meta)
        self.word_map = {}
        for category, entries in raw.items():
            if category.startswith("_"):
                continue
            if isinstance(entries, dict):
                for hindi_word, english_word in entries.items():
                    self.word_map[hindi_word.lower()] = english_word

        # Load Telugu-English lexicon (alongside Hinglish)
        telugu_path = cfg["normalizer"].get("telugu_lexicon_path", "data/telugu_english_lexicon.json")
        try:
            telugu_raw = load_json(telugu_path)
            for category, entries in telugu_raw.items():
                if category.startswith("_"):
                    continue
                if isinstance(entries, dict):
                    for telugu_word, english_word in entries.items():
                        if telugu_word.lower() not in self.word_map:
                            self.word_map[telugu_word.lower()] = english_word
            logger.info("Telugu lexicon loaded from: %s", telugu_path)
        except Exception:
            logger.debug("Telugu lexicon not found at %s, skipping", telugu_path)

        # Multi-word phrase patterns (longer phrases first for greedy match)
        self.phrase_patterns = self._build_phrase_patterns()

        # Sentence-level pedagogical patterns for relationship extraction
        self.pedagogical_patterns = self._build_pedagogical_patterns()

        logger.info(
            "Normalizer loaded: %d word mappings, %d phrase patterns",
            len(self.word_map),
            len(self.phrase_patterns),
        )

    def _build_phrase_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Build regex patterns for multi-word Hindi phrases.

        Returns:
            List of (compiled_regex, replacement_string) tuples,
            sorted by phrase length (longest first).
        """
        phrases = []

        # Multi-word entries from the lexicon
        multi_word_entries = [
            (k, v) for k, v in self.word_map.items() if " " in k and v
        ]
        # Sort longest-first to match greedily
        multi_word_entries.sort(key=lambda x: len(x[0]), reverse=True)

        for hindi_phrase, english_phrase in multi_word_entries:
            pattern = re.compile(
                r"\b" + re.escape(hindi_phrase) + r"\b", re.IGNORECASE
            )
            phrases.append((pattern, english_phrase))

        return phrases

    def _build_pedagogical_patterns(self) -> list[tuple[re.Pattern, str]]:
        """Build patterns that detect pedagogical relationship cues.

        These patterns are used later by the dependency detector
        but normalized here for reuse.

        Returns:
            List of (pattern, template) tuples.
        """
        patterns = [
            # "pehle X samjho phir Y" → prerequisite(X, Y)
            (
                re.compile(
                    r"peh?le\s+(.+?)\s+(?:samjho|seekho|padho)\s+(?:phir|fir|tab)\s+(.+?)(?:\s|$)",
                    re.IGNORECASE,
                ),
                "first understand {0} then {1}",
            ),
            # "pehle X phir Y"
            (
                re.compile(
                    r"peh?le\s+(.+?)\s+(?:phir|fir)\s+(.+?)(?:\s|$)",
                    re.IGNORECASE,
                ),
                "first {0} then {1}",
            ),
            # "X ke baad Y"
            (
                re.compile(
                    r"(.+?)\s+ke\s+baad\s+(.+?)(?:\s|$)",
                    re.IGNORECASE,
                ),
                "after {0} comes {1}",
            ),
            # "X pe depend karta hai Y" or "Y X pe depend"
            (
                re.compile(
                    r"(.+?)\s+(?:pe|par)\s+depend\s+(?:karta|karti|karte)\s+(?:hai|hain)",
                    re.IGNORECASE,
                ),
                "{0} depends on this",
            ),
            # "X zaruri hai Y ke liye"
            (
                re.compile(
                    r"(.+?)\s+(?:zaruri|zaroori)\s+hai\s+(.+?)\s+ke\s+liye",
                    re.IGNORECASE,
                ),
                "{0} is necessary for {1}",
            ),
            # "X ka concept Y pe based hai"
            (
                re.compile(
                    r"(.+?)\s+(?:pe|par)\s+based\s+hai",
                    re.IGNORECASE,
                ),
                "{0} is based on this",
            ),
            # "X ke bina Y nahi"
            (
                re.compile(
                    r"(.+?)\s+ke\s+bina\s+(.+?)\s+nahi",
                    re.IGNORECASE,
                ),
                "without {0}, {1} is not possible",
            ),
            # ── Telugu pedagogical patterns ──
            # "mundu X nerchukondi tarvata Y" → prerequisite(X, Y)
            (
                re.compile(
                    r"mund(?:u|hu)\s+(.+?)\s+(?:nerchukondi|ardham\s+chesuko|chaduvukondi)\s+(?:tarvata|tarvaata)\s+(.+?)(?:\s|$)",
                    re.IGNORECASE,
                ),
                "first understand {0} then {1}",
            ),
            # "mundu X tarvata Y"
            (
                re.compile(
                    r"mund(?:u|hu)\s+(.+?)\s+(?:tarvata|tarvaata)\s+(.+?)(?:\s|$)",
                    re.IGNORECASE,
                ),
                "first {0} then {1}",
            ),
            # "X tarvata Y"
            (
                re.compile(
                    r"(.+?)\s+(?:tarvata|tarvaata)\s+(.+?)(?:\s|$)",
                    re.IGNORECASE,
                ),
                "after {0} comes {1}",
            ),
            # "X meeda depend avuthundi"
            (
                re.compile(
                    r"(.+?)\s+(?:meeda|pyna)\s+depend\s+(?:avuthundi|avtundi)",
                    re.IGNORECASE,
                ),
                "{0} depends on this",
            ),
            # "X avasaram Y kosam"
            (
                re.compile(
                    r"(.+?)\s+(?:avasaram|avsaram)\s+(.+?)\s+kosam",
                    re.IGNORECASE,
                ),
                "{0} is necessary for {1}",
            ),
            # "X meeda based"
            (
                re.compile(
                    r"(.+?)\s+(?:meeda|pyna)\s+based",
                    re.IGNORECASE,
                ),
                "{0} is based on this",
            ),
            # "X lekunda Y kaadu"
            (
                re.compile(
                    r"(.+?)\s+lekunda\s+(.+?)\s+kaadu",
                    re.IGNORECASE,
                ),
                "without {0}, {1} is not possible",
            ),
        ]
        return patterns

    def normalize_text(self, text: str) -> str:
        """Normalize a single text string from Hinglish to English.

        Args:
            text: Raw code-mixed text.

        Returns:
            Normalized English text.
        """
        if not text or not text.strip():
            return text

        # Step 0: Transliterate any Devanagari to Roman
        result = transliterate_devanagari(text)

        # Step 1: Apply multi-word phrase replacements first
        for pattern, replacement in self.phrase_patterns:
            result = pattern.sub(replacement, result)

        # Step 2: Word-level replacements
        words = result.split()
        normalized_words = []
        for word in words:
            clean = word.strip(".,!?;:()[]{}\"'").lower()
            if clean in self.word_map and self.word_map[clean]:
                # Preserve original punctuation
                prefix = ""
                suffix = ""
                for ch in word:
                    if ch.isalnum():
                        break
                    prefix += ch
                for ch in reversed(word):
                    if ch.isalnum():
                        break
                    suffix = ch + suffix
                normalized_words.append(prefix + self.word_map[clean] + suffix)
            else:
                normalized_words.append(word)

        result = " ".join(normalized_words)
        return result

    def normalize_transcript(self, transcript: dict) -> dict:
        """Normalize a full transcript with segments.

        If the transcript already contains dual-pass data (original_text per
        segment from Hindi transcription and text from English translation),
        transliterate the Hindi to Roman and keep the English as-is.
        Otherwise fall back to rule-based normalization.

        Args:
            transcript: Transcript dict with 'segments' and 'full_text' keys.

        Returns:
            New transcript dict with normalized text added.
        """
        logger.info("Normalizing transcript: %s", transcript.get("video_id", "unknown"))

        normalized_segments = []
        normalized_full_parts = []
        original_full_parts = []

        # Check if transcript already has dual-pass data from Whisper
        has_dual = "original_full_text" in transcript

        for seg in transcript.get("segments", []):
            if has_dual and seg.get("original_text"):
                # Dual-pass: transliterate Hindi original to Roman, keep English text
                roman_text = transliterate_devanagari(seg["original_text"])
                normalized_text = seg.get("text", roman_text)
            else:
                # Single-pass fallback: rule-based normalization
                raw_text = seg.get("text", "")
                roman_text = transliterate_devanagari(raw_text)
                normalized_text = self.normalize_text(raw_text)

            new_seg = dict(seg)
            new_seg["original_text"] = roman_text
            new_seg["text"] = normalized_text
            normalized_segments.append(new_seg)
            normalized_full_parts.append(normalized_text)
            original_full_parts.append(roman_text)

        result = dict(transcript)
        if has_dual:
            # Transliterate the full Hindi text to Roman
            result["original_full_text"] = transliterate_devanagari(
                transcript["original_full_text"]
            )
            result["full_text"] = transcript["full_text"]
        else:
            result["original_full_text"] = " ".join(original_full_parts)
            result["full_text"] = " ".join(normalized_full_parts)
        result["segments"] = normalized_segments
        result["normalization_applied"] = True

        logger.info("Normalization complete: %d segments processed", len(normalized_segments))
        return result

    def detect_pedagogical_cues(self, text: str) -> list[dict]:
        """Detect pedagogical relationship cues in text.

        This helps the dependency detector downstream.

        Args:
            text: Raw or normalized text to scan.

        Returns:
            List of detected cue dicts with pattern info.
        """
        cues = []
        for pattern, template in self.pedagogical_patterns:
            for match in pattern.finditer(text):
                cue = {
                    "matched_text": match.group(0),
                    "groups": list(match.groups()),
                    "template": template,
                    "start_pos": match.start(),
                    "end_pos": match.end(),
                }
                cues.append(cue)
        return cues
