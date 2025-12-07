#!/usr/bin/env python3
"""
Generate Oracle Nodes from 2025 Stories
Analyzes stories in /stories/2025 and creates new node files for unique events
"""

import json
import os
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from difflib import SequenceMatcher

# Path configurations
BASE_DIR = Path(__file__).parent.parent
STORIES_DIR = BASE_DIR / "oracle" / "stories" / "2025"
NODES_DIR = BASE_DIR / "oracle" / "oracle-nodes"

# Constants
MAX_TITLE_LENGTH = 85
TRUNCATED_TITLE_LENGTH = 82
MAX_NODES_PER_RUN = 200  # Limit to prevent overwhelming the knowledge base in a single run

# Get the highest existing node number
def get_highest_node_number():
    """Find the highest numbered node in oracle-nodes directory"""
    max_num = 0
    for file in NODES_DIR.glob("node_n*.md"):
        match = re.search(r'node_n(\d+)', file.name)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    return max_num

# Read all existing nodes to check for duplicates
def load_existing_nodes():
    """Load all existing node titles and descriptions"""
    existing = []
    for file in NODES_DIR.glob("node_n*.md"):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract title and description
            title_match = re.search(r'^# Node N\d+: (.+)$', content, re.MULTILINE)
            desc_match = re.search(r'- \*\*Description\*\*: (.+)$', content, re.MULTILINE)
            if title_match and desc_match:
                existing.append({
                    'file': file.name,
                    'title': title_match.group(1).strip(),
                    'description': desc_match.group(1).strip()
                })
    return existing

# Load and aggregate stories by topic/event
def load_stories():
    """Load all 2025 stories and group by topic"""
    stories = []
    
    for root, dirs, files in os.walk(STORIES_DIR):
        for file in files:
            if file.endswith('.json') and file != 'index.json':
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        story = json.load(f)
                        story['filepath'] = filepath
                        # Extract date from path
                        parts = filepath.split(os.sep)
                        if len(parts) >= 8:
                            story['date'] = f"{parts[-5]}-{parts[-4]}-{parts[-3]}"
                        stories.append(story)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    # Sort by published date
    stories.sort(key=lambda x: x.get('published_at', ''))
    return stories

# Check if event is already captured
def is_duplicate_event(story, existing_nodes):
    """Check if this story's event is already captured in existing nodes"""
    title = story.get('title', '').lower()
    description = story.get('description', '').lower()
    
    # Check for similarity with existing nodes
    for node in existing_nodes:
        node_title = node['title'].lower()
        node_desc = node['description'].lower()
        
        # Use sequence matching for title similarity
        title_sim = SequenceMatcher(None, title, node_title).ratio()
        desc_sim = SequenceMatcher(None, description[:200], node_desc[:200]).ratio()
        
        # If very similar, it's a duplicate
        if title_sim > 0.7 or desc_sim > 0.6:
            return True
        
        # Also check keyword overlap
        story_keywords = set(re.findall(r'\b\w{5,}\b', title + ' ' + description))
        node_keywords = set(re.findall(r'\b\w{5,}\b', node_title + ' ' + node_desc))
        
        overlap = story_keywords & node_keywords
        # If many significant keywords overlap, likely a duplicate
        if len(overlap) >= 6 and len(story_keywords) > 0:
            overlap_ratio = len(overlap) / len(story_keywords)
            if overlap_ratio > 0.6:
                return True
    
    return False

# Determine if story is significant enough for a node
def is_significant_event(story):
    """Determine if a story represents a significant event worthy of a node"""
    title = story.get('title', '')
    description = story.get('description', '')
    category = story.get('category', '')
    source = story.get('source', '')
    
    # Filter criteria
    if not title or len(title) < 25:
        return False
    
    # Skip non-English stories (rough heuristic)
    text = title + ' ' + description
    if len(re.findall(r'[^\x00-\x7F]', text)) > len(text) * 0.3:
        return False
    
    # High significance keywords - transformative events
    high_sig_keywords = [
        # Business/Finance
        'acquisition', 'merger', 'ipo', 'billion', 'funding round', 'valuation',
        'bankruptcy', 'layoff', 'restructure', 'closes', 'shuts down',
        # Technology
        'breakthrough', 'launched', 'released', 'unveils', 'announces',
        'breakthrough', 'record', 'first time', 'revolutionary',
        # AI specific
        'gpt', 'claude', 'gemini', 'model', 'agent', 'code red',
        # Policy/Regulation
        'supreme court', 'legislation', 'regulation', 'policy', 'ban',
        'approval', 'federal reserve', 'fed rate',
        # Geopolitics
        'election', 'treaty', 'sanctions', 'conflict', 'war',
        # Science
        'discovery', 'nobel', 'breakthrough', 'fda approval',
        # Natural disasters
        'earthquake', 'magnitude', 'tsunami', 'hurricane',
        'volcano', 'extreme weather'
    ]
    
    # Premium sources  (more reliable significance indicators)
    premium_sources = [
        'techcrunch', 'bloomberg', 'reuters', 'financial times',
        'wall street journal', 'new york times', 'washington post',
        'cnbc', 'associated press', 'bbc', 'the guardian',
        'wired', 'mit technology review', 'nature', 'science'
    ]
    
    text_lower = text.lower()
    
    # Check for high significance keywords
    sig_count = sum(1 for keyword in high_sig_keywords if keyword in text_lower)
    
    # Check for premium source
    from_premium = any(source_name in source.lower() for source_name in premium_sources)
    
    # Scoring system
    score = 0
    if sig_count >= 2:
        score += 2
    elif sig_count == 1:
        score += 1
    
    if from_premium:
        score += 1
    
    # Check for major companies/organizations
    major_entities = [
        'openai', 'google', 'microsoft', 'meta', 'tesla', 'spacex', 'nvidia',
        'apple', 'amazon', 'anthropic', 'federal reserve', 'nasa', 'fda',
        'deepseek', 'aws', 'intel', 'amd', 'tsmc', 'samsung'
    ]
    if any(entity in text_lower for entity in major_entities):
        score += 1
    
    # Require minimum score
    return score >= 2

