"""Streamlit Dashboard for Pedagogical Knowledge Graph Extractor.

Interactive web interface that lets users:
  - Upload educational videos or transcripts
  - Process through the full pipeline
  - Explore interactive knowledge graphs
  - View concept timelines and analytics
  - Download structured JSON output
"""

import json
import os
import sys
import tempfile
import streamlit as st
import streamlit.components.v1 as components

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pipeline.normalizer import CodeMixedNormalizer, transliterate_devanagari
from pipeline.concept_extractor import ConceptExtractor
from pipeline.dependency_detector import DependencyDetector
from pipeline.graph_builder import GraphBuilder
from visualization.graph_visualizer import visualize_graph, get_graph_html
from visualization.timeline_plotter import create_timeline_figure, create_frequency_chart
from utils.helpers import save_json

# ─── Page Config ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Pedagogical Knowledge Graph Extractor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4dd0e1, #2196f3, #5c6bc0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    .sub-header {
        font-size: 0.92rem;
        color: #718096;
        text-align: center;
        margin-bottom: 1.5rem;
        letter-spacing: 0.2px;
    }

    /* Metric cards */
    .metric-row { display: flex; gap: 16px; margin-bottom: 20px; }
    .metric-card {
        flex: 1;
        background: linear-gradient(135deg, rgba(33,150,243,0.07), rgba(92,107,192,0.07));
        border: 1px solid rgba(33,150,243,0.12);
        border-radius: 16px;
        padding: 22px 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4dd0e1, #2196f3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.78rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 6px;
        font-weight: 500;
    }

    /* Concept cards */
    .concept-card {
        background: rgba(33,150,243,0.04);
        border: 1px solid rgba(33,150,243,0.08);
        border-radius: 14px;
        padding: 14px 18px;
        margin: 8px 0;
        color: inherit;
        transition: background 0.2s;
    }
    .concept-card:hover {
        background: rgba(33,150,243,0.09);
    }
    .concept-top {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .concept-rank {
        width: 30px; height: 30px;
        border-radius: 50%;
        background: linear-gradient(135deg, #4dd0e1, #2196f3);
        color: white;
        font-weight: 600;
        font-size: 13px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }
    .concept-name { font-weight: 600; font-size: 15px; }
    .concept-meta { color: #64748b; font-size: 12px; margin-top: 4px; padding-left: 42px; }
    .concept-bar {
        height: 3px;
        background: rgba(255,255,255,0.06);
        border-radius: 3px;
        margin-top: 8px;
        margin-left: 42px;
        overflow: hidden;
    }
    .concept-bar-fill {
        height: 100%;
        border-radius: 3px;
        background: linear-gradient(90deg, #4dd0e1, #2196f3, #5c6bc0);
    }

    /* Learning path */
    .learning-path {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
        padding: 18px 20px;
        background: rgba(33,150,243,0.03);
        border: 1px solid rgba(33,150,243,0.08);
        border-radius: 16px;
        margin-top: 8px;
    }
    .lp-step {
        background: linear-gradient(135deg, rgba(33,150,243,0.10), rgba(92,107,192,0.10));
        border: 1px solid rgba(33,150,243,0.14);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 500;
        color: #e2e8f0;
    }
    .lp-arrow { color: #4dd0e1; font-size: 16px; margin: 0 2px; }

    /* Relationship cards */
    .rel-card {
        padding: 10px 16px;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        margin: 6px 0;
    }
    .rel-card .rel-main { font-size: 14px; }
    .rel-card .rel-meta { color: #64748b; font-size: 12px; margin-top: 3px; }

    /* Section headers */
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 16px;
        padding-bottom: 10px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }

    /* Hide default streamlit metrics */
    [data-testid="stMetric"] { display: none; }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize Streamlit session state variables."""
    defaults = {
        "transcript": None,
        "normalized_transcript": None,
        "concepts": None,
        "relationships": None,
        "graph": None,
        "graph_builder": None,
        "json_output": None,
        "processed": False,
        "extraction_mode": "Rule-Based (CS Only)",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def process_transcript(transcript: dict) -> dict:
    """Run the full pipeline on a transcript.

    Args:
        transcript: Transcript dict with segments and full_text.

    Returns:
        Final JSON output dict.
    """
    progress = st.progress(0, text="Initializing pipeline...")

    # Step 1: Normalize
    progress.progress(15, text="Normalizing code-mixed text...")
    normalizer = CodeMixedNormalizer()
    normalized = normalizer.normalize_transcript(transcript)
    st.session_state.normalized_transcript = normalized

    # Step 2: Extract concepts
    progress.progress(40, text="Extracting concepts...")
    extractor = ConceptExtractor()
    concepts = extractor.extract(normalized)
    st.session_state.concepts = concepts

    # Step 3: Detect dependencies
    progress.progress(60, text="Detecting prerequisite relationships...")
    detector = DependencyDetector()
    relationships = detector.detect(normalized, concepts)
    st.session_state.relationships = relationships

    # Step 4: Build graph
    progress.progress(80, text="Building knowledge graph...")
    builder = GraphBuilder()
    video_id = transcript.get("video_id", "uploaded_video")
    graph = builder.build(video_id, concepts, relationships, normalized)
    st.session_state.graph = graph
    st.session_state.graph_builder = builder

    # Step 5: Generate JSON output
    progress.progress(95, text="Generating output...")
    json_output = builder.to_json(normalized)
    st.session_state.json_output = json_output

    progress.progress(100, text="Done!")
    st.session_state.processed = True

    return json_output


def process_transcript_llm(transcript: dict) -> dict:
    """Run the LLM-powered pipeline on a transcript.

    Args:
        transcript: Transcript dict with segments and full_text.

    Returns:
        Final JSON output dict.
    """
    from pipeline.llm_extractor import LLMExtractor

    progress = st.progress(0, text="Initializing LLM pipeline...")

    # Step 1: LLM extraction (concepts + prerequisites)
    progress.progress(20, text="Sending to LLM for analysis...")
    extractor = LLMExtractor()
    result = extractor.extract(transcript)

    # Step 1b: Rule-based normalization for full text display
    # normalizer.normalize_transcript() already produces:
    #   - original_full_text: transliterated Hinglish (Roman script)
    #   - full_text: normalized English
    #   - segments with original_text and text per segment
    progress.progress(50, text="Normalizing full transcript...")
    normalizer = CodeMixedNormalizer()
    normalized = normalizer.normalize_transcript(transcript)

    st.session_state.normalized_transcript = normalized

    concepts = result.get("concepts", [])
    relationships = result.get("relationships", [])
    st.session_state.concepts = concepts
    st.session_state.relationships = relationships

    # Step 2: Build graph
    progress.progress(70, text="Building knowledge graph...")
    builder = GraphBuilder()
    video_id = transcript.get("video_id", "uploaded_video")
    graph = builder.build(video_id, concepts, relationships, normalized)
    st.session_state.graph = graph
    st.session_state.graph_builder = builder

    # Step 3: Generate JSON output
    progress.progress(90, text="Generating output...")
    json_output = builder.to_json(normalized)
    # Add domain info from LLM
    json_output["metadata"]["domain"] = result.get("domain", "Unknown")
    json_output["metadata"]["extraction_method"] = "llm"
    st.session_state.json_output = json_output

    progress.progress(100, text="Done!")
    st.session_state.processed = True

    return json_output


def process_video(video_path: str) -> dict:
    """Run the full pipeline starting from video file.

    Args:
        video_path: Path to the video file.

    Returns:
        Final JSON output dict.
    """
    # Import here to avoid loading Whisper unless needed
    from pipeline.speech_to_text import transcribe

    transcript = transcribe(video_path)
    st.session_state.transcript = transcript

    # Route to the right pipeline based on mode
    mode = st.session_state.get("extraction_mode", "Rule-Based (CS Only)")
    if mode == "LLM-Powered (Any Domain)":
        return process_transcript_llm(transcript)
    return process_transcript(transcript)


def _run_transcript_pipeline(transcript: dict) -> dict:
    """Route transcript to the correct pipeline based on extraction mode."""
    mode = st.session_state.get("extraction_mode", "Rule-Based (CS Only)")
    if mode == "LLM-Powered (Any Domain)":
        return process_transcript_llm(transcript)
    return process_transcript(transcript)


def download_youtube_video(url: str) -> str:
    """Download a YouTube video using yt-dlp.

    Args:
        url: YouTube video URL.

    Returns:
        Path to the downloaded video file.
    """
    import subprocess
    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, "%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio/best[height<=720]/best",
        "--no-playlist",
        "-o", output_path,
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
    # Find the downloaded file
    for f in os.listdir(tmp_dir):
        return os.path.join(tmp_dir, f)
    raise RuntimeError("No file downloaded")


def render_sidebar():
    """Render the sidebar with input options."""
    with st.sidebar:
        st.markdown("## 📥 Input")

        input_mode = st.radio(
            "Choose input type:",
            ["YouTube URL", "Upload Video", "Upload Transcript JSON", "Paste Transcript"],
            index=0,
        )

        if input_mode == "YouTube URL":
            yt_url = st.text_input(
                "YouTube Video URL",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            if yt_url and st.button("🚀 Process YouTube Video", type="primary"):
                try:
                    with st.spinner("Downloading video from YouTube..."):
                        video_path = download_youtube_video(yt_url)
                    st.success(f"Downloaded: {os.path.basename(video_path)}")
                    with st.spinner("Transcribing and processing..."):
                        process_video(video_path)
                    # Cleanup downloaded file
                    try:
                        os.unlink(video_path)
                        os.rmdir(os.path.dirname(video_path))
                    except OSError:
                        pass
                except Exception as e:
                    st.error(f"Error: {e}")

        elif input_mode == "Upload Video":
            video_file = st.file_uploader(
                "Upload educational video",
                type=["mp4", "mkv", "webm", "avi", "mov"],
            )
            if video_file and st.button("🚀 Process Video", type="primary"):
                # Save uploaded file temporarily
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=os.path.splitext(video_file.name)[1]
                )
                tmp.write(video_file.read())
                tmp.close()
                with st.spinner("Processing video..."):
                    process_video(tmp.name)
                os.unlink(tmp.name)

        elif input_mode == "Upload Transcript JSON":
            json_file = st.file_uploader(
                "Upload transcript JSON",
                type=["json"],
            )
            if json_file and st.button("🚀 Process Transcript", type="primary"):
                transcript = json.loads(json_file.read().decode("utf-8"))
                st.session_state.transcript = transcript
                with st.spinner("Processing transcript..."):
                    _run_transcript_pipeline(transcript)

        else:  # Paste Transcript
            st.markdown("#### Paste raw transcript text below")
            pasted_text = st.text_area(
                "Transcript text (code-mixed / Hinglish)",
                height=200,
                placeholder=(
                    "Aaj hum arrays ke baare mein samjhenge. "
                    "Pehle arrays samjho phir linked list easy lagega. "
                    "Stack ka concept push aur pop pe depend karta hai..."
                ),
            )
            video_id = st.text_input("Video ID (optional)", value="pasted_video")

            if pasted_text and st.button("🚀 Process Text", type="primary"):
                # Convert pasted text to transcript format
                sentences = [s.strip() for s in pasted_text.replace("\n", " ").split(".") if s.strip()]
                segments = []
                for i, sent in enumerate(sentences):
                    segments.append({
                        "id": i,
                        "start": i * 10.0,
                        "end": (i + 1) * 10.0,
                        "text": sent,
                        "timestamp_label": f"{i // 6}:{(i % 6) * 10:02d}",
                    })

                transcript = {
                    "video_id": video_id,
                    "metadata": {"source_file": "pasted_text", "language_detected": "hi"},
                    "full_text": pasted_text,
                    "segments": segments,
                }
                st.session_state.transcript = transcript
                with st.spinner("Processing..."):
                    _run_transcript_pipeline(transcript)

        st.markdown("---")
        st.markdown("### ⚙️ Settings")

        extraction_mode = st.radio(
            "Extraction Mode",
            ["Rule-Based (CS Only)", "LLM-Powered (Any Domain)"],
            index=0 if st.session_state.get("extraction_mode") == "Rule-Based (CS Only)" else 1,
            help="Rule-Based uses hardcoded CS dictionary + RAKE. LLM uses Groq API for any domain.",
        )
        st.session_state.extraction_mode = extraction_mode

        if extraction_mode == "Rule-Based (CS Only)":
            st.markdown(f"**Min concept score:** {0.3}")
            st.markdown(f"**Min confidence:** {0.4}")
        else:
            st.caption("Uses Groq LLM for any-domain extraction")

        if st.session_state.processed:
            st.markdown("---")
            st.success("✅ Pipeline complete!")


def render_main():
    """Render the main content area."""
    st.markdown('<div class="main-header">🎓 Pedagogical Knowledge Graph Extractor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">'
        'Transform educational videos into interactive knowledge graphs with AI-powered analysis'
        '</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.processed:
        st.info("👈 Use the sidebar to upload a video, transcript, or paste text to begin.")

        # Show sample architecture
        with st.expander("📊 System Architecture", expanded=True):
            st.code("""
    Video Input  →  Speech-to-Text (Whisper)
                         │
                    ┌────┴────┐
                    │         │
           Rule-Based     LLM-Powered
           (CS Only)      (Any Domain)
                    │         │
            ┌───────┘         └──── Groq API ──┐
            │                                   │
    Code-Mixed Normalizer             Single LLM call:
    (Hinglish → English)              Normalize + Extract
            │                         + Prerequisites
    Concept Extractor                       │
    (Domain Dict + RAKE)                    │
            │                               │
    Prerequisite Detector                   │
    (Pattern + Temporal)                    │
            │                               │
            └───────────┬───────────────────┘
                        │
                Knowledge Graph Builder
                    (NetworkX)
                        │
                Interactive Visualization
                   (PyVis + Streamlit)
            """, language=None)
        return

    # ─── Results Tabs ────────────────────────────────────────────
    tabs = st.tabs([
        "🔗 Knowledge Graph",
        "📝 Transcript",
        "🧠 Concepts",
        "📊 Analytics",
        "📄 JSON Output",
    ])

    # === TAB 1: Knowledge Graph ===
    with tabs[0]:
        graph = st.session_state.graph
        if graph and graph.number_of_nodes() > 0:
            builder = st.session_state.graph_builder
            path = builder.get_learning_path() if builder else []

            # Custom metric cards
            st.markdown(
                f'<div class="metric-row">'
                f'<div class="metric-card"><div class="metric-value">{graph.number_of_nodes()}</div><div class="metric-label">Concepts</div></div>'
                f'<div class="metric-card"><div class="metric-value">{graph.number_of_edges()}</div><div class="metric-label">Prerequisites</div></div>'
                f'<div class="metric-card"><div class="metric-value">{len(path)}</div><div class="metric-label">Learning Steps</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            html = get_graph_html(graph, height="650px")
            components.html(html, height=670, scrolling=False)

            # Learning path
            if builder and path:
                st.markdown('<div class="section-title">📚 Recommended Learning Order</div>', unsafe_allow_html=True)
                steps_html = ''.join(
                    [f'<span class="lp-step">{c.replace("_", " ").title()}</span><span class="lp-arrow">→</span>' for c in path]
                )
                # Remove trailing arrow
                if steps_html.endswith('<span class="lp-arrow">→</span>'):
                    steps_html = steps_html[:-len('<span class="lp-arrow">→</span>')]
                st.markdown(f'<div class="learning-path">{steps_html}</div>', unsafe_allow_html=True)
        else:
            st.warning("No graph data available. Try with more content.")

    # === TAB 2: Transcript ===
    with tabs[1]:
        st.markdown('<div class="section-title">📝 Transcript</div>', unsafe_allow_html=True)

        transcript = st.session_state.transcript

        if transcript:
            full_text = transcript.get("full_text", "")
            st.text_area("Full Transcript", value=full_text, height=400, disabled=True)

            # Segment-by-segment view
            with st.expander("📋 Segment-by-Segment View"):
                for seg in transcript.get("segments", []):
                    ts = seg.get("timestamp_label", "")
                    text = seg.get("text", "")
                    st.markdown(f"**[{ts}]** {text}")
                    st.markdown("---")

    # === TAB 3: Concepts ===
    with tabs[2]:
        concepts = st.session_state.concepts
        if concepts:
            st.markdown('<div class="section-title">🧠 Extracted Concepts</div>', unsafe_allow_html=True)
            max_score = max((c.get("importance_score", 0) for c in concepts), default=1) or 1
            for i, concept in enumerate(concepts, 1):
                name = concept["name"].replace("_", " ").title()
                score = concept.get("importance_score", 0)
                freq = concept.get("frequency", 0)
                first = concept.get("first_mention", "N/A")
                bar_pct = round((score / max_score) * 100)

                st.markdown(
                    f'<div class="concept-card">'
                    f'<div class="concept-top">'
                    f'<div class="concept-rank">{i}</div>'
                    f'<div class="concept-name">{name}</div>'
                    f'</div>'
                    f'<div class="concept-meta">Score: {score:.2f} &nbsp;·&nbsp; Mentions: {freq} &nbsp;·&nbsp; First: {first}</div>'
                    f'<div class="concept-bar"><div class="concept-bar-fill" style="width:{bar_pct}%"></div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Relationships
            relationships = st.session_state.relationships
            if relationships:
                st.markdown('<div class="section-title" style="margin-top:28px">🔗 Detected Prerequisites</div>', unsafe_allow_html=True)
                for rel in relationships:
                    src = rel["from"].replace("_", " ").title()
                    tgt = rel["to"].replace("_", " ").title()
                    conf = rel.get("confidence", 0)
                    evidence = rel.get("evidence", "")
                    method = rel.get("detection_method", "")

                    dot = "🟢" if conf > 0.8 else "🟡" if conf > 0.6 else "🟠"
                    meta_parts = [f"confidence: {conf:.2f}"]
                    if method:
                        meta_parts.append(f"method: {method}")
                    meta = ", ".join(meta_parts)
                    ev_html = f'<div class="rel-meta">\"{evidence}\"</div>' if evidence else ''

                    st.markdown(
                        f'<div class="rel-card">'
                        f'<div class="rel-main">{dot} <b>{src}</b> → <b>{tgt}</b></div>'
                        f'<div class="rel-meta">{meta}</div>'
                        f'{ev_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
        else:
            st.warning("No concepts extracted.")

    # === TAB 4: Analytics ===
    with tabs[3]:
        json_output = st.session_state.json_output
        concepts = st.session_state.concepts

        if json_output and concepts:
            st.markdown('<div class="section-title">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
            analytics = json_output.get("analytics", {})

            # --- Graph Metrics ---
            builder = st.session_state.graph_builder
            graph = st.session_state.graph
            if builder and graph and graph.number_of_nodes() > 0:
                gm = builder.get_metrics_summary()

                st.markdown(
                    f'<div class="metric-row">'
                    f'<div class="metric-card"><div class="metric-value">{analytics.get("total_concepts", 0)}</div><div class="metric-label">Concepts</div></div>'
                    f'<div class="metric-card"><div class="metric-value">{analytics.get("total_relationships", 0)}</div><div class="metric-label">Relationships</div></div>'
                    f'<div class="metric-card"><div class="metric-value">{analytics.get("avg_confidence", 0):.2f}</div><div class="metric-label">Avg Confidence</div></div>'
                    f'<div class="metric-card"><div class="metric-value">{gm.get("density", 0):.3f}</div><div class="metric-label">Graph Density</div></div>'
                    f'<div class="metric-card"><div class="metric-value">{gm.get("max_depth", 0)}</div><div class="metric-label">Max Depth</div></div>'
                    f'<div class="metric-card"><div class="metric-value">{gm.get("num_communities", 1)}</div><div class="metric-label">Clusters</div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Graph metrics panels
                gm_col1, gm_col2 = st.columns(2)

                with gm_col1:
                    st.markdown("##### 🏆 Top Concepts by PageRank")
                    for name, pr in gm.get("top_pagerank", []):
                        display = name.replace("_", " ").title()
                        bar_w = int(pr / max(gm["top_pagerank"][0][1], 0.0001) * 100)
                        st.markdown(
                            f'<div class="concept-card" style="padding:10px 14px;margin:4px 0">'
                            f'<div style="display:flex;justify-content:space-between">'
                            f'<span style="font-weight:600">{display}</span>'
                            f'<span style="color:#4dd0e1;font-weight:600">{pr:.4f}</span></div>'
                            f'<div class="concept-bar" style="margin-left:0"><div class="concept-bar-fill" style="width:{bar_w}%"></div></div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown("##### 🌉 Gateway Concepts (Betweenness)")
                    for name, bw in gm.get("top_gateway", []):
                        if bw == 0:
                            continue
                        display = name.replace("_", " ").title()
                        st.markdown(
                            f'<div class="concept-card" style="padding:10px 14px;margin:4px 0">'
                            f'<span style="font-weight:600">{display}</span>'
                            f' &nbsp;·&nbsp; <span style="color:#ffb74d">{bw:.3f}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                with gm_col2:
                    st.markdown("##### 🏗️ Most Foundational (Out-degree)")
                    for name, deg in gm.get("top_foundational", []):
                        if deg == 0:
                            continue
                        display = name.replace("_", " ").title()
                        st.markdown(
                            f'<div class="concept-card" style="padding:10px 14px;margin:4px 0">'
                            f'<span style="font-weight:600">{display}</span>'
                            f' &nbsp;·&nbsp; <span style="color:#81c784">teaches {deg} concepts</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    st.markdown("##### 🎯 Most Complex (In-degree)")
                    for name, deg in gm.get("top_complex", []):
                        if deg == 0:
                            continue
                        display = name.replace("_", " ").title()
                        st.markdown(
                            f'<div class="concept-card" style="padding:10px 14px;margin:4px 0">'
                            f'<span style="font-weight:600">{display}</span>'
                            f' &nbsp;·&nbsp; <span style="color:#ef9a9a">needs {deg} prerequisites</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                # Community clusters
                community_summary = gm.get("communities", [])
                if community_summary and len(community_summary) > 1:
                    st.markdown("##### 🧩 Topic Clusters (Community Detection)")
                    cluster_colors = ["#4dd0e1", "#ff7043", "#66bb6a", "#ab47bc", "#ffa726",
                                      "#42a5f5", "#ef5350", "#26c6da", "#8d6e63", "#78909c"]
                    for c in community_summary:
                        cid = c["id"]
                        color = cluster_colors[cid % len(cluster_colors)]
                        members_str = ", ".join(c["members"])
                        st.markdown(
                            f'<div class="concept-card" style="padding:10px 14px;margin:4px 0;border-left:3px solid {color}">'
                            f'<span style="font-weight:600;color:{color}">Cluster #{cid + 1}</span>'
                            f' &nbsp;·&nbsp; <span style="color:#94a3b8">{c["size"]} concepts</span>'
                            f'<div style="color:#b0bec5;font-size:12px;margin-top:4px">{members_str}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                st.markdown("---")

            else:
                st.markdown(
                    f'<div class="metric-row">'
                    f'<div class="metric-card"><div class="metric-value">{analytics.get("total_concepts", 0)}</div><div class="metric-label">Total Concepts</div></div>'
                    f'<div class="metric-card"><div class="metric-value">{analytics.get("total_relationships", 0)}</div><div class="metric-label">Relationships</div></div>'
                    f'<div class="metric-card"><div class="metric-value">{analytics.get("avg_confidence", 0):.2f}</div><div class="metric-label">Avg Confidence</div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Timeline
            timeline_data = json_output.get("timeline", [])
            if timeline_data:
                st.markdown("#### ⏱️ Concept Timeline")
                fig = create_timeline_figure(timeline_data)
                st.plotly_chart(fig, use_container_width=True)

            # Frequency chart
            st.markdown("#### 📊 Concept Frequency")
            fig = create_frequency_chart(concepts)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No analytics data available.")

    # === TAB 5: JSON Output ===
    with tabs[4]:
        st.markdown('<div class="section-title">📄 Structured JSON Output</div>', unsafe_allow_html=True)
        json_output = st.session_state.json_output
        if json_output:
            json_str = json.dumps(json_output, indent=2, ensure_ascii=False)
            st.code(json_str, language="json", line_numbers=True)

            # Download button
            json_str = json.dumps(json_output, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"{json_output.get('video_id', 'output')}_knowledge_graph.json",
                mime="application/json",
            )

            # Also save to outputs
            video_id = json_output.get("video_id", "output")
            save_path = os.path.join(PROJECT_ROOT, "outputs", "json", f"{video_id}_knowledge_graph.json")
            save_json(json_output, save_path)
            st.caption(f"Also saved to: outputs/json/{video_id}_knowledge_graph.json")


# ─── Main Entry ──────────────────────────────────────────────────
def main():
    init_session_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
