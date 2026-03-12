# 🎓 Pedagogical Knowledge Graph Extractor - Implementation Plan

> **Project Goal:** Convert code-mixed educational videos into interactive pedagogical knowledge graphs showing concept relationships and prerequisites.

---

## 📊 PROJECT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        VIDEO INPUT                               │
│                    (Code-Mixed Content)                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SPEECH-TO-TEXT (Whisper)                       │
│              Extract audio + Generate transcript                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              CODE-MIXED LANGUAGE NORMALIZER                      │
│           Hinglish → English (with preservation)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CONCEPT EXTRACTOR                               │
│         Domain Dict + RAKE + POS Tagging (Hybrid)                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              PREREQUISITE DETECTOR                               │
│        Pattern Matching + Co-occurrence Analysis                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 KNOWLEDGE GRAPH BUILDER                          │
│              NetworkX + Metadata Enrichment                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   VISUALIZATION LAYER                            │
│           PyVis + Plotly + Streamlit Dashboard                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ PROJECT STRUCTURE

```
PedagogicalFlowExtractor/
│
├── data/
│   ├── raw_videos/              # Input videos
│   ├── transcripts/             # Generated transcripts
│   ├── hinglish_lexicon.json    # Translation dictionary
│   └── cs_concepts.json         # Computer Science concepts list
│
├── pipeline/
│   ├── __init__.py
│   ├── speech_to_text.py        # Whisper integration
│   ├── normalizer.py            # Code-mixed normalizer
│   ├── concept_extractor.py     # Hybrid concept extraction
│   ├── dependency_detector.py   # Prerequisite detection
│   └── graph_builder.py         # Knowledge graph construction
│
├── visualization/
│   ├── __init__.py
│   ├── graph_visualizer.py      # PyVis interactive graphs
│   ├── timeline_plotter.py      # Concept timeline
│   └── analytics_charts.py      # Statistical visualizations
│
├── outputs/
│   ├── graphs/                  # HTML graph outputs
│   ├── json/                    # Structured data
│   └── reports/                 # Analysis reports
│
├── app/
│   └── streamlit_app.py         # Interactive dashboard
│
├── tests/
│   ├── test_normalizer.py
│   ├── test_extractor.py
│   └── test_detector.py
│
├── utils/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── logger.py                # Logging utilities
│   └── helpers.py               # Common functions
│
├── config.yaml                  # Configuration file
├── requirements.txt             # Dependencies
├── README.md                    # Documentation
├── PLAN.md                      # This file
└── .gitignore
```

---

## 🎯 IMPLEMENTATION PHASES

### ✅ **PHASE 1: MINIMAL VIABLE PRODUCT (MVP)** 
**Priority: CRITICAL | Timeline: Days 1-4**

#### 1.1 Project Setup
- [x] Create directory structure
- [x] Setup virtual environment
- [x] Install core dependencies
- [x] Create configuration system
- [x] Setup logging

#### 1.2 Data Collection
- [x] Download 3-5 sample videos (8-15 min each)
  - CodeWithHarry (Data Structures)
  - Gate Smashers (Algorithms)
  - Apna College (DBMS/DSA)
- [x] Create Hinglish lexicon (50+ common terms)
- [x] Create CS concepts dictionary (100+ terms)

#### 1.3 Core Pipeline - Speech-to-Text
- [x] Implement Whisper integration
- [x] Audio extraction from video
- [x] Timestamp-aware transcription
- [x] Save transcript with metadata
- [x] Test with sample video

**Output:** `transcript.json`
```json
{
  "video_id": "video_001",
  "segments": [
    {
      "start": 0.0,
      "end": 5.4,
      "text": "Aaj hum arrays ke baare mein samjhenge"
    }
  ]
}
```

#### 1.4 Code-Mixed Normalizer
- [x] Load Hinglish lexicon
- [x] Word-level translation
- [x] Basic pattern matching (top 10 patterns)
  - "pehle X phir Y" → "first X then Y"
  - "X ke baad Y" → "after X comes Y"
  - "X ko samjho" → "understand X"
