# ╔══════════════════════════════════════════════════════════════════════════╗
# ║       ALGORITHMIC INSTRUCTIONAL DESIGNER — Google Colab (Groq)          ║
# ║       Model : llama-3.3-70b-versatile via Groq API                      ║
# ║       Paste this entire file into a Colab code cell, or run             ║
# ║       cell-by-cell using the # @title markers.                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝


# ════════════════════════════════════════════════════════════════════════════
# CELL 1 — Install Dependencies
# ════════════════════════════════════════════════════════════════════════════
# @title 📦 Cell 1 — Install Dependencies

import subprocess, sys

for pkg in ["groq>=0.9.0", "gradio>=4.44.0", "reportlab>=4.0.0"]:
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

print("✅ groq, gradio, reportlab installed.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 2 — Imports
# ════════════════════════════════════════════════════════════════════════════
# @title 🔌 Cell 2 — Imports

import json, logging, os, pathlib, re, sys, time, textwrap
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from groq import Groq

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("instructional_designer")
print("✅ Imports ready.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 3 — Data Models
# ════════════════════════════════════════════════════════════════════════════
# @title 📐 Cell 3 — Data Models

class LearnerProfile(Enum):
    BEGINNER        = "beginner"
    MSC_STUDENT     = "msc_student"
    PRODUCT_MANAGER = "product_manager"


PROFILE_DESCRIPTIONS = {
    LearnerProfile.BEGINNER: (
        "Undergraduate first AI/CS course. Prior knowledge: basic Python, "
        "high-school algebra, no prior NLP. Session duration ~120 min."
    ),
    LearnerProfile.MSC_STUDENT: (
        "Graduate-level MSc Generative AI intermediate practitioner. "
        "Prior knowledge: linear algebra, neural networks, transformer "
        "architecture, attention mechanisms, tokenisation, LLMs."
    ),
    LearnerProfile.PRODUCT_MANAGER: (
        "Non-technical product manager. Needs conceptual understanding, "
        "business applications, semantic search intuition, awareness of "
        "bias/drift — no mathematical depth required."
    ),
}


@dataclass
class LessonArtifacts:
    architect_outline:  str = ""
    lesson_plan:        str = ""
    student_handout:    str = ""
    quiz:               str = ""
    teacher_answer_key: str = ""


@dataclass
class AssessmentResult:
    score:        float = 0.0   # 0.0 – 1.0
    passed:       bool  = False
    feedback:     str   = ""
    failed_areas: list  = field(default_factory=list)


@dataclass
class GenerationConfig:
    # ── Groq / Model ─────────────────────────────────────────────────────
    groq_model:     str   = "llama-3.3-70b-versatile"
    # Groq rate-limit: ~6 000 tokens/min on free tier; 30 000 on paid.
    # We use smaller max_tokens per call to stay within limits.
    max_tokens:     int   = 2048

    # ── Lesson settings ───────────────────────────────────────────────────
    topic_title:        str            = "Embeddings and Vector Databases"
    topic_description:  str            = (
        "How text is encoded as dense numeric vectors, how cosine similarity "
        "works, and how vector databases enable semantic search at scale."
    )
    learner_profile:    LearnerProfile = LearnerProfile.MSC_STUDENT

    # ── Quality control ───────────────────────────────────────────────────
    pass_threshold: float = 0.80   # simulated student must score ≥ 80 %
    max_retries:    int   = 2      # max revision loops before delivering anyway


print("✅ Data models defined.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 4 — Groq Helper
# ════════════════════════════════════════════════════════════════════════════
# @title 🤖 Cell 4 — Groq Helper & JSON Utility

def groq_chat(client: Groq, cfg: GenerationConfig, prompt: str,
              system: str = "") -> str:
    """
    Single-turn chat via Groq.
    Handles the free-tier rate limit with an exponential back-off retry.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model    = cfg.groq_model,
                messages = messages,
                max_tokens = cfg.max_tokens,
                temperature = 0.3,
            )
            return resp.choices[0].message.content
        except Exception as exc:
            wait = 2 ** attempt * 5        # 5 s, 10 s, 20 s, 40 s
            logger.warning("Groq error (attempt %d): %s — retrying in %ds",
                           attempt + 1, exc, wait)
            time.sleep(wait)

    raise RuntimeError("Groq API failed after 4 attempts.")


def extract_json(text: str) -> dict:
    """Best-effort JSON extraction; strips markdown fences."""
    cleaned = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    logger.warning("JSON extraction failed — wrapping raw text.")
    return {"raw": text}


print("✅ Groq helper ready.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 5 — Architect Agent
# ════════════════════════════════════════════════════════════════════════════
# @title 🏗️ Cell 5 — Architect Agent

class ArchitectAgent:
    """
    Maps raw source documentation to instructional design frameworks:
      • Gagne's Nine Events of Instruction
      • Merrill's First Principles of Instruction
    Produces a JSON lesson blueprint for the Content Agent.
    """

    GAGNES_EVENTS = [
        "1. Gain Attention",
        "2. Inform Learners of Objectives",
        "3. Stimulate Recall of Prior Learning",
        "4. Present the Content",
        "5. Provide Learning Guidance",
        "6. Elicit Performance (Practice)",
        "7. Provide Feedback",
        "8. Assess Performance",
        "9. Enhance Retention and Transfer",
    ]

    MERRILLS_PRINCIPLES = [
        "Problem-Centred Learning",
        "Activation of Prior Knowledge",
        "Demonstration of Skills",
        "Application by Learners",
        "Integration into Real World",
    ]

    SYSTEM = (
        "You are an expert instructional designer. "
        "You produce precise, structured JSON lesson blueprints. "
        "Return ONLY valid JSON — no markdown fences, no preamble."
    )

    def __init__(self, client: Groq, cfg: GenerationConfig):
        self.client = client
        self.cfg    = cfg

    def create_outline(self, source: str,
                       revision_feedback: Optional[str] = None) -> str:
        revision_block = ""
        if revision_feedback:
            revision_block = (
                "\n=== REVISION MODE ===\n"
                "Previous lesson FAILED the quality assessment.\n"
                f"Student Failure Analysis:\n{revision_feedback}\n"
                "Your revised outline MUST directly address every gap above.\n"
                "===================\n"
            )

        profile_desc = PROFILE_DESCRIPTIONS.get(self.cfg.learner_profile, "")

        prompt = f"""{revision_block}
Analyse the source documentation below and output a lesson blueprint as
valid JSON using BOTH frameworks:

Gagne's Nine Events: {' | '.join(self.GAGNES_EVENTS)}
Merrill's First Principles: {' | '.join(self.MERRILLS_PRINCIPLES)}

Session Context
  Learner Profile : {self.cfg.learner_profile.value}
  Profile Details : {profile_desc}
  Topic           : {self.cfg.topic_title}
  Description     : {self.cfg.topic_description}
  Pass Threshold  : {int(self.cfg.pass_threshold * 100)}%

Source Documentation (first 5000 chars):
{source[:5000]}

Return ONLY this JSON structure — no extra text:
{{
  "topic": "...",
  "learner_profile": "...",
  "estimated_duration_minutes": 90,
  "learning_objectives": ["SMART objective 1", "..."],
  "prerequisite_knowledge": ["...", "..."],
  "key_concepts": ["concept 1", "..."],
  "difficulty_calibration": "brief note",
  "gagnes_events": {{
    "gain_attention": "...",
    "objectives_statement": "...",
    "prior_recall": "...",
    "content_presentation": "...",
    "learning_guidance": "...",
    "practice_elicitation": "...",
    "feedback_strategy": "...",
    "assessment_design": "...",
    "retention_transfer": "..."
  }},
  "merrills_alignment": {{
    "problem_scenario": "...",
    "activation_strategy": "...",
    "demonstration_approach": "...",
    "application_exercises": ["exercise 1", "exercise 2"],
    "integration_activity": "..."
  }},
  "assessment_criteria": {{
    "pass_threshold": {self.cfg.pass_threshold},
    "total_marks": 30,
    "section_breakdown": {{"multiple_choice": 10, "short_answer": 12, "application": 8}},
    "bloom_levels_targeted": ["remember", "understand", "apply", "analyse"]
  }}
}}"""

        logger.info("[Architect] Creating outline (revision=%s) …",
                    bool(revision_feedback))
        return groq_chat(self.client, self.cfg, prompt, self.SYSTEM)


print("✅ ArchitectAgent defined.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 6 — Content Agent
# ════════════════════════════════════════════════════════════════════════════
# @title 📝 Cell 6 — Content Agent

class ContentAgent:
    """
    Generates four lesson artefacts from the Architect's blueprint:
      1. Lesson Plan (teacher guide)
      2. Student Handout (pre-class reading)
      3. Quiz / Assessment
      4. Teacher Answer Key
    """

    SYSTEM = (
        "You are an expert instructional content writer. "
        "You produce clear, professional, pedagogically sound lesson materials "
        "formatted with markdown headings and bullet points."
    )

    def __init__(self, client: Groq, cfg: GenerationConfig):
        self.client = client
        self.cfg    = cfg

    # ── Lesson Plan ─────────────────────────────────────────────────────────
    def generate_lesson_plan(self, outline: str, source: str) -> str:
        logger.info("[Content] Generating lesson plan …")
        prompt = f"""Create a TEACHER LESSON PLAN using the blueprint and source below.

Blueprint JSON:
{outline[:1500]}

Source material (first 4000 chars):
{source[:4000]}

Structure your lesson plan with these sections:
# LESSON PLAN — {self.cfg.topic_title}
## Session Overview (topic, level, duration, materials)
## SMART Learning Objectives (4–5 objectives)
## Minute-by-Minute Lesson Flow (Gagne's 9 Events as a markdown table)
## Core Concepts with Explanations (minimum 3 concepts grounded in source)
## Worked Examples (minimum 2 step-by-step examples)
## Guided Discussion Questions (4 questions with facilitation tips)
## Common Misconceptions to Address
## Differentiation for {self.cfg.learner_profile.value}

Write at least 500 words. Use markdown."""
        return groq_chat(self.client, self.cfg, prompt, self.SYSTEM)

    # ── Student Handout ──────────────────────────────────────────────────────
    def generate_student_handout(self, outline: str, source: str) -> str:
        logger.info("[Content] Generating student handout …")
        prompt = f"""Create a PRE-CLASS STUDENT HANDOUT for a {self.cfg.learner_profile.value}.

Blueprint JSON:
{outline[:1200]}

Source material (first 4000 chars):
{source[:4000]}

Structure:
# Student Handout — {self.cfg.topic_title}
## Why This Matters (1-paragraph context)
## Key Vocabulary (6–8 terms with clear definitions)
## Core Concepts Explained (clear prose, minimum 3 concepts)
## Mental Models & Analogies (2 real-world analogies)
## Visual Representation (ASCII diagram or structured text)
## Pre-Class Warm-Up Questions (3 priming questions)
## Further Reading

Write at least 450 words. Keep tone engaging and student-friendly."""
        return groq_chat(self.client, self.cfg, prompt, self.SYSTEM)

    # ── Quiz ─────────────────────────────────────────────────────────────────
    def generate_quiz(self, outline: str, lesson_plan: str) -> str:
        logger.info("[Content] Generating quiz …")
        prompt = f"""Create a STUDENT QUIZ for level: {self.cfg.learner_profile.value}.

Blueprint JSON:
{outline[:1200]}

Lesson plan excerpt (first 2000 chars):
{lesson_plan[:2000]}

IMPORTANT FORMATTING RULES:
- Section A: EXACTLY 10 Multiple Choice questions.
  For EACH question mark the correct option with [CORRECT] like this:
  Q1. Question text?
  a) Wrong option
  b) Correct option [CORRECT]
  c) Wrong option
  d) Wrong option

