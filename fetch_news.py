#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI News Fetcher — 每天自动采集 AI 最新消息
数据源: Hacker News, ArXiv, TechCrunch, OpenAI
"""

import json
import os
import re
import html as html_mod
import sys
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import requests


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "news_data.json")
HTML_FILE = os.path.join(BASE_DIR, "index.html")
MAX_ITEMS = 60
REQUEST_TIMEOUT = 8  # seconds per request


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ── Data Sources ─────────────────────────────────────

def fetch_hn_ai_stories():
    """Hacker News Algolia API"""
    log("🌐 HN 社区...")
    stories = []
    queries = [
        '"artificial intelligence"',
        '"machine learning"',
        '"large language model"',
        '"deep learning"',
        '"AI"',
    ]
    seen = set()
    sess = requests.Session()
    for query in queries:
        try:
            url = (
                f"https://hn.algolia.com/api/v1/search?"
                f"query={quote_plus(query)}&hitsPerPage=20&tags=story"
            )
            resp = sess.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for hit in data.get("hits", []):
                sid = hit.get("objectID")
                if sid in seen:
                    continue
                seen.add(sid)
                stories.append({
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                    "source": "Hacker News",
                    "summary": f"⭐ {hit.get('points',0)} points | by {hit.get('author','?')} | 💬 {hit.get('num_comments',0)} comments",
                    "published": hit.get("created_at", ""),
                    "category": "community",
                })
        except Exception as e:
            log(f"  ⚠ HN '{query}': {type(e).__name__}")
    log(f"  ✓ {len(stories)} 条")
    return stories


def fetch_arxiv_papers():
    """ArXiv RSS"""
    log("📄 ArXiv 论文...")
    papers = []
    categories = {
        "cs.AI": "AI",
        "cs.LG": "Machine Learning",
        "cs.CL": "NLP",
        "cs.CV": "Computer Vision",
    }
    seen = set()
    sess = requests.Session()
    for cat_id, cat_name in categories.items():
        try:
            url = f"https://rss.arxiv.org/rss/{cat_id}"
            resp = sess.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:8]:
                title = entry.get("title", "").replace("\n", " ").strip()
                key = title.lower()[:80]
                if key in seen:
                    continue
                seen.add(key)
                summary = entry.get("summary", "")[:300].replace("\n", " ").strip()
                m = re.search(r'Authors?:?\s*(.*?)(?:\.|$)', summary)
                authors = m.group(1).strip() if m else ""
                papers.append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "source": f"ArXiv ({cat_name})",
                    "summary": f"👤 {authors}" if authors else summary[:200],
                    "published": entry.get("published", ""),
                    "category": "research",
                })
        except Exception as e:
            log(f"  ⚠ ArXiv {cat_id}: {type(e).__name__}")
    log(f"  ✓ {len(papers)} 条")
    return papers


def fetch_rss_feed(url, source_name, category="news", max_items=15):
    """Generic RSS fetcher"""
    items = []
    try:
        sess = requests.Session()
        resp = sess.get(url, timeout=REQUEST_TIMEOUT,
                        headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            log(f"  ⚠ {source_name}: HTTP {resp.status_code}")
            return items
        feed = feedparser.parse(resp.text)
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "")[:250].replace("\n", " ").strip()
            summary = re.sub(r'<[^>]+>', '', summary)
            items.append({
                "title": title,
                "url": entry.get("link", ""),
                "source": source_name,
                "summary": summary,
                "published": entry.get("published", ""),
                "category": category,
            })
    except Exception as e:
        log(f"  ⚠ {source_name}: {type(e).__name__}")
    return items


def fetch_techcrunch():
    log("📰 TechCrunch...")
    items = fetch_rss_feed(
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "TechCrunch AI", "news")
    log(f"  ✓ {len(items)} 条")
    return items


def fetch_openai():
    log("🤖 OpenAI...")
    items = fetch_rss_feed(
        "https://openai.com/blog/rss.xml",
        "OpenAI", "news")
    log(f"  ✓ {len(items)} 条")
    return items


# ── HTML Renderer ────────────────────────────────────

def time_ago(published_str):
    if not published_str:
        return ""
    for fmt in [
        "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
        "%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(published_str, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            break
        except ValueError:
            continue
    else:
        return published_str[:10]

    diff = datetime.now(timezone.utc) - dt
    secs = int(diff.total_seconds())
    if secs < 0:
        return "刚刚"
    if secs < 60:
        return f"{secs}秒前"
    mins = secs // 60
    if mins < 60:
        return f"{mins}分钟前"
    hrs = mins // 60
    if hrs < 24:
        return f"{hrs}小时前"
    days = hrs // 24
    if days < 30:
        return f"{days}天前"
    return f"{days // 30}个月前"


def generate_html(all_news):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cards = ""
    for item in all_news:
        ago = time_ago(item["published"])
        cat = item.get("category", "news")
        te = html_mod.escape(item["title"])
        se = html_mod.escape(item["summary"][:200])
        ue = html_mod.escape(item["url"])
        src = html_mod.escape(item["source"])

        # Source icon & color
        icon_map = {"Hacker News": "🔶", "ArXiv": "📄", "TechCrunch": "📰", "OpenAI": "🤖"}
        col_map = {"research": "#8b5cf6", "news": "#3b82f6", "community": "#f59e0b"}
        icon = next((v for k, v in icon_map.items() if k in item["source"]), "📡")
        color = col_map.get(cat, "#6b7280")
        cat_zh = {"research": "研究", "news": "资讯", "community": "社区"}.get(cat, cat)

        cards += f"""
        <a href="{ue}" target="_blank" rel="noopener" class="news-card" data-category="{cat}">
            <div class="card-header">
                <span class="source-badge" style="background:{color}22; color:{color}">{icon} {src}</span>
                <span class="time">{ago}</span>
            </div>
            <h3 class="card-title">{te}</h3>
            <p class="card-summary">{se}</p>
            <div class="card-footer">
                <span class="category-tag" style="background:{color}">{cat_zh}</span>
            </div>
        </a>"""

    n_news = sum(1 for n in all_news if n["category"] == "news")
    n_research = sum(1 for n in all_news if n["category"] == "research")
    n_community = sum(1 for n in all_news if n["category"] == "community")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 每日速递</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
    background: #0a0a0f; color: #e2e2e8; min-height: 100vh;
  }}
  .header {{
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1040 50%, #0f0f1a 100%);
    border-bottom: 1px solid #1e1e2e; padding: 40px 20px; text-align: center;
  }}
  .header h1 {{
    font-size: 2.5em; font-weight: 800;
    background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 8px;
  }}
  .header p {{ color: #888; font-size: 0.95em; }}
  .header .update-time {{ color: #666; font-size: 0.85em; margin-top: 6px; }}
  .controls {{
    display: flex; gap: 10px; justify-content: center;
    padding: 20px; flex-wrap: wrap; border-bottom: 1px solid #14141f;
  }}
  .filter-btn {{
    padding: 8px 20px; border: 1px solid #2a2a3e; border-radius: 20px;
    background: transparent; color: #aaa; cursor: pointer;
    font-size: 0.9em; transition: all 0.2s;
  }}
  .filter-btn:hover {{ border-color: #6366f1; color: #e2e2e8; }}
  .filter-btn.active {{
    background: linear-gradient(135deg, #6366f133, #a855f733);
    border-color: #818cf8; color: #c4b5fd;
  }}
  .news-grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 16px; padding: 20px; max-width: 1400px; margin: 0 auto;
  }}
  .news-card {{
    display: block; background: #11111a; border: 1px solid #1e1e2e;
    border-radius: 12px; padding: 20px; text-decoration: none; color: inherit;
    transition: all 0.25s ease; position: relative; overflow: hidden;
  }}
  .news-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, #6366f1, transparent);
    opacity: 0; transition: opacity 0.3s;
  }}
  .news-card:hover {{
    border-color: #6366f1; transform: translateY(-3px);
    box-shadow: 0 8px 30px rgba(99, 102, 241, 0.1);
  }}
  .news-card:hover::before {{ opacity: 1; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
  .source-badge {{ font-size: 0.78em; padding: 3px 10px; border-radius: 8px; }}
  .time {{ font-size: 0.78em; color: #666; }}
  .card-title {{
    font-size: 1.05em; font-weight: 600; line-height: 1.4; margin-bottom: 8px; color: #f0f0f8;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }}
  .card-summary {{
    font-size: 0.85em; line-height: 1.5; color: #888;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
  }}
  .card-footer {{ margin-top: 12px; display: flex; justify-content: flex-end; }}
  .category-tag {{ font-size: 0.72em; padding: 2px 10px; border-radius: 6px; color: white; }}
  .stats {{
    display: flex; gap: 20px; justify-content: center;
    padding: 10px 20px; font-size: 0.85em; color: #666;
  }}
  footer {{
    text-align: center; padding: 30px; color: #444; font-size: 0.85em;
    border-top: 1px solid #14141f;
  }}
  @media (max-width: 640px) {{
    .news-grid {{ grid-template-columns: 1fr; }}
    .header h1 {{ font-size: 1.8em; }}
  }}
</style>
</head>
<body>
<div class="header">
  <h1>🤖 AI 每日速递</h1>
  <p>每天自动聚合全球 AI 最新消息 · 研究 · 社区动态</p>
  <div class="update-time">🔄 最后更新: {now_str}</div>
</div>

<div class="controls">
  <button class="filter-btn active" data-filter="all">🌐 全部</button>
  <button class="filter-btn" data-filter="news">📰 资讯</button>
  <button class="filter-btn" data-filter="research">📚 研究</button>
  <button class="filter-btn" data-filter="community">💬 社区</button>
</div>

<div class="news-grid" id="newsGrid">
  {cards}
</div>

<div class="stats">
  <span>📊 共 {len(all_news)} 条</span>
  <span>📰 {n_news} 资讯</span>
  <span>📚 {n_research} 研究</span>
  <span>💬 {n_community} 社区</span>
</div>

<footer>
  Powered by Hermes Agent · 来源: Hacker News, ArXiv, TechCrunch, OpenAI
</footer>

<script>
  document.querySelectorAll('.filter-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelector('.filter-btn.active').classList.remove('active');
      btn.classList.add('active');
      const f = btn.dataset.filter;
      document.querySelectorAll('.news-card').forEach(c => {{
        c.style.display = (f === 'all' || c.dataset.category === f) ? 'block' : 'none';
      }});
    }});
  }});
</script>
</body>
</html>"""
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"✅ HTML 已生成: {HTML_FILE}")


# ── Main ─────────────────────────────────────────────

def main():
    log(f"{'='*40}")
    log("🚀 AI 新闻采集开始")
    all_news = []

    fetchers = [
        fetch_hn_ai_stories,
        fetch_arxiv_papers,
        fetch_techcrunch,
        fetch_openai,
    ]

    for fetcher in fetchers:
        try:
            all_news.extend(fetcher())
        except Exception as e:
            log(f"  ❌ {fetcher.__name__}: {e}")

    # Dedup
    seen = set()
    deduped = []
    for item in all_news:
        key = item["title"].lower().strip()[:60]
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    deduped.sort(key=lambda x: x.get("published", ""), reverse=True)
    deduped = deduped[:MAX_ITEMS]

    log(f"📊 原始 {len(all_news)} 条 → 去重后 {len(deduped)} 条")

    # Save JSON
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "total": len(deduped), "items": deduped},
                  f, ensure_ascii=False, indent=2)

    generate_html(deduped)
    log("🎉 完成!")


if __name__ == "__main__":
    main()
