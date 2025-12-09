"""
Metadata Generator Module - Generates YouTube titles, descriptions, and hashtags
"""
from typing import Dict, List
import re


class MetadataGenerator:
    """Generates YouTube metadata for videos"""
    
    def __init__(self):
        self.hashtag_templates = {
            'aita': ['#AITA', '#AmItheAsshole', '#RedditStories', '#Drama'],
            'askreddit': ['#AskReddit', '#RedditStories', '#Stories', '#Viral'],
            'confession': ['#Confession', '#TrueStory', '#RedditStories', '#Storytime'],
            'relationship': ['#RelationshipAdvice', '#Dating', '#RedditStories', '#Drama'],
            'tifu': ['#TIFU', '#Fail', '#RedditStories', '#Funny'],
            'revenge': ['#Revenge', '#PettyRevenge', '#ProRevenge', '#RedditStories'],
            'default': ['#RedditStories', '#Storytime', '#Viral', '#Shorts']
        }
    
    def generate_metadata(self, story: Dict, rewritten_story: Dict) -> Dict:
        """
        Generate complete metadata for YouTube video
        
        Args:
            story: Original Reddit story
            rewritten_story: Rewritten story script
        
        Returns:
            Dict with title, description, hashtags, tags
        """
        title = self._generate_title(story, rewritten_story)
        description = self._generate_description(story, rewritten_story)
        hashtags = self._generate_hashtags(story)
        tags = self._generate_tags(story)
        
        return {
            'title': title,
            'description': description,
            'hashtags': hashtags,
            'tags': tags
        }
    
    def _generate_title(self, story: Dict, rewritten_story: Dict) -> str:
        """Generate viral-style title"""
        original_title = story.get('title', '')
        subreddit = story.get('subreddit', '').lower()
        
        # Extract key words from original title
        title_words = original_title.split()[:8]  # First 8 words
        
        # Create variations based on subreddit
        if 'aita' in subreddit:
            prefix = "AITA for"
            if not original_title.lower().startswith('aita'):
                title = f"{prefix} {original_title[:60]}"
            else:
                title = original_title[:70]
        elif 'tifu' in subreddit:
            prefix = "TIFU by"
            if not original_title.lower().startswith('tifu'):
                title = f"{prefix} {original_title[:60]}"
            else:
                title = original_title[:70]
        else:
            # Generic viral title
            title = original_title[:70]
        
        # Add emoji for engagement (optional)
        if len(title) < 60:
            title = f"🔥 {title}"
        
        # Ensure it's not too long (YouTube limit is 100 chars, but shorter is better)
        return title[:70]
    
    def _generate_description(self, story: Dict, rewritten_story: Dict) -> str:
        """Generate YouTube description"""
        subreddit = story.get('subreddit', '')
        original_title = story.get('title', '')
        
        description = f"""🔥 {original_title}

📖 Story sourced from r/{subreddit}

Stories are sourced from public online forums and rewritten for entertainment purposes.

💬 What do you think? Let us know in the comments!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ DISCLAIMER: Stories are sourced from public online forums and rewritten for entertainment. All identifying information has been removed or altered. This content is for entertainment purposes only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#RedditStories #Storytime #Shorts #Viral"""
        
        return description
    
    def _generate_hashtags(self, story: Dict) -> List[str]:
        """Generate relevant hashtags"""
        subreddit = story.get('subreddit', '').lower()
        
        # Determine category
        if 'aita' in subreddit or 'amitheasshole' in subreddit:
            category = 'aita'
        elif 'askreddit' in subreddit:
            category = 'askreddit'
        elif 'confession' in subreddit:
            category = 'confession'
        elif 'relationship' in subreddit:
            category = 'relationship'
        elif 'tifu' in subreddit:
            category = 'tifu'
        elif 'revenge' in subreddit:
            category = 'revenge'
        else:
            category = 'default'
        
        hashtags = self.hashtag_templates.get(category, self.hashtag_templates['default'])
        
        # Add subreddit-specific hashtag
        hashtags.append(f"#{subreddit}")
        
        return hashtags[:10]  # Limit to 10 hashtags
    
    def _generate_tags(self, story: Dict) -> List[str]:
        """Generate tags for YouTube"""
        tags = [
            'reddit stories',
            'reddit reads',
            'storytime',
            'shorts',
            'viral',
            story.get('subreddit', '').lower(),
            'story',
            'drama',
            'entertainment'
        ]
        
        # Add keywords from title
        title_words = story.get('title', '').lower().split()
        tags.extend([w for w in title_words if len(w) > 4][:5])
        
        return list(set(tags))[:15]  # Remove duplicates, limit to 15


def generate_metadata(story: Dict, rewritten_story: Dict) -> Dict:
    """
    Main function to generate metadata
    """
    generator = MetadataGenerator()
    return generator.generate_metadata(story, rewritten_story)