- Section B: EXACTLY 4 Short Answer questions (3 pts each = 12 pts total)
- Section C: 1 Application Exercise (8 pts)
- End with a Scoring Summary table:
  Section A MCQ: 10 pts | Section B Short Answer: 12 pts | Section C Application: 8 pts | Total: 30 pts
  Pass mark: {int(self.cfg.pass_threshold * 30)}/30 ({int(self.cfg.pass_threshold * 100)}%)

Topic: {self.cfg.topic_title}
Mix Bloom's taxonomy levels: Remember, Understand, Apply, Analyse."""
        return groq_chat(self.client, self.cfg, prompt, self.SYSTEM)

    # ── Teacher Answer Key ───────────────────────────────────────────────────
    def generate_answer_key(self, quiz: str, outline: str, source: str) -> str:
        logger.info("[Content] Generating teacher answer key …")
        prompt = f"""Create a TEACHER ANSWER KEY for the quiz below.

Quiz:
{quiz[:2500]}

Source material (first 2000 chars):
{source[:2000]}

Structure:
# Teacher Answer Key — {self.cfg.topic_title}
## Section A: MCQ Answers
  For each Q: state correct letter + explain WHY correct + why distractors are wrong.
## Section B: Model Short Answers
  For each Q: full model answer with 3pt/2pt/1pt/0pt rubric.
## Section C: Model Application Solution
  Step-by-step solution with marking rubric.
## Score Interpretation
  | 90-100% Excellent | 80-89% Good | 70-79% Satisfactory | <70% Reteach |
## Teaching Notes (common errors + discussion facilitation tips)"""
        return groq_chat(self.client, self.cfg, prompt, self.SYSTEM)


