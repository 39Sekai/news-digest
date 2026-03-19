#!/usr/bin/env python3
"""Convert OPML file to news-digest JSON format"""

import xml.etree.ElementTree as ET
import json
import re
from pathlib import Path

def opml_to_json(opml_path, output_path):
    """Convert OPML feed list to JSON format."""
    
    tree = ET.parse(opml_path)
    root = tree.getroot()
    
    feeds = []
    
    # Map categories from OPML to our categories
    category_map = {
        'AI/': 'AI',
        'TECH/': 'tech',
        'CS/': 'tech',
        'ROBOTICS/': 'tech',
        'SECURITY/': 'tech',
        'GENERAL/': 'general',
        'EVENTS/': 'events',
        'ALERT/': 'alerts',
        'SPACE/': 'space',
        'UNIVERSITIES/': 'education',
        'SOCIETY/': 'society',
        'YouTube subscriptions': 'video',
    }
    
    def get_reliability(feed_name, category):
        """Assign reliability based on source type."""
        # High reliability sources
        high_reliability = [
            'MIT', 'Stanford', 'OpenAI', 'Google', 'DeepMind', 'NVIDIA',
            'arxiv', 'IEEE', 'Nature', 'Science', 'Hugging Face',
            'TechCrunch', 'Wired', 'Ars Technica', 'The Verge'
        ]
        
        # Medium reliability
        medium_reliability = [
            'Reddit', 'Twitter', 'YouTube', 'Blog'
        ]
        
        name_lower = feed_name.lower()
        
        for source in high_reliability:
            if source.lower() in name_lower:
                return 0.9
        
        for source in medium_reliability:
            if source.lower() in name_lower:
                return 0.7
        
        # Default based on category
        if category in ['AI', 'tech', 'education']:
            return 0.85
        elif category in ['events', 'alerts']:
            return 0.8
        else:
            return 0.75
    
    def process_outline(outline, current_category='general'):
        """Process an outline element recursively."""
        
        text = outline.get('text', '')
        xmlUrl = outline.get('xmlUrl', '')
        
        # If it has children, it's a category
        children = list(outline)
        
        if children:
            # This is a category folder
            category = category_map.get(text, text.lower().rstrip('/'))
            for child in children:
                process_outline(child, category)
        elif xmlUrl:
            # This is a feed
            title = outline.get('title', text) or text
            
            # Skip certain problematic feeds
            if 'kill-the-newsletter' in xmlUrl and 'the-batch' not in title.lower():
                # Skip kill-the-newsletter feeds except The Batch
                pass
            elif 'twitter.com' in xmlUrl or 'rsshub.app/twitter' in xmlUrl:
                # Skip Twitter feeds (often broken)
                pass
            else:
                reliability = get_reliability(title, current_category)
                
                feeds.append({
                    'url': xmlUrl,
                    'name': title,
                    'category': current_category,
                    'reliability': reliability,
                    'enabled': True
                })
    
    # Process all outlines in body
    body = root.find('body')
    if body is not None:
        for outline in body:
            process_outline(outline)
    
    # Write output
    output = {'feeds': feeds}
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    return len(feeds)

if __name__ == '__main__':
    opml_file = '/home/krisspy/.openclaw-nemesis/workspace/Inoreader Feeds 20260306.xml'
    output_file = '/home/krisspy/.openclaw-nemesis/workspace/news-digest/config/feeds.json'
    
    count = opml_to_json(opml_file, output_file)
    print(f"✅ Converted {count} feeds from OPML to JSON")
    print(f"📁 Output: {output_file}")
