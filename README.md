# 🎓 Algorithmic Instructional Designer

> Transform raw technical documentation into structured, pedagogically sound
> lesson materials using a **multi-agent AI pipeline** powered by
> **Groq** and **LLaMA 3.3 70B**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Groq](https://img.shields.io/badge/Groq-LLaMA%203.3%2070B-orange)](https://console.groq.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ✨ What It Does

Most "AI tutors" output walls of unstructured text. This system applies real
**instructional design frameworks** to produce four ready-to-use artefacts:

| Artefact | Description |
|---|---|
| 📘 **Lesson Plan** | Minute-by-minute teacher guide aligned to Gagne's 9 Events |
| 📋 **Student Handout** | Pre-class reading with analogies, vocab, and warm-up questions |
| ❓ **Quiz** | 30-mark assessment (MCQ + short answer + application) |
| 🔑 **Teacher Answer Key** | Full model answers, rubrics, and facilitation notes |

---

## 🏗️ Architecture

```
Raw Source Docs
      │
      ▼
┌─────────────────┐
│  Architect Agent │  Maps content to Gagne's 9 Events + Merrill's 5 Principles
│                 │  → outputs structured JSON lesson blueprint
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Content Agent  │  Generates Lesson Plan, Handout, Quiz, Answer Key
│                 │  grounded in source document + blueprint
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Simulated Student   │  Attempts the quiz using ONLY the Student Handout
│ Agent               │  Scores attempt + produces structured failure analysis
└────────┬────────────┘
         │
    score ≥ threshold?
    ├── YES → deliver artefacts
    └── NO  → revision feedback → Architect (retry, up to max_retries)
```

### Instructional Design Frameworks Used

**Gagne's Nine Events of Instruction**
1. Gain Attention
2. Inform Learners of Objectives
3. Stimulate Recall of Prior Learning
4. Present the Content
5. Provide Learning Guidance
6. Elicit Performance (Practice)
7. Provide Feedback
8. Assess Performance
9. Enhance Retention and Transfer

**Merrill's First Principles**
- Problem-Centred Learning
- Activation of Prior Knowledge
- Demonstration of Skills
- Application by Learners
- Integration into Real World

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-username/algorithmic-instructional-designer.git
cd algorithmic-instructional-designer

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your Groq API key
# Get a free key at: https://console.groq.com
```

Or add it directly in the Streamlit sidebar at runtime.

### 3. Run the App

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🖥️ Using the App

1. **Paste source text** or upload `.txt` / `.pdf` files in the main area
2. **Configure** topic, learner profile, pass threshold in the sidebar
3. Click **🚀 Generate Lesson**
4. Watch the **pipeline diagram** update in real-time as each agent runs
5. Review the four artefacts in the **tabbed output area**
6. **Download PDFs** with one click

### Learner Profiles

| Profile | Description |
|---|---|
| **Beginner** | Undergraduate, first AI/CS course, basic Python only |
| **MSc Student** | Graduate level, knows neural networks and transformers |
| **Product Manager** | Non-technical, needs concepts and business context |

---

## 📁 Project Structure

```
algorithmic-instructional-designer/
├── app.py                    # Streamlit UI (main entry point)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── sdk/
    ├── __init__.py           # Public API exports
    ├── models.py             # Data classes & enums
    ├── utils.py              # Groq helper, JSON extractor
    ├── agents.py             # ArchitectAgent, ContentAgent,
    │                         #   SimulatedStudentAgent, LessonController
    └── pdf_generator.py      # ReportLab PDF generation
```

---

## 🛠️ SDK Usage (Programmatic)

```python
from sdk import GenerationConfig, LearnerProfile, LessonController
from sdk.pdf_generator import artifacts_to_pdfs

cfg = GenerationConfig(
    topic_title      = "Transformer Self-Attention",
    topic_description= "How multi-head self-attention works",
    learner_profile  = LearnerProfile.MSC_STUDENT,
    pass_threshold   = 0.80,
    max_retries      = 2,
)

source = open("my_document.txt").read()

controller      = LessonController(api_key="gsk_…", cfg=cfg)
artifacts, log  = controller.run(source, progress_cb=print)

pdf_paths = artifacts_to_pdfs(artifacts, cfg, output_dir="outputs/")
```

---

## ⚡ Performance & Cost

| Tier | Tokens/min | Est. time per run | Est. cost |
|---|---|---|---|
| Groq Free | 6 000 | ~3–5 min | **Free** |
| Groq Paid | 30 000+ | ~45–90 sec | < $0.02 |

The pipeline makes **5–6 sequential API calls per attempt**.
With `max_retries=2` the worst case is 15–18 calls, still well within limits.

---

## 🔧 Configuration Reference

| Parameter | Default | Description |
|---|---|---|
| `groq_model` | `llama-3.3-70b-versatile` | Groq model to use |
| `max_tokens` | `2048` | Max tokens per API call |
| `pass_threshold` | `0.80` | Min student score (0–1) to accept artefacts |
| `max_retries` | `2` | Max revision loops |
| `learner_profile` | `MSC_STUDENT` | `BEGINNER`, `MSC_STUDENT`, `PRODUCT_MANAGER` |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