- [x] Preserve technical terms
- [x] Test with sample transcripts

**Output:** Normalized transcript

#### 1.5 Concept Extractor (Basic)
- [x] Implement domain dictionary matching
- [x] Implement RAKE keyword extraction
- [x] Basic scoring mechanism
- [x] Deduplicate and rank concepts
- [x] Test extraction accuracy

**Output:** Ranked concepts list

#### 1.6 Prerequisite Detector (Basic)
- [x] Define 10 key relationship patterns
- [x] Pattern matching implementation
- [x] Extract relationship triplets
- [x] Confidence scoring
- [x] Test with sample data

**Output:** Prerequisite edges

#### 1.7 Graph Builder
- [x] Create NetworkX directed graph
- [x] Add nodes (concepts)
- [x] Add edges (prerequisites)
- [x] Add basic metadata
- [x] Export to JSON format

**Output:** Knowledge graph JSON

#### 1.8 Basic Visualization
- [x] PyVis interactive graph
- [x] Node coloring by type
- [x] Edge arrows for direction
- [x] Save as HTML
- [x] Test interactivity

#### 1.9 Simple Streamlit App
- [x] File upload interface
- [x] Process button
- [x] Display transcript
- [x] Show interactive graph
- [x] Download JSON output

#### 1.10 Documentation
- [x] README with setup instructions
- [x] Usage examples
- [x] Sample outputs
- [x] Architecture diagram (ASCII)

---

### 🟡 **PHASE 2: MODERATE FEATURES**
**Priority: HIGH | Timeline: Days 5-6**

#### 2.1 Enhanced Concept Extraction
- [ ] Add POS tagging (spaCy)
- [ ] TF-IDF scoring
- [ ] Multi-signal scoring
  ```python
  score = (domain_match * 0.4) + (tfidf * 0.3) + (pos_weight * 0.2) + (rake * 0.1)
  ```
- [ ] Improve accuracy benchmarking
- [ ] Test with multiple videos

#### 2.2 Concept Timeline
- [ ] Extract first mention timestamps
- [ ] Create timeline data structure
- [ ] Plotly timeline visualization
- [ ] Interactive playback markers
- [ ] Add to Streamlit dashboard

**Output:**
```json
"timeline": [
  {"time": "0:45", "concept": "variable", "importance": 0.7},
  {"time": "1:23", "concept": "array", "importance": 0.9}
]
```

#### 2.3 Difficulty Estimation
- [ ] Count prerequisite dependencies
- [ ] Analyze mention frequency
- [ ] Detect teacher emphasis patterns
- [ ] Calculate composite difficulty score
  ```python
  difficulty = (prereq_count * 0.4) + (freq_inverse * 0.3) + (emphasis * 0.3)
  ```
- [ ] Classify as Easy/Medium/Hard
- [ ] Color-code in visualizations

#### 2.4 Teaching Style Detection
- [ ] Define pattern matchers:
  - Analogy: "jaise", "ki tarah", "like"
  - Example: "example", "udaharan"
  - Definition: "means", "matlab", "is defined as"
  - Step-by-step: "pehle", "phir", "step"
- [ ] Tag concepts with teaching approach
- [ ] Show statistics in dashboard

#### 2.5 Enhanced Visualization
- [ ] Size nodes by importance
- [ ] Color nodes by difficulty
- [ ] Add hover tooltips (timestamp, style)
- [ ] Hierarchical layout option
- [ ] Zoom and pan controls

#### 2.6 Analytics Dashboard
- [ ] Concept frequency bar chart
- [ ] Difficulty distribution pie chart
- [ ] Teaching style breakdown
- [ ] Timeline plot
- [ ] Summary statistics

#### 2.7 Export Options
- [ ] Export to GraphML
- [ ] Export to CSV (edges & nodes)
- [ ] Generate PDF report
- [ ] Download all formats

