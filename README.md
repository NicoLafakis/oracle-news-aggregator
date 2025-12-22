# 🔮 Oracle News Aggregator

A GitHub Actions-powered system that automatically collects, deduplicates, and catalogs global news events to build a comprehensive knowledge base for AI models.

## 🎯 Purpose

This system serves as an **oracle** — a continuously updated repository of global events that AI models can reference for up-to-date world knowledge. It uses a curated set of **100 keyword searches** designed to track the signals that actually matter for understanding the world.

## 📊 The 100 Searches

The oracle monitors 14 categories with strategically crafted search queries:

| Category | Searches | Focus |
|----------|----------|-------|
| **AI & Machine Intelligence** | 12 | Model releases, inference costs, lab dynamics, enterprise adoption, safety research |
| **Robotics & Physical Automation** | 6 | Humanoid robots, warehouse automation, autonomous vehicles, manipulation |
| **Semiconductors & Compute** | 6 | Fab construction, GPU supply, export controls, AI chip startups |
| **Energy & Resources** | 8 | Solar/battery costs, nuclear revival, grid infrastructure, critical minerals |
| **Macroeconomics & Finance** | 12 | Fed decisions, inflation, recession indicators, VC funding, crypto regulation |
| **Geopolitics & Security** | 12 | US-China, Taiwan, Russia-NATO, Middle East, cyber warfare, sanctions |
| **Politics & Governance** | 8 | Elections, legislation, Supreme Court, protests, executive orders |
| **Labor & Employment** | 6 | Layoffs, automation displacement, unions, wage growth, remote work |
| **Demographics & Migration** | 5 | Birth rates, immigration, aging, urbanization, brain drain |
| **Health & Biotech** | 7 | Pandemics, FDA approvals, longevity research, gene therapy, mental health |
| **Climate & Environment** | 6 | Extreme weather, climate policy, drought, food security, sea level rise |
| **Space & Frontier** | 4 | SpaceX, satellite constellations, commercial space stations |
| **Media, Information & Trust** | 5 | Misinformation, platform policies, deepfakes, journalism |
| **Culture & Social Dynamics** | 5 | Consumer sentiment, social movements, generational trends |

**Total: 102 searches** (uses full NewsAPI daily quota of 100 requests)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              GitHub Actions (News Aggregator)                │
│                  Runs daily at 00:00 UTC                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    News Aggregator                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ NewsAPI │ │  GDELT  │ │  USGS   │ │   RSS   │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
│       └───────────┴───────────┴───────────┘                 │
│                      │                                       │
│                      ▼                                       │
│            ┌─────────────────┐                              │
│            │ Deduplication   │ ← manifest.json              │
│            │ Engine          │   (hashes + titles)          │
│            └────────┬────────┘                              │
│                     │                                        │
│                     ▼                                        │
│            ┌─────────────────┐                              │
│            │ Story Storage   │ → oracle/stories/YYYY/MM/DD  │
│            └─────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Git Commit & Push                          │
│              "📰 Oracle Update: 2024-12-05"                  │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│           GitHub Actions (Node Generator)                    │
│            Runs daily at 12:00 PM EST (17:00 UTC)           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Node Generator                            │
│  - Processes latest articles from oracle/stories/           │
│  - Filters for significant events                           │
│  - Deduplicates against existing nodes                      │
│  - Generates up to 200 new oracle nodes                     │
│  → oracle/oracle-nodes/node_nXXX_*.md                       │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Git Commit & Push                          │
│        "Daily Node Generation: 2024-12-05 - 25 nodes"       │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Repository Structure

