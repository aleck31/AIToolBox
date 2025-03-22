# Copyright iX.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for processing media files such as image and pdf"""
import re
import base64
import logging
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image


# Default size constants
SMALL_FILE_SIZE = 1 * 1024 * 1024  # Files under 1MB need minimal optimization


class FileProcessor:
    """Class for processing and optimizing various media files"""
    
    def __init__(self, max_file_size=None):
        """Initialize FileProcessor with optional max file size
        
        Args:
            max_file_size: Maximum allowed file size in bytes (None for no limit)
        """
        self.max_file_size = max_file_size
        # Target file size is 90% of max_file_size if provided, otherwise use a default
        self.target_file_size = int(max_file_size * 0.9) if max_file_size is not None else 4.5 * 1024 * 1024
    
    @staticmethod
    def convert_to_rgb(image: Image.Image) -> Image.Image:
        """Convert image to RGB format if needed by removing alpha channel
        
        Args:
            image: PIL Image object to convert
            
        Returns:
            PIL.Image: RGB format image
        """
        if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[3])
            return background
        return image

    def optimize_image(self, image: Image.Image, format: str = 'JPEG') -> Image.Image:
        """Optimize image size and quality while maintaining visual information
        
        Quality levels are tried in sequence until target size is reached:
        - 95%: High quality, minimal compression artifacts
        - 75%: Balanced quality, good compression ratio
        - 50%: Maximum compression, acceptable quality for LLM vision tasks
        
        Args:
            image: PIL Image object to optimize
            
        Returns:
            PIL.Image: Optimized image
        """
        # Convert to RGB if needed
        image = self.convert_to_rgb(image)
        
        # Quality levels to try in order
        quality_levels = [95, 75, 50]
        
        for quality in quality_levels:
            buffer = BytesIO()
            image.save(buffer, format=format, quality=quality, optimize=True)
            size = buffer.tell()
            
            # If small enough or reached minimum quality, return this version
            if size <= self.target_file_size or quality == quality_levels[-1]:
                logging.debug(f"Optimized image with {quality}% quality: {size / 1024:.1f} KB")
                buffer.seek(0)
                return Image.open(buffer)

    def image_to_bytes(self, image: Image.Image, optimize: bool = False, format: str = 'JPEG') -> bytes:
        """Convert PIL Image to bytes with optional optimization and format specification
        
        Args:
            image: PIL Image object to convert
            optimize: Whether to optimize the image before conversion
            format: Output format ('JPEG' or 'PNG')
            
        Returns:
            bytes: Image bytes in specified format
        """
        buffer = BytesIO()
        img = self.optimize_image(image, format) if optimize else image
        img.save(buffer, format=format)
        return buffer.getvalue()

    def image_to_base64(self, image: Image.Image, optimize: bool = False) -> str:
        """Convert PIL Image object to base64 string with optional optimization
        
        Args:
            image: PIL Image object to convert
            optimize: Whether to optimize the image before conversion
            
        Returns:
            str: Base64 encoded string of the image
        """
        try:
            return base64.b64encode(self.image_to_bytes(image, optimize)).decode("utf-8")
        except Exception as e:
            raise ValueError(f"Failed to convert image to base64: {str(e)}") from e

    def read_file(self, file_path: str, optimize: bool = True) -> bytes:
        """Read file bytes from path with automatic type detection and optimization
        
        Args:
            file_path: Path to the file to read
            optimize: Whether to optimize images
            
        Returns:
            bytes: File content as bytes
        """
        try:
            # Auto-detect file type
            file_type, _ = self.get_file_type_and_format(file_path)
            
            # Process image files
            if file_type == 'image':
                with Image.open(file_path) as img:
                    return self.image_to_bytes(img, optimize)
            
            # For non-image files, read raw bytes
            with open(file_path, 'rb') as f:
                content = f.read()
                if self.max_file_size and len(content) > self.max_file_size:
                    raise ValueError(
                        f"File '{file_path}' exceeds maximum size of {self.max_file_size/1024/1024:.1f}MB"
                    )
                return content
        except Exception as e:
            raise Exception(
                f"Failed to read file '{file_path}'. "
                f"Error type: {type(e).__name__}. "
                f"Details: {str(e)}"
            )

    @staticmethod
    def file_to_base64(file_path: str) -> str:
        """Load media file from path and encode as base64 string
        
        Args:
            file_path: Path to the media file
            
        Returns:
            str: Base64 encoded string of the file contents
        """
        try:
            with open(file_path, "rb") as media_file:
                encoded_string = base64.b64encode(media_file.read()).decode("utf-8")
                return encoded_string
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except IOError as e:
            raise IOError(f"Failed to read file {file_path}: {str(e)}")

    @staticmethod
    def get_file_name(file_path: str) -> str:
        """Extract filename and sanitize it according to requirements
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Sanitized filename
        """
        # Handle both forward and backward slashes for cross-platform compatibility
        file_name = re.split(r'[/\\]', file_path)[-1]
        # Replace invalid characters with hyphens
        sanitized_name = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', '-', file_name)
        # Replace consecutive whitespace with single space
        sanitized_name = re.sub(r'\s+', ' ', sanitized_name)
        # Trim any leading/trailing whitespace
        sanitized_name = sanitized_name.strip()
        return sanitized_name

    @staticmethod
    def get_file_type_and_format(file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Determine file type and format from file path
        
        Args:
            file_path: Path to the file
            
        Returns:
            tuple: (file_type, file_format) where both can be None if format is unknown
        """
        try:
            ext = file_path.lower().split('.')[-1]
        except IndexError:
            return None, None
        
        # Image formats - normalize to Bedrock supported formats
        if ext in ['jpg', 'jpeg']:
            return 'image', 'jpeg'
        elif ext in ['png', 'gif', 'webp']:
            return 'image', ext

        # Document formats    
        if ext in ['pdf', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'md']:
            return 'document', ext

        # Video formats
        if ext in ['mkv', 'mov', 'mp4', 'webm', 'flv', 'mpeg', 'mpg', 'wmv', '3gp']:
            return 'video', ext

        return None, None
