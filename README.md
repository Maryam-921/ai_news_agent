# 🧠 Daily AI Intelligence Dashboard

An AI-powered system that transforms raw AI news into structured insights, trends, and actionable intelligence using LLMs.

---

## 🚀 Overview

This project builds a complete pipeline that:
1. Collects AI-related news articles
2. Filters and ranks relevance
3. Extracts and cleans full article content
4. Uses LLMs to generate structured summaries
5. Synthesizes cross-article insights
6. Presents everything in an interactive Streamlit dashboard

The goal is to move from **information overload → decision-ready insights**.

---

## ✨ Features

### 🔍 Intelligent Filtering
- Semantic similarity filtering using Sentence Transformers
- LLM-based classification for AI relevance

### 🧾 Structured Summarization
Each article is converted into:
- Summary (≤ 5 sentences)
- Key points
- Category (Research, Product Launch, etc.)
- Entities (companies, products, technologies)
- Impact, novelty, and hype scores
- Trend signals and keywords

### 🧠 Insight Generation
Aggregates multiple articles to produce:
- Daily AI summary
- Top 3 most impactful articles
- Key trends (clustered across articles)
- Emerging signals
- Key companies and technologies

### 🎧 Audio Briefing
- Converts daily summary into speech for quick consumption

### 📊 Interactive Dashboard
Built with Streamlit:
- Daily summary (highlighted)
- Trend cards
- Top stories with “why it matters”
- Emerging signals (visual tags)
- Entity tracking
- Article explorer with filtering (category, company, tech)

---

## 🏗️ Architecture
Raw RSS Feeds
    ↓
Preprocessing (cleaning, normalization)
    ↓
Semantic Filtering (Sentence Transformers)
    ↓
LLM Filtering (Gemini)
    ↓
Content Extraction (newspaper3k)
    ↓
LLM Summarization (Agent)
    ↓
Insight Generation (Agent)
    ↓
Streamlit UI

---

## 🧰 Tech Stack

- **Frontend/UI**
  - Streamlit

- **Data Processing**
  - Pandas, NumPy

- **Scraping & Parsing**
  - feedparser
  - BeautifulSoup
  - newspaper3k

- **NLP / ML**
  - Sentence Transformers

- **LLM & Agents**
  - Gemini (via agno)
  - Agent-based prompting

- **Audio**
  - Kokoro (text-to-speech)
  - PyTorch

---

## ⚙️ Installation

```bash
git clone <repo_url>
cd project
pip install -r requirements.txt

🧠 Key Design Decisions
LLM for reasoning, not data retrieval
Metadata (author, link) handled outside LLM
Two-stage pipeline
Article-level summarization
Cross-article synthesis
Structured JSON outputs
Enables consistent UI rendering

🚧 Future Improvements
Async/batched LLM calls (performance)
Deduplication of similar articles
Persistent storage (database)
User personalization
Trend tracking over time

📌 Takeaway
This project demonstrates how LLMs can be used to build end-to-end intelligence systems, not just chat interfaces.