#### 2.8 Configuration System
- [ ] YAML config file
- [ ] Adjustable thresholds
- [ ] Model selection options
- [ ] Output preferences
- [ ] UI for config in Streamlit

---

### 🔴 **PHASE 3: ADVANCED FEATURES**
**Priority: OPTIONAL | Timeline: Days 7-8+**

#### 3.1 Multi-Video Processing
**Complexity: High | Effort: 1-2 days**
- [ ] Batch processing interface
- [ ] Process multiple videos in parallel
- [ ] Merge concept graphs across videos
- [ ] Cross-video prerequisite detection
- [ ] Course-level knowledge graph
- [ ] Topic clustering across videos

**Why Complex:**
- Graph merging strategies (node deduplication)
- Handling conflicting prerequisites
- Memory management for large datasets
- Progress tracking for multiple processes

#### 3.2 LLM-Enhanced Extraction
**Complexity: High | Effort: 1 day**
- [ ] OpenAI/Claude API integration
- [ ] Prompt engineering for concept extraction
- [ ] LLM-based relationship detection
- [ ] Confidence scoring
- [ ] Fallback to rule-based approach
- [ ] Cost optimization

**Why Complex:**
- API key management
- Rate limiting and error handling
- Prompt optimization
- Cost considerations
- Consistency validation

#### 3.3 Pedagogical Pattern Mining
**Complexity: Medium-High | Effort: 1 day**
- [ ] Detect repeated concepts (emphasis)
- [ ] Forward references ("we'll learn later")
- [ ] Backward references ("remember we learned")
- [ ] Concept spiraling patterns
- [ ] Teaching sequence optimization
- [ ] Generate insights report

**Why Complex:**
- Temporal pattern recognition
- Contextual understanding required
- Advanced NLP techniques

#### 3.4 Automatic Video Segmentation
**Complexity: High | Effort: 1 day**
- [ ] Topic change detection
- [ ] Silence-based segmentation
- [ ] Visual scene detection
- [ ] Auto-generate chapter markers
- [ ] Per-segment processing

**Why Complex:**
- Video/audio processing overhead
- ML model for scene detection
- Threshold tuning

#### 3.5 Real-time Processing
**Complexity: Very High | Effort: 2 days**
- [ ] Stream video in chunks
- [ ] Incremental transcription
- [ ] Live graph updates
- [ ] WebSocket integration
- [ ] Progress streaming

**Why Complex:**
- Concurrency and threading
- State management
- Memory optimization
- WebSocket implementation

#### 3.6 Concept Clustering
**Complexity: Medium | Effort: 0.5 day**
- [ ] Group related concepts
- [ ] Topic modeling (LDA/LSA)
- [ ] Visualize clusters
- [ ] Auto-generate topic names

#### 3.7 Multi-language Support
**Complexity: Medium | Effort: 1 day**
- [ ] Expand to Tamil, Telugu, Bengali
- [ ] Language detection
- [ ] Multi-lexicon system
- [ ] Language-specific patterns

#### 3.8 Manual Correction Interface
**Complexity: Medium | Effort: 1 day**
- [ ] Edit concepts
- [ ] Add/remove relationships
- [ ] Adjust confidence scores
- [ ] Save corrections for retraining

---

### 🟢 **PHASE 4: POLISH & DEPLOYMENT**
**Priority: HIGH | Timeline: Day 8**

#### 4.1 Testing
- [ ] Unit tests for all modules
- [ ] Integration tests
- [ ] End-to-end test with sample videos
- [ ] Edge case handling
- [ ] Test coverage report

#### 4.2 Docker Deployment
**Complexity: Easy | Effort: 2-3 hours**
- [ ] Create Dockerfile
- [ ] Docker Compose setup
- [ ] One-command deployment
- [ ] Volume mounts for data
- [ ] Documentation

#### 4.3 Logging & Monitoring
**Complexity: Easy | Effort: 2 hours**
- [ ] Structured logging
- [ ] Log levels (DEBUG, INFO, ERROR)
- [ ] Log file rotation
- [ ] Performance metrics
- [ ] Error tracking