```
oracle-news-aggregator/
├── .github/
│   └── workflows/
│       └── oracle-aggregator.yml    # GitHub Action (runs daily)
├── scripts/
│   └── news_aggregator.py           # Main aggregation script
├── oracle/
│   ├── manifest.json                # Deduplication tracking
│   └── stories/
│       └── YYYY/
│           └── MM/
│               └── DD/
│                   ├── index.json   # Daily summary
│                   ├── ai_machine_intelligence/
│                   ├── robotics_automation/
│                   ├── semiconductors_compute/
│                   ├── energy_resources/
│                   ├── macroeconomics_finance/
│                   ├── geopolitics_security/
│                   ├── politics_governance/
│                   ├── labor_employment/
│                   ├── demographics_migration/
│                   ├── health_biotech/
│                   ├── climate_environment/
│                   ├── space_frontier/
│                   ├── media_information_trust/
│                   ├── culture_social/
│                   └── geological_events/
├── logs/
│   └── run_summary.json             # Latest run statistics
├── config/
│   └── config.example.yaml          # The 100 searches reference
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### 1. Fork or Clone This Repository

```bash
git clone https://github.com/yourusername/oracle-news-aggregator.git
cd oracle-news-aggregator
```

### 2. Configure API Keys (Optional but Recommended)

Go to your repository's **Settings → Secrets and Variables → Actions** and add:

| Secret Name | Required | Description |
|------------|----------|-------------|
| `NEWS_API_KEY` | Optional | API key from [newsapi.org](https://newsapi.org) |

> **⚠️ NewsAPI Free Tier Limitations:**
> - 100 requests/day (our script uses ~7-10 per run)
> - Articles delayed by 24 hours
> - **For development/testing ONLY** - production requires paid plan ($449+/mo)
> - Content truncated to 200 characters
>
> **Good news:** GDELT, USGS, and RSS sources work without any API keys and have no limitations!

### 3. Enable GitHub Actions

1. Go to your repository's **Actions** tab
2. Click "I understand my workflows, go ahead and enable them"

### 4. Run Manually (Optional)

You can trigger the workflows manually:

**News Aggregator:**
1. Go to **Actions → Oracle News Aggregator**
2. Click **Run workflow**
3. Optionally adjust the lookback hours

**Node Generation:**
1. Go to **Actions → Daily Node Generation**
2. Click **Run workflow**
3. Optionally adjust max nodes to generate

## 🤖 Automated Workflows

The repository runs two automated GitHub Actions workflows:

### 1. Oracle News Aggregator
- **Schedule**: Daily at 00:00 UTC (midnight)
- **Purpose**: Fetches and stores news articles from multiple sources
- **Workflow File**: `.github/workflows/oracle-aggregator.yml`
- **Output**: New articles in `oracle/stories/YYYY/MM/DD/`

### 2. Daily Node Generation
- **Schedule**: Daily at 12:00 PM EST (17:00 UTC)
- **Purpose**: Converts latest fetched articles into oracle knowledge nodes
- **Workflow File**: `.github/workflows/daily-node-generation.yml`
- **Output**: New oracle nodes in `oracle/oracle-nodes/`
- **Behavior**:
  - Processes stories from the latest articles
  - Filters for significant events only
  - Deduplicates against existing nodes
  - Generates up to 200 nodes per run
  - Only commits if new nodes are created

## ⚙️ Configuration

### Adjusting Categories

Edit the `ORACLE_CATEGORIES` dictionary in `scripts/news_aggregator.py`:

```python
ORACLE_CATEGORIES = {
    "your_new_category": {
        "keywords": ["keyword1", "keyword2", "keyword3"],
        "newsapi_category": "technology",  # Optional
    },
    # ...
}
```

### Adjusting Deduplication Sensitivity

In `DeduplicationEngine.__init__()`:

```python
self.similarity_threshold = 0.75  # Lower = stricter, Higher = more lenient
```

### Adding RSS Feeds

Edit `RSSFetcher.FEEDS`:

```python
FEEDS = {
    "your_category": [
        "https://example.com/rss/feed.xml",
    ],
}
```

## 📊 Story Format

Each story is stored as a JSON file:

```json
{
  "id": "a1b2c3d4e5f6g7h8",
  "title": "Major AI Breakthrough Announced",
  "description": "Researchers unveil new...",
  "content": "Full article content...",
  "source": "TechNews",
  "source_url": "https://technews.com/article/123",
  "published_at": "2024-12-05T10:30:00+00:00",
  "fetched_at": "2024-12-05T12:00:00+00:00",
  "category": "computing_ai",
  "subcategory": null,
  "keywords": ["artificial intelligence", "machine learning", "research"],
  "location": null,
  "raw_data": { ... }
}
```

## 🤖 Using as AI Project Knowledge

### With Claude Projects

1. Clone this repository
2. In Claude, create a new Project
3. Add the `oracle/stories/` directory as Project Knowledge
4. Claude can now reference accumulated global events!

### With Custom AI Applications

```python
import json
from pathlib import Path
from datetime import datetime, timedelta

