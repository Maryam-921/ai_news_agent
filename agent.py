import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
import json
from newspaper import Article
from agno.agent import Agent
from agno.run.agent import RunOutput
from agno.models.google import Gemini
from kokoro import KPipeline
import torch
import re
from interface import display_app

# 1. Extract article links
def rssToData(feedLink):
    feed = feedparser.parse(feedLink)
    for entry in feed.entries:
        content = ""
        if ("content" in entry and entry.content):
            content = entry.content  
        return {
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "description": entry.description,
            "author": entry.author,
            "content": content
        }

def getData():
    data = []
    rssFeeds = [
        "https://www.theverge.com/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://venturebeat.com/category/ai/feed",
        "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",
        "https://the-decoder.com/feed/",
        "https://pub.towardsai.net/feed",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://www.oneusefulthing.org/feed",
        "https://www.ai-supremacy.com/feed",
        "https://www.marktechpost.com/feed/"
    ]
    for feed in rssFeeds:
        data.append(rssToData(feed))
    return data

# 2. Filter by time
def filterByTime(df):
    df = df.copy()
    df["published"] = pd.to_datetime(df["published"], utc=True, errors="coerce", format="mixed")
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)
    return df[df["published"] >= last_24h].reset_index(drop=True)

# 3. Clean text - description
def clean_html(text):
    soup = BeautifulSoup(text, "html.parser")
    # remove images completely
    for img in soup.find_all("img"):
        img.decompose()
    # extract clean text
    return soup.get_text(separator=" ", strip=True)

# 4. Filtering articles using sentence transformers
def semantic_score(text):
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    AI_SEED_TEXTS = [
        "artificial intelligence research",
        "large language models, agents, and reasoning systems",
        "machine learning breakthroughs",
        "AI industry news and companies like OpenAI Google Nvidia",
        "AI research papers and new methodologies",
        "AI system design and production engineering insights",
        "AI model releases and benchmarks"
    ]
    ai_seed_embeddings = embedding_model.encode(AI_SEED_TEXTS)
    emb = embedding_model.encode(text)
    # cosine similarity
    sims = np.dot(ai_seed_embeddings, emb) / (
        np.linalg.norm(ai_seed_embeddings, axis=1) * np.linalg.norm(emb)
    )
    return np.max(sims)

# 5. Filter articles using llm model
def llmFilter(df, titles, llm):
    df = df.copy()
    try:
        # Define the agent
        filter_agent = Agent(
            name="",
            role="",
            model=llm,
            instructions=["""
                You are a strict classification system for AI/tech news.
                Classify each title into exactly one of:
                - HIGH_VALUE
                - MEDIUM_VALUE
                - LOW_VALUE

                Return ONLY valid JSON in this format:

                {{
                "results": [
                    {{"id": 0, "title": "...", "label": "HIGH_VALUE"}},
                    {{"id": 1, "title": "...", "label": "LOW_VALUE"}}
                ]
                }}

                Rules:
                - Do NOT include explanations
                - Do NOT include extra text
                - One output per input title
                - Return **only valid JSON**. Do NOT use markdown formatting. Do NOT include ```.
                """
            ]
        )
        # Run the agent
        result: RunOutput = filter_agent.run(titles)
        filter_result = result.content
        try:
            json_match = re.search(r'\{.*\}', filter_result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = json.loads(filter_result)
        except json.JSONDecodeError as e:
            st.error(f"Failed to parse calorie content: {e}")
            return df
        labels = [item["label"] for item in data["results"]]
        df["llm_class"] = labels
        return df[df["llm_class"] != "LOW_VALUE"]
    except Exception as e:
        st.error(f"❌ An error occurred: {e}")

    # response = ""
    # response_text = response.text
    # data = json.loads(response_text)
    # labels = [item["label"] for item in data["results"]]
    # df["llm_class"] = labels
    # return df[df["llm_class"] != "LOW_VALUE"]

# 6. Scrape article content from the web
def get_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        return ""

def normalize_content(x):
    # Case 1: already clean text (from newspaper3k)
    if isinstance(x, str):
        return x.strip()

    # Case 2: RSS content (list of dicts)
    if isinstance(x, list) and len(x) > 0:
        item = x[0]

        if isinstance(item, dict) and "value" in item:
            html = item["value"]
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator="\n").strip()

    # Case 3: anything else
    return ""

