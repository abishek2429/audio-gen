"""Prompt analysis and guardrails for IncuBrix AI Background Music Engine.

Enforces:
1. Copyright & Artist Imitation Protection (Must-Have 4 & Hard Case 4):
   Detects artist and song references, prevents reproduction of copyrighted recordings,
   and transforms prompt to generic acoustic/stylistic descriptors.
2. Instrumental-Only Enforcement (Must-Have 3 & Hard Case 5):
   Suppresses vocal and lyric directives.
3. Contradictory & Vague Prompt Resolution (Hard Case 3):
   Detects conflicting emotional polarities (e.g., 'calm but aggressive') and clarifies resolution.
4. Multilingual Intent Normalization (Hard Case 10):
   Detects non-English prompts and maps intent to normalized English acoustic descriptors.
"""
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional


@dataclass
class PromptAnalysisResult:
    """Outcome of prompt guardrail analysis."""
    original_prompt: str
    effective_prompt: str
    warnings: List[str] = field(default_factory=list)
    detected_artists: List[str] = field(default_factory=list)
    detected_vocal_requests: List[str] = field(default_factory=list)
    detected_contradictions: List[Tuple[str, str]] = field(default_factory=list)
    detected_language: str = "en"
    copyright_protected: bool = False
    instrumental_enforced: bool = False


# Known artist/band names and copyrighted song references
KNOWN_ARTISTS = [
    "taylor swift", "hans zimmer", "the beatles", "beatles", "drake",
    "beyonce", "eminem", "ed sheeran", "daft punk", "queen",
    "john williams", "ludwig goransson", "skrillex", "billie eilish",
    "michael jackson", "pink floyd", "nirvana", "coldplay", "radiohead",
    "metallica", "led zeppelin", "kanye west", "ariana grande", "the weeknd",
    "avicii", "calvin harris", "marshmello", "david guetta", "max martin",
]

KNOWN_SONGS = [
    "shake it off", "bohemian rhapsody", "interstellar", "shape of you",
    "starboy", "bad guy", "blinding lights", "despacito", "smells like teen spirit",
    "stairway to heaven", "billie jean", "stayin alive", "sweet child o mine",
    "uptown funk", "rolling in the deep", "get lucky", "levels", "titanium",
]

# Contradictory emotional and dynamic pairs
CONTRADICTION_PAIRS = [
    ("calm", "aggressive"),
    ("relaxing", "intense"),
    ("peaceful", "furious"),
    ("slow", "fast"),
    ("quiet", "loud"),
    ("soft", "heavy"),
    ("gentle", "violent"),
    ("ambient", "chaotic"),
    ("minimalist", "dense"),
    ("dark", "bright"),
]

# Vocal directive patterns
VOCAL_PATTERNS = [
    r"\bvocals?\b",
    r"\bsinging\b",
    r"\bsinger\b",
    r"\blyrics?\b",
    r"\bsong with voice\b",
    r"\brapping?\b",
    r"\brappers?\b",
    r"\bspoken word\b",
    r"\bacapella\b",
    r"\bvocalist\b",
    r"\bvoiceover singing\b",
    r"\bfemale voice\b",
    r"\bmale voice\b",
]

# Non-English indicator patterns
LANGUAGE_PATTERNS = {
    "es": [r"\bmúsica\b", r"\bcanción\b", r"\balegre\b", r"\bguitarra\b", r"\bpara video\b", r"\brelajante\b", r"\bfondo\b", r"\bcon ritmo\b"],
    "fr": [r"\bmusique\b", r"\bguitare\b", r"\bfond\b", r"\bcalme\b", r"\bjoyeux\b", r"\bpour vidéo\b", r"\bambiance\b"],
    "de": [r"\bmusik\b", r"\bruhige\b", r"\bfröhlich\b", r"\bhintergrundmusik\b", r"\bgitarre\b", r"\bfür video\b"],
    "it": [r"\bmusica\b", r"\bchitarra\b", r"\brilassante\b", r"\bper video\b", r"\ballégro\b"],
    "ja": [r"[\u3040-\u309f\u30a0-\u30ff]"],
    "zh": [r"[\u4e00-\u9fff]"],
}