#### 4.4 Documentation
- [ ] Comprehensive README
  - Installation guide
  - Usage examples
  - API documentation
  - Troubleshooting
- [ ] Architecture diagram (Excalidraw)
- [ ] Code comments
- [ ] Docstrings
- [ ] Demo video (2-3 min)
- [ ] Screenshots/GIFs

#### 4.5 Performance Optimization
- [ ] Profile code bottlenecks
- [ ] Optimize graph algorithms
- [ ] Cache intermediate results
- [ ] Parallel processing where possible

#### 4.6 GitHub Best Practices
- [ ] Clean commit history
- [ ] .gitignore setup
- [ ] Badges (Python, License, Build)
- [ ] Contributing guidelines
- [ ] License file (MIT)

#### 4.7 Optional: Cloud Deployment
**Complexity: Easy-Medium | Effort: 3-4 hours**
- [ ] Deploy Streamlit app to Streamlit Cloud
- [ ] Update README with live demo link
- [ ] Configure secrets for API keys

---

## 📦 DEPENDENCIES

### Core (MVP)
```
openai-whisper>=20230314
torch>=2.0.0
ffmpeg-python>=0.2.0
networkx>=3.0
pyvis>=0.3.1
streamlit>=1.28.0
rake-nltk>=1.0.6
pydub>=0.25.1
```

### Enhanced (Moderate)
```
spacy>=3.5.0
plotly>=5.14.0
scikit-learn>=1.2.0
pandas>=2.0.0
numpy>=1.24.0
```

### Advanced (Optional)
```
openai>=1.0.0
anthropic>=0.7.0
transformers>=4.30.0
opencv-python>=4.7.0
pytube>=15.0.0
```

---

## 🎯 OUTPUT SPECIFICATIONS

### Final JSON Format
```json
{
  "video_id": "ds_arrays_hinglish_001",
  "metadata": {
    "title": "Arrays in Hinglish",
    "duration": "12:34",
    "language": "code-mixed (Hindi-English)",
    "topic": "Data Structures",
    "processed_at": "2026-03-08T10:30:00Z"
  },
  "transcript": {
    "original": "...",
    "normalized": "...",
    "segments": [...]
  },
  "concepts": [
    {
      "id": 1,
      "name": "array",
      "normalized_name": "Array",
      "first_mention": "1:23",
      "frequency": 15,
      "difficulty": "easy",
      "teaching_style": ["example-based", "analogy"],
      "importance_score": 0.89,
      "timestamps": ["1:23", "2:45", "5:12"]
    }
  ],
  "relationships": [
    {
      "from": "array",
      "to": "linked_list",
      "relation": "prerequisite",
      "evidence": "pehle arrays samjho phir linked list",
      "timestamp": "3:45",
      "confidence": 0.92
    }
  ],
  "timeline": [
    {"time": "0:45", "concept": "variable", "importance": 0.7},
    {"time": "1:23", "concept": "array", "importance": 0.9}
  ],
  "analytics": {
    "total_concepts": 12,
    "total_relationships": 8,
    "difficulty_distribution": {
      "easy": 5,
      "medium": 4,
      "hard": 3
    },
    "teaching_styles": {
      "analogy": 5,
      "example": 12,
      "definition": 8,
      "step-by-step": 6
    }
  }
}
```

---

## 🏆 SUCCESS CRITERIA

### MVP Success
- [x] Process 1 video end-to-end
- [ ] Extract at least 80% of major concepts
- [ ] Detect at least 70% of explicit prerequisites
- [ ] Generate interactive graph
- [ ] Working Streamlit demo
- [ ] Clean, professional README

### Moderate Success
- [ ] Process 3+ videos successfully
- [ ] Concept extraction accuracy >85%
- [ ] Timeline visualization works
- [ ] Difficulty estimation reasonable
- [ ] Dashboard has 4+ visualizations

