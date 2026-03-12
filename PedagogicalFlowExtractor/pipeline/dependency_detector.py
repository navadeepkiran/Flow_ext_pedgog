"""Prerequisite Dependency Detector.

Detects prerequisite relationships between concepts using:
  - Pedagogical cue patterns (explicit linguistic markers)
  - Temporal ordering (concept mention order)
  - Co-occurrence analysis within segments

Designed to be extensible for advanced pattern mining in Phase 3.
"""

import re
from itertools import combinations

from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)


class DependencyDetector:
    """Detects prerequisite relationships between extracted concepts."""

    def __init__(self):
        """Initialize detector with cue patterns and config thresholds."""
        cfg = load_config()
        self.min_confidence = cfg["detector"]["min_confidence"]

        # Pedagogical cue patterns
        # Each pattern: (regex, relationship_direction, base_confidence)
        # Direction: "forward" = group1 is prereq of group2
        #            "backward" = group2 is prereq of group1
        self.cue_patterns = self._build_patterns()

        logger.info("Dependency detector loaded: %d patterns", len(self.cue_patterns))

    def _build_patterns(self) -> list[tuple[re.Pattern, str, float]]:
        """Build regex patterns that detect prerequisite cues.

        Returns:
            List of (compiled_regex, direction, base_confidence) tuples.
        """
        patterns = [
            # --- Hindi/Hinglish patterns ---
            # "pehle X samjho phir Y easy lagega"
            (
                re.compile(
                    r"peh?le\s+(.+?)\s+(?:samjho|seekho|padho|karo)\s+(?:phir|fir|tab|toh)\s+(.+?)(?:\s+(?:easy|simple|samajh|aayega|lagega|hoga)|[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.90,
            ),
            # "pehle X phir Y"
            (
                re.compile(
                    r"peh?le\s+(.+?)\s+(?:phir|fir|tab)\s+(.+?)(?:[,.\s]|$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.80,
            ),
            # "X ke baad Y aata/seekhenge"
            (
                re.compile(
                    r"(.+?)\s+ke\s+baad\s+(.+?)(?:\s+(?:aata|aayega|seekhenge|karenge|hota)|[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.75,
            ),
            # "X Y pe depend karta hai"
            (
                re.compile(
                    r"(.+?)\s+(.+?)\s+(?:pe|par)\s+depend\s+(?:karta|karti|karte)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.85,
            ),
            # "X ka concept Y pe depend karta hai" — e.g. "Stack ka concept push aur pop pe depend karta hai"
            (
                re.compile(
                    r"(.+?)\s+(?:ka|ki)\s+concept\s+(.+?)\s+(?:pe|par)\s+depend\s+(?:karta|karti|karte)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.90,
            ),
            # "X samjhne/seekhne ke liye pehle Y samjho" — e.g. "Recursion samjhne ke liye pehle function samjho"
            (
                re.compile(
                    r"(.+?)\s+(?:samjhne|seekhne|padhne|karne)\s+ke\s+liye\s+peh?le\s+(.+?)\s+(?:samjho|seekho|padho|karo|samjhna|seekhna)",
                    re.IGNORECASE,
                ),
                "backward",
                0.90,
            ),
            # "X ke liye Y zaruri/zaroori hai" — e.g. "Recursion ke liye function zaruri hai"
            (
                re.compile(
                    r"(.+?)\s+ke\s+liye\s+(.+?)\s+(?:zaruri|zaroori|important|necessary)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.85,
            ),
            # "X zaruri hai Y ke liye"
            (
                re.compile(
                    r"(.+?)\s+(?:zaruri|zaroori)\s+hai\s+(.+?)\s+ke\s+liye",
                    re.IGNORECASE,
                ),
                "forward",
                0.85,
            ),
            # "X ke bina Y nahi"
            (
                re.compile(
                    r"(.+?)\s+ke\s+bina\s+(.+?)\s+(?:nahi|nhi|impossible|mushkil)",
                    re.IGNORECASE,
                ),
                "forward",
                0.85,
            ),
            # "X ka base Y hai" or "X ka foundation Y hai"
            (
                re.compile(
                    r"(.+?)\s+ka\s+(?:base|foundation|neev)\s+(.+?)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.80,
            ),
            # "X se Y banta hai"
            (
                re.compile(
                    r"(.+?)\s+se\s+(.+?)\s+(?:banta|banti|milta|milti)\s+hai",
                    re.IGNORECASE,
                ),
                "forward",
                0.70,
            ),

            # --- English patterns ---
            # "before learning Y, you should know X"
            (
                re.compile(
                    r"before\s+(?:learning|understanding|studying)\s+(.+?)[,]\s*(?:you\s+)?(?:should|must|need\s+to)\s+(?:know|understand|learn)\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "backward",
                0.90,
            ),
            # "X is prerequisite for Y" / "X is required for Y"
            (
                re.compile(
                    r"(.+?)\s+(?:is|are)\s+(?:a\s+)?(?:prerequisite|required|necessary|needed)\s+(?:for|to\s+(?:learn|understand))\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.90,
            ),
            # "Y depends on X" / "Y is based on X"
            (
                re.compile(
                    r"(.+?)\s+(?:depends?|is\s+based)\s+on\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "backward",
                0.85,
            ),
            # "first X then Y" / "first learn X then Y"
            (
                re.compile(
                    r"first\s+(?:learn|understand|study|do)?\s*(.+?)\s+(?:then|and\s+then|after\s+that)\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.80,
            ),
            # "after X comes Y" / "after X we learn Y"
            (
                re.compile(
                    r"after\s+(.+?)\s+(?:comes?|we\s+(?:learn|study|do)|you\s+(?:learn|study))\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.75,
            ),
            # "X leads to Y"
            (
                re.compile(
                    r"(.+?)\s+leads?\s+to\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.70,
            ),
            # "you need X for Y" / "you need X to understand Y"
            (
                re.compile(
                    r"(?:you\s+)?need\s+(.+?)\s+(?:for|to\s+(?:understand|learn|do))\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "forward",
                0.80,
            ),
            # "without X, Y is not possible"
            (
                re.compile(
                    r"without\s+(.+?)[,]\s*(.+?)\s+(?:is|are)\s+not\s+(?:possible|easy|doable)",
                    re.IGNORECASE,
                ),
                "forward",
                0.85,
            ),

            # --- "uses / implements" patterns (Hindi + English) ---
            # "X mein Y use hota/hoti hai" → Y is prereq of X
            (
                re.compile(
                    r"(.+?)\s+mein\s+(.+?)\s+(?:use|istemal|upyog)\s+(?:hota|hoti|hote|karta|karti|karte)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.75,
            ),
            # "X Y use karta hai" → Y is prereq of X
            (
                re.compile(
                    r"(.+?)\s+(.+?)\s+(?:use|istemal)\s+(?:karta|karti|karte)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.70,
            ),
            # "X Y se implement hota hai" → Y is prereq of X
            (
                re.compile(
                    r"(.+?)\s+(.+?)\s+se\s+(?:implement|bana|banaya|create|construct)\s+(?:hota|hoti|karta|karti|kiya|karte)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.75,
            ),
            # "X uses Y" / "X utilizes Y" → Y is prereq of X
            (
                re.compile(
                    r"(.+?)\s+(?:uses?|utilizes?|employs?)\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "backward",
                0.70,
            ),
            # "X is implemented using Y" → Y is prereq of X
            (
                re.compile(
                    r"(.+?)\s+(?:is|are)\s+(?:implemented|built|constructed|created|made)\s+(?:using|with|from)\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "backward",
                0.75,
            ),
            # "X works on Y" / "X is based on Y" (broader variant)
            (
                re.compile(
                    r"(.+?)\s+(?:works?|operates?)\s+(?:on|with)\s+(.+?)(?:[,.]|\s*$)",
                    re.IGNORECASE,
                ),
                "backward",
                0.60,
            ),
            # "X ke andar Y hota hai" / "X mein Y aata hai" → Y is component of X, so Y prereq X
            (
                re.compile(
                    r"(.+?)\s+(?:ke\s+andar|mein)\s+(.+?)\s+(?:hota|hoti|aata|aati)\s+hai",
                    re.IGNORECASE,
                ),
                "backward",
                0.65,
            ),
        ]
        return patterns

    def _match_concept_in_text(self, text_fragment: str, concepts: list[str]) -> str | None:
        """Find the best matching concept within a text fragment.

        Args:
            text_fragment: The captured group text from regex.
            concepts: List of known concept names.

        Returns:
            Best matching concept name or None.
        """
        fragment_lower = text_fragment.lower().strip()

        # Exact match
        if fragment_lower in concepts:
            return fragment_lower

        # Check if any concept is contained in the fragment
        best_match = None
        best_len = 0
        for concept in concepts:
            if concept in fragment_lower and len(concept) > best_len:
                best_match = concept
                best_len = len(concept)

        return best_match

    def _match_concepts_in_text(self, text_fragment: str, concepts: list[str]) -> list[str]:
        """Find ALL matching concepts in a text fragment.

        Handles compound phrases like "push aur pop" → ["push", "pop"].

        Args:
            text_fragment: The captured group text from regex.
            concepts: List of known concept names.

        Returns:
            List of matching concept names.
        """
        results = []
        # Split on conjunction words (aur, and, or, aur bhi, ya)
        parts = re.split(r"\s+(?:aur|and|or|ya|evam)\s+", text_fragment.lower().strip())
        for part in parts:
            match = self._match_concept_in_text(part.strip(), concepts)
            if match and match not in results:
                results.append(match)
        # Fallback: try the whole fragment as well
        if not results:
            match = self._match_concept_in_text(text_fragment, concepts)
            if match:
                results.append(match)
        return results

    def detect_from_patterns(
        self,
        transcript: dict,
        concepts: list[dict],
    ) -> list[dict]:
        """Detect prerequisite relationships using pedagogical cue patterns.

        Args:
            transcript: Transcript dict with 'segments'.
            concepts: List of extracted concept dicts.

        Returns:
            List of relationship dicts.
        """
        concept_names = [c["name"] for c in concepts]
        relationships = []
        seen_pairs = set()

        segments = transcript.get("segments", [])

        for seg in segments:
            # Check both original and normalized text
            texts_to_check = [
                seg.get("text", ""),
                seg.get("original_text", ""),
            ]

            for text in texts_to_check:
                if not text:
                    continue

                # Split into sentences to prevent patterns matching across boundaries
                sentences = re.split(r"[.!?।]+", text)

                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    for pattern, direction, base_conf in self.cue_patterns:
                        for match in pattern.finditer(sentence):
                            group1 = match.group(1).strip()
                            group2 = match.group(2).strip() if match.lastindex >= 2 else None

                            if not group2:
                                continue

                            # Match concepts, handling compound phrases like "push aur pop"
                            concepts_a = self._match_concepts_in_text(group1, concept_names)
                            concepts_b = self._match_concepts_in_text(group2, concept_names)

                            if not concepts_a or not concepts_b:
                                continue

                            # Generate relationships for all concept pairs
                            for ca in concepts_a:
                                for cb in concepts_b:
                                    if ca == cb:
                                        continue

                                    # Determine prerequisite direction
                                    if direction == "forward":
                                        prereq, target = ca, cb
                                    else:
                                        prereq, target = cb, ca

                                    pair_key = (prereq, target)
                                    if pair_key in seen_pairs:
                                        continue
                                    seen_pairs.add(pair_key)

                                    relationships.append({
                                        "from": prereq,
                                        "to": target,
                                        "relation": "prerequisite",
                                        "confidence": round(base_conf, 4),
                                        "evidence": sentence.strip(),
                                        "timestamp": seg.get("timestamp_label", ""),
                                        "detection_method": "pattern_matching",
                                    })

        logger.info(
            "Pattern matching found %d prerequisite relationships",
            len(relationships),
        )
        return relationships

    def detect_from_temporal_order(
        self,
        concepts: list[dict],
    ) -> list[dict]:
        """Infer prerequisites from concept mention order in the video.

        Heuristic: If concept A is first mentioned significantly before
        concept B, A may be a prerequisite for B (lower confidence).

        Args:
            concepts: List of extracted concept dicts with timestamps.

        Returns:
            List of relationship dicts.
        """
        # Sort concepts by first mention time
        timed_concepts = []
        for c in concepts:
            ts = c.get("first_mention")
            if ts:
                parts = ts.split(":")
                seconds = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
                timed_concepts.append((c["name"], seconds, c.get("importance_score", 0)))

        timed_concepts.sort(key=lambda x: x[1])

        relationships = []
        seen = set()

        for i in range(len(timed_concepts)):
            for j in range(i + 1, min(i + 4, len(timed_concepts))):
                name_a, time_a, score_a = timed_concepts[i]
                name_b, time_b, score_b = timed_concepts[j]

                # Only if there's a meaningful time gap (>30s)
                time_diff = time_b - time_a
                if time_diff < 30:
                    continue

                pair_key = (name_a, name_b)
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                # Confidence based on time gap and proximity in mention order
                confidence = min(0.55, 0.35 + (time_diff / 600) * 0.2)

                relationships.append({
                    "from": name_a,
                    "to": name_b,
                    "relation": "prerequisite",
                    "confidence": round(confidence, 4),
                    "evidence": f"temporal order: {name_a} mentioned at {timed_concepts[i][1]}s, {name_b} at {timed_concepts[j][1]}s",
                    "timestamp": "",
                    "detection_method": "temporal_order",
                })

        logger.info(
            "Temporal ordering found %d potential relationships",
            len(relationships),
        )
        return relationships

    def detect_from_cooccurrence(
        self,
        transcript: dict,
        concepts: list[dict],
    ) -> list[dict]:
        """Detect prerequisites from concept co-occurrence within segments.

        If two concepts appear in the same segment and one was introduced
        earlier in the video, the earlier concept may be a prerequisite.

        Args:
            transcript: Transcript dict with 'segments'.
            concepts: List of extracted concept dicts.

        Returns:
            List of relationship dicts.
        """
        # Build concept → first-mention-time map
        first_mention_time = {}
        for c in concepts:
            ts = c.get("first_mention")
            if ts:
                parts = ts.split(":")
                seconds = int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0
                first_mention_time[c["name"]] = seconds

        concept_names = {c["name"] for c in concepts}
        segments = transcript.get("segments", [])
        relationships = []
        seen = set()

        for seg in segments:
            text = (seg.get("text", "") + " " + seg.get("original_text", "")).lower()

            # Find which concepts appear in this segment
            present = []
            for cname in concept_names:
                pattern = re.compile(r"\b" + re.escape(cname) + r"\b", re.IGNORECASE)
                if pattern.search(text):
                    present.append(cname)

            if len(present) < 2:
                continue

            # For each pair, if one was introduced earlier, create a low-confidence edge
            for i in range(len(present)):
                for j in range(i + 1, len(present)):
                    a, b = present[i], present[j]
                    time_a = first_mention_time.get(a)
                    time_b = first_mention_time.get(b)
                    if time_a is None or time_b is None:
                        continue
                    # Earlier concept is the prerequisite
                    if time_a < time_b:
                        prereq, target = a, b
                    elif time_b < time_a:
                        prereq, target = b, a
                    else:
                        continue  # same time, skip

                    pair_key = (prereq, target)
                    if pair_key in seen:
                        continue
                    seen.add(pair_key)

                    relationships.append({
                        "from": prereq,
                        "to": target,
                        "relation": "prerequisite",
                        "confidence": 0.45,
                        "evidence": f"co-occurrence: both '{prereq}' and '{target}' appear in same segment",
                        "timestamp": seg.get("timestamp_label", ""),
                        "detection_method": "cooccurrence",
                    })

        logger.info(
            "Co-occurrence found %d potential relationships",
            len(relationships),
        )
        return relationships

    def detect(
        self,
        transcript: dict,
        concepts: list[dict],
    ) -> list[dict]:
        """Run all detection methods and merge results.

        Args:
            transcript: Transcript dict with segments.
            concepts: List of extracted concept dicts.

        Returns:
            Deduplicated, sorted list of relationship dicts.
        """
        logger.info("Detecting prerequisite relationships...")

        # Method 1: Pattern-based detection (higher confidence)
        pattern_rels = self.detect_from_patterns(transcript, concepts)

        # Method 2: Temporal ordering (lower confidence)
        temporal_rels = self.detect_from_temporal_order(concepts)

        # Method 3: Co-occurrence within segments (lowest confidence)
        cooccurrence_rels = self.detect_from_cooccurrence(transcript, concepts)

        # Merge: pattern results take priority, then temporal, then cooccurrence
        all_rels = {}
        for rel in pattern_rels:
            key = (rel["from"], rel["to"])
            all_rels[key] = rel

        for rel in temporal_rels:
            key = (rel["from"], rel["to"])
            if key not in all_rels:
                all_rels[key] = rel

        for rel in cooccurrence_rels:
            key = (rel["from"], rel["to"])
            if key not in all_rels:
                all_rels[key] = rel

        # Filter by minimum confidence
        filtered = [
            r for r in all_rels.values()
            if r["confidence"] >= self.min_confidence
        ]

        # Sort by confidence (highest first)
        filtered.sort(key=lambda x: -x["confidence"])

        logger.info(
            "Total relationships detected: %d (after filtering)",
            len(filtered),
        )
        return filtered
