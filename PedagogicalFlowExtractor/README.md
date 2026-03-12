# 🎓 Pedagogical Knowledge Graph Extractor

> **Converting unstructured multilingual educational discourse into structured pedagogical knowledge graphs.**

An intelligent system that processes code-mixed (Hinglish) educational videos, extracts key academic concepts, detects prerequisite relationships, and outputs an interactive knowledge graph — enabling automated curriculum sequencing and learning path optimization.

---

## 🌟 Key Features

- **🗣️ Speech-to-Text** — Whisper-based transcription with timestamp awareness
- **🌐 Code-Mixed Normalization** — Hinglish → English translation preserving technical terms
- **🧠 Hybrid Concept Extraction** — Domain dictionary + RAKE keyword extraction with weighted scoring
- **🔗 Prerequisite Detection** — Pattern-based and temporal pedagogical cue analysis
- **📊 Interactive Knowledge Graph** — PyVis visualization with hover tooltips and directional edges
- **⏱️ Concept Timeline** — Visual teaching flow showing when concepts appear
- **🖥️ Streamlit Dashboard** — Full interactive web interface

---

## 📊 Architecture

```
             ┌────────────────────┐
             │    Video Input     │
             │  (Code-Mixed)      │
             └─────────┬──────────┘
                       │
                       ▼
             ┌────────────────────┐
             │  Speech-to-Text    │
             │    (Whisper)       │
             └─────────┬──────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │  Code-Mixed Normalization │
         │  (Hinglish → English)     │
         └────────────┬─────────────┘
                      │
                      ▼
             ┌────────────────────┐
             │  Concept Extractor  │
             │ (Dict + RAKE)       │
             └─────────┬──────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │  Prerequisite Detector    │
         │  (Patterns + Temporal)    │
         └────────────┬─────────────┘
                      │
                      ▼
             ┌────────────────────┐
             │  Knowledge Graph    │
             │   (NetworkX)        │
             └─────────┬──────────┘
                       │
                       ▼
         ┌──────────────────────────┐
         │   Interactive Dashboard   │
         │  (PyVis + Streamlit)      │
         └──────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- FFmpeg (for audio extraction)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd PedagogicalFlowExtractor

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Download NLTK data (needed for RAKE)
python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"
```

### Usage

#### Option 1: Streamlit Dashboard (Recommended)

```bash
cd PedagogicalFlowExtractor
streamlit run app/streamlit_app.py
```

Then open `http://localhost:8501` in your browser.

#### Option 2: Python Script

```python
from pipeline.speech_to_text import transcribe
from pipeline.normalizer import CodeMixedNormalizer
from pipeline.concept_extractor import ConceptExtractor
from pipeline.dependency_detector import DependencyDetector
from pipeline.graph_builder import GraphBuilder
from visualization.graph_visualizer import visualize_graph

# Step 1: Transcribe video
transcript = transcribe("data/raw_videos/my_video.mp4")

# Step 2: Normalize code-mixed text
normalizer = CodeMixedNormalizer()
normalized = normalizer.normalize_transcript(transcript)

# Step 3: Extract concepts
extractor = ConceptExtractor()
concepts = extractor.extract(normalized)

# Step 4: Detect prerequisites
detector = DependencyDetector()
relationships = detector.detect(normalized, concepts)

# Step 5: Build knowledge graph
builder = GraphBuilder()
graph = builder.build("my_video", concepts, relationships, normalized)
builder.save()

# Step 6: Visualize
visualize_graph(graph)
```

---

## 📁 Project Structure

```
PedagogicalFlowExtractor/
│
├── data/
│   ├── raw_videos/              # Input videos
│   ├── transcripts/             # Generated transcripts
│   ├── hinglish_lexicon.json    # 150+ Hinglish → English mappings
│   └── cs_concepts.json         # 150+ CS concept dictionary
│
├── pipeline/
│   ├── speech_to_text.py        # Whisper STT integration
│   ├── normalizer.py            # Code-mixed normalizer
│   ├── concept_extractor.py     # Hybrid concept mining
│   ├── dependency_detector.py   # Prerequisite detection
│   └── graph_builder.py         # Knowledge graph construction
│
├── visualization/
│   ├── graph_visualizer.py      # PyVis interactive graphs
│   └── timeline_plotter.py      # Plotly concept timeline
│
├── app/
│   └── streamlit_app.py         # Interactive dashboard
│
├── outputs/
│   ├── graphs/                  # HTML graph files
│   ├── json/                    # Knowledge graph JSON
│   └── reports/                 # Logs and reports
│
├── utils/
│   ├── config.py                # Configuration management
│   ├── logger.py                # Structured logging
│   └── helpers.py               # Utility functions
│
├── config.yaml                  # Pipeline configuration
├── requirements.txt             # Dependencies
└── README.md
```

---

## 📝 Output Format

```json
{
  "video_id": "dsa_hinglish_001",
  "metadata": {
    "language": "code-mixed (Hindi-English)",
    "processed_at": "2026-03-08T10:30:00Z"
  },
  "concepts": [
    {
      "name": "array",
      "normalized_name": "Array",
      "importance_score": 0.89,
      "frequency": 15,
      "first_mention": "1:23",
      "timestamps": ["1:23", "2:45", "5:12"]
    }
  ],
  "relationships": [
    {
      "from": "array",
      "to": "linked list",
      "relation": "prerequisite",
      "confidence": 0.92,
      "evidence": "pehle arrays samjho phir linked list"
    }
  ],
  "timeline": [
    {"time": "0:45", "concept": "variable", "importance": 0.7},
    {"time": "1:23", "concept": "array", "importance": 0.9}
  ]
}
```

---

## 🔧 Configuration

Edit `config.yaml` to customize:

```yaml
whisper:
  model: "base"       # tiny/base/small/medium/large
  language: "hi"

extractor:
  min_concept_score: 0.3
  weights:
    domain_match: 0.5
    rake: 0.3
    frequency: 0.2

detector:
  min_confidence: 0.4
```

---

## 🎯 Innovation Highlights

1. **Code-Mixed Language Robustness** — Handles Hinglish naturally using a 150+ term lexicon with phrase-level and pedagogical pattern matching

2. **Hybrid Concept Extraction** — Multi-signal approach combining domain dictionary, RAKE, and frequency analysis with configurable weights

3. **Pedagogical Cue Detection** — 18+ linguistic patterns (Hindi + English) for detecting prerequisite relationships from teaching discourse

4. **Temporal Prerequisite Inference** — Uses concept mention ordering as weak supervision for relationship discovery

5. **Interactive Knowledge Graphs** — Force-directed PyVis graphs with color-coded importance, directional prerequisite arrows, and rich hover tooltips

---

## 🧪 Sample Videos

Tested with code-mixed educational content from:
- CodeWithHarry (Data Structures)
- Gate Smashers (Algorithms)
- Apna College (DSA)

---

## 📜 License

MIT License

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [NetworkX](https://networkx.org/) for graph algorithms
- [PyVis](https://pyvis.readthedocs.io/) for interactive visualization
- [Streamlit](https://streamlit.io/) for rapid dashboard development
