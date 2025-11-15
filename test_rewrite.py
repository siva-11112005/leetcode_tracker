#!/usr/bin/env python3
"""Quick test script to verify the rewritten code works."""
import asyncio
import sys
import os

# Add the project to path
sys.path.insert(0, '/root/leetcode_tracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leetcode_tracker.settings')

import django
django.setup()

from tracker.views import LeetCodeAPI, parse_user_stats

async def test():
    """Test API fetch and parsing."""
    username = 'sivasakthivel__11'
    print(f"Testing with username: {username}\n")
    
    # Test 1: Fetch raw data
    print("=" * 60)
    print("TEST 1: Fetch raw API data")
    print("=" * 60)
    raw_data = await LeetCodeAPI.fetch_user_data(username)
    print(f"Error: {raw_data.get('error')}")
    print(f"Has profile: {bool(raw_data.get('profile'))}")
    print(f"Profile keys: {list(raw_data.get('profile', {}).keys())[:10]}")
    print(f"Has submissions: {bool(raw_data.get('submissions'))}")
    print(f"Submissions count: {len(raw_data.get('submissions', []))}")
    print(f"Has contest: {bool(raw_data.get('contest'))}")
    
    # Test 2: Parse to normalized format
    print("\n" + "=" * 60)
    print("TEST 2: Parse to normalized format")
    print("=" * 60)
    stats = parse_user_stats(raw_data)
    print(f"Username: {stats.get('username')}")
    print(f"Display name: {stats.get('display_name')}")
    print(f"Total solved: {stats.get('total_solved')}")
    print(f"Easy/Medium/Hard: {stats.get('easy_solved')}/{stats.get('medium_solved')}/{stats.get('hard_solved')}")
    print(f"Ranking: {stats.get('ranking')}")
    print(f"Contest rating: {stats.get('contest_rating')}")
    print(f"Current streak: {stats.get('current_streak')}")
    print(f"Max streak: {stats.get('max_streak')}")
    print(f"Recent submissions: {len(stats.get('recent_submissions', []))}")
    if stats.get('recent_submissions'):
        print(f"First submission: {stats['recent_submissions'][0]}")
    print(f"Error: {stats.get('error')}")
    
    print("\n✅ All tests completed successfully!\n")

if __name__ == '__main__':
    asyncio.run(test())
