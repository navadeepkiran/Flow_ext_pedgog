"""LLM-Powered Concept & Prerequisite Extractor using Groq.

Replaces the rule-based normalizer, concept extractor, and dependency
detector with a single LLM call that handles all three stages:
  1. Code-mixed (Hinglish / Tenglish) → English normalization
  2. Academic concept extraction (any domain)
  3. Prerequisite relationship detection

Uses Groq's free API with Llama models for fast inference.
"""

import json
import os
import re

from pipeline.normalizer import transliterate_devanagari
from utils.config import load_config
from utils.logger import get_logger

logger = get_logger(__name__)

# The structured extraction prompt with few-shot examples
# PASS 1: Extract concepts only
CONCEPT_EXTRACTION_PROMPT = """You are an expert educational content analyzer. You will be given a transcript from an educational video lecture. The lecture may contain Hinglish (Hindi-English code-mixed), Tenglish (Telugu-English code-mixed), or pure English text.

Your task is to:
1. Identify the academic domain
2. Extract ALL academic concepts from the transcript

RULES FOR CONCEPTS:
- Extract ALL concepts that are discussed, explained, demonstrated, used, or referenced in the lecture
- Include the MAIN topic concepts AND supporting/building-block concepts
- Include umbrella/category concepts (e.g. "data structure", "sorting") AND specific ones (e.g. "merge sort", "linked list")
- Include techniques, paradigms, operations (e.g. "divide and conquer", "recursion", "loop", "traversal")
- Include building-block concepts even if they are not the primary focus (e.g. "loop", "variable", "recursion", "function") as long as they are mentioned in a technical context
- Aim for completeness: extract 10-30 concepts for a typical lecture. It is better to include a borderline concept than to miss it.
- Use canonical English names ("binary search tree" not "BST concept")
- Importance: how central is this concept to the lecture (0.0-1.0)
- Difficulty: "easy", "medium", or "hard"

--- EXAMPLE 1 ---
Transcript: "Binary tree ek hierarchical data structure hai. BST ek special binary tree hai jisme left chhota right bada. Pehle binary tree samjho phir BST easy lagega. AVL tree self-balancing BST hai. BST ke baad AVL seekho. Recursion use hota hai tree traversal mein."

Output:
{{{{
  "domain": "Computer Science",
  "concepts": [
    {{{{"name": "binary tree", "normalized_name": "Binary Tree", "importance_score": 0.9, "difficulty": "medium", "description": "Hierarchical data structure where each node has at most two children"}}}},
    {{{{"name": "binary search tree", "normalized_name": "Binary Search Tree", "importance_score": 0.95, "difficulty": "medium", "description": "Binary tree with left < parent < right ordering property"}}}},
    {{{{"name": "avl tree", "normalized_name": "AVL Tree", "importance_score": 0.8, "difficulty": "hard", "description": "Self-balancing binary search tree using rotations"}}}},
    {{{{"name": "recursion", "normalized_name": "Recursion", "importance_score": 0.6, "difficulty": "medium", "description": "A function calling itself to solve sub-problems"}}}},
    {{{{"name": "tree traversal", "normalized_name": "Tree Traversal", "importance_score": 0.7, "difficulty": "medium", "description": "Process of visiting all nodes in a tree"}}}},
    {{{{"name": "data structure", "normalized_name": "Data Structure", "importance_score": 0.5, "difficulty": "easy", "description": "Way of organizing and storing data"}}}}
  ]
}}}}

--- EXAMPLE 2 ---
Transcript: "Merge sort divide and conquer approach use karta hai. Array ko half half mein divide karte hain phir merge karte hain. Recursion se implement hota hai merge sort. Time complexity O(n log n) hai."

Output:
{{{{
  "domain": "Computer Science",
  "concepts": [
    {{{{"name": "merge sort", "normalized_name": "Merge Sort", "importance_score": 0.95, "difficulty": "medium", "description": "Sorting algorithm using divide and conquer approach"}}}},
    {{{{"name": "divide and conquer", "normalized_name": "Divide And Conquer", "importance_score": 0.8, "difficulty": "medium", "description": "Algorithm paradigm of breaking problem into smaller sub-problems"}}}},
    {{{{"name": "array", "normalized_name": "Array", "importance_score": 0.6, "difficulty": "easy", "description": "Linear data structure with contiguous memory"}}}},
    {{{{"name": "recursion", "normalized_name": "Recursion", "importance_score": 0.7, "difficulty": "medium", "description": "A function calling itself to solve sub-problems"}}}},
    {{{{"name": "time complexity", "normalized_name": "Time Complexity", "importance_score": 0.6, "difficulty": "easy", "description": "Measure of algorithm efficiency as input grows"}}}}
  ]
}}}}

--- NOW ANALYZE THIS TRANSCRIPT ---
Respond with ONLY valid JSON in the same format. Extract ALL concepts, including supporting ones.

TRANSCRIPT:
{transcript}"""

