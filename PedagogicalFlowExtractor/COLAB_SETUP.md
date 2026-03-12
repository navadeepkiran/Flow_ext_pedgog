# 🚀 Google Colab Deployment Guide

## Quick Start (3 Steps)

### 1. Open the Colab Notebook
Click here to open in Google Colab:
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/PedagogicalFlowExtractor/blob/main/PedagogicalKG_Complete_Colab.ipynb)

Or upload `PedagogicalKG_Complete_Colab.ipynb` to Google Colab manually.

### 2. Prepare Your Project Package
Run this command in your local terminal to create the deployment package:

**Windows (PowerShell):**
```powershell
cd C:\Users\navad\Documents\sem4\LTRC\Task\PedagogicalFlowExtractor
python package_for_colab.py
```

**Linux/Mac:**
```bash
cd /path/to/PedagogicalFlowExtractor
python package_for_colab.py
```

This creates `PedagogicalFlowExtractor_Colab.zip` (~60KB) with all your code.

### 3. Run the Notebook
1. In Colab, **Runtime → Run all**
2. **Set your Groq API key** in Cell 3
3. **Upload the ZIP file** when prompted (Cell 7)
4. **Click the ngrok URL** to access your app
5. **Use the Streamlit UI** — exactly the same as localhost!

---

## What You Get

✅ **Full Streamlit Web UI** — Same interface as local deployment  
✅ **Multi-language Support** — English, Hinglish, Tenglish  
✅ **Speech-to-Text** — Whisper automatic transcription  
✅ **LLM Extraction** — Groq Llama-3.3-70B powered  
✅ **Interactive Graphs** — PyVis visualization  
✅ **Graph Analytics** — PageRank, centrality, communities  
✅ **Export Options** — JSON, HTML, reports  

---

## Detailed Setup Instructions

### Option 1: Direct Upload (Fastest)

1. **Create package** (locally):
   ```bash
   python package_for_colab.py
   ```

2. **Upload to Colab**:
   - Run Cell 7 in the notebook
   - Click "Choose Files"
   - Select `PedagogicalFlowExtractor_Colab.zip`
   - Wait for extraction

3. **Done!** Streamlit will launch automatically.

### Option 2: Google Drive (Best for Repeated Use)

1. **Upload to Drive**:
   - Upload `PedagogicalFlowExtractor_Colab.zip` to Google Drive
   - Note the path (e.g., `/MyDrive/LTRC/PedagogicalFlowExtractor_Colab.zip`)

2. **Method Google Drive in Colab**:
   - Run Cell 5 to mount Drive
   - Uncomment and update the path:
     ```python
     from google.colab import drive
     drive.mount('/content/drive')
     
     import zipfile
     with zipfile.ZipFile('/content/drive/MyDrive/LTRC/PedagogicalFlowExtractor_Colab.zip', 'r') as zip_ref:
         zip_ref.extractall('/content/PedagogicalFlowExtractor')
     ```

3. **Done!** No need to upload again in future sessions.