# 7. Summarize articles
def get_summary(agent, article):
    llm_input = {
        "title": article["title"],
        "content": article["content"]
    }
    # Run the agent
    result: RunOutput = agent.run(json.dumps(llm_input))
    summary = result.content
    try:
        json_match = re.search(r'\{.*\}', summary, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            data = json.loads(summary)
        return data
    except json.JSONDecodeError as e:
        st.error(f"⚠️ Skipping article (JSON parse failed): {e}")
        return None


def summarize_articles(articles, llm):
    summaries = []
    try:
        # Define the agent
        summary_agent = Agent(
            name="AI News Summarizer",
            role="Summarizes AI articles into structured insights",
            model=llm,
            instructions=["""
                You are an expert AI news analyst.

                Your task is to analyze a single AI-related article and produce a structured summary optimized for a daily news intelligence system.
                INPUT: You will be give the article title and full content.
                
                OUTPUT FORMAT (JSON only):
                {
                "title": "...",
                "summary": "...", 
                "key_points": ["...", "...", "..."],
                "category": "...",
                "entities": {
                    "companies": ["..."],
                    "products": ["..."],
                    "technologies": ["..."]
                },
                "impact_score": 1-10,
                "novelty_score": 1-10,
                "trend_signals": ["...", "..."],
                "keywords": ["...", "...", "..."],
                }

                GUIDELINES:

                1. Summary:
                - Max 5 sentences
                - Clear, dense, no fluff

                2. Key Points:
                - 3–5 bullet points
                - Extract facts, not opinions

                3. Category:
                Choose ONE:
                - Research
                - Product Launch
                - Funding
                - Regulation
                - Open Source
                - Application
                - Opinion

                4. Entities:
                - Extract real, specific names only
                - Do not hallucinate

                5. Scoring:
                - Impact: real-world importance
                - Novelty: how new or surprising
                - Hype: marketing vs substance

                6. Trend signals:
                - Capture broader themes (e.g., "AI agents", "multimodal models")

                7. Keywords:
                - 5–10 concise tags

                8. Be objective, precise, and avoid speculation.
                
                9. Return **only valid JSON**. Do NOT use markdown formatting. Do NOT include ```.
                """
            ]
        )
        for art in articles:
            data = get_summary(summary_agent, art)
            if data:  # skip failed ones
                # 🔥 Merge metadata here
                data["author"] = art.get("author", "")
                data["link"] = art.get("link", "")

                summaries.append(data)
        return summaries
    except Exception as e:
        st.error(f"❌ Error in summarization: {e}")
        return []

# 8. Generate insights
def get_insights(summaries, llm):
    try:
        # Define the agent
        insights_agent = Agent(
            name="AI News Strategist",
            role="Synthesizes multiple article summaries into insights",
            model=llm,
            instructions=["""
                You are a senior AI news strategist.
                You are given structured summaries of multiple AI news articles from today.
                Your job is to synthesize them into high-level insights for a daily AI news dashboard.

                INPUT: List of article summaries (JSON objects)

                OUTPUT FORMAT (JSON only):
                {
                    "daily_summary": "...",
                    "top_articles": [
                        {
                        "title": "...",
                        "reason": "..."
                        }
                    ],
                    "top_trends": [
                        {
                        "name": "...",
                        "description": "...",
                        "article_count": number,
                        }
                    ],
                    "emerging_signals": ["...", "..."],
                    "key_entities": {
                        "companies": ["..."],
                        "technologies": ["..."]
                    },
                }
                GUIDELINES:
                1. Daily Summary:
                - 4–6 sentences
                - Describe the “big picture” of today in AI
                
                2. Top Articles:
                - Select exactly 3
                - Based on impact + novelty (not popularity)
                - Explain WHY each was chosen

                4. Top Trends:
                - Cluster articles into themes
                - Each trend must be supported by multiple articles
                - Describe what is happening and why it matters

                5. Emerging Signals:
                - Weak but interesting patterns
                - Early-stage ideas worth watching

                6. Key Entities:
                - Most frequently mentioned or most impactful

                IMPORTANT:
                - Do not repeat article summaries
                - Focus on synthesis, not duplication
                - Be analytical, not descriptive
                - Return **only valid JSON**. Do NOT use markdown formatting. Do NOT include ```.
                """
            ]
        )
        # Run the agent
        input_data = json.dumps(summaries)
        result: RunOutput = insights_agent.run(input_data)
        content = result.content
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = json.loads(content)
            return data
        
        except json.JSONDecodeError as e:
            st.error(f"❌ Failed to parse insights JSON: {e}")
            return {}
    
    except Exception as e:
        st.error(f"❌ Error generating insights: {e}")
        return {}

# Text to Speech
def text_to_speech(text):
    pipeline = KPipeline(lang_code='a')
    generator = pipeline(text, voice='af_heart')
    audio_chunks = []
    for _, _, audio in generator:
        audio_chunks.append(audio)
    
    # Combine all chunks
    full_audio = np.concatenate(audio_chunks)
    return full_audio

def main():
    """
    Main pipeline for the AI News Dashboard.

    Steps:
    1. Initialize LLM
    2. Fetch and preprocess raw news data
    3. Filter for AI-relevant articles (semantic + LLM filtering)
    4. Extract and clean full article content
    5. Generate structured summaries using LLM
    6. Synthesize insights across articles
    7. Convert summary to audio
    8. Render UI
    """

    # Initialize LLM
    gemini_api_key = ""
    if gemini_api_key:
        try:
            llm = Gemini(id="gemini-2.5-flash-lite", api_key=gemini_api_key)
        except Exception as e:
            st.error(f"❌ Error initializing Gemini model: {e}")
            return    
    
    # 1. Load and preprocess data
    df = pd.DataFrame(getData())
    df_recent = filterByTime(df)
    df_recent["clean_des"] = df_recent["description"].apply(clean_html)
    
    # 2. Semantic filtering
    df_recent["text"] = df_recent["title"] + " " + df_recent["clean_des"]
    df_recent["semantic_score"] = df_recent["text"].apply(semantic_score)
    df_semantic = df_recent[df_recent["semantic_score"] > 0.35] # keep AI-relevant articles
    
    # 3. LLM-based filtering (refinement)
    titles = df_semantic["title"].tolist()
    df_filtered = llmFilter(df_semantic, titles, llm)

    # 4. Fetch full article content
    new_content = df_filtered["link"].apply(get_article_text)
    df_filtered["content"] = df_filtered["content"].where(
        new_content == "",  # keep old when new is empty
        new_content         # otherwise use new
    )
    df_filtered["content"] = df_filtered["content"].apply(normalize_content)
    df_final = df_filtered[df_filtered["content"].str.len() > 200] # Remove low-quality / empty articles
    
    # 5. Prepare articles for LLM
    articles = []
    for _, row in df_final.iterrows():
        articles.append({
            "title": row["title"],
            "content": row["content"],
            "author": row["author"],
            "link": row["link"]
        })

    # 6. Generate summaries
    summaries = summarize_articles(articles, llm)
    if not summaries:
        st.error("No valid summaries generated.")
        return
    
    # 7. Generate insights
    insights = get_insights(summaries, llm)
    if not summaries:
        st.error("Failed to generate insights")
        return

    # 8. Generate audio brief
    audio = text_to_speech(insights["daily_summary"])

    # 9. Render UI
    display_app(insights, summaries, audio)

if __name__ == "__main__":
    main()