def load_recent_stories(oracle_path: str, days: int = 7) -> list[dict]:
    """Load stories from the last N days."""
    stories = []
    base = Path(oracle_path) / "oracle" / "stories"
    
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        date_path = base / date.strftime("%Y/%m/%d")
        
        if date_path.exists():
            for category_dir in date_path.iterdir():
                if category_dir.is_dir():
                    for story_file in category_dir.glob("*.json"):
                        with open(story_file) as f:
                            stories.append(json.load(f))
    
    return stories

# Use in your AI context
stories = load_recent_stories("./oracle-news-aggregator", days=30)
context = "\n".join([
    f"[{s['category']}] {s['title']}: {s['description']}"
    for s in stories
])
```

### With LangChain

```python
from langchain.document_loaders import DirectoryLoader, JSONLoader

def metadata_func(record: dict, metadata: dict) -> dict:
    metadata["category"] = record.get("category")
    metadata["source"] = record.get("source")
    metadata["published_at"] = record.get("published_at")
    return metadata

loader = DirectoryLoader(
    "./oracle/stories",
    glob="**/*.json",
    loader_cls=JSONLoader,
    loader_kwargs={
        "jq_schema": ".",
        "content_key": "content",
        "metadata_func": metadata_func,
    }
)

documents = loader.load()
# Now use with a vector store for RAG
```

## 🔍 Deduplication System

The system uses a multi-layer deduplication approach:

1. **Content Hash**: SHA-256 hash of normalized title + source
2. **Title Similarity**: SequenceMatcher with 75% threshold
3. **Manifest Tracking**: Persistent storage of all seen content

This ensures you never get the same story twice, even if:
- Multiple sources report the same event
- Headlines are slightly reworded
- The same story appears in different feeds

## 📈 Monitoring

### Via GitHub Actions

Each run generates a summary visible in the Actions tab:

```
## Oracle Aggregation Summary

**Run Date:** 2024-12-05 00:00 UTC
**Lookback Period:** 24 hours

### Stories by Category
- **computing_ai**: 45
- **geological_events**: 3
- **financial_markets**: 28
- **political**: 15

**Total New Stories:** 91
**Duplicates Filtered:** 234
```

### Via logs/run_summary.json

```json
{
  "total_fetched": 325,
  "total_new": 91,
  "duplicates_filtered": 234,
  "by_category": {
    "computing_ai": 45,
    "geological_events": 3
  },
  "by_source": {
    "TechCrunch": 12,
    "USGS": 3
  }
}
```

## 🛠️ Advanced Usage

### Manual Local Run

```bash
pip install -r requirements.txt
export NEWS_API_KEY="your-key-here"  # Optional
python scripts/news_aggregator.py --hours 48
```

### Backfill Historical Data

```bash
# Run multiple times with different date ranges
python scripts/news_aggregator.py --hours 168  # Last 7 days
```

### Custom Cron Schedule

Edit `.github/workflows/oracle-aggregator.yml`:

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
```

## 📜 Data Sources

| Source | Type | API Key Required | Coverage | Limitations |
|--------|------|------------------|----------|-------------|
| [NewsAPI](https://newsapi.org) | General News | Yes (free tier) | 150,000+ sources | **Free tier: 100 req/day, 24hr delay, DEV ONLY** |
| [GDELT](https://gdeltproject.org) | Global Events | No | Real-time global monitoring | None |
| [USGS](https://earthquake.usgs.gov) | Earthquakes | No | Worldwide seismic data | None |
| RSS Feeds | Various | No | Curated sources | None |

### NewsAPI Important Notes

The **free Developer tier** has significant limitations:

1. **100 requests/day** - Our optimized queries use ~7-10 requests per run
2. **24-hour article delay** - Articles aren't available until 24 hours after publication
3. **Development only** - Cannot be used in production without a paid plan
4. **Content truncated** - Article content limited to 200 characters

For production deployments, you'll need to either:
- Upgrade to a [paid NewsAPI plan](https://newsapi.org/pricing) ($449+/month)
- Rely on the free sources (GDELT, USGS, RSS) which have no limitations
- Consider alternatives like [NewsData.io](https://newsdata.io) or [GNews](https://gnews.io)

## 🤝 Contributing

1. Fork the repository
2. Add new sources or categories
3. Submit a pull request

## 📄 License

MIT License - Use freely for your AI oracle projects!

---

**Built for AI knowledge accumulation** 🧠📚
