# Copyright iX.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for processing media files such as image and pdf"""
import re
import base64
from io import BytesIO


def pil_to_base64(image) -> str:
    """ Convert PIL Image object to base64 strings 
    
    Args:
        image: PIL Image object to convert
        
    Returns:
        str: Base64 encoded string of the image
    """
    try:
        img_buff = BytesIO()
        image.save(img_buff, format="JPEG")
        encoded_string = base64.b64encode(img_buff.getvalue()).decode("utf-8")
        return encoded_string
    except Exception as e:
        raise ValueError(f"Failed to convert image to base64: {str(e)}") from e


def path_to_base64(file_path: str) -> str:
    """ Load media file from path and encode as base64 strings 
    
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


# from pdf2image import convert_from_path
# def pdf_to_imgs(file_path):
#     """ Convert PDF file into Pillow images, return a list of PIL.JpegImageFile """
#     # Set maximum page size to avoid exceeding the message api limit: image_count <= 20
#     max_pages = 20
#     try:
#         img_list = convert_from_path(
#             file_path, dpi=300, thread_count=4, fmt='jpeg', last_page=max_pages)
#         return img_list
#     except:
#         raise


def get_file_name(file_path: str) -> str:
    """ Extract filename and sanitize it according to Bedrock requirements:
     - Only alphanumeric, whitespace, hyphens, parentheses, and square brackets
     - No consecutive whitespace
    
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


def get_file_type_and_format(file_path: str) -> tuple[str | None, str | None]:
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


def read_file_bytes(file_path: str) -> bytes:
    """Read file bytes from file path
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        bytes: Raw bytes content of the file
    """
    try:
        with open(file_path, 'rb') as f:
            return f.read()
    except Exception as e:
        raise Exception(
            f"Failed to read file '{file_path}'. "
            f"Error type: {type(e).__name__}. "
            f"Details: {str(e)}"
        )