### Option 3: GitHub (Best for Version Control)

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/PedagogicalFlowExtractor.git
   git push -u origin main
   ```

2. **Clone in Colab**:
   - Update Cell 6 in the notebook:
     ```python
     !git clone https://github.com/YOUR_USERNAME/PedagogicalFlowExtractor.git
     !cp -r PedagogicalFlowExtractor/* /content/PedagogicalFlowExtractor/
     ```

3. **Done!** Easy updates with `git pull`.

---

## Configuration

### Required: Groq API Key
Get a free API key at https://console.groq.com/keys

In Cell 3, update:
```python
GROQ_API_KEY = "your_actual_key_here"
```

### Optional: ngrok Auth Token
For tunnels longer than 2 hours, get a free token at https://dashboard.ngrok.com/get-started/your-authtoken

In Cell 3, update:
```python
NGROK_AUTH_TOKEN = "your_ngrok_token_here"
```

---

## Using the App

Once Streamlit launches, you'll get a public URL like:
```
🌐 PUBLIC URL: https://abc123.ngrok.io
```

### Upload Options

1. **Upload Video/Audio File**
   - Click "Browse files" in sidebar
   - Select .mp4, .mp3, .wav, etc.
   - Whisper transcribes automatically

2. **Paste YouTube URL**
   - Enter YouTube link
   - Click "Process"
   - Audio downloads and transcribes

3. **Paste Text Directly**
   - Paste transcript/lecture text
   - Skip transcription step

### Extraction Modes

**Rule-Based (Fast)**
- Pattern matching + domain dictionary
- Best for CS/DSA topics
- ~0.1s per transcript
- Good for testing

**LLM-Powered (Accurate)**
- Groq Llama-3.3-70B
- Works for ANY subject
- ~5-10s per transcript
- Best for production

### Features to Test

✅ **Interactive Graph**
- Zoom, pan, drag nodes
- Search for concepts
- Click nodes for details
- Color-coded communities

✅ **Analytics Dashboard**
- Concept count
- Relationship count  
- Graph metrics (PageRank, centrality)
- Learning path

✅ **Timeline View**
- When concepts appear
- Concept frequency
- Temporal progression

✅ **Export Options**
- Download JSON graph
- Save HTML visualization
- Generate PDF report

---

## Troubleshooting

### "Module not found" errors
**Solution**: Re-run Cell 1 (dependency installation)

### "API key not set" error
**Solution**: Update `GROQ_API_KEY` in Cell 3 and re-run

### Streamlit won't start
**Solution**: Check Cell 9 logs, restart with Cell 11

### Tunnel expired
**Solution**: 
- Free tunnels expire after 2 hours
- Set `NGROK_AUTH_TOKEN` for longer sessions
- Or just re-run Cell 9

### Files not uploaded correctly
**Solution**:
- Check Cell 7 output for extraction confirmation
- Verify files: `!ls -R /content/PedagogicalFlowExtractor`
- Re-upload if needed

### OOM (Out of Memory) errors
**Solution**:
- Use "small" Whisper model (default)
- Enable GPU: Runtime → Change runtime type → GPU
- Process shorter videos

---

## File Structure

After extraction, you should have:
```
/content/PedagogicalFlowExtractor/
├── app/
│   └── streamlit_app.py         # Web UI
├── pipeline/
│   ├── speech_to_text.py        # Whisper STT
│   ├── normalizer.py            # Code-mixing handler
│   ├── concept_extractor.py     # Concept extraction
│   ├── dependency_detector.py   # Prerequisite detection
│   ├── llm_extractor.py         # LLM-powered extraction
│   └── graph_builder.py         # Graph construction
├── utils/
│   ├── config.py                # Config loader
│   ├── helpers.py               # Utility functions
│   └── logger.py                # Logging setup
├── visualization/
│   ├── graph_visualizer.py      # PyVis graphs
│   └── timeline_plotter.py      # Plotly timelines
├── data/
│   ├── cs_concepts.json         # CS domain dictionary
│   ├── hinglish_lexicon.json    # Hindi-English mappings
│   └── telugu_english_lexicon.json  # Telugu-English mappings
├── config.yaml                  # Main configuration
├── requirements.txt             # Python dependencies
└── README.md                    # Documentation
```

---

## Monitoring

### Check if Streamlit is running:
```python
!ps aux | grep streamlit
```

### View logs:
```python
!tail -n 50 /root/.streamlit/logs/*.log
```

### Restart if needed:
Run Cell 11 in the notebook

### Stop everything:
Run Cell 12 in the notebook

---

## Performance Tips

### For Faster Processing:
- Use rule-based mode for CS topics
- Use "tiny" or "small" Whisper model
- Process shorter clips (<5 min)

### For Better Accuracy:
- Use LLM mode for all subjects
- Use "medium" Whisper model
- Enable GPU in Colab

### For Cost Efficiency:
- Groq API is free (rate limited)
- Colab free tier sufficient
- Upgrade to Colab Pro for longer sessions

---

## Example Workflows

### Test with Sample Data:
1. Launch app (Cell 9)
2. Use "Sample Data" option in sidebar
3. Select "DSA - Arrays and Linked Lists"
4. Click "Extract Knowledge Graph"
5. Explore visualization

### Upload Your Own Video:
1. Launch app
2. Click "Upload Video/Audio"
3. Select your .mp4 lecture
4. Wait for transcription (1-2 min)
5. Choose "LLM-Powered" mode
6. Click "Extract Knowledge Graph"
7. Download results

### Process YouTube Playlist:
1. Launch app
2. For each video:
   - Paste YouTube URL
   - Click "Process"
   - Download JSON
3. Combine graphs offline or in new session

---

## Support & Documentation

- **Full docs**: See main `README.md`
- **Code reference**: Browse files in Colab
- **Issues**: Check troubleshooting section above
- **API docs**: 
  - Groq: https://console.groq.com/docs
  - Whisper: https://github.com/openai/whisper

---

## What's Different from Local?

**Same:**
- ✅ Exact same Streamlit UI
- ✅ All features and functionality
- ✅ Same graph visualization
- ✅ Same export options

**Different:**
- 🌐 Public URL (ngrok tunnel) instead of localhost
- ⏱️ 2-hour session limit (free tier)
- 💾 Temporary storage (download results!)
- 🚀 No installation required

---

## Next Steps

1. **Star the repo** if you find it useful!
2. **Customize** for your use case
3. **Extend** with new features
4. **Share** your graphs

**Ready to extract knowledge? Let's go! 🎓📊**
