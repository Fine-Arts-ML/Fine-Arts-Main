"""
Hash Helper for Node.js Integration

This script calculates perceptual hashes for images using the same imagehash
library as the main Python app. It receives base64-encoded image data via stdin
and returns hash values as base64-encoded JSON via stdout.

Called from Node.js via child_process.spawn for consistent hash calculation
with the database values.
"""

import sys
import base64
import json
from PIL import Image
from io import BytesIO

try:
    import imagehash
except ImportError:
    print("Error: imagehash library not installed", file=sys.stderr)
    sys.exit(1)


def calculate_hashes(image_bytes: bytes) -> dict:
    """
    Calculate perceptual hashes for an image.
    Images are resized to 1080x1080 to match the database hashes.

    Parameters:
        image_bytes: Raw image bytes

    Returns:
        dict with whash, ahash, and phash strings
    """
    img = Image.open(BytesIO(image_bytes)).convert('RGB')
    img = img.resize((1080, 1080))
    
    return {
        "whash": str(imagehash.whash(img)),
        "ahash": str(imagehash.average_hash(img)),
        "phash": str(imagehash.phash(img)),
    }


def main():
    """Read base64 image from stdin, output base64 JSON hashes to stdout."""
    try:
        b64_data = sys.stdin.read().strip()
        image_bytes = base64.b64decode(b64_data)
        
        result = calculate_hashes(image_bytes)
        json_result = json.dumps(result)
        b64_result = base64.b64encode(json_result.encode()).decode()
        
        print(b64_result)
    except Exception as e:
        error_result = json.dumps({"error": str(e)})
        b64_error = base64.b64encode(error_result.encode()).decode()
        print(b64_error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