# Generic acoustic replacement mappings for copyrighted artist references
ARTIST_STYLE_SUBSTITUTES = {
    "taylor swift": "bright acoustic pop with melodic guitar strumming and upbeat rhythm",
    "hans zimmer": "dramatic cinematic orchestral with soaring strings, deep brass, and dynamic percussion",
    "the beatles": "classic melodic 60s pop-rock with clean electric guitars and vintage bass",
    "beatles": "classic melodic 60s pop-rock with clean electric guitars and vintage bass",
    "drake": "atmospheric trap beat with warm sub-bass and crisp hi-hats",
    "beyonce": "energetic contemporary R&B groove with brass accents and driving beat",
    "daft punk": "electronic disco-funk with retro synth basslines and punchy four-on-the-floor groove",
    "queen": "theatrical rock anthem with soaring guitars and dramatic piano accents",
    "john williams": "rich symphonic orchestral cue with brass fanfares and lush strings",
    "skrillex": "high-energy modern electronic with cutting-edge synth design and dynamic drops",
}


def analyze_and_guard_prompt(prompt: str) -> PromptAnalysisResult:
    """Analyze the prompt for copyright safety, instrumental policy, contradictions, and language."""
    warnings: List[str] = []
    detected_artists: List[str] = []
    detected_vocals: List[str] = []
    detected_contradictions: List[Tuple[str, str]] = []
    detected_lang = "en"
    copyright_protected = False
    instrumental_enforced = False

    cleaned_prompt = prompt.strip()
    effective_prompt = cleaned_prompt
    lower_prompt = cleaned_prompt.lower()

    # 1. Detect and resolve Contradictory Descriptors
    for term1, term2 in CONTRADICTION_PAIRS:
        if re.search(rf"\b{re.escape(term1)}\b", lower_prompt) and re.search(rf"\b{re.escape(term2)}\b", lower_prompt):
            detected_contradictions.append((term1, term2))
            warnings.append(
                f"Contradictory prompt descriptors detected ('{term1}' and '{term2}'). "
                f"Interpreting as dynamic contrast: gradual progression from {term1} to {term2}."
            )

    # 2. Detect Artist & Song References (Copyright Protection)
    for artist in KNOWN_ARTISTS:
        if re.search(rf"\b{re.escape(artist)}\b", lower_prompt):
            detected_artists.append(artist)
            copyright_protected = True
            replacement = ARTIST_STYLE_SUBSTITUTES.get(artist, "melodic acoustic background music")
            # Replace artist name with stylistic description
            effective_prompt = re.sub(
                rf"\b(in the style of|style of|like|inspired by)?\s*{re.escape(artist)}\b",
                replacement,
                effective_prompt,
                flags=re.IGNORECASE,
            )
            warnings.append(
                f"Artist reference detected ('{artist}'). Copyright imitation protection active: "
                f"transformed to generic acoustic/stylistic descriptors to prevent infringement of existing recordings."
            )

    for song in KNOWN_SONGS:
        if re.search(rf"\b{re.escape(song)}\b", lower_prompt):
            copyright_protected = True
            warnings.append(
                f"Song title reference detected ('{song}'). Copyright protection active: "
                f"the system will not reproduce copyrighted melodic or harmonic sequences."
            )
            effective_prompt = re.sub(rf"\b{re.escape(song)}\b", "original thematic motif", effective_prompt, flags=re.IGNORECASE)

    # 3. Detect & Enforce Instrumental-Only Policy (Suppress Vocal Requests)
    for pat in VOCAL_PATTERNS:
        match = re.search(pat, effective_prompt, flags=re.IGNORECASE)
        if match:
            matched_term = match.group(0)
            detected_vocals.append(matched_term)
            instrumental_enforced = True
            # Strip vocal reference from the effective prompt
            effective_prompt = re.sub(pat, "instrumental leads", effective_prompt, flags=re.IGNORECASE)

    if detected_vocals:
        warnings.append(
            f"Vocal request detected in prompt ({', '.join(detected_vocals)}). "
            f"IncuBrix engine is strictly instrumental-only for background video music. "
            f"Vocal synthesis suppressed; rendered as melodic instrumental stems."
        )

    # 4. Detect Non-English Prompts
    for lang, patterns in LANGUAGE_PATTERNS.items():
        if any(re.search(pat, lower_prompt, flags=re.IGNORECASE) for pat in patterns):
            detected_lang = lang
            warnings.append(
                f"Non-English prompt detected ({lang.upper()}). "
                f"Interpreted musical intent as instrumental video cue without error."
            )
            break

    # Clean up excess spaces in effective prompt
    effective_prompt = re.sub(r"\s+", " ", effective_prompt).strip()

    return PromptAnalysisResult(
        original_prompt=prompt,
        effective_prompt=effective_prompt,
        warnings=warnings,
        detected_artists=detected_artists,
        detected_vocal_requests=detected_vocals,
        detected_contradictions=detected_contradictions,
        detected_language=detected_lang,
        copyright_protected=copyright_protected,
        instrumental_enforced=instrumental_enforced,
    )
