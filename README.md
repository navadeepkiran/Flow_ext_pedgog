# 🎓 Pedagogical Knowledge Graph Extractor
### 📂 Google Drive — All Outputs

**[📁 View All Video Outputs on Google Drive](https://drive.google.com/drive/folders/1OsHUFPUKO1nrj10ChS3uKDVBH0SxNb3o?usp=sharing)**

> **Converting unstructured multilingual educational discourse into structured pedagogical knowledge graphs.**

An intelligent system that processes code-mixed (Hinglish & Tenglish) educational videos, extracts key academic concepts, detects prerequisite relationships, and outputs an interactive knowledge graph — enabling automated curriculum sequencing and learning path optimization.



## 🛠️ Setup & Installation

### Prerequisites

| Tool | Required | Notes |
|------|----------|-------|
| **Python** | 3.10+ | Tested on 3.11 |
| **FFmpeg** | Required | For audio extraction from videos |
| **Groq API Key** | Optional | Only needed for LLM mode ([get free key](https://console.groq.com/keys)) |

### Step 1: Clone & Create Virtual Environment

```bash
git clone <repo-url>
cd PedagogicalFlowExtractor

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Download NLTK Data

```bash
python -c "import nltk; nltk.download('punkt_tab'); nltk.download('stopwords')"
```

### Step 4: Install FFmpeg

- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH, or use `winget install FFmpeg`
- **Linux**: `sudo apt install ffmpeg`
- **Mac**: `brew install ffmpeg`

### Step 5: Set Groq API Key (Optional — LLM Mode Only)

Create a `.env` file in `PedagogicalFlowExtractor/`:
```env
GROQ_API_KEY=your_api_key_here
```

Or set it in `config.yaml` under `llm.api_key`.

---

## 🚀 How to Run

### Option 1: Streamlit Dashboard (Recommended)

```bash
cd PedagogicalFlowExtractor
streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` in your browser. The dashboard lets you:
- 🔗 Paste a **YouTube URL** to download & process
- 📁 **Upload a video** file directly
- 📝 **Paste transcript** text (Hinglish / Tenglish / English)
- 🔄 Switch between **Rule-based** and **LLM** extraction modes
- 📊 View interactive **knowledge graph**, concepts, timeline, and analytics

### Option 2: Command-Line Interface

```bash
# Process a video file
python run_pipeline.py --video data/raw_videos/my_video.mp4

# Process from transcript JSON
python run_pipeline.py --transcript data/raw_videos/65ybTFOurZE_transcript.json

# Process raw text (Hinglish / Tenglish)
python run_pipeline.py --text "Pehle arrays samjho phir linked list easy lagega."

# Use LLM mode instead of rule-based
python run_pipeline.py --video my_video.mp4 --mode llm
```

### Option 3: Python API

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

## ☁️ Google Colab (GPU)

For faster processing (especially Whisper transcription), use the included Colab notebook:

1. Upload `PedagogicalKG_Colab.ipynb` to [Google Colab](https://colab.research.google.com)
2. **Runtime → Change runtime type → GPU (T4)**
3. Enter your Groq API key when prompted
4. Choose your input mode (YouTube URL, upload file, paste text)
5. Run cells in order — results inline + downloadable

> **GPU Benefit:** Whisper transcription runs ~5-10x faster on T4 GPU compared to CPU.

---

## 🎬 Sample Videos & Outputs

### 📂 Google Drive — All Outputs

**[📁 View All Video Outputs on Google Drive](https://drive.google.com/drive/folders/1OsHUFPUKO1nrj10ChS3uKDVBH0SxNb3o?usp=sharing)**

Contains: knowledge graph HTML files, JSON outputs, transcripts, and graphs for all 5 videos.

### 🎥 YouTube Video Links

| # | Video | Code-Mixed Language | YouTube Link |
|---|-------|-------------------|-------------|
| 1 | Video 1 | **Hindi-English (Hinglish)** | [https://www.youtube.com/watch?v=t9MJ1gxcJ4w](https://www.youtube.com/watch?v=t9MJ1gxcJ4w) |
| 2 | Video 2 | **Hindi-English (Hinglish)** | [https://www.youtube.com/watch?v=65ybTFOurZE](https://www.youtube.com/watch?v=65ybTFOurZE) |
| 3 | Video 3 | **Hindi-English (Hinglish)** | [https://www.youtube.com/watch?v=VZou5pYcWXM](https://www.youtube.com/watch?v=VZou5pYcWXM) |
| 4 | Video 4 | **Hindi-English (Hinglish)** | [https://www.youtube.com/watch?v=63HJ2-jV6Mk](https://www.youtube.com/watch?v=63HJ2-jV6Mk&list=PLnccP3XNVxGrWkKFJMCtL5mDEcOnrjjib&index=9) |
| 5 | Video 5 | **Hindi-English (Hinglish)** | [https://www.youtube.com/watch?v=p_r42RVY-pA](https://www.youtube.com/watch?v=p_r42RVY-pA) |

---

## 🌟 Key Features

| Feature | Description |
|---------|-------------|
| **🗣️ Speech-to-Text** | Whisper-based transcription with automatic language detection and timestamp awareness |
| **🌐 Code-Mixed Normalization** | Hinglish (Hindi-English) & Tenglish (Telugu-English) → English translation preserving technical terms |
| **🧠 Hybrid Concept Extraction** | Domain dictionary + RAKE keyword extraction with weighted scoring |
| **🔗 Prerequisite Detection** | Linguistic patterns (Hindi, Telugu, English) for pedagogical cue analysis |
| **📊 Interactive Knowledge Graph** | PyVis visualization with community detection, PageRank sizing, and hover tooltips |
| **🤖 LLM Mode** | Groq-powered extraction using Llama 3.3 70B (any academic domain, not just CS) |
| **⏱️ Concept Timeline** | Visual teaching flow showing when concepts appear in the video |
| **📈 Graph Analytics** | PageRank, betweenness centrality, HITS scores, community detection, learning path generation |
| **🖥️ Streamlit Dashboard** | Full interactive web interface with YouTube download support |
| **🧪 Evaluation Suite** | Test cases including Telugu-English for measuring pipeline performance |

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
            ┌───────────┴───────────┐
            │                       │
            ▼                       ▼
  ┌──────────────────┐   ┌──────────────────┐
  │   Rule-Based     │   │    LLM Mode      │
  │   Pipeline       │   │   (Groq API)     │
  └────────┬─────────┘   └────────┬─────────┘
           │                      │
           ▼                      │
  ┌──────────────────┐            │
  │  Code-Mixed      │            │
  │  Normalizer      │            │
  │ (Hinglish/       │            │
  │  Tenglish→EN)    │            │
  └────────┬─────────┘            │
           ▼                      │
  ┌──────────────────┐            │
  │  Concept         │            │
  │  Extractor       │            │
  │ (Dict + RAKE)    │            │
  └────────┬─────────┘            │
           ▼                      │
  ┌──────────────────┐            │
  │  Prerequisite    │            │
  │  Detector        │            │
  │ (Patterns)       │            │
  └────────┬─────────┘            │
           │                      │
           └───────────┬──────────┘
                       ▼
              ┌────────────────────┐
              │  Knowledge Graph   │
              │  Builder           │
              │ (NetworkX + Dedup  │
              │  + PageRank +      │
              │  Communities)      │
              └─────────┬──────────┘
                        │
                        ▼
          ┌──────────────────────────┐
          │   Interactive Dashboard   │
          │  (PyVis + Streamlit)      │
          └──────────────────────────┘
```

---

## 📁 Project Structure

```
Task/
│
├── PedagogicalFlowExtractor/
│   ├── app/
│   │   └── streamlit_app.py              # Interactive Streamlit dashboard
│   │
│   ├── pipeline/
│   │   ├── speech_to_text.py             # Whisper STT with auto-language detection
│   │   ├── normalizer.py                 # Hinglish/Tenglish → English normalizer
│   │   ├── concept_extractor.py          # Hybrid concept mining (Dict + RAKE)
│   │   ├── dependency_detector.py        # Prerequisite detection (patterns)
│   │   ├── graph_builder.py              # Knowledge graph construction + metrics
│   │   └── llm_extractor.py              # Groq LLM-powered extraction
│   │
│   ├── visualization/
│   │   ├── graph_visualizer.py           # PyVis interactive graph renderer
│   │   └── timeline_plotter.py           # Plotly concept timeline charts
│   │
│   ├── data/
│   │   ├── raw_videos/                   # Input videos & transcript JSONs
│   │   ├── transcripts/                  # Generated transcripts
│   │   ├── hinglish_lexicon.json         # 150+ Hinglish → English mappings
│   │   ├── telugu_english_lexicon.json   # 250+ Telugu → English mappings
│   │   └── cs_concepts.json              # 150+ CS concept dictionary
│   │
│   ├── utils/
│   │   ├── config.py                     # Configuration management
│   │   ├── logger.py                     # Structured logging
│   │   └── helpers.py                    # Utility functions
│   │
│   ├── outputs/
│   │   ├── graphs/                       # Generated HTML knowledge graphs
│   │   ├── json/                         # Knowledge graph JSON exports
│   │   └── reports/                      # Evaluation logs and reports
│   │
│   ├── config.yaml                       # Pipeline configuration
│   ├── requirements.txt                  # Python dependencies
│   ├── run_pipeline.py                   # CLI entry point
│   ├── evaluate.py                       # Evaluation & benchmarking suite
│   ├── PedagogicalKG_Colab.ipynb         # Google Colab notebook (GPU)
│   └── .env                              # API keys (Groq)
│
├── PLAN.md                               # Implementation plan
└── README.md                             # ← This file
```

---

## ⚙️ Pipeline Modes

### Rule-Based Mode (Default)

- **Best for:** Computer Science educational content
- **No API key needed**
- Uses 150+ CS concept dictionary, RAKE keyword extraction, and pedagogical cue patterns (Hindi & English)
- Handles Hinglish code-mixed input via lexicon-based normalization

```bash
python run_pipeline.py --video video.mp4 --mode rule
```

### LLM Mode (Groq API)

- **Best for:** Any academic domain (Physics, Math, Biology, etc.)
- **Requires free Groq API key**
- Uses Llama 3.3 70B (via Groq) for concept extraction and relationship detection
- Two-pass architecture: Pass 1 extracts concepts, Pass 2 detects relationships
- Handles long transcripts via intelligent chunking with overlap
- Full Telugu-English (Tenglish) support

```bash
python run_pipeline.py --video video.mp4 --mode llm
```

---

## 📝 Output Format

The pipeline generates a structured JSON output:

```json
{
  "video_id": "dsa_hinglish_001",
  "metadata": {
    "language": "code-mixed (Hindi-English)",
    "processed_at": "2026-03-13T10:30:00Z"
  },
  "concepts": [
    {
      "name": "array",
      "normalized_name": "Array",
      "importance_score": 0.89,
      "frequency": 15,
      "first_mention": "1:23",
      "timestamps": ["1:23", "2:45", "5:12"],
      "pagerank": 0.1234,
      "community": 0,
      "depth": 0
    }
  ],
  "relationships": [
    {
      "from": "array",
      "to": "linked list",
      "relation": "prerequisite",
      "confidence": 0.92,
      "evidence": "pehle arrays samjho phir linked list",
      "detection_method": "pattern_matching"
    }
  ],
  "timeline": [
    {"time": "0:45", "concept": "variable", "importance": 0.7},
    {"time": "1:23", "concept": "array", "importance": 0.9}
  ],
  "analytics": {
    "total_concepts": 12,
    "total_relationships": 8,
    "avg_confidence": 0.78
  }
}
```

Additionally, an **interactive HTML knowledge graph** is generated in `outputs/graphs/`.

---

## 🔧 Configuration

Edit `config.yaml` to customize pipeline behavior:

```yaml
whisper:
  model: "small"        # tiny / base / small / medium / large
  language: "hi"        # Language hint (null = auto-detect)

normalizer:
  hinglish_lexicon: "data/hinglish_lexicon.json"
  telugu_lexicon: "data/telugu_english_lexicon.json"

extractor:
  min_concept_score: 0.3
  use_rake: true
  use_domain_dict: true
  weights:
    domain_match: 0.5
    rake: 0.3
    frequency: 0.2

detector:
  min_confidence: 0.4

llm:
  model: "llama-3.3-70b-versatile"
  max_tokens: 8192
```

---

## 🧪 Evaluation Suite

Run the built-in evaluation suite to benchmark pipeline performance:

```bash
# Rule-based evaluation
python evaluate.py --mode rule --verbose

# LLM evaluation
python evaluate.py --mode llm --verbose

# Both modes with saved results
python evaluate.py --mode both --verbose --save
```

### Metrics Evaluated

- **Concept Extraction**: Precision, Recall, F1 Score
- **Relationship Detection**: Precision, Recall, F1 Score
- **Normalization Quality**: Keyword presence in normalized text
- **Latency**: Processing time per test case
- **Graph Quality**: Node count, edge count, density

---

## 🎯 Innovation Highlights

1. **Multilingual Code-Mixed Robustness** — Handles Hinglish (Hindi-English) and Tenglish (Telugu-English) using 400+ term lexicons with phrase-level and pedagogical pattern matching

2. **Dual Extraction Pipeline** — Rule-based mode (fast, no API) for CS content + LLM mode (Groq Llama 3.3 70B) for any academic domain, both producing identical output formats

3. **Pedagogical Cue Patterns** — Linguistic patterns across Hindi, Telugu, and English for detecting prerequisite relationships from teaching discourse (e.g., *"pehle X samjho phir Y"*, *"mundu X nerchukondi tarvata Y"*)

4. **Embedding-Based Concept Deduplication** — Uses sentence-transformers to merge near-duplicate concepts (e.g., "binary search tree" & "BST") before graph construction

5. **Advanced Graph Analytics** — PageRank (foundational concepts), betweenness centrality (gateway concepts), HITS (hubs & authorities), Louvain community detection, pedagogical topological sort for learning path generation

6. **Interactive Knowledge Graphs** — Dark-themed PyVis graphs with community coloring, importance-based sizing, custom hover tooltips, and directional prerequisite edges