# PASS 2: Detect relationships given the concept list
RELATIONSHIP_DETECTION_PROMPT = """You are an expert educational content analyzer. You have already extracted concepts from a lecture transcript. Now detect prerequisite relationships between them.

CONCEPTS FOUND:
{concept_list}

RULES FOR RELATIONSHIPS:
- A prerequisite means: "To understand concept B, you should first understand concept A"
- Detect prerequisites from BOTH explicit AND implicit cues in the transcript:
  - EXPLICIT (Hindi): "pehle X samjho phir Y", "X zaruri hai Y ke liye"
  - EXPLICIT (Telugu): "mundu X nerchukondi tarvata Y", "X avasaram Y kosam"
  - EXPLICIT (English): "X is required for Y", "first learn X then Y"
  - IMPLICIT: "X uses Y" means Y is prerequisite of X. "X is implemented using Y" means Y is prereq of X. If concept A is used to explain concept B, A is prereq of B.
- If the transcript says "merge sort recursion use karta hai" → recursion is prerequisite of merge sort
- If the transcript says "array se stack implement karte hain" → array is prerequisite of stack
- Do NOT create edges from specifics TO their umbrella (e.g. "array" → "data structure" is WRONG)
- Only use concepts from the list above. Do not invent new ones.
- Confidence: 0.5-1.0 based on how clear the evidence is

--- EXAMPLE ---
Concepts: merge sort, divide and conquer, array, recursion, time complexity
Transcript: "Merge sort divide and conquer approach use karta hai. Recursion se implement hota hai merge sort."

Output:
{{{{
  "relationships": [
    {{{{"from": "divide and conquer", "to": "merge sort", "confidence": 0.85, "evidence": "Merge sort uses divide and conquer approach"}}}},
    {{{{"from": "recursion", "to": "merge sort", "confidence": 0.85, "evidence": "Merge sort is implemented using recursion"}}}}
  ]
}}}}

--- NOW ANALYZE ---
Respond with ONLY valid JSON. Detect ALL prerequisite relationships supported by the transcript.

TRANSCRIPT:
{transcript}"""


