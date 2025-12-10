"""
Story Sourcing Module - Fetches Reddit posts without API key
"""
import requests
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import json
import time
import random
from .config import ALLOWED_SUBREDDITS, MIN_UPVOTES, MAX_POST_LENGTH, MIN_STORY_WORDS, MAX_STORY_WORDS


class RedditScraper:
    """Scrapes Reddit posts without using API key"""
    
    def __init__(self):
        # Use old.reddit.com which is friendlier to bots and JSON endpoints
        self.base_url = "https://old.reddit.com"
        # Strong User-Agent to reduce 403 blocks
        self.headers = {
            "User-Agent": "RedditReadsBot/1.0 (+https://github.com/Prwae/yt_reddit_shortgen)",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.8",
        }
    
    def fetch_subreddit_posts(self, subreddit: str, sort: str = "hot", limit: int = 25) -> List[Dict]:
        """
        Fetch posts from a subreddit
        Args:
            subreddit: Subreddit name (without r/)
            sort: Sort method (hot, top, new)
            limit: Number of posts to fetch
        Returns:
            List of post dictionaries
        """
        # Handle top with time period
        params = {"limit": limit}
        url_path = f"/r/{subreddit}/{sort}.json"
        if "?" in sort:
            # Format: "top?t=day" -> path="/r/sub/top.json" params include t=day
            base_sort, query_part = sort.split("?", 1)
            url_path = f"/r/{subreddit}/{base_sort}.json"
            for piece in query_part.split("&"):
                if "=" in piece:
                    k, v = piece.split("=", 1)
                    params[k] = v

        url = f"{self.base_url}{url_path}"

        retries = 3
        backoff = 2

        for attempt in range(retries):
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                # If 429/403, backoff and retry
                if response.status_code in (403, 429):
                    wait = backoff ** attempt
                    print(f"⚠️  Reddit returned {response.status_code} for r/{subreddit}, retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()
                
                # Check if we got rate limited or blocked via JSON error
                if 'error' in data:
                    error_msg = data.get('message', 'Unknown error')
                    print(f"⚠️  Reddit API error for r/{subreddit}: {error_msg}")
                    return []
                
                posts = []
                for child in data.get('data', {}).get('children', []):
                    post_data = child.get('data', {})
                    
                    # Filter criteria
                    selftext = post_data.get('selftext', '')
                    word_count = len(selftext.split()) if selftext else 0
                    
                    if (post_data.get('score', 0) >= MIN_UPVOTES and
                        selftext and
                        len(selftext) < MAX_POST_LENGTH and
                        MIN_STORY_WORDS <= word_count <= MAX_STORY_WORDS and  # Filter by word count
                        not post_data.get('over_18', False) and
                        selftext != '[removed]' and
                        selftext != '[deleted]'):
                        
                        posts.append({
                            'id': post_data.get('id'),
                            'title': post_data.get('title', ''),
                            'text': post_data.get('selftext', ''),
                            'author': post_data.get('author', ''),
                            'score': post_data.get('score', 0),
                            'subreddit': subreddit,
                            'url': f"{self.base_url}{post_data.get('permalink', '')}",
                            'created_utc': post_data.get('created_utc', 0)
                        })
                
                return posts
            
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    wait = backoff ** attempt
                    print(f"⚠️  Network error fetching from r/{subreddit}: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"⚠️  Network error fetching from r/{subreddit}: {e}")
                return []
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error for r/{subreddit}: {e}")
                print(f"   Response status: {response.status_code if 'response' in locals() else 'N/A'}")
                return []
            except Exception as e:
                print(f"⚠️  Error fetching from r/{subreddit}: {e}")
                return []
    
    def clean_text(self, text: str) -> str:
        """Clean and format Reddit post text"""
        # Remove markdown links [text](url) -> text
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def identify_hook(self, text: str) -> Optional[str]:
        """
        Identify the hook (first compelling sentence/paragraph)
        """
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return None
        
        # Return first sentence or first two if short
        hook = sentences[0]
        if len(hook) < 50 and len(sentences) > 1:
            hook = sentences[0] + ". " + sentences[1]
        
        return hook[:200]  # Limit hook length
    
    def filter_by_emotional_intensity(self, text: str) -> bool:
        """
        Simple heuristic to check if story has emotional intensity
        """
        emotional_keywords = [
            'angry', 'furious', 'upset', 'devastated', 'heartbroken',
            'shocked', 'surprised', 'confused', 'betrayed', 'disappointed',
            'excited', 'thrilled', 'amazing', 'incredible', 'unbelievable',
            'regret', 'guilty', 'ashamed', 'embarrassed', 'humiliated'
        ]
        
        text_lower = text.lower()
        matches = sum(1 for keyword in emotional_keywords if keyword in text_lower)
        return matches >= 2
    
    def get_best_story(self, subreddits: Optional[List[str]] = None, avoid_ids: Optional[List[str]] = None) -> Optional[Dict]:
        """
        Get a random story from allowed subreddits
        
        Args:
            subreddits: List of subreddits to fetch from
            avoid_ids: List of post IDs to avoid (to prevent duplicates)
        """
        if subreddits is None:
            subreddits = ALLOWED_SUBREDDITS
        
        if avoid_ids is None:
            avoid_ids = []
        
        all_posts = []
        
        # Randomize subreddit selection
        shuffled_subreddits = random.sample(subreddits, min(len(subreddits), 5))
        
        # Fetch from multiple subreddits with random sort methods
        # Try more subreddits if needed
        max_attempts = 5
        attempts = 0
        
        for subreddit in shuffled_subreddits:
            if attempts >= max_attempts:
                break
                
            # Randomize sort method (hot, top, new, rising)
            sort_methods = ["hot", "top", "new"]
            sort_method = random.choice(sort_methods)
            
            # For "top", also randomize time period
            if sort_method == "top":
                time_periods = ["day", "week", "month"]
                time_period = random.choice(time_periods)
                # Use special format for top with time period
                posts = self.fetch_subreddit_posts(subreddit, sort=f"top?t={time_period}", limit=25)
            else:
                posts = self.fetch_subreddit_posts(subreddit, sort=sort_method, limit=25)
            
            # Filter out posts we've already used
            posts = [p for p in posts if p['id'] not in avoid_ids]
            all_posts.extend(posts)
            attempts += 1
            
            # If we have enough posts, break early
            if len(all_posts) >= 10:
                break
                
            time.sleep(1.5)  # Rate limiting - increased delay
        
        if not all_posts:
            print("⚠️  No posts found from any subreddit. This might be due to:")
            print("   - Rate limiting from Reddit")
            print("   - All posts filtered out (word count, upvotes, etc.)")
            print("   - Network connectivity issues")
            return None
        
        # Filter by word count (ensure stories fit in 3 minutes)
        filtered_posts = []
        for post in all_posts:
            word_count = len(post['text'].split())
            if MIN_STORY_WORDS <= word_count <= MAX_STORY_WORDS:
                filtered_posts.append(post)
        
        # If no posts match word count, relax the filter slightly
        if not filtered_posts:
            print(f"⚠️  No posts match exact word count ({MIN_STORY_WORDS}-{MAX_STORY_WORDS} words)")
            print("   Relaxing word count filter...")
            # Accept posts with at least MIN_STORY_WORDS (remove upper limit)
            for post in all_posts:
                word_count = len(post['text'].split())
                if word_count >= MIN_STORY_WORDS:
                    filtered_posts.append(post)
        
        # If still no posts, try with emotional intensity filter
        if not filtered_posts:
            print("   Trying emotional intensity filter...")
            filtered_posts = [
                post for post in all_posts
                if self.filter_by_emotional_intensity(post['text'])
            ]
        
        # If still no posts, use all posts (will be trimmed later if needed)
        if not filtered_posts:
            print("   Using all available posts (will trim if needed)...")
            filtered_posts = all_posts
        
        # Instead of always picking top, randomly select from top candidates
        # Sort by score to get quality posts, but pick randomly from top 10
        filtered_posts.sort(key=lambda x: x['score'], reverse=True)
        
        # Pick randomly from top 10 posts (or all if less than 10)
        top_candidates = filtered_posts[:min(10, len(filtered_posts))]
        selected_post = random.choice(top_candidates)
        
        # Clean and process
        selected_post['text'] = self.clean_text(selected_post['text'])
        selected_post['hook'] = self.identify_hook(selected_post['text'])
        
        return selected_post


def fetch_story(subreddits: Optional[List[str]] = None, avoid_ids: Optional[List[str]] = None) -> Optional[Dict]:
    """
    Main function to fetch a story
    
    Args:
        subreddits: List of subreddits to fetch from
        avoid_ids: List of post IDs to avoid (prevents duplicates)
    """
    scraper = RedditScraper()
    return scraper.get_best_story(subreddits, avoid_ids)


if __name__ == "__main__":
    # Test the scraper
    story = fetch_story()
    if story:
        print(f"Title: {story['title']}")
        print(f"Score: {story['score']}")
        print(f"Subreddit: r/{story['subreddit']}")
        print(f"Hook: {story['hook']}")
        print(f"\nText preview: {story['text'][:200]}...")

