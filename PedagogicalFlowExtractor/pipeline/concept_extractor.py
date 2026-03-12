"""Hybrid Concept Extractor.

Extracts academic concepts from transcripts using multiple signals:
  - Domain dictionary matching (CS concepts)
  - RAKE keyword extraction
  - Frequency analysis

Designed to be extensible for Phase 2 additions (POS tagging, TF-IDF).
"""

import re
from collections import Counter

from rake_nltk import Rake

from utils.config import load_config
from utils.helpers import load_json
from utils.logger import get_logger

logger = get_logger(__name__)


# Single words that are common English words — only keep if they appear
# in a technical CS context (e.g. "new operator", "delete node").
# Maps ambiguous_word → set of CS context words that must appear nearby.
AMBIGUOUS_WORDS = {
    "new": {"operator", "keyword", "malloc", "allocate", "memory", "object", "instance", "create"},
    "delete": {"operator", "keyword", "free", "memory", "node", "pointer", "deallocate", "remove"},
    "return": {"type", "value", "statement", "function", "method", "void", "keyword"},
    "break": {"statement", "keyword", "loop", "switch"},
    "continue": {"statement", "keyword", "loop"},
    "set": {"data structure", "hash", "unordered", "ordered", "collection"},
    "map": {"data structure", "hash", "unordered", "ordered", "key", "value", "dictionary"},
    "edge": {"graph", "vertex", "node", "weight", "directed", "undirected"},
    "node": {"tree", "graph", "linked list", "child", "parent", "leaf", "pointer", "next"},
    "list": {"linked", "data structure", "array", "singly", "doubly", "circular"},
    "pair": {"key", "value", "tuple", "data structure"},
    "input": {"output", "scanf", "cin", "stdin", "stream", "user"},
    "output": {"input", "printf", "cout", "stdout", "stream", "print"},
    "print": {"printf", "cout", "output", "statement", "console"},
}

# When an ambiguous word IS valid (has CS context), promote it to a longer
# contextual name so the learner sees something meaningful.
# e.g. "new" in context of "operator" → show "new operator" instead of just "new"
AMBIGUOUS_PROMOTIONS = {
    "new": "new operator",
    "delete": "delete operator",
    "return": "return statement",
    "break": "break statement",
    "continue": "continue statement",
}


