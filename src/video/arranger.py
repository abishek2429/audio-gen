"""Musical arrangement engine converting video visual metrics into structured, timestamped music plans."""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.models import SectionPlan
from src.video.analyzer import VideoAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class MusicalAccent:
    """Timestamped musical accent aligned with a visual event."""
    timestamp_s: float
    event_description: str
    musical_action: str


@dataclass
class MusicPlan:
    """Structured musical composition plan tailored to video duration, pacing, and visual cuts."""
    genre: str
    mood: str
    tempo_bpm: int
    key: str
    rhythmic_style: str
    intensity: str
    instrumentation: List[str]
    target_duration_s: float
    sections: List[SectionPlan]
    accents: List[MusicalAccent]
    prompt: str


class VideoArranger:
    """Translates computer-vision video analysis into structured musical arrangement plans."""

    STYLE_PROFILES = {
        "cinematic": {
            "genre": "Cinematic Orchestral",
            "base_bpm": 92,
            "key": "D minor",
            "rhythmic_style": "Half-time cinematic groove with orchestral timpani and hybrid risers",
            "intensity": "dynamic building",
            "instrumentation": ["soaring orchestral strings", "warm french horns", "deep sub-bass", "epic cinematic percussion", "legato cellos"],
            "prompt_template": "dramatic cinematic orchestral, soaring strings, warm brass swells, hybrid cinematic percussion, building tension and emotional climax",
        },
        "electronic": {
            "genre": "Modern Electronic",
            "base_bpm": 126,
            "key": "A minor",
            "rhythmic_style": "Driving 4/4 electronic beat with sidechained bass and rhythmic arpeggios",
            "intensity": "high",
            "instrumentation": ["pulsating analog synths", "punchy electronic kick and snare", "grooving synth bass", "crisp hi-hats", "melodic lead pluck"],
            "prompt_template": "modern driving electronic synthwave, punchy drum machine groove, pulsating melodic bassline, crisp synth textures, high energy",
        },
        "corporate": {
            "genre": "Uplifting Acoustic & Tech",
            "base_bpm": 114,
            "key": "C major",
            "rhythmic_style": "Bright syncopated acoustic groove with light hand percussion",
            "intensity": "medium",
            "instrumentation": ["bright acoustic guitars", "warm upright piano", "subtle acoustic bass", "light shaker and claps", "glockenspiel bells"],
            "prompt_template": "uplifting tech corporate acoustic, bright acoustic guitar picking, light optimistic piano, warm organic percussion, inspiring progress",
        },
        "lo_fi": {
            "genre": "Lo-Fi Chillhop",
            "base_bpm": 84,
            "key": "F major",
            "rhythmic_style": "Laid-back swung boom-bap rhythm with subtle vinyl warmth",
            "intensity": "low",
            "instrumentation": ["dusty electric piano Rhodes", "warm 808 sub-bass", "swung lo-fi drum beats", "mellow guitar licks", "vinyl crackle texture"],
            "prompt_template": "relaxing lo-fi chillhop, vintage electric piano chords, mellow swung drum groove, warm tape saturation, nostalgic peaceful atmosphere",
        },
        "ambient": {
            "genre": "Ambient & Atmospheric",
            "base_bpm": 74,
            "key": "E minor",
            "rhythmic_style": "Slow-tempo evolving soundscape with gentle percussive textures",
            "intensity": "low",
            "instrumentation": ["lush evolving synthesizer pads", "delicate reverb piano", "drone sub-bass", "crystal shimmer textures", "distant chimes"],
            "prompt_template": "atmospheric ambient soundscape, deep evolving synthesizer pads, gentle echoing piano notes, serene contemplative space",
        },
        "action": {
            "genre": "Driving Action & Rock",
            "base_bpm": 136,
            "key": "E minor",
            "rhythmic_style": "Heavy driving rock beat with fast syncopated drums and aggressive bass",
            "intensity": "high",
            "instrumentation": ["distorted rhythm guitars", "driving live rock drums", "growling electric bass", "percussive crash cymbals", "melodic guitar riffs"],
            "prompt_template": "driving action rock, high energy distorted guitars, powerful live acoustic drum beats, aggressive driving bassline, adrenaline rush",
        },
    }

    def create_plan(
        self,
        analysis: VideoAnalysisResult,
        style_preference: Optional[str] = None,
        custom_prompt_override: Optional[str] = None,
    ) -> MusicPlan:
        """Generate a complete musical arrangement plan tailored to video duration, cuts, and visual activity."""
        duration = analysis.metadata.duration_s
        activity = analysis.activity
        cuts = analysis.scene_cuts
        accents_ts = analysis.accent_timestamps

        # 1. Resolve Style Profile
        style_key = self._resolve_style_key(style_preference, activity)
        profile = self.STYLE_PROFILES[style_key]

        # 2. Adjust BPM based on video pacing and motion
        bpm = self._calculate_adaptive_bpm(profile["base_bpm"], activity)

        # 3. Determine sections aligned with scene cuts
        sections = self._arrange_sections(duration, cuts, accents_ts, profile["genre"])

        # 4. Map musical accents to visual transitions
        accents = self._map_musical_accents(accents_ts, style_key)

        # 5. Formulate prompt incorporating visual context
        prompt = custom_prompt_override.strip() if custom_prompt_override and custom_prompt_override.strip() else (
            f"{profile['prompt_template']}, instrumental background music, pacing {activity.pacing}, {activity.detected_mood} mood"
        )

        return MusicPlan(
            genre=profile["genre"],
            mood=activity.detected_mood,
            tempo_bpm=bpm,
            key=profile["key"],
            rhythmic_style=profile["rhythmic_style"],
            intensity=profile["intensity"],
            instrumentation=profile["instrumentation"],
            target_duration_s=duration,
            sections=sections,
            accents=accents,
            prompt=prompt,
        )

    def _resolve_style_key(self, style_preference: Optional[str], activity: Any) -> str:
        """Select appropriate style key based on preference or automatic visual inference."""
        if style_preference:
            norm = style_preference.lower().replace("-", "_").replace(" ", "_")
            if norm in self.STYLE_PROFILES:
                return norm
            for k in self.STYLE_PROFILES:
                if k in norm:
                    return k

        # Automatic Selection from Visual Analysis
        if activity.pacing == "fast-paced" or activity.avg_motion >= 0.22:
            return "electronic" if activity.warm_color_ratio < 0.4 else "action"
        if activity.detected_mood == "dark & atmospheric":
            return "cinematic"
        if activity.detected_mood == "uplifting & warm":
            return "corporate"
        if activity.detected_mood == "melancholic & reflective":
            return "lo_fi"
        if activity.pacing == "slow":
            return "ambient"
        return "cinematic"

    def _calculate_adaptive_bpm(self, base_bpm: int, activity: Any) -> int:
        """Adapt tempo within natural musical bounds based on visual motion dynamics."""
        motion_factor = (activity.avg_motion - 0.10) * 40.0
        adapted = int(round(base_bpm + motion_factor))
        # Keep within valid IncuBrix tempo constraints (40-240 BPM) and musical style bounds
        return max(60, min(160, adapted))

    def _arrange_sections(
        self,
        duration: float,
        cuts: List[float],
        accents: List[float],
        genre: str,
    ) -> List[SectionPlan]:
        """Create structured arrangement sections aligned with scene cuts, enforcing the >= 1.5s separation rule."""
        sections: List[SectionPlan] = []

        # 1. Section 1: Intro (always at 0.0s)
        sections.append(SectionPlan(start_s=0.0, mood=f"gentle intro establishing {genre} theme and mood"))

        if duration < 8.0:
            return sections

        # 2. Section 2: Build-up / Movement
        # Find candidate cut around 20% to 35% of the timeline
        target_bu = duration * 0.25
        bu_cand = self._find_closest_cut(cuts, target_bu, min_s=2.0, max_s=duration * 0.40)
        bu_start = bu_cand if bu_cand is not None else round(target_bu, 2)
        if bu_start - sections[-1].start_s >= 1.5 and bu_start < duration - 2.0:
            sections.append(SectionPlan(start_s=bu_start, mood="build-up adding driving rhythmic percussion and harmonic layers"))

        # 3. Section 3: Peak / Drop
        # Align with primary accent or midpoint cut (45% to 70% of duration)
        target_peak = duration * 0.55
        peak_cand = None
        if accents:
            # Pick first accent in 35%-75% range
            for acc in accents:
                if duration * 0.35 <= acc <= duration * 0.75:
                    peak_cand = acc
                    break
        if peak_cand is None:
            peak_cand = self._find_closest_cut(cuts, target_peak, min_s=duration * 0.40, max_s=duration * 0.75)

        peak_start = peak_cand if peak_cand is not None else round(target_peak, 2)
        if peak_start - sections[-1].start_s >= 1.5 and peak_start < duration - 2.5:
            sections.append(SectionPlan(start_s=peak_start, mood="energetic peak drop with full instrumentation, driving bass, and prominent melody"))

        # 4. Section 4: Resolution / Outro (before track end)
        target_outro = max(duration - 4.0, duration * 0.82)
        if target_outro - sections[-1].start_s >= 2.0 and target_outro < duration - 1.2:
            outro_cand = self._find_closest_cut(cuts, target_outro, min_s=sections[-1].start_s + 1.5, max_s=duration - 1.2)
            outro_start = outro_cand if outro_cand is not None else round(target_outro, 2)
            if outro_start - sections[-1].start_s >= 1.5 and outro_start < duration:
                sections.append(SectionPlan(start_s=outro_start, mood="smooth musical resolution tapering dynamics into final cadence"))

        # Enforce strict validation: ensure all sections have >= 1.5s gap and start_s <= duration
        validated_sections: List[SectionPlan] = [sections[0]]
        for sec in sections[1:]:
            if sec.start_s - validated_sections[-1].start_s >= 1.5 and sec.start_s < duration:
                validated_sections.append(sec)

        return validated_sections

    def _find_closest_cut(
        self, cuts: List[float], target: float, min_s: float, max_s: float
    ) -> Optional[float]:
        """Find the nearest scene cut within the allowable window [min_s, max_s]."""
        valid = [c for c in cuts if min_s <= c <= max_s]
        if not valid:
            return None
        return min(valid, key=lambda c: abs(c - target))

    def _map_musical_accents(self, accent_timestamps: List[float], style_key: str) -> List[MusicalAccent]:
        """Assign specific musical accent descriptions to visual event moments."""
        accents: List[MusicalAccent] = []
        accent_actions = {
            "cinematic": ["Orchestral brass hit and timpani accent", "Riser crescendo swell and crash cymbal", "Sub-bass pulse and string flourish"],
            "electronic": ["Percussive drop with open hi-hat splash", "Snare roll build and synth sweep", "Bass drop with punchy kick accent"],
            "corporate": ["Acoustic guitar strum accent and bell chime", "Snare rimshot and upbeat swell", "Bright piano chord resolution"],
            "lo_fi": ["Vinyl scratch accent and laid-back rimshot", "Muted trumpet lick and tape stop nuance", "Warm Rhodes chord downbeat accent"],
            "ambient": ["Shimmer texture swell and crystal bell hit", "Deep drone octave shift", "Resonant filter sweep and chime fade"],
            "action": ["Crash cymbal hit with heavy guitar powerchord", "Aggressive drum fill and bass slide", "Sudden rhythmic stop and punchy hit"],
        }
        actions_list = accent_actions.get(style_key, accent_actions["cinematic"])

        for i, ts in enumerate(accent_timestamps):
            action = actions_list[i % len(actions_list)]
            accents.append(
                MusicalAccent(
                    timestamp_s=ts,
                    event_description=f"Visual transition & motion spike at {ts:.2f}s",
                    musical_action=action,
                )
            )
        return accents