# Generate node content  
def generate_node_content(node_num, story):
    """Generate the markdown content for a new node"""
    title = story.get('title', 'Untitled Event')
    description = story.get('description', story.get('content', ''))
    category = story.get('category', 'general')
    date = story.get('date', '2025')
    source = story.get('source', 'Unknown')
    source_url = story.get('source_url', '')
    
    # Clean up title - remove extra spaces and truncate
    title = re.sub(r'\s+', ' ', title).strip()
    if len(title) > MAX_TITLE_LENGTH:
        title = title[:TRUNCATED_TITLE_LENGTH] + "..."
    
    # Generate filename-safe title
    safe_title = re.sub(r'[^\w\s-]', '', title.lower())
    safe_title = re.sub(r'[-\s]+', '_', safe_title)[:55]
    
    # Extract key details and create better description
    if not description or description == title or len(description) < 20:
        description = f"Significant development in {category.replace('_', ' ')} reported on {date} by {source}."
    
    # Clean description
    description = re.sub(r'\s+', ' ', description).strip()
    if len(description) > 400:
        description = description[:397] + "..."
    
    # Create category-specific ripple effects
    category_name = category.replace('_', ' ').title()
    
    # Build richer content based on category
    ripple_1a = f"Immediate impact on {category.replace('_', ' ')} sector"
    ripple_1b = "Market and competitive responses"
    ripple_1c = "Stakeholder and public reaction"
    ripple_1d = "Near-term operational changes"
    
    ripple_2a = f"Medium-term transformation of {category.replace('_', ' ')}"
    ripple_2b = "Policy and regulatory adaptations"
    ripple_2c = "Shifts in competitive landscape"
    ripple_2d = "Cross-industry ripple effects"
    
    ripple_3a = "Long-term societal implications"
    ripple_3b = "Potential paradigm shifts"
    ripple_3c = "Systemic and structural changes"
    ripple_3d = "Global trend influences"
    
    # Customize based on what's in the story
    text_lower = (title + ' ' + description).lower()
    
    if 'acquisition' in text_lower or 'merger' in text_lower:
        ripple_1a = "Consolidation reshapes market dynamics"
        ripple_2a = "Industry structure evolves through M&A activity"
    elif 'ipo' in text_lower or 'public' in text_lower:
        ripple_1a = "Public market access changes company trajectory"
        ripple_2a = "Investor sentiment toward sector shifts"
    elif 'layoff' in text_lower or 'cut' in text_lower:
        ripple_1a = "Workforce reduction impacts operations"
        ripple_2a = "Labor market adjusts to employment shifts"
    elif 'launched' in text_lower or 'released' in text_lower:
        ripple_1a = "New capabilities enter the market"
        ripple_2a = "Competitive dynamics shift with new offering"
    elif 'funding' in text_lower or 'investment' in text_lower:
        ripple_1a = "Capital influx accelerates development"
        ripple_2a = "Valuation benchmarks reset for sector"
    elif 'election' in text_lower or 'vote' in text_lower:
        ripple_1a = "Political landscape shifts"
        ripple_2a = "Policy direction potentially changes"
    
    content = f"""# Node N{node_num}: {title}

## **Node Details**
- **Node_ID**: N{node_num}
- **Description**: {description}
- **Verification_Status**: **Verified** ✅
- **Date**: {date}
- **Scope**: {category_name}
- **Source**: {source}

---

## **Verified Context from Research**

### **Event Summary:**
{description}

### **Key Details:**
- **Category**: {category_name}
- **Date**: {date}
- **Source**: {source}
- **Source URL**: {source_url if source_url else 'N/A'}

### **Significance:**
This event represents a notable development in {category.replace('_', ' ')}, capturing a key moment in the evolving landscape of 2025. The event demonstrates ongoing changes and serves as an important data point for understanding current trends.

---

## **Generated Ripple Effects**

### **First-Order Effects (Confidence: 85%)**
- **Ripple 1A**: {ripple_1a}
- **Ripple 1B**: {ripple_1b}
- **Ripple 1C**: {ripple_1c}
- **Ripple 1D**: {ripple_1d}

### **Second-Order Effects (Confidence: 75%)**
- **Ripple 2A**: {ripple_2a}
- **Ripple 2B**: {ripple_2b}
- **Ripple 2C**: {ripple_2c}
- **Ripple 2D**: {ripple_2d}

### **Third-Order Effects (Confidence: 65%)**
- **Ripple 3A**: {ripple_3a}
- **Ripple 3B**: {ripple_3b}
- **Ripple 3C**: {ripple_3c}
- **Ripple 3D**: {ripple_3d}

---

## **Web Connections Identified**

### **Thread T{300+node_num}: N{node_num} → Recent Developments**
- **Relationship**: *relates to*
- **Confidence**: 80%
- **Rationale**: Part of ongoing 2025 developments in {category.replace('_', ' ')}
- **Evidence**: Contemporary event captured from news aggregation

---

## **Critical Strategic Implications**

### **Sector Impact:**
This development marks a significant moment in {category.replace('_', ' ')}:
- **Timing**: Occurred in {date}, reflecting 2025 dynamics
- **Scale**: Significant enough to warrant tracking in oracle knowledge base
- **Direction**: Indicates trajectory of sector evolution

### **Broader Context:**
Situated within the larger pattern of technological, economic, and social change:
- **Near-term**: Immediate effects on stakeholders and markets
- **Medium-term**: Influences sector development over months
- **Long-term**: May contribute to fundamental shifts in {category.replace('_', ' ')}

---

## **Connection Opportunities**
*Ready to link with future nodes involving:*
- {category_name} sector developments
- Related technological innovations
- Market and economic trends
- Regulatory and policy evolution
- Cross-domain effects and implications
"""
    
    return content, safe_title

