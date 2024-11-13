import requests
import re
from typing import Tuple, Optional
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def validate_image_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if a URL is a valid and accessible image URL.
    
    Args:
        url (str): The URL to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
        - is_valid: True if URL is valid and accessible
        - error_message: None if valid, error description if invalid
    """
    try:
        # Check if the URL format is valid
        if not url:
            logger.error("Empty URL provided")
            return False, "Empty URL provided"
            
        # Check URL format
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            logger.error(f"Invalid URL format: {url}")
            return False, "Invalid URL format"
            
        # Check if URL matches common image patterns
        image_pattern = r'.*\.(jpg|jpeg|png|gif|bmp|webp)$'
        if not re.match(image_pattern, url.lower()):
            logger.warning(f"URL doesn't end with common image extension: {url}")
            # Don't return False here as some valid image URLs might not end with extensions
            
        # Try to fetch headers only
        logger.debug(f"Attempting to validate URL: {url}")
        response = requests.head(url, allow_redirects=True, timeout=5)
        
        # Log response details
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {response.headers}")
        
        # Check response status
        if response.status_code != 200:
            logger.error(f"URL returned status code {response.status_code}")
            return False, f"URL returned status code {response.status_code}"
            
        # Check content type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            logger.error(f"URL doesn't point to an image. Content-Type: {content_type}")
            return False, f"URL doesn't point to an image (Content-Type: {content_type})"
            
        # Check file size (if available)
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            logger.error("Image file too large")
            return False, "Image file too large (>10MB)"
            
        logger.info(f"URL validation successful: {url}")
        return True, None
        
    except requests.Timeout:
        logger.error("URL validation timeout")
        return False, "URL validation timeout"
    except requests.RequestException as e:
        logger.error(f"Error validating URL: {str(e)}")
        return False, f"Error validating URL: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during URL validation: {str(e)}")
        return False, f"Unexpected error: {str(e)}" 