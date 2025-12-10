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
        # Try both modern and old reddit hosts; rotate on 403
        self.hosts = [
            "https://www.reddit.com",
            "https://old.reddit.com",
        ]
        # Rotate user agents to reduce blocking
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (compatible; yt_reddit_shortgen/1.0; +https://github.com/Prwae/yt_reddit_shortgen)",
        ]
        self.session = requests.Session()
    
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
        if "?" in sort:
            # Format: "top?t=day" -> "/r/subreddit/top.json?t=day&limit=25"
            base_sort = sort.split("?")[0]  # "top"
            params = sort.split("?")[1] if "?" in sort else ""  # "t=day"
            path = f"/r/{subreddit}/{base_sort}.json?{params}&limit={limit}&raw_json=1"
        else:
            path = f"/r/{subreddit}/{sort}.json?limit={limit}&raw_json=1"

        # Shuffle hosts to vary traffic
        host_candidates = self.hosts[:]
        random.shuffle(host_candidates)

        # Try multiple hosts with a few retries, but move to next host quickly on 403
        for host in host_candidates:
            url = f"{host}{path}"
            for attempt in range(2):
                # Small jitter to reduce burstiness
                time.sleep(0.8 + random.random())
                ua = random.choice(self.user_agents)
                headers = {
                    "User-Agent": ua,
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                }
                try:
                    response = self.session.get(url, headers=headers, timeout=15)
                    if response.status_code == 403:
                        # Blocked; backoff and try next attempt/host
                        print(f"⚠️  403 from {host} for r/{subreddit} (attempt {attempt+1}); switching UA/host...")
                        time.sleep(3.0 + attempt * 2 + random.random() * 2)
                        continue
                    response.raise_for_status()
                    data = response.json()
                    
                    # Check if we got rate limited or blocked
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
                                'url': f"{host}{post_data.get('permalink', '')}",
                                'created_utc': post_data.get('created_utc', 0)
                            })
                    
                    return posts
                
                except requests.exceptions.RequestException as e:
                    print(f"⚠️  Network error fetching from r/{subreddit} ({host}) attempt {attempt+1}: {e}")
                    time.sleep(1.0 + attempt + random.random())
                    continue
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON decode error for r/{subreddit} ({host}) attempt {attempt+1}: {e}")
                    print(f"   Response status: {response.status_code if 'response' in locals() else 'N/A'}")
                    time.sleep(1.0 + attempt + random.random())
                    continue
                except Exception as e:
                    print(f"⚠️  Error fetching from r/{subreddit} ({host}) attempt {attempt+1}: {e}")
                    time.sleep(1.0 + attempt + random.random())
                    continue

        # If all hosts/attempts failed, pause longer before returning
        print(f"⚠️  Failed to fetch posts from r/{subreddit} after retries. Cooling down...")
        time.sleep(5 + random.random() * 3)
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