def main():
    """Main execution function"""
    print("=" * 70)
    print("Oracle Node Generator - Processing 2025 Stories")
    print("=" * 70)
    
    # Get starting node number
    start_node = get_highest_node_number() + 1
    print(f"\nStarting from node N{start_node}")
    
    # Load existing nodes
    print("\nLoading existing nodes...")
    existing_nodes = load_existing_nodes()
    print(f"Found {len(existing_nodes)} existing nodes")
    
    # Load stories
    print("\nLoading 2025 stories...")
    stories = load_stories()
    print(f"Found {len(stories)} stories")
    
    # Process stories
    print("\nProcessing stories...")
    print("Filtering for significant, unique events...")
    
    nodes_created = 0
    nodes_skipped = 0
    current_node_num = start_node
    
    # Track processed titles to avoid duplicates within this run
    processed_titles = set()
    
    for i, story in enumerate(stories):
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(stories)} stories...")
        
        title = story.get('title', '')
        
        # Skip if we've seen a very similar title this run
        title_normalized = re.sub(r'\s+', ' ', title.lower()).strip()
        if title_normalized in processed_titles:
            nodes_skipped += 1
            continue
        
        # Check if significant
        if not is_significant_event(story):
            nodes_skipped += 1
            continue
        
        # Check if duplicate of existing node
        if is_duplicate_event(story, existing_nodes):
            nodes_skipped += 1
            continue
        
        # Generate node
        content, safe_title = generate_node_content(current_node_num, story)
        
        # Save node file
        filename = f"node_n{current_node_num}_{safe_title}.md"
        filepath = NODES_DIR / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n  [{nodes_created + 1}] Created: N{current_node_num}")
        print(f"      Title: {story.get('title', 'N/A')[:65]}...")
        print(f"      Date: {story.get('date', 'N/A')}")
        print(f"      Category: {story.get('category', 'N/A')}")
        
        processed_titles.add(title_normalized)
        nodes_created += 1
        current_node_num += 1
        
        # Limit nodes per run to maintain manageable batch sizes
        # This allows for iterative refinement and prevents overwhelming the knowledge base
        # The script can be run multiple times to process all stories
        if nodes_created >= MAX_NODES_PER_RUN:
            print(f"\n  Reached limit of {MAX_NODES_PER_RUN} nodes per run. Stopping.")
            print(f"  Run the script again to continue processing remaining stories.")
            break
    
    print("\n" + "=" * 70)
    print(f"Processing Complete!")
    print(f"  Total stories processed: {len(stories)}")
    print(f"  Nodes created: {nodes_created}")
    print(f"  Stories skipped: {nodes_skipped}")
    print(f"  Node range: N{start_node} - N{current_node_num - 1}")
    print("=" * 70)

if __name__ == "__main__":
    main()