### Advanced Success
- [ ] Multi-video processing
- [ ] LLM integration (optional)
- [ ] Advanced analytics
- [ ] Production-ready deployment
- [ ] Live demo deployed

---

## 🎨 INNOVATION HIGHLIGHTS

### What Makes This Stand Out:

1. **Code-Mixed Language Handling** 🌐
   - Robust Hinglish normalization
   - Pattern-based translation
   - Technical term preservation

2. **Hybrid Extraction Approach** 🧠
   - Multi-method concept mining
   - Weighted scoring system
   - Domain-aware extraction

3. **Pedagogical Intelligence** 📚
   - Teaching style detection
   - Difficulty estimation
   - Learning path optimization

4. **Interactive Visualizations** 📊
   - PyVis knowledge graphs
   - Concept timeline
   - Rich analytics dashboard

5. **Research-Level Positioning** 🎓
   > "Converting unstructured multilingual educational discourse into structured pedagogical knowledge graphs"

---

## ⚠️ RISK MANAGEMENT

### Potential Challenges

1. **Whisper Processing Time**
   - **Risk:** Slow on long videos
   - **Mitigation:** Use smaller model, chunk processing

2. **Hinglish Variability**
   - **Risk:** Many dialects and styles
   - **Mitigation:** Expand lexicon iteratively, focus on common patterns

3. **Concept Extraction Accuracy**
   - **Risk:** Missing domain-specific terms
   - **Mitigation:** Comprehensive CS dictionary, manual validation

4. **Prerequisite Detection**
   - **Risk:** Implicit relationships hard to detect
   - **Mitigation:** Start with explicit patterns, expand gradually

5. **Graph Complexity**
   - **Risk:** Too many nodes, unreadable
   - **Mitigation:** Filtering, importance thresholds, clustering

---

## 📈 TESTING STRATEGY

### Unit Tests
- Each pipeline module
- Normalizer patterns
- Extraction algorithms
- Graph operations

### Integration Tests
- Full pipeline on sample video
- Edge cases (short/long videos)
- Different teaching styles

### Manual Validation
- Expert review of extracted concepts
- Prerequisite relationship accuracy
- Visual graph quality check

---

## 🚀 DEPLOYMENT OPTIONS

### Option 1: Local Deployment
- Clone repo
- Install dependencies
- Run Streamlit locally

### Option 2: Docker
- Pull Docker image
- Run container
- Access via localhost

### Option 3: Cloud (Streamlit Cloud)
- Push to GitHub
- Connect to Streamlit Cloud
- Auto-deploy on push

---

## 📝 NOTES FOR IMPLEMENTATION

### Best Practices
1. Write modular, reusable code
2. Separate concerns (pipeline vs visualization)
3. Use configuration files, not hardcoded values
4. Log extensively for debugging
5. Test each module independently before integration
6. Version control at each milestone
7. Document as you code

### Code Quality
- Follow PEP 8 style guide
- Use type hints
- Write docstrings
- Keep functions small and focused
- Handle errors gracefully

### Performance
- Profile before optimizing
- Cache expensive operations
- Use generators for large data
- Parallel processing where applicable

---

## ✅ IMPLEMENTATION CHECKLIST

### Week 1: MVP
- [ ] Day 1: Setup + Data collection
- [ ] Day 2: Speech-to-text + Normalizer
- [ ] Day 3: Concept extraction + Prerequisites
- [ ] Day 4: Graph builder + Basic visualization

### Week 2: Enhancement
- [ ] Day 5: Moderate features (Timeline, Difficulty)
- [ ] Day 6: Enhanced visualization + Analytics
- [ ] Day 7: Testing + Documentation
- [ ] Day 8: Polish + Deployment

---

## 🎯 NEXT STEPS

1. **Immediate:** Create project structure
2. **Next:** Install dependencies
3. **Then:** Download sample videos
4. **After:** Implement speech-to-text module
5. **Follow:** This plan step-by-step

---

**Last Updated:** March 8, 2026  
**Version:** 1.0  
**Status:** Ready for Implementation 🚀
