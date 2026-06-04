# 🤖 AI 每日速递

每天自动聚合全球 AI 最新消息、研究论文和社区动态。

🌐 **在线地址**: https://philokun.github.io/ai-news-daily/

---

## 📡 数据来源

| 源 | 类型 | 内容 |
|----|------|------|
| [Hacker News](https://news.ycombinator.com/) | 💬 社区 | AI 相关的热门讨论和文章 |
| [ArXiv](https://arxiv.org/) | 📄 研究 | cs.AI / cs.LG / cs.CL / cs.CV 最新论文 |
| [TechCrunch AI](https://techcrunch.com/category/artificial-intelligence/) | 📰 资讯 | AI 行业新闻和创业动态 |
| [OpenAI Blog](https://openai.com/blog/) | 🤖 官方 | OpenAI 官方发布和公告 |
| [VentureBeat AI](https://venturebeat.com/category/ai/) | 📰 资讯 | AI 行业深度报道 |
| [Wired AI](https://www.wired.com/tag/artificial-intelligence/) | 🔮 科技 | AI 科技文化 |
| [MIT Tech Review AI](https://www.technologyreview.com/topic/artificial-intelligence/) | 🎓 深度 | AI 前沿技术分析 |
| [Google AI Blog](https://blog.google/technology/ai/) | 🔬 官方 | Google AI 研究发布 |
| [InfoQ](https://www.infoq.cn/) | 📖 中文 | 中文技术社区 AI 内容 |
| [开源中国](https://www.oschina.net/) | 🇨🇳 中文 | 中文开源技术新闻 |

## 🚀 自动更新

- **GitHub Actions** — 每天 UTC 07:00（北京时间 15:00）自动抓取并部署
- **手动触发** — 在 Actions 页面点 `Run workflow` 即可强制刷新
- **本地定时** — Hermes Agent 每天早上 8:00 本地抓取并推送

## 🛠 本地运行

```bash
# 安装依赖
pip install requests feedparser lxml

# 抓取新闻并生成页面
python fetch_news.py

# 本地预览
python -m http.server 8000
# 浏览器打开 http://localhost:8000
```

## 📁 项目结构

```
├── fetch_news.py          # 新闻采集脚本
├── index.html             # 生成的网站（自动部署）
├── news_data.json         # 新闻数据缓存
├── vercel.json            # Vercel 部署配置（备用）
└── .github/workflows/
    └── daily.yml          # GitHub Actions 自动更新
```

## 🎨 页面功能

- 深色主题 + 渐变标题
- 按分类筛选：全部 / 资讯 / 研究 / 社区
- 自适应网格布局（桌面 + 移动端）
- 来源标签 + 相对时间（X小时前 / X天前）

## 📝 License

MIT