class LLMExtractor:
    """Extracts concepts and prerequisites using Groq LLM API."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize with Groq API key.

        Args:
            api_key: Groq API key. Falls back to GROQ_API_KEY env var or config.
            model: Model name. Defaults to config or llama-3.1-8b-instant.
        """
        cfg = load_config()
        llm_cfg = cfg.get("llm", {})

        self.api_key = api_key or os.environ.get("GROQ_API_KEY") or llm_cfg.get("api_key", "")
        self.model = model or llm_cfg.get("model", "llama-3.1-8b-instant")
        self.max_tokens = llm_cfg.get("max_tokens", 4096)

        if not self.api_key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY environment variable "
                "or add it to config.yaml under llm.api_key"
            )

        logger.info("LLM Extractor initialized: model=%s", self.model)

    def extract(self, transcript: dict) -> dict:
        """Run the full two-pass LLM extraction pipeline.

        Pass 1: Extract all concepts from transcript.
        Pass 2: Given the concept list + transcript, detect relationships.

        Args:
            transcript: Transcript dict with 'full_text' and 'segments'.

        Returns:
            Dict with normalized_text, concepts list, and relationships list.
        """
        from groq import Groq

        text = transcript.get("full_text", "")
        if not text:
            logger.warning("Empty transcript, skipping LLM extraction")
            return {"normalized_text": "", "concepts": [], "relationships": []}

        # Transliterate Urdu/Devanagari to Roman for better LLM tokenization
        text = transliterate_devanagari(text)

        logger.info("Sending transcript to Groq LLM (%s)...", self.model)

        client = Groq(api_key=self.api_key)

        def _call_llm(prompt_text: str, use_json_mode: bool = True) -> str:
            kwargs = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert educational content analyzer. Respond with ONLY valid JSON, no markdown formatting, no code blocks.",
                    },
                    {"role": "user", "content": prompt_text},
                ],
                "temperature": 0.1,
                "max_tokens": self.max_tokens,
            }
            if use_json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content

        # Chunk long transcripts and merge results
        CHUNK_LIMIT = 25000  # chars per chunk (~6K tokens)
        if len(text) > CHUNK_LIMIT:
            result = self._extract_chunked(text, client, _call_llm, transcript, CHUNK_LIMIT)
        else:
            result = self._extract_single(text, _call_llm, transcript)

        return result

    def _extract_single(self, text: str, _call_llm, transcript: dict) -> dict:
        """Two-pass extraction from a single (short enough) transcript.

        Pass 1: Extract concepts.
        Pass 2: Use concept list to detect relationships.
        """
        # --- PASS 1: Extract concepts ---
        logger.info("Pass 1: Extracting concepts...")
        p1 = CONCEPT_EXTRACTION_PROMPT.format(transcript=text)
        try:
            raw_concepts = _call_llm(p1, use_json_mode=True)
        except Exception as e:
            err_msg = str(e)
            if "max_tokens" in err_msg or "json_validate" in err_msg or "max completion" in err_msg:
                logger.warning("LLM hit token limit on pass 1, retrying with shorter transcript...")
                short_text = text[:15000] + "\n[... transcript truncated for length ...]"
                p1 = CONCEPT_EXTRACTION_PROMPT.format(transcript=short_text)
                try:
                    raw_concepts = _call_llm(p1, use_json_mode=True)
                except Exception:
                    logger.warning("JSON mode still failing, trying without json_object mode...")
                    raw_concepts = _call_llm(p1, use_json_mode=False)
            else:
                raise

        logger.info("Pass 1 response received (%d chars)", len(raw_concepts))
        concept_data = self._parse_json_response(raw_concepts)
        domain = concept_data.get("domain", "Unknown")
        concepts_raw = concept_data.get("concepts", [])

        if not concepts_raw:
            logger.warning("Pass 1 returned no concepts")
            return {"domain": domain, "concepts": [], "relationships": []}

        # Build concept name list for pass 2
        concept_names_for_p2 = [c.get("name", "") for c in concepts_raw if c.get("name")]
        concept_list_str = ", ".join(concept_names_for_p2)

        # --- PASS 2: Detect relationships ---
        logger.info("Pass 2: Detecting relationships among %d concepts...", len(concept_names_for_p2))
        p2 = RELATIONSHIP_DETECTION_PROMPT.format(
            concept_list=concept_list_str,
            transcript=text,
        )
        try:
            raw_rels = _call_llm(p2, use_json_mode=True)
        except Exception as e:
            err_msg = str(e)
            if "max_tokens" in err_msg or "json_validate" in err_msg or "max completion" in err_msg:
                logger.warning("LLM hit token limit on pass 2, retrying with shorter transcript...")
                short_text = text[:15000] + "\n[... transcript truncated for length ...]"
                p2 = RELATIONSHIP_DETECTION_PROMPT.format(
                    concept_list=concept_list_str,
                    transcript=short_text,
                )
                try:
                    raw_rels = _call_llm(p2, use_json_mode=True)
                except Exception:
                    raw_rels = _call_llm(p2, use_json_mode=False)
            else:
                raise

        logger.info("Pass 2 response received (%d chars)", len(raw_rels))
        rel_data = self._parse_json_response(raw_rels)
        relationships_raw = rel_data.get("relationships", [])

        # Combine into final result and parse
        combined_data = {
            "domain": domain,
            "concepts": concepts_raw,
            "relationships": relationships_raw,
        }
        return self._build_pipeline_output(combined_data, transcript)

    def _extract_chunked(self, text: str, client, _call_llm, transcript: dict, chunk_limit: int) -> dict:
        """Split long transcript into chunks, extract from each, merge results."""
        # Split into overlapping chunks for better context at boundaries
        overlap = chunk_limit // 5  # 20% overlap
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_limit
            chunk = text[start:end]
            # Snap to word boundary to avoid cutting mid-word
            if end < len(text):
                last_space = chunk.rfind(" ")
                if last_space > chunk_limit // 2:
                    chunk = chunk[:last_space]
                    end = start + last_space
            chunks.append(chunk)
            start = end - overlap if end < len(text) else len(text)

        logger.info("Transcript too long (%d chars), splitting into %d chunks", len(text), len(chunks))

        all_concepts = []
        all_relationships = []
        domain = "Unknown"

        for i, chunk in enumerate(chunks):
            logger.info("Processing chunk %d/%d (%d chars)...", i + 1, len(chunks), len(chunk))
            try:
                chunk_result = self._extract_single(chunk, _call_llm, transcript)
                if chunk_result.get("domain", "Unknown") != "Unknown":
                    domain = chunk_result["domain"]
                all_concepts.extend(chunk_result.get("concepts", []))
                all_relationships.extend(chunk_result.get("relationships", []))
            except Exception as e:
                logger.warning("Chunk %d failed: %s", i + 1, e)
                continue

        # Deduplicate concepts across chunks
        seen_names = set()
        merged_concepts = []
        for c in all_concepts:
            name = c["name"].lower().strip().replace("_", " ")
            if name not in seen_names:
                seen_names.add(name)
                merged_concepts.append(c)
            else:
                # Update frequency for duplicates
                for mc in merged_concepts:
                    if mc["name"] == name:
                        mc["frequency"] = mc.get("frequency", 1) + c.get("frequency", 1)
                        break

        # Deduplicate relationships across chunks
        concept_names = {c["name"] for c in merged_concepts}
        seen_edges = set()
        merged_rels = []
        for r in all_relationships:
            src = r["from"]
            tgt = r["to"]
            edge_key = (src, tgt)
            if edge_key not in seen_edges and src in concept_names and tgt in concept_names:
                seen_edges.add(edge_key)
                merged_rels.append(r)

        logger.info("Merged chunks: %d concepts, %d relationships", len(merged_concepts), len(merged_rels))

        return {
            "domain": domain,
            "concepts": merged_concepts,
            "relationships": merged_rels,
        }

    def _parse_response(self, raw: str, transcript: dict) -> dict:
        """Parse the LLM JSON response into pipeline-compatible format.
        Legacy method — delegates to new methods.
        """
        data = self._parse_json_response(raw)
        return self._build_pipeline_output(data, transcript)

    def _parse_json_response(self, raw: str) -> dict:
        """Parse raw JSON string from LLM into a dict.

        Has 4-tier fallback: direct parse → code block → brace extraction → empty.
        """
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e1:
            logger.warning("Direct JSON parse failed: %s", e1)
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError as e2:
                    logger.warning("Code block JSON parse failed: %s", e2)

            brace_start = raw.find("{")
            if brace_start >= 0:
                depth = 0
                brace_end = -1
                for idx in range(brace_start, len(raw)):
                    if raw[idx] == "{":
                        depth += 1
                    elif raw[idx] == "}":
                        depth -= 1
                        if depth == 0:
                            brace_end = idx
                            break
                if brace_end > brace_start:
                    try:
                        return json.loads(raw[brace_start:brace_end + 1])
                    except json.JSONDecodeError as e3:
                        logger.warning("Brace-extracted JSON parse failed: %s", e3)

            logger.error("Failed to parse LLM response as JSON. First 500 chars: %s", raw[:500])
            return {}

    def _build_pipeline_output(self, data: dict, transcript: dict) -> dict:
        """Build pipeline-compatible output from parsed LLM data.

        Args:
            data: Parsed dict with 'domain', 'concepts', 'relationships'.
            transcript: Original transcript for segment matching.

        Returns:
            Formatted dict with concepts and relationships.
        """

        domain = data.get("domain", "Unknown")
        raw_concepts = data.get("concepts", [])
        raw_rels = data.get("relationships", [])

        if not raw_concepts and not raw_rels:
            return {"concepts": [], "relationships": [], "domain": domain}

        logger.info("LLM extracted: %d concepts, %d relationships (domain: %s)",
                     len(raw_concepts), len(raw_rels), domain)

        # Build concepts in pipeline-compatible format
        segments = transcript.get("segments", [])
        full_text = transcript.get("full_text", "").lower()

        concepts = []
        seen_names = set()
        for i, c in enumerate(raw_concepts):
            name = c.get("name", "").lower().strip().replace("_", " ")
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            # Find timestamps where concept appears in segments
            timestamps = self._find_timestamps(name, segments)
            frequency = self._count_mentions(name, full_text)

            concepts.append({
                "name": name,
                "normalized_name": c.get("normalized_name", name.title()),
                "importance_score": round(float(c.get("importance_score", 0.5)), 4),
                "frequency": max(frequency, 1),  # LLM found it, so at least 1
                "first_mention": timestamps[0] if timestamps else None,
                "timestamps": timestamps,
                "difficulty": c.get("difficulty", "unknown"),
                "description": c.get("description", ""),
            })

        # Build relationships in pipeline-compatible format (deduplicated)
        concept_names = {c["name"] for c in concepts}
        relationships = []
        seen_edges = set()
        min_confidence = 0.5  # Lowered from 0.75 to keep more valid edges
        for r in raw_rels:
            src = r.get("from", "").lower().strip().replace("_", " ")
            tgt = r.get("to", "").lower().strip().replace("_", " ")
            conf = float(r.get("confidence", 0.7))
            if conf < min_confidence:
                continue
            # Fuzzy-match relationship endpoints to extracted concept names
            src = self._match_concept_name(src, concept_names) or src
            tgt = self._match_concept_name(tgt, concept_names) or tgt
            edge_key = (src, tgt)
            if src in concept_names and tgt in concept_names and src != tgt and edge_key not in seen_edges:
                seen_edges.add(edge_key)
                relationships.append({
                    "from": src,
                    "to": tgt,
                    "relation": "prerequisite",
                    "confidence": round(conf, 4),
                    "evidence": r.get("evidence", "LLM-inferred"),
                    "timestamp": "",
                    "detection_method": "llm",
                })

        return {
            "domain": domain,
            "concepts": concepts,
            "relationships": relationships,
        }

    @staticmethod
    def _match_concept_name(name: str, concept_names: set) -> str | None:
        """Fuzzy-match a name to the closest concept in the set."""
        if name in concept_names:
            return name
        # Try substring matching
        for cn in concept_names:
            if name in cn or cn in name:
                return cn
        # Common abbreviations
        abbrevs = {"bst": "binary search tree", "avl": "avl tree", "dsa": "data structure"}
        if abbrevs.get(name) in concept_names:
            return abbrevs[name]
        return None

    def _find_timestamps(self, concept: str, segments: list[dict]) -> list[str]:
        """Find transcript segments mentioning a concept."""
        pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.IGNORECASE)
        timestamps = []
        for seg in segments:
            text = seg.get("text", "") + " " + seg.get("original_text", "")
            if pattern.search(text):
                label = seg.get("timestamp_label", "")
                if label and label not in timestamps:
                    timestamps.append(label)
        return timestamps

    def _count_mentions(self, concept: str, text: str) -> int:
        """Count occurrences of a concept in text."""
        pattern = re.compile(r"\b" + re.escape(concept) + r"\b", re.IGNORECASE)
        return len(pattern.findall(text))