print("✅ ContentAgent defined.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 7 — Simulated Student Agent
# ════════════════════════════════════════════════════════════════════════════
# @title 🎓 Cell 7 — Simulated Student Agent

class SimulatedStudentAgent:
    """
    Simulates a learner of the configured profile attempting the quiz.
    Uses a separate LLM context (only sees what a real student would see).
    Scores the attempt; if below threshold, returns structured failure
    analysis to feed the revision loop.
    """

    SYSTEM_STUDENT = (
        "You are a realistic student. Answer only from what you studied. "
        "If something is unclear or missing from your study material, show "
        "that uncertainty — do NOT invent knowledge. "
        "Return ONLY valid JSON, no markdown fences."
    )

    SYSTEM_GRADER = (
        "You are an impartial quiz grader. "
        "Grade objectively based on the [CORRECT] markers and rubrics provided. "
        "Return ONLY valid JSON, no markdown fences."
    )

    def __init__(self, client: Groq, cfg: GenerationConfig):
        self.client = client
        self.cfg    = cfg

    # ── public ──────────────────────────────────────────────────────────────
    def attempt_quiz(self, quiz: str, handout: str) -> AssessmentResult:
        logger.info("[Student] Simulated student attempting quiz …")
        student_json_text = self._answer(quiz, handout)
        return self._grade(student_json_text, quiz)

    # ── private ─────────────────────────────────────────────────────────────
    def _answer(self, quiz: str, handout: str) -> str:
        prompt = f"""You are a {self.cfg.learner_profile.value} student.
You have studied ONLY this material:
{handout[:3000]}

Attempt every question below as honestly as a real student at this level.
If something was not clearly explained in your study material, note it.

QUIZ:
{quiz[:2500]}

Return ONLY this JSON:
{{
  "section_a_answers": ["b","c","a","d","b","c","a","d","b","c"],
  "section_b_answers": ["answer1","answer2","answer3","answer4"],
  "section_c_answer": "full application answer here",
  "self_assessment": {{
    "confident_topics": ["topic A"],
    "confused_topics":  ["topic X"],
    "unclear_questions": ["Q3 was unclear because ..."],
    "estimated_score_pct": 72
  }},
  "failure_analysis": {{
    "content_gaps": ["gap 1","gap 2"],
    "confusing_sections": ["section X was hard because ..."],
    "missing_examples": ["an example showing ... would help"],
    "suggestions_for_improvement": ["specific improvement 1"]
  }}
}}"""
        return groq_chat(self.client, self.cfg, prompt, self.SYSTEM_STUDENT)

    def _grade(self, student_json_text: str, quiz: str) -> AssessmentResult:
        logger.info("[Student] Grading …")
        grade_prompt = f"""Grade the student's answers below against the quiz.

STUDENT ANSWERS (JSON):
{student_json_text}

QUIZ (check [CORRECT] markers for MCQ):
{quiz[:2500]}

Scoring rules:
  Section A (MCQ): 1 pt per correct answer (compare to [CORRECT] marker).
  Section B (Short Answer): 0-3 pts per question based on accuracy & depth.
  Section C (Application): 0-8 pts based on correctness of approach.

Return ONLY this JSON:
{{
  "section_a_score": 7,
  "section_b_score": 9,
  "section_c_score": 6,
  "total_score": 22,
  "max_score": 30,
  "percentage": 73.3,
  "passed": false,
  "failed_areas": ["Q3 incorrect","Q7 incorrect","B2 incomplete"],
  "grader_feedback": "paragraph on strengths and weaknesses"
}}"""

        raw         = groq_chat(self.client, self.cfg, grade_prompt, self.SYSTEM_GRADER)
        grade_data  = extract_json(raw)
        student_data = extract_json(student_json_text)

        percentage  = float(grade_data.get("percentage", 0))
        score_frac  = percentage / 100.0
        passed      = score_frac >= self.cfg.pass_threshold

        fa = student_data.get("failure_analysis", {})
        feedback_parts = [
            f"Score : {percentage:.1f}%  "
            f"({grade_data.get('total_score','?')}/{grade_data.get('max_score',30)})",
            f"Passed: {passed}  |  Threshold: {int(self.cfg.pass_threshold*100)}%",
            "",
            "Grader Feedback:",
            grade_data.get("grader_feedback", "N/A"),
            "",
            "Content Gaps Identified:",
            *[f"  • {g}" for g in fa.get("content_gaps", [])],
            "Confusing Sections:",
            *[f"  • {s}" for s in fa.get("confusing_sections", [])],
            "Missing Examples Needed:",
            *[f"  • {e}" for e in fa.get("missing_examples", [])],
            "Revision Suggestions:",
            *[f"  • {s}" for s in fa.get("suggestions_for_improvement", [])],
        ]

        return AssessmentResult(
            score=score_frac,
            passed=passed,
            feedback="\n".join(feedback_parts),
            failed_areas=grade_data.get("failed_areas", []),
        )


print("✅ SimulatedStudentAgent defined.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 8 — Lesson Controller (Orchestrator)
# ════════════════════════════════════════════════════════════════════════════
# @title 🎛️ Cell 8 — Lesson Controller

class LessonController:
    """
    Orchestrates the full multi-agent pipeline:

        Source Docs ──► ArchitectAgent (outline)
                              │
                         ContentAgent
                    (lesson plan / handout / quiz / key)
                              │
                    SimulatedStudentAgent (attempt quiz)
                              │
                   score ≥ threshold? ──Yes──► deliver artefacts
                              │ No
                    revision_feedback ──► ArchitectAgent (retry)
                         (max_retries limit)
    """

    def __init__(self, api_key: str, cfg: GenerationConfig):
        self.client    = Groq(api_key=api_key)
        self.cfg       = cfg
        self.architect = ArchitectAgent(self.client, cfg)
        self.content   = ContentAgent(self.client, cfg)
        self.student   = SimulatedStudentAgent(self.client, cfg)

    def run(
        self,
        source_content: str,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> tuple:
        """
        Run the pipeline.
        Returns (LessonArtifacts, list[dict iteration_log])
        """
        def _log(msg: str):
            logger.info(msg)
            if progress_cb:
                progress_cb(msg)

        artifacts     = LessonArtifacts()
        iteration_log = []
        revision_fb   = None

        for attempt in range(self.cfg.max_retries + 1):
            entry = {"attempt": attempt + 1}
            t0    = time.time()

            _log(f"🏗️  [Attempt {attempt+1}] Architect Agent → creating outline …")
            artifacts.architect_outline = self.architect.create_outline(
                source_content, revision_fb)

            _log(f"📝  [Attempt {attempt+1}] Content Agent → lesson plan …")
            artifacts.lesson_plan = self.content.generate_lesson_plan(
                artifacts.architect_outline, source_content)

            _log(f"📋  [Attempt {attempt+1}] Content Agent → student handout …")
            artifacts.student_handout = self.content.generate_student_handout(
                artifacts.architect_outline, source_content)

            _log(f"❓  [Attempt {attempt+1}] Content Agent → quiz …")
            artifacts.quiz = self.content.generate_quiz(
                artifacts.architect_outline, artifacts.lesson_plan)

            _log(f"🔑  [Attempt {attempt+1}] Content Agent → answer key …")
            artifacts.teacher_answer_key = self.content.generate_answer_key(
                artifacts.quiz, artifacts.architect_outline, source_content)

            _log(f"🎓  [Attempt {attempt+1}] Simulated Student → attempting quiz …")
            result = self.student.attempt_quiz(
                artifacts.quiz, artifacts.student_handout)

            entry.update({
                "score_pct":     round(result.score * 100, 1),
                "passed":        result.passed,
                "feedback":      result.feedback,
                "total_seconds": round(time.time() - t0, 1),
            })
            iteration_log.append(entry)

            if result.passed:
                _log(f"✅  PASSED — {result.score*100:.1f}% ≥ "
                     f"{self.cfg.pass_threshold*100:.0f}%")
                break
            elif attempt < self.cfg.max_retries:
                _log(f"⚠️  {result.score*100:.1f}% below threshold — "
                     f"revision loop {attempt+1}/{self.cfg.max_retries} …")
                revision_fb = result.feedback
            else:
                _log(f"🔴  Max retries reached. Final: {result.score*100:.1f}%")

        return artifacts, iteration_log


print("✅ LessonController defined.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 9 — PDF Generator
# ════════════════════════════════════════════════════════════════════════════
# @title 🖨️ Cell 9 — PDF Generator

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT

BRAND_BLUE  = colors.HexColor("#1B2A47")
BRAND_TEAL  = colors.HexColor("#00897B")
BRAND_GREY  = colors.HexColor("#F4F6F8")


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Heading1"],
               textColor=BRAND_BLUE, fontSize=17, spaceAfter=6,
               fontName="Helvetica-Bold"),
        "h2": ParagraphStyle("h2", parent=base["Heading2"],
               textColor=BRAND_TEAL, fontSize=12, spaceAfter=4,
               fontName="Helvetica-Bold"),
        "h3": ParagraphStyle("h3", parent=base["Heading3"],
               textColor=BRAND_BLUE, fontSize=10, spaceAfter=3,
               fontName="Helvetica-BoldOblique"),
        "body": ParagraphStyle("body", parent=base["Normal"],
                fontSize=9.5, leading=13.5, spaceAfter=3),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
                  fontSize=9.5, leading=13, leftIndent=14,
                  bulletIndent=4, spaceAfter=2),
        "meta": ParagraphStyle("meta", parent=base["Normal"],
                fontSize=8.5, textColor=colors.grey),
    }


def _md_to_flowables(text: str, styles: dict) -> list:
    flowables = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            flowables.append(Spacer(1, 3))
        elif s.startswith("### "):
            flowables.append(Paragraph(s[4:], styles["h3"]))
        elif s.startswith("## "):
            flowables.append(Spacer(1, 5))
            flowables.append(Paragraph(s[3:], styles["h2"]))
        elif s.startswith("# "):
            flowables.append(Spacer(1, 8))
            flowables.append(Paragraph(s[2:], styles["h1"]))
            flowables.append(HRFlowable(width="100%",
                             color=BRAND_TEAL, thickness=1))
        elif s.startswith(("- ", "• ", "* ")):
            flowables.append(Paragraph("• " + s[2:], styles["bullet"]))
        elif s.startswith("---"):
            flowables.append(HRFlowable(width="100%",
                             color=colors.lightgrey, thickness=0.5))
        else:
            safe = s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
            safe = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", safe)
            flowables.append(Paragraph(safe, styles["body"]))
    return flowables


def artifacts_to_pdfs(
    artifacts: LessonArtifacts,
    cfg: GenerationConfig,
    output_dir: str = "/content",
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    styles    = _build_styles()
    safe      = cfg.topic_title.replace(" ", "_").replace("/", "-")
    ts        = time.strftime("%Y%m%d_%H%M%S")

    docs = {
        "lesson_plan":        ("Lesson_Plan",        artifacts.lesson_plan),
        "student_handout":    ("Student_Handout",     artifacts.student_handout),
        "quiz":               ("Quiz",                artifacts.quiz),
        "teacher_answer_key": ("Teacher_Answer_Key",  artifacts.teacher_answer_key),
    }

    paths = {}
    for key, (label, content) in docs.items():
        filename = f"{output_dir}/{safe}_{label}_{ts}.pdf"
        doc = SimpleDocTemplate(
            filename, pagesize=A4,
            leftMargin=2.5*cm, rightMargin=2.5*cm,
            topMargin=2.5*cm,  bottomMargin=2.5*cm,
        )
        story = [
            Paragraph(f"📚  {label.replace('_',' ')}", styles["h1"]),
            Paragraph(f"Topic: {cfg.topic_title}", styles["h2"]),
            Paragraph(
                f"Learner: {cfg.learner_profile.value}   |   "
                f"Model: {cfg.groq_model}   |   "
                f"Generated: {time.strftime('%d %b %Y %H:%M')}",
                styles["meta"],
            ),
            HRFlowable(width="100%", color=BRAND_BLUE, thickness=2),
            Spacer(1, 10),
        ]
        story.extend(_md_to_flowables(content, styles))
        doc.build(story)
        paths[key] = filename
        print(f"   📄 {label}: {filename}")

    return paths


print("✅ PDF generator ready.")


# ════════════════════════════════════════════════════════════════════════════
# CELL 10 — API Key & Config
# ════════════════════════════════════════════════════════════════════════════
# @title 🔑 Cell 10 — API Key & Lesson Config

# ── Groq API Key ─────────────────────────────────────────────────────────────
# Best practice: add to Colab Secrets (🔑 icon, left panel) as GROQ_API_KEY
try:
    from google.colab import userdata
    GROQ_API_KEY = userdata.get("GROQ_API_KEY")
    print("✅ Groq API key loaded from Colab Secrets.")
except Exception:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    if GROQ_API_KEY:
        print("✅ Groq API key loaded from environment variable.")
    else:
        GROQ_API_KEY = input("Paste your Groq API key: ").strip()
        print("✅ Groq API key set.")

# ── Lesson Configuration ──────────────────────────────────────────────────────
CONFIG = GenerationConfig(
    groq_model          = "llama-3.3-70b-versatile",
    max_tokens          = 2048,

    topic_title         = "Embeddings and Vector Databases",
    topic_description   = (
        "How text is encoded as dense numeric vectors, cosine similarity, "
        "ANN search, and vector databases for semantic retrieval in RAG systems."
    ),
    learner_profile     = LearnerProfile.MSC_STUDENT,
    # ↑ Change to: LearnerProfile.BEGINNER  or  LearnerProfile.PRODUCT_MANAGER

    pass_threshold      = 0.80,   # simulated student must score ≥ 80%
    max_retries         = 2,      # max revision loops
)

print("\n📋 Active Configuration:")
print(f"   Model          : {CONFIG.groq_model}")
print(f"   Topic          : {CONFIG.topic_title}")
print(f"   Learner Profile: {CONFIG.learner_profile.value}")
print(f"   Pass Threshold : {int(CONFIG.pass_threshold*100)}%")
print(f"   Max Retries    : {CONFIG.max_retries}")


# ════════════════════════════════════════════════════════════════════════════
# CELL 11 — Source Document
# ════════════════════════════════════════════════════════════════════════════
# @title 📄 Cell 11 — Source Document
# @markdown Paste your content into SOURCE_TEXT, or set FILE_PATH to upload a file.

FILE_PATH = ""   # e.g. "/content/my_document.txt"  — leave "" to use SOURCE_TEXT below

SOURCE_TEXT = """
Word Embeddings and Vector Representations
===========================================

Introduction
------------
Word embeddings are dense vector representations of words in a continuous
vector space where semantically similar words are mapped to nearby points.
Unlike one-hot encodings (sparse, high-dimensional), embeddings capture
semantic relationships between words.

Key Concept: Word2Vec
---------------------
Word2Vec (Mikolov et al., 2013) introduced two architectures:
  CBOW  (Continuous Bag-of-Words): predicts target word from context words.
  Skip-gram: predicts context words from a target word.
Both produce dense vectors typically 100-300 dimensions.

Mathematical Foundation
-----------------------
Given vocabulary V and embedding dimension d, learn matrix E in R^(|V|xd).
Similarity measured with cosine similarity:
  cos(u,v) = (u dot v) / (||u|| * ||v||)
Range: -1 (opposite direction) to +1 (same direction).

Sentence Embeddings
-------------------
Sentence-BERT (SBERT): Fine-tuned BERT with siamese networks for
sentence-level semantic similarity.
OpenAI text-embedding-3-small / large: State-of-the-art general purpose.
Dimensions: 768 (BERT-base), 1536 (ada-002), up to 3072 (text-embedding-3-large).

Vector Databases
----------------
Vector databases store and index high-dimensional vectors for Approximate
Nearest Neighbour (ANN) search at scale.

Popular systems:
  Pinecone   — fully managed, serverless, production-ready
  Weaviate   — open-source, multi-modal, GraphQL API
  ChromaDB   — lightweight, Python-native, local-first
  Qdrant     — Rust-based, open-source, high performance
  FAISS      — Facebook library, in-memory, no built-in persistence

Indexing Algorithms
-------------------
HNSW (Hierarchical Navigable Small World): Graph-based, best recall/speed
  trade-off. Default in most production vector databases.
IVF (Inverted File Index): Cluster-based partitioning; fast retrieval.
PQ (Product Quantisation): Compresses vectors for memory efficiency.

Retrieval-Augmented Generation (RAG)
-------------------------------------
1. Chunk documents into passages of 256-512 tokens.
2. Embed each chunk using an embedding model.
3. Store embeddings in a vector database.
4. At query time: embed query, run ANN search, retrieve top-k chunks.
5. Inject retrieved chunks into LLM prompt as context.
6. LLM generates a grounded, factual answer.

Key Metrics
-----------
Recall@K      : fraction of true neighbours found in top-K results
MRR           : Mean Reciprocal Rank
NDCG          : Normalised Discounted Cumulative Gain
Latency p95   : 95th-percentile query response time

Bias and Concept Drift
----------------------
Embedding bias: models trained on biased corpora encode social stereotypes.
Concept drift: domain vocabulary evolves; periodic re-embedding is needed.
Mitigation: debiasing layers, regular fine-tuning, cosine drift monitoring.

Practical Considerations
------------------------
Optimal chunk size: 256-512 tokens with 10-20% overlap between chunks.
Re-ranking: Use a cross-encoder (ms-marco-MiniLM) after ANN retrieval.
Cost estimate: ~$0.02 per 1M tokens with OpenAI ada-002.
Storage: Plan for index size ~4x raw vector data with HNSW.
"""

# ── Load from file if provided ─────────────────────────────────────────────
if FILE_PATH and pathlib.Path(FILE_PATH).exists():
    ext = pathlib.Path(FILE_PATH).suffix.lower()
    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(FILE_PATH) as pdf:
                SOURCE_TEXT = "\n".join(p.extract_text() or "" for p in pdf.pages)
            print(f"✅ Loaded PDF: {len(SOURCE_TEXT):,} chars")
        except ImportError:
            print("⚠️  Run: pip install pdfplumber -q")
    else:
        with open(FILE_PATH, "r", encoding="utf-8", errors="ignore") as fh:
            SOURCE_TEXT = fh.read()
        print(f"✅ Loaded file: {len(SOURCE_TEXT):,} chars")
else:
    print(f"ℹ️  Using built-in source text ({len(SOURCE_TEXT):,} chars)")


# ════════════════════════════════════════════════════════════════════════════
# CELL 12 — Run Pipeline (no UI)
# ════════════════════════════════════════════════════════════════════════════
# @title 🚀 Cell 12 — Run Pipeline (text output, no Gradio)
# @markdown Runs the full agent pipeline and saves 4 PDFs to /content.

def run_pipeline(api_key: str, cfg: GenerationConfig, source: str):
    print("=" * 62)
    print("  🎓  ALGORITHMIC INSTRUCTIONAL DESIGNER  |  Groq + LLaMA")
    print("=" * 62)
    t_start = time.time()

    controller             = LessonController(api_key=api_key, cfg=cfg)
    artifacts, iter_log    = controller.run(source, progress_cb=print)

    print(f"\n⏱️  Total time: {time.time() - t_start:.0f} s")
    print("\n📊 Iteration Summary:")
    for e in iter_log:
        status = "✅ PASS" if e["passed"] else "❌ FAIL"
        print(f"   Attempt {e['attempt']}: {status} — "
              f"Score {e['score_pct']}% — {e['total_seconds']}s")

    print("\n🖨️  Generating PDFs …")
    pdf_paths = artifacts_to_pdfs(artifacts, cfg)

    print("\n✅ Pipeline complete. Artefacts:")
    for k, p in pdf_paths.items():
        print(f"   • {k}: {p}")

    return artifacts, iter_log, pdf_paths


# Run immediately:
artifacts, iter_log, pdf_paths = run_pipeline(
    api_key = GROQ_API_KEY,
    cfg     = CONFIG,
    source  = SOURCE_TEXT,
)


# ════════════════════════════════════════════════════════════════════════════
# CELL 13 — Gradio UI  (optional — run after Cell 12)
# ════════════════════════════════════════════════════════════════════════════
# @title 🖥️ Cell 13 — Gradio UI (optional)
# @markdown Launches an interactive web interface with a public share link.

import gradio as gr

_ARTIFACTS = LessonArtifacts()
_PDF_PATHS: dict = {}


def _profile_from_str(s: str) -> LearnerProfile:
    return {
        "Beginner":        LearnerProfile.BEGINNER,
        "MSc Student":     LearnerProfile.MSC_STUDENT,
        "Product Manager": LearnerProfile.PRODUCT_MANAGER,
    }.get(s, LearnerProfile.MSC_STUDENT)


def gradio_run(
    api_key_input, topic_title, topic_description,
    profile_str, threshold_pct, retries,
    source_text, uploaded_files,
    progress=gr.Progress(),
):
    global _ARTIFACTS, _PDF_PATHS

    # ── Build source ──────────────────────────────────────────────────────
    source = source_text.strip()
    if uploaded_files:
        for f in (uploaded_files if isinstance(uploaded_files, list) else [uploaded_files]):
            path = f if isinstance(f, str) else f.name
            ext  = pathlib.Path(path).suffix.lower()
            if ext == ".pdf":
                try:
                    import pdfplumber
                    with pdfplumber.open(path) as pdf:
                        source += "\n\n" + "\n".join(
                            p.extract_text() or "" for p in pdf.pages)
                except Exception as e:
                    source += f"\n[PDF error: {e}]"
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    source += "\n\n" + fh.read()

    if not source:
        return ("❌ No source content.",) + ("",) * 4 + (None,) * 4

    key = api_key_input.strip() or GROQ_API_KEY
    if not key:
        return ("❌ No Groq API key.",) + ("",) * 4 + (None,) * 4

    cfg = GenerationConfig(
        topic_title       = topic_title,
        topic_description = topic_description,
        learner_profile   = _profile_from_str(profile_str),
        pass_threshold    = float(threshold_pct) / 100.0,
        max_retries       = int(retries),
    )

    log_lines = []
    def _cb(msg):
        log_lines.append(msg)
        progress((len(log_lines), 30), desc=msg)

    try:
        ctrl              = LessonController(api_key=key, cfg=cfg)
        _ARTIFACTS, log   = ctrl.run(source, progress_cb=_cb)
        _PDF_PATHS        = artifacts_to_pdfs(_ARTIFACTS, cfg)

        summary = "\n".join(
            f"Attempt {e['attempt']}: {'✅ PASS' if e['passed'] else '❌ FAIL'} "
            f"— {e['score_pct']}%"
            for e in log
        )

        return (
            "\n".join(log_lines) + "\n\n" + summary,
            _ARTIFACTS.lesson_plan,
            _ARTIFACTS.student_handout,
            _ARTIFACTS.quiz,
            _ARTIFACTS.teacher_answer_key,
            _PDF_PATHS.get("lesson_plan"),
            _PDF_PATHS.get("student_handout"),
            _PDF_PATHS.get("quiz"),
            _PDF_PATHS.get("teacher_answer_key"),
        )
    except Exception:
        import traceback
        return (f"❌ Error:\n{traceback.format_exc()}",) + ("",)*4 + (None,)*4


with gr.Blocks(title="Instructional Designer — Groq",
               theme=gr.themes.Soft(primary_hue="teal")) as demo:

    gr.Markdown("""
# 🎓 Algorithmic Instructional Designer
### Powered by **Groq** · **llama-3.3-70b-versatile**
Multi-agent system: **Architect → Content → Simulated Student → Revision Loop**
    """)

    with gr.Row():
        # ── Inputs ──────────────────────────────────────────────────────────
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Configuration")
            api_box   = gr.Textbox(label="Groq API Key (optional if set above)",
                                   type="password", placeholder="gsk_…")
            title_box = gr.Textbox(label="Topic Title",
                                   value=CONFIG.topic_title)
            desc_box  = gr.Textbox(label="Topic Description",
                                   value=CONFIG.topic_description, lines=3)
            prof_drop = gr.Dropdown(
                label="Learner Profile",
                choices=["Beginner", "MSc Student", "Product Manager"],
                value="MSc Student",
            )
            thresh_sl = gr.Slider(label="Pass Threshold (%)",
                                  minimum=50, maximum=100, step=5,
                                  value=int(CONFIG.pass_threshold * 100))
            retry_sl  = gr.Slider(label="Max Revision Retries",
                                  minimum=0, maximum=3, step=1,
                                  value=CONFIG.max_retries)

            gr.Markdown("### 📄 Source Material")
            upload    = gr.File(label="Upload .txt / .pdf",
                                file_count="multiple",
                                file_types=[".txt", ".pdf"])
            src_box   = gr.Textbox(label="Or paste source text",
                                   value=SOURCE_TEXT[:1500] + "\n\n[…truncated…]",
                                   lines=8, max_lines=16)
            run_btn   = gr.Button("🚀 Generate Lesson",
                                  variant="primary", size="lg")

        # ── Outputs ─────────────────────────────────────────────────────────
        with gr.Column(scale=2):
            gr.Markdown("### 📊 Pipeline Log")
            log_box = gr.Textbox(label="Progress", lines=9, interactive=False)

            gr.Markdown("### 📑 Generated Artefacts")
            with gr.Tabs():
                with gr.TabItem("📘 Lesson Plan"):
                    lp_txt = gr.Textbox(lines=18, interactive=False)
                    lp_pdf = gr.File(label="⬇️ Download PDF")
                with gr.TabItem("📋 Student Handout"):
                    sh_txt = gr.Textbox(lines=18, interactive=False)
                    sh_pdf = gr.File(label="⬇️ Download PDF")
                with gr.TabItem("❓ Quiz"):
                    qz_txt = gr.Textbox(lines=18, interactive=False)
                    qz_pdf = gr.File(label="⬇️ Download PDF")
                with gr.TabItem("🔑 Answer Key"):
                    ak_txt = gr.Textbox(lines=18, interactive=False)
                    ak_pdf = gr.File(label="⬇️ Download PDF")

    run_btn.click(
        fn=gradio_run,
        inputs=[api_box, title_box, desc_box, prof_drop,
                thresh_sl, retry_sl, src_box, upload],
        outputs=[log_box, lp_txt, sh_txt, qz_txt, ak_txt,
                 lp_pdf, sh_pdf, qz_pdf, ak_pdf],
    )

demo.queue()
demo.launch(share=True, debug=False)