class ConceptExtractor:
    """Extracts and ranks academic concepts from transcript text."""

    def __init__(self, concepts_path: str = None):
        """Initialize extractor with domain concepts dictionary.

        Args:
            concepts_path: Path to cs_concepts.json.
                          Defaults to config value.
        """
        cfg = load_config()
        self.weights = cfg["extractor"]["weights"]
        self.min_score = cfg["extractor"]["min_concept_score"]
        self.use_rake = cfg["extractor"]["use_rake"]
        self.use_domain_dict = cfg["extractor"]["use_domain_dict"]

        if concepts_path is None:
            concepts_path = cfg["extractor"]["concepts_path"]

        raw = load_json(concepts_path)

        # Build flat set of all known concepts (lowercased)
        self.known_concepts = set()
        # Map from alias → canonical name
        self.alias_map = {}

        for category, entries in raw.items():
            if category.startswith("_"):
                continue
            if category == "common_aliases":
                for canonical, aliases in entries.items():
                    canonical_lower = canonical.lower()
                    for alias in aliases:
                        self.alias_map[alias.lower()] = canonical_lower
            elif isinstance(entries, list):
                for concept in entries:
                    self.known_concepts.add(concept.lower())

        # Also add all aliases as known concepts pointing to canonical
        for alias in self.alias_map:
            self.known_concepts.add(alias)

        logger.info(
            "Extractor loaded: %d known concepts, %d aliases",
            len(self.known_concepts),
            len(self.alias_map),
        )

    def _canonicalize(self, concept: str) -> str:
        """Return the canonical form of a concept.

        Args:
            concept: Extracted concept string (lowercased).

        Returns:
            Canonical concept name.
        """
        c = concept.lower().strip()
        return self.alias_map.get(c, c)

    def _domain_dict_match(self, text: str) -> dict[str, float]:
        """Find domain concepts by matching against the dictionary.

        Uses multi-word matching (longest match first) to handle
        concepts like 'binary search tree', 'linked list', etc.

        Args:
            text: Normalized transcript text.

        Returns:
            Dict mapping canonical concept → match count (normalized).
        """
        text_lower = text.lower()
        matches = Counter()

        # Sort concepts by word count (longest first) for greedy matching
        sorted_concepts = sorted(self.known_concepts, key=len, reverse=True)

        for concept in sorted_concepts:
            # Use word-boundary regex for accurate matching
            pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.IGNORECASE)
            count = len(pattern.findall(text_lower))
            if count > 0:
                canonical = self._canonicalize(concept)
                matches[canonical] += count

        if not matches:
            return {}

        # Normalize using log-dampened scale so single-mention concepts
        # aren't crushed when one concept dominates (e.g. stack=80 mentions).
        # A concept mentioned once gets ~0.33, twice ~0.58, three+ ~0.73+.
        import math
        return {c: min(math.log(1 + count) / math.log(1 + max(3, max(matches.values()))), 1.0)
                for c, count in matches.items()}

    def _rake_extract(self, text: str) -> dict[str, float]:
        """Extract keywords using RAKE algorithm.

        Args:
            text: Normalized transcript text.

        Returns:
            Dict mapping keyword → normalized RAKE score.
        """
        rake = Rake(
            min_length=1,
            max_length=4,
            include_repeated_phrases=False,
        )
        rake.extract_keywords_from_text(text)
        scored = rake.get_ranked_phrases_with_scores()

        if not scored:
            return {}

        # Filter: only keep phrases that overlap with known concepts
        results = {}
        max_score = scored[0][0] if scored else 1.0

        for score, phrase in scored:
            phrase_lower = phrase.lower().strip()
            canonical = self._canonicalize(phrase_lower)

            # Check if this phrase matches or contains a known concept
            if canonical in self.known_concepts:
                results[canonical] = max(
                    results.get(canonical, 0), score / max_score
                )
            else:
                # Check partial overlap using whole-word matching.
                # All words of the concept must appear in the phrase
                # to avoid "first" matching "breadth first search".
                phrase_words = set(phrase_lower.split())
                for concept in self.known_concepts:
                    concept_words = set(concept.split())
                    if concept_words <= phrase_words:  # subset check
                        can = self._canonicalize(concept)
                        results[can] = max(
                            results.get(can, 0), score / max_score * 0.8
                        )

        return results

    def _frequency_score(self, text: str, concepts: set[str]) -> dict[str, float]:
        """Score concepts by their mention frequency in the text.

        Also counts aliases (e.g. 'arrays' counts for 'array').

        Args:
            text: Normalized transcript text.
            concepts: Set of concept names to count.

        Returns:
            Dict mapping concept → normalized frequency score.
        """
        text_lower = text.lower()
        counts = {}
        for concept in concepts:
            # Build pattern that also matches known aliases
            variants = {concept}
            for alias, canonical in self.alias_map.items():
                if canonical == concept:
                    variants.add(alias)
            pattern_str = "|".join(r"\b" + re.escape(v) + r"\b" for v in variants)
            pattern = re.compile(pattern_str, re.IGNORECASE)
            count = len(pattern.findall(text_lower))
            if count > 0:
                counts[concept] = count

        if not counts:
            return {}

        import math
        return {c: min(math.log(1 + count) / math.log(1 + max(3, max(counts.values()))), 1.0)
                for c, count in counts.items()}

    def extract(self, transcript: dict) -> list[dict]:
        """Extract concepts from a transcript using hybrid method.

        Args:
            transcript: Transcript dict with 'full_text' and 'segments'.

        Returns:
            Sorted list of concept dicts with name, score, and metadata.
        """
        text = transcript.get("full_text", "")
        if not text:
            logger.warning("Empty transcript text, no concepts to extract")
            return []

        logger.info("Extracting concepts from transcript...")

        # Signal 1: Domain dictionary matching
        domain_scores = {}
        if self.use_domain_dict:
            domain_scores = self._domain_dict_match(text)
            logger.info("Domain dict found %d concepts", len(domain_scores))

        # Signal 2: RAKE keyword extraction
        rake_scores = {}
        if self.use_rake:
            rake_scores = self._rake_extract(text)
            logger.info("RAKE found %d concept-related keywords", len(rake_scores))

        # Collect all candidate concepts
        all_concepts = set(domain_scores.keys()) | set(rake_scores.keys())

        # Signal 3: Frequency analysis
        freq_scores = self._frequency_score(text, all_concepts)

        # Combine signals with weights
        combined = {}
        for concept in all_concepts:
            score = (
                self.weights["domain_match"] * domain_scores.get(concept, 0)
                + self.weights["rake"] * rake_scores.get(concept, 0)
                + self.weights["frequency"] * freq_scores.get(concept, 0)
            )
            combined[concept] = score

        # Filter by minimum score and remove concepts with zero actual mentions
        filtered = {}
        for c, s in combined.items():
            if s < self.min_score:
                continue
            # A concept must actually appear in the text (freq > 0)
            if self._count_mentions(c, text) == 0:
                continue
            filtered[c] = s

        # Filter ambiguous single-word concepts that lack CS context
        text_lower = text.lower()
        to_remove_ambiguous = set()
        promotions = {}  # old_name → new_name
        for c in list(filtered.keys()):
            if c in AMBIGUOUS_WORDS:
                context_words = AMBIGUOUS_WORDS[c]
                # Check if any CS context word appears near this word in text
                has_context = False
                for ctx in context_words:
                    if ctx in text_lower:
                        has_context = True
                        break
                if not has_context:
                    # No CS context → remove this ambiguous word
                    to_remove_ambiguous.add(c)
                else:
                    # Has context → promote to more descriptive name
                    if c in AMBIGUOUS_PROMOTIONS:
                        promotions[c] = AMBIGUOUS_PROMOTIONS[c]
        for c in to_remove_ambiguous:
            del filtered[c]
        # Apply promotions (rename ambiguous words to contextual names)
        for old_name, new_name in promotions.items():
            if old_name in filtered:
                filtered[new_name] = filtered.pop(old_name)

        # Deduplicate: remove sub-concepts when a longer concept exists
        # e.g. remove "list" if "linked list" is present,
        #      remove "search" if "binary search" is present
        to_remove = set()
        concept_names = set(filtered.keys())
        for c1 in concept_names:
            for c2 in concept_names:
                if c1 != c2 and c1 in c2 and len(c1) < len(c2):
                    # c1 is a substring of c2 — keep c2, remove c1
                    # But only if c1 is a single word (avoid removing real standalone concepts)
                    if " " not in c1:
                        to_remove.add(c1)
        for c in to_remove:
            del filtered[c]

        # Build result list with metadata
        results = []
        for concept, score in sorted(filtered.items(), key=lambda x: -x[1]):
            # Find timestamps where this concept appears
            timestamps = self._find_timestamps(concept, transcript.get("segments", []))

            results.append({
                "name": concept,
                "normalized_name": concept.replace("_", " ").title(),
                "importance_score": round(score, 4),
                "frequency": self._count_mentions(concept, text),
                "first_mention": timestamps[0] if timestamps else None,
                "timestamps": timestamps,
                "signals": {
                    "domain_match": round(domain_scores.get(concept, 0), 4),
                    "rake": round(rake_scores.get(concept, 0), 4),
                    "frequency": round(freq_scores.get(concept, 0), 4),
                },
            })

        logger.info("Extracted %d concepts (after filtering)", len(results))
        return results

    def _count_mentions(self, concept: str, text: str) -> int:
        """Count how many times a concept is mentioned (including aliases)."""
        variants = {concept}
        for alias, canonical in self.alias_map.items():
            if canonical == concept:
                variants.add(alias)
        pattern_str = "|".join(r"\b" + re.escape(v) + r"\b" for v in variants)
        pattern = re.compile(pattern_str, re.IGNORECASE)
        return len(pattern.findall(text))

    def _find_timestamps(self, concept: str, segments: list[dict]) -> list[str]:
        """Find which transcript segments mention a concept.

        Args:
            concept: Concept name to search for.
            segments: List of transcript segment dicts.

        Returns:
            List of timestamp labels where concept appears.
        """
        pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.IGNORECASE)
        timestamps = []
        for seg in segments:
            text = seg.get("text", "") + " " + seg.get("original_text", "")
            if pattern.search(text):
                label = seg.get("timestamp_label", "")
                if label and label not in timestamps:
                    timestamps.append(label)
        return timestamps
