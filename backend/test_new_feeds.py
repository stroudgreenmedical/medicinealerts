#!/usr/bin/env python3
"""
Test script to verify new RSS feeds for DSU and NatPSA
"""

import asyncio
import httpx
import feedparser
from datetime import datetime

# Feed configurations
FEEDS = {
    'MHRA_DSU': {
        'url': 'https://www.gov.uk/drug-safety-update.atom',
        'source': 'MHRA DSU',
        'type': 'atom',
        'category': 'Drug Safety Update'
    },
    'NHS_ENGLAND_PSA': {
        'url': 'https://www.england.nhs.uk/feed/?post_type=psa',
        'source': 'NHS England PSA', 
        'type': 'rss',
        'category': 'National Patient Safety Alert'
    }
}

async def test_feed(feed_name, feed_config):
    """Test a single feed"""
    print(f"\n{'='*60}")
    print(f"Testing: {feed_name}")
    print(f"URL: {feed_config['url']}")
    print(f"Category: {feed_config['category']}")
    print('='*60)
    
    try:
        # Fetch the feed
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(feed_config['url'])
            response.raise_for_status()
            print(f"✅ HTTP Status: {response.status_code}")
            
            # Parse the feed
            feed = feedparser.parse(response.text)
            
            if feed.bozo:
                print(f"⚠️  Feed parsing issue: {feed.bozo_exception}")
            else:
                print(f"✅ Feed parsed successfully")
            
            # Display feed info
            print(f"\nFeed Title: {feed.feed.get('title', 'N/A')}")
            print(f"Feed Description: {feed.feed.get('description', 'N/A')[:100]}...")
            print(f"Number of entries: {len(feed.entries)}")
            
            # Show first 3 entries
            print(f"\nRecent entries:")
            for i, entry in enumerate(feed.entries[:3], 1):
                print(f"\n  {i}. {entry.get('title', 'No title')}")
                pub_date = entry.get('published', entry.get('updated', 'No date'))
                print(f"     Date: {pub_date}")
                print(f"     Link: {entry.get('link', 'No link')}")
                
                # Show summary preview
                summary = entry.get('summary', 'No summary')
                if summary:
                    # Clean HTML tags for display
                    import re
                    clean_summary = re.sub('<.*?>', '', summary)[:150]
                    print(f"     Summary: {clean_summary}...")
            
            return True
            
    except httpx.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Test all feeds"""
    print("Testing New RSS/ATOM Feeds for Medicines Alerts Manager")
    print("="*60)
    
    results = {}
    for feed_name, feed_config in FEEDS.items():
        success = await test_feed(feed_name, feed_config)
        results[feed_name] = success
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for feed_name, success in results.items():
        status = "✅ Working" if success else "❌ Failed"
        print(f"{feed_name}: {status}")
    
    all_working = all(results.values())
    if all_working:
        print("\n✅ All feeds are working correctly!")
    else:
        print("\n⚠️  Some feeds have issues. Please check the errors above.")
    
    return all_working

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)