"""
Compliance Module - Ensures content meets YouTube guidelines
"""
from typing import Dict, List, Tuple
import re


class ComplianceChecker:
    """Checks content for compliance with YouTube guidelines"""
    
    def __init__(self):
        self.banned_keywords = [
            'kill', 'murder', 'suicide', 'self-harm', 'violence',
            'drug', 'illegal', 'weapon', 'gun', 'knife'
        ]
        
        self.identifying_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Full names
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{3}\.\d{3}\.\d{4}\b',  # Phone numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
    
    def check_story(self, story: Dict, rewritten_story: Dict) -> Tuple[bool, List[str]]:
        """
        Check if story meets compliance requirements
        
        Returns:
            Tuple of (is_compliant, list_of_issues)
        """
        issues = []
        
        # Check original story
        original_issues = self._check_text(story.get('text', ''))
        if original_issues:
            issues.extend([f"Original story: {issue}" for issue in original_issues])
        
        # Check rewritten story
        rewritten_issues = self._check_text(rewritten_story.get('script', ''))
        if rewritten_issues:
            issues.extend([f"Rewritten story: {issue}" for issue in rewritten_issues])
        
        # Check for identifying information
        identifying_issues = self._check_identifying_info(rewritten_story.get('script', ''))
        if identifying_issues:
            issues.extend(identifying_issues)
        
        is_compliant = len(issues) == 0
        return is_compliant, issues
    
    def _check_text(self, text: str) -> List[str]:
        """Check text for policy violations"""
        issues = []
        text_lower = text.lower()
        
        # Check for banned keywords (context matters, but flag for review)
        for keyword in self.banned_keywords:
            if keyword in text_lower:
                # Check context - might be okay in certain contexts
                if self._is_harmful_context(text_lower, keyword):
                    issues.append(f"Potentially harmful content: {keyword}")
        
        return issues
    
    def _is_harmful_context(self, text: str, keyword: str) -> bool:
        """Check if keyword appears in harmful context"""
        # Simple heuristic - can be improved
        harmful_phrases = [
            f'how to {keyword}',
            f'want to {keyword}',
            f'going to {keyword}',
            f'plan to {keyword}'
        ]
        
        return any(phrase in text for phrase in harmful_phrases)
    
    def _check_identifying_info(self, text: str) -> List[str]:
        """Check for identifying information"""
        issues = []
        
        for pattern in self.identifying_patterns:
            matches = re.findall(pattern, text)
            if matches:
                issues.append(f"Potential identifying information found: {matches[:3]}")
        
        return issues
    
    def filter_content(self, text: str) -> str:
        """Filter out potentially problematic content"""
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[email]', text)
        
        # Remove phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone]', text)
        
        # Remove potential SSNs
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[id]', text)
        
        return text


def check_compliance(story: Dict, rewritten_story: Dict) -> Tuple[bool, List[str]]:
    """
    Main function to check compliance
    """
    checker = ComplianceChecker()
    return checker.check_story(story, rewritten_story)





