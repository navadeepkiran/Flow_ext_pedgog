"""Run the full PedagogicalFlowExtractor pipeline from the command line.

Usage:
    python run_pipeline.py --video data/raw_videos/my_video.mp4
    python run_pipeline.py --transcript data/transcripts/my_transcript.json
    python run_pipeline.py --text "Pehle arrays samjho phir linked list"
"""

import argparse
import json
import os
import sys

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.normalizer import CodeMixedNormalizer
from pipeline.concept_extractor import ConceptExtractor
from pipeline.dependency_detector import DependencyDetector
from pipeline.graph_builder import GraphBuilder
from visualization.graph_visualizer import visualize_graph
from utils.helpers import save_json, format_timestamp
from utils.logger import get_logger

logger = get_logger("run_pipeline")


def build_transcript_from_text(text: str, video_id: str = "cli_input") -> dict:
    """Convert raw text into a transcript dict.

    Args:
        text: Raw transcript text.
        video_id: Identifier for the source.

    Returns:
        Transcript dictionary.
    """
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    segments = []
    for i, sent in enumerate(sentences):
        segments.append({
            "id": i,
            "start": i * 10.0,
            "end": (i + 1) * 10.0,
            "text": sent,
            "timestamp_label": format_timestamp(i * 10.0),
        })

    return {
        "video_id": video_id,
        "metadata": {"source_file": "cli_text", "language_detected": "hi"},
        "full_text": text,
        "segments": segments,
    }


def run(transcript: dict) -> dict:
    """Execute the full pipeline on a transcript.

    Args:
        transcript: Transcript dict.

    Returns:
        Knowledge graph JSON output.
    """
    video_id = transcript.get("video_id", "unknown")

    # Step 1: Normalize
    logger.info("=" * 60)
    logger.info("STEP 1: Normalizing code-mixed text")
    logger.info("=" * 60)
    normalizer = CodeMixedNormalizer()
    normalized = normalizer.normalize_transcript(transcript)

    # Step 2: Extract concepts
    logger.info("=" * 60)
    logger.info("STEP 2: Extracting concepts")
    logger.info("=" * 60)
    extractor = ConceptExtractor()
    concepts = extractor.extract(normalized)

    logger.info("Extracted concepts:")
    for c in concepts:
        logger.info("  - %-20s (score: %.3f, freq: %d)", c["name"], c["importance_score"], c["frequency"])

    # Step 3: Detect prerequisites
    logger.info("=" * 60)
    logger.info("STEP 3: Detecting prerequisite relationships")
    logger.info("=" * 60)
    detector = DependencyDetector()
    relationships = detector.detect(normalized, concepts)

    logger.info("Detected relationships:")
    for r in relationships:
        logger.info("  %s → %s (conf: %.2f, method: %s)", r["from"], r["to"], r["confidence"], r["detection_method"])

    # Step 4: Build graph
    logger.info("=" * 60)
    logger.info("STEP 4: Building knowledge graph")
    logger.info("=" * 60)
    builder = GraphBuilder()
    graph = builder.build(video_id, concepts, relationships, normalized)

    # Step 5: Save outputs
    logger.info("=" * 60)
    logger.info("STEP 5: Saving outputs")
    logger.info("=" * 60)
    json_path = builder.save(transcript=normalized)
    html_path = visualize_graph(graph)
    json_output = builder.to_json(normalized)

    # Learning path
    learning_path = builder.get_learning_path()
    logger.info("Recommended learning order: %s", " → ".join(learning_path))

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("  JSON output : %s", json_path)
    logger.info("  Graph HTML  : %s", html_path)
    logger.info("  Concepts    : %d", len(concepts))
    logger.info("  Relationships: %d", len(relationships))
    logger.info("=" * 60)

    return json_output


def run_llm(transcript: dict) -> dict:
    """Execute the LLM-powered pipeline on a transcript.

    Args:
        transcript: Transcript dict.

    Returns:
        Knowledge graph JSON output.
    """
    from pipeline.llm_extractor import LLMExtractor

    video_id = transcript.get("video_id", "unknown")

    # Single LLM call for normalization + extraction + prerequisites
    logger.info("=" * 60)
    logger.info("LLM MODE: Sending to Groq for analysis")
    logger.info("=" * 60)
    extractor = LLMExtractor()
    result = extractor.extract(transcript)

    normalized = dict(transcript)
    normalized["original_full_text"] = transcript.get("full_text", "")
    # Use rule-based normalizer for full text normalization
    from pipeline.normalizer import CodeMixedNormalizer
    normalizer = CodeMixedNormalizer()
    norm_result = normalizer.normalize_transcript(transcript)
    normalized["full_text"] = norm_result.get("full_text", transcript.get("full_text", ""))
    normalized["normalization_applied"] = True

    concepts = result.get("concepts", [])
    relationships = result.get("relationships", [])

    logger.info("Extracted concepts:")
    for c in concepts:
        logger.info("  - %-20s (score: %.3f, freq: %d)", c["name"], c["importance_score"], c["frequency"])
    logger.info("Detected relationships:")
    for r in relationships:
        logger.info("  %s → %s (conf: %.2f)", r["from"], r["to"], r["confidence"])

    # Build graph
    logger.info("=" * 60)
    logger.info("Building knowledge graph")
    logger.info("=" * 60)
    builder = GraphBuilder()
    graph = builder.build(video_id, concepts, relationships, normalized)

    # Save outputs
    json_path = builder.save(transcript=normalized)
    html_path = visualize_graph(graph)
    json_output = builder.to_json(normalized)
    json_output["metadata"]["domain"] = result.get("domain", "Unknown")
    json_output["metadata"]["extraction_method"] = "llm"

    learning_path = builder.get_learning_path()
    logger.info("Recommended learning order: %s", " → ".join(learning_path))

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE (LLM Mode)")
    logger.info("  JSON output : %s", json_path)
    logger.info("  Graph HTML  : %s", html_path)
    logger.info("  Concepts    : %d", len(concepts))
    logger.info("  Relationships: %d", len(relationships))
    logger.info("  Domain      : %s", result.get("domain", "Unknown"))
    logger.info("=" * 60)

    return json_output


def main():
    parser = argparse.ArgumentParser(
        description="Pedagogical Knowledge Graph Extractor - CLI"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video", help="Path to educational video file")
    group.add_argument("--transcript", help="Path to transcript JSON file")
    group.add_argument("--text", help="Raw transcript text string")

    parser.add_argument("--video-id", default=None, help="Video identifier")
    parser.add_argument(
        "--mode", choices=["rule", "llm"], default="rule",
        help="Extraction mode: 'rule' for rule-based CS, 'llm' for LLM-powered any domain",
    )

    args = parser.parse_args()

    if args.video:
        from pipeline.speech_to_text import transcribe
        transcript = transcribe(args.video)
    elif args.transcript:
        with open(args.transcript, "r", encoding="utf-8") as f:
            transcript = json.load(f)
    else:
        vid = args.video_id or "cli_input"
        transcript = build_transcript_from_text(args.text, vid)

    if args.mode == "llm":
        run_llm(transcript)
    else:
        run(transcript)


if __name__ == "__main__":
    main()
