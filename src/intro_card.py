"""
Intro Card Module - Generates intro card with rounded rectangle, avatar, nickname, and title
"""
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from pathlib import Path
import os
from .config import (
    INTRO_CARD_BG_COLOR,
    INTRO_CARD_CORNER_RADIUS, AVATAR_SIZE, AVATAR_POSITION,
    NICKNAME_POSITION, TITLE_POSITION, NICKNAME_FONT_SIZE,
    AVATAR_DIR, NICKNAME_FILE, BASE_DIR, SUBTITLE_FONT_SIZE, FONTS_DIR
)
import requests
from io import BytesIO


class IntroCardGenerator:
    """Generates intro cards for Reddit Reads videos"""
    
    def __init__(self):
        # Card dimensions will be calculated dynamically based on title
        pass
    
    def generate_card(self, 
                     title: str,
                     nickname: Optional[str] = None,
                     avatar_url: Optional[str] = None,
                     avatar_path: Optional[str] = None,
                     output_path: Optional[str] = None) -> Image.Image:
        """
        Generate intro card with:
        - Rounded corner rectangle background (white)
        - Circular avatar in top left (from user's avatar folder)
        - Nickname to the right of avatar (from user's nickname file)
        - Title below both
        
        Args:
            title: Post title
            nickname: Override nickname (optional, will load from file if not provided)
            avatar_url: URL to avatar image (optional, will load from folder if not provided)
            avatar_path: Local path to avatar image (optional, will load from folder if not provided)
            output_path: Path to save the card (optional)
        """
        # Load user's nickname from file if not provided
        if nickname is None:
            nickname = self._load_nickname()
        
        # Load user's avatar from folder if not provided
        if avatar_path is None:
            avatar_path = self._find_user_avatar()
        
        # Fixed sizes for avatar and nickname (don't change)
        nickname_font = self._get_nickname_font(NICKNAME_FONT_SIZE)
        
        # Calculate nickname dimensions (fixed)
        temp_img = Image.new('RGB', (2000, 2000))
        temp_draw = ImageDraw.Draw(temp_img)
        nickname_bbox = temp_draw.textbbox((0, 0), nickname, font=nickname_font)
        nickname_width = nickname_bbox[2] - nickname_bbox[0]
        
        # Fixed card width based on avatar + nickname (title will wrap within this)
        padding = 40
        avatar_space = AVATAR_SIZE + 20  # Avatar width + spacing
        card_width = max(
            avatar_space + nickname_width + padding * 2,
            900  # Minimum width (increased to make window wider)
        )
        
        # Try to wrap title first with original font size
        title_font_size = SUBTITLE_FONT_SIZE
        title_font = self._get_subtitle_font(title_font_size)
        title_lines, title_height = self._wrap_title_text(title, card_width - padding * 2, title_font, temp_draw)
        
        # If title is too tall even after wrapping, reduce font size
        max_title_height = 300  # Maximum height for title area
        min_font_size = int(SUBTITLE_FONT_SIZE * 0.6)  # Don't go below 60% of original
        
        while title_height > max_title_height and title_font_size > min_font_size:
            title_font_size = max(min_font_size, int(title_font_size * 0.9))  # Reduce by 10%
            title_font = self._get_subtitle_font(title_font_size)
            title_lines, title_height = self._wrap_title_text(title, card_width - padding * 2, title_font, temp_draw)
        
        # Calculate final card height: avatar row + title lines + buttons + padding
        buttons_height = 50  # Space for interaction buttons (increased for bigger buttons)
        card_height = AVATAR_SIZE + title_height + buttons_height + padding * 3
        
        # Create base image with white background (will apply rounded mask at the end)
        img = Image.new('RGB', (int(card_width), int(card_height)), INTRO_CARD_BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # Load and place avatar
        avatar_img = self._load_avatar(avatar_url, avatar_path, nickname)
        if avatar_img:
            avatar_circle = self._make_circular(avatar_img, AVATAR_SIZE)
            img.paste(avatar_circle, AVATAR_POSITION, avatar_circle if avatar_circle.mode == 'RGBA' else None)
        
        # Draw nickname (black text on white background) - FIXED SIZE
        nickname_x, nickname_y = NICKNAME_POSITION
        self._draw_text_with_font(draw, nickname, (nickname_x, nickname_y), nickname_font, (0, 0, 0))
        
        # Draw verified checkmark next to nickname
        nickname_bbox = temp_draw.textbbox((0, 0), nickname, font=nickname_font)
        nickname_width = nickname_bbox[2] - nickname_bbox[0]
        checkmark_x = nickname_x + nickname_width + 8
        checkmark_y = nickname_y + 2
        self._draw_verified_checkmark(draw, (checkmark_x, checkmark_y), 16)
        
        # Draw award/emoji icons below nickname
        awards_start_x = nickname_x
        awards_y = nickname_y + nickname_bbox[3] - nickname_bbox[1] + 8
        self._draw_award_icons(draw, awards_start_x, awards_y, 8)
        
        # Draw title (black text on white background) - multi-line if needed
        title_x = padding
        title_y = AVATAR_SIZE + padding * 2
        
        # Draw interaction buttons (upvotes, comments, share) below title
        buttons_y = title_y + title_height + 15
        self._draw_interaction_buttons(draw, padding, buttons_y, card_width - padding)
        
        # Calculate line height from font
        if title_lines:
            test_bbox = temp_draw.textbbox((0, 0), title_lines[0], font=title_font)
            line_height = int((test_bbox[3] - test_bbox[1]) * 1.1)  # 10% spacing between lines
        else:
            line_height = int(title_font_size * 1.2)
        
        for i, line in enumerate(title_lines):
            y_pos = title_y + (i * line_height)
            self._draw_text_with_font(draw, line, (title_x, y_pos), title_font, (0, 0, 0))
        
        # Apply rounded corners mask to the entire image
        img = self._apply_rounded_corners(img, INTRO_CARD_CORNER_RADIUS)
        
        # Draw the rounded outline on the final image
        final_draw = ImageDraw.Draw(img)
        final_draw.rounded_rectangle(
            [(0, 0), (img.width, img.height)],
            radius=INTRO_CARD_CORNER_RADIUS,
            outline=(100, 100, 100),
            width=2
        )
        
        # Save if output path provided
        if output_path:
            img.save(output_path, 'PNG')
        
        return img
    
    def _load_nickname(self) -> str:
        """Load nickname from user's nickname file"""
        if NICKNAME_FILE.exists():
            try:
                with open(NICKNAME_FILE, 'r', encoding='utf-8') as f:
                    nickname = f.read().strip()
                    if nickname:
                        return nickname
            except Exception as e:
                print(f"Warning: Could not read nickname file: {e}")
        
        # Default fallback
        return "Redditor"
    
    def _find_user_avatar(self) -> Optional[str]:
        """Find user's avatar image in avatar folder"""
        if not AVATAR_DIR.exists():
            return None
        
        # Look for common image formats
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']
        for ext in image_extensions:
            avatar_files = list(AVATAR_DIR.glob(ext))
            if avatar_files:
                return str(avatar_files[0])  # Return first found
        
        return None
    
    def _apply_rounded_corners(self, img: Image.Image, radius: int) -> Image.Image:
        """Apply rounded corners to an image using a mask"""
        width, height = img.size
        
        # Create a mask for rounded corners
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        # Draw white rounded rectangle on mask - this creates the rounded shape
        mask_draw.rounded_rectangle(
            [(0, 0), (width, height)],
            radius=radius,
            fill=255
        )
        
        # Convert image to RGBA if needed
        if img.mode != 'RGBA':
            img_rgba = img.convert('RGBA')
        else:
            img_rgba = img.copy()
        
        # Apply the rounded mask to the alpha channel
        img_rgba.putalpha(mask)
        
        # Convert back to RGB with white background (for areas outside the mask)
        result = Image.new('RGB', (width, height), INTRO_CARD_BG_COLOR)
        result.paste(img_rgba, mask=img_rgba.split()[3])
        
        return result
    
    def _load_avatar(self, avatar_url: Optional[str], avatar_path: Optional[str], nickname: str) -> Optional[Image.Image]:
        """Load avatar from URL or path, or generate default"""
        # Try local path first
        if avatar_path and Path(avatar_path).exists():
            try:
                return Image.open(avatar_path).convert('RGB')
            except:
                pass
        
        # Try URL
        if avatar_url:
            try:
                response = requests.get(avatar_url, timeout=5)
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content)).convert('RGB')
            except:
                pass
        
        # Generate default avatar with initial
        return self._generate_default_avatar(nickname)
    
    def _generate_default_avatar(self, nickname: str) -> Image.Image:
        """Generate a simple default avatar with initial"""
        size = AVATAR_SIZE
        img = Image.new('RGB', (size, size), (70, 130, 180))  # Steel blue
        draw = ImageDraw.Draw(img)
        
        # Get initial
        initial = nickname[0].upper() if nickname else '?'
        
        # Try to use a font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", size // 2)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size // 2)
            except:
                font = ImageFont.load_default()
        
        # Get text size and center it
        bbox = draw.textbbox((0, 0), initial, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        position = ((size - text_width) // 2, (size - text_height) // 2)
        
        draw.text(position, initial, fill=(255, 255, 255), font=font)
        return img
    
    def _make_circular(self, img: Image.Image, size: int) -> Image.Image:
        """Crop image to circle"""
        # Resize to square
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        
        # Create circular mask
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse([(0, 0), (size, size)], fill=255)
        
        # Apply mask
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0))
        output.putalpha(mask)
        
        return output
    
    def _draw_text(self, draw: ImageDraw.Draw, text: str, position: tuple, font_size: int, color: tuple):
        """Draw text with fallback fonts (legacy method)"""
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                font = ImageFont.load_default()
        
        draw.text(position, text, fill=color, font=font)
    
    def _draw_text_with_font(self, draw: ImageDraw.Draw, text: str, position: tuple, font: ImageFont.FreeTypeFont, color: tuple):
        """Draw text with provided font"""
        draw.text(position, text, fill=color, font=font)
    
    def _get_subtitle_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get subtitle font (same as video_assembly uses)"""
        username = os.getenv("USERNAME", os.getenv("USER", ""))
        
        font_paths = [
            # Qilka-Bold (primary choice) - in fonts folder
            str(FONTS_DIR / "Qilka-Bold copy.otf"),
            str(FONTS_DIR / "Qilka-Bold copy.OTF"),
            str(FONTS_DIR / "qilka-bold copy.otf"),
            str(FONTS_DIR / "Qilka-Bold.otf"),
            str(FONTS_DIR / "qilka-bold.otf"),
            str(FONTS_DIR / "Qilka-Bold.ttf"),
            str(FONTS_DIR / "qilka-bold.ttf"),
            # CuteOutline-Regular (fallback) - in fonts folder
            str(FONTS_DIR / "CuteOutline-Regular.ttf"),
            str(FONTS_DIR / "CuteOutline-Regular.otf"),
            # Fallback fonts
            "C:/Windows/Fonts/ARLRDBD.TTF",  # Arial Rounded MT Bold
            "C:/Windows/Fonts/comic.ttf",  # Comic Sans MS
            "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold
        ]
        
        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    return ImageFont.truetype(font_path, size)
            except:
                continue
        
        # Last resort
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", size)
        except:
            return ImageFont.load_default()
    
    def _get_nickname_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get font for nickname"""
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)
        except:
            try:
                return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
            except:
                return ImageFont.load_default()
    
    def _wrap_title_text(self, text: str, max_width: int, font: ImageFont.FreeTypeFont, draw: ImageDraw.Draw) -> tuple:
        """
        Wrap title text to fit within max_width using actual font measurements.
        Returns: (list of lines, total height)
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Test if adding this word would exceed max_width
            test_line = ' '.join(current_line + [word]) if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
            
            if line_width <= max_width:
                current_line.append(word)
            else:
                # Current line is full, start new line
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        # Add remaining words
        if current_line:
            lines.append(' '.join(current_line))
        
        # Limit to reasonable number of lines (max 4)
        lines = lines[:4]
        
        # Calculate total height
        if not lines:
            return ([], 0)
        
        # Get height of one line
        single_line_bbox = draw.textbbox((0, 0), lines[0], font=font)
        line_height = single_line_bbox[3] - single_line_bbox[1]
        
        # Total height with some spacing between lines
        total_height = len(lines) * line_height * 1.1  # 10% spacing between lines
        
        return (lines, int(total_height))
    
    def _draw_verified_checkmark(self, draw: ImageDraw.Draw, position: tuple, size: int):
        """Draw a blue verified checkmark icon"""
        x, y = position
        # Draw blue circle background
        draw.ellipse([x, y, x + size, y + size], fill=(0, 122, 255))  # Reddit blue
        # Draw white checkmark
        checkmark_size = size - 4
        check_x = x + 2
        check_y = y + 2
        # Simple checkmark shape
        draw.line([(check_x + 2, check_y + checkmark_size // 2), 
                   (check_x + checkmark_size // 2 - 1, check_y + checkmark_size - 2),
                   (check_x + checkmark_size - 2, check_y + 2)], 
                  fill=(255, 255, 255), width=2)
    
    def _draw_award_icons(self, draw: ImageDraw.Draw, start_x: int, y: int, count: int = 8):
        """Draw colorful award/emoji icons"""
        icon_size = 20
        spacing = 4
        x = start_x
        
        # Award colors (various colors like Reddit awards)
        award_colors = [
            (255, 215, 0),    # Gold
            (192, 192, 192),  # Silver
            (255, 140, 0),    # Orange
            (255, 20, 147),   # Pink
            (0, 191, 255),    # Sky blue
            (50, 205, 50),    # Lime green
            (255, 69, 0),     # Red-orange
            (138, 43, 226),   # Blue violet
        ]
        
        for i in range(min(count, len(award_colors))):
            # Draw circular award icon
            draw.ellipse([x, y, x + icon_size, y + icon_size], 
                        fill=award_colors[i], outline=(200, 200, 200), width=1)
            # Draw simple symbol inside (trophy/star shape)
            center_x = x + icon_size // 2
            center_y = y + icon_size // 2
            # Draw a simple trophy/star - use triangle for simplicity
            draw.polygon([(center_x, y + 5), 
                         (x + 7, y + icon_size - 5),
                         (x + icon_size - 7, y + icon_size - 5)],
                        fill=(255, 255, 255))
            # Add a small circle on top for trophy look
            draw.ellipse([center_x - 3, y + 3, center_x + 3, y + 9], fill=(255, 255, 255))
            
            x += icon_size + spacing
    
    def _draw_interaction_buttons(self, draw: ImageDraw.Draw, start_x: int, y: int, card_width: int):
        """Draw Reddit-style interaction buttons (upvotes, comments, share) - BIGGER"""
        button_font_size = 24  # Increased from 18
        try:
            button_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", button_font_size)
        except:
            button_font = ImageFont.load_default()
        
        x = start_x
        button_spacing = 30  # Increased spacing
        
        # Upvotes button (heart icon + "99+") - BIGGER
        heart_size = 28  # Increased from 18
        draw.ellipse([x, y, x + heart_size, y + heart_size], 
                    fill=(255, 69, 0), outline=(200, 200, 200), width=2)
        # Simple heart shape - bigger
        center_x = x + heart_size // 2
        center_y = y + heart_size // 2
        # Draw heart using two circles and a triangle
        draw.ellipse([center_x - 8, center_y - 5, center_x, center_y + 3], fill=(255, 255, 255))
        draw.ellipse([center_x, center_y - 5, center_x + 8, center_y + 3], fill=(255, 255, 255))
        draw.polygon([(center_x - 5, center_y), (center_x + 5, center_y), (center_x, center_y + 6)], 
                    fill=(255, 255, 255))
        
        x += heart_size + 8
        draw.text((x, y + 4), "99+", fill=(100, 100, 100), font=button_font)
        x += 50 + button_spacing
        
        # Comments button (speech bubble + "99+") - BIGGER
        bubble_size = 28  # Increased from 18
        # Draw speech bubble
        draw.ellipse([x, y, x + bubble_size, y + bubble_size], 
                    fill=(100, 149, 237), outline=(200, 200, 200), width=2)
        # Draw small triangle for speech bubble tail
        draw.polygon([(x + bubble_size // 2, y + bubble_size), 
                     (x + bubble_size // 2 - 4, y + bubble_size + 6),
                     (x + bubble_size // 2 + 4, y + bubble_size + 6)], 
                    fill=(100, 149, 237))
        # Draw lines inside bubble (representing text)
        draw.line([(x + 6, y + bubble_size // 2 - 3), (x + bubble_size - 6, y + bubble_size // 2 - 3)], 
                 fill=(255, 255, 255), width=2)
        draw.line([(x + 6, y + bubble_size // 2 + 3), (x + bubble_size - 8, y + bubble_size // 2 + 3)], 
                 fill=(255, 255, 255), width=2)
        
        x += bubble_size + 8
        draw.text((x, y + 4), "99+", fill=(100, 100, 100), font=button_font)
        x += 50 + button_spacing
        
        # Share button (arrow icon + "Share") - BIGGER
        arrow_size = 28  # Increased from 18
        # Draw upward arrow
        draw.polygon([(x + arrow_size // 2, y + 3),
                     (x + 3, y + arrow_size - 3),
                     (x + arrow_size - 3, y + arrow_size - 3)],
                    fill=(100, 100, 100))
        # Draw arrow shaft
        draw.rectangle([(x + arrow_size // 2 - 2, y + arrow_size // 2), 
                       (x + arrow_size // 2 + 2, y + arrow_size - 3)],
                      fill=(100, 100, 100))
        
        x += arrow_size + 8
        draw.text((x, y + 4), "Share", fill=(100, 100, 100), font=button_font)
    
    def _wrap_text(self, text: str, max_width: int, font_size: int) -> list:
        """Wrap text to fit within max_width (legacy method)"""
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            except:
                font = ImageFont.load_default()
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            # Approximate width (characters * approximate width per char)
            width = len(test_line) * (font_size * 0.6)
            
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines[:3]  # Max 3 lines


def generate_intro_card(title: str, 
                       nickname: str,
                       avatar_url: Optional[str] = None,
                       avatar_path: Optional[str] = None,
                       output_path: Optional[str] = None) -> Image.Image:
    """
    Main function to generate intro card
    """
    generator = IntroCardGenerator()
    return generator.generate_card(title, nickname, avatar_url, avatar_path, output_path)

