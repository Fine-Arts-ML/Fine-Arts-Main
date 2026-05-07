"""FastAPI application for Hash Calculation microservice.

Provides perceptual hash calculation for reverse image search.
Receives base64-encoded images and returns whash, ahash, and phash values.

Modeled after the existing rag_search service pattern.
"""

import os
import sys
import time
import logging
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .config import HashCalcConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ─── Pydantic Models ────────────────────────────────────────────────────────

class HashRequest(BaseModel):
    """Request body for hash calculation."""
    image: str = Field(..., description="Base64-encoded image data")
    hashMethod: str = Field(default="whash", description="Primary hash method (whash, ahash, phash)")


class HashResponse(BaseModel):
    """Response with calculated hash values."""
    whash: str
    ahash: str
    phash: str
    timestamp: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    uptime_seconds: float
    dependencies: dict


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None


# ─── Global State ────────────────────────────────────────────────────────────

config = HashCalcConfig()
start_time = time.time()

# ─── Hash Calculation Logic ─────────────────────────────────────────────────

def calculate_hashes(image_bytes: bytes) -> dict:
    """
    Calculate perceptual hashes for an image.
    Images are resized to 1080x1080 to match the database hashes.

    Parameters:
        image_bytes: Raw image bytes

    Returns:
        dict with whash, ahash, and phash strings
    """
    from PIL import Image
    import imagehash
    from io import BytesIO

    img = Image.open(BytesIO(image_bytes)).convert('RGB')
    img = img.resize((1080, 1080))

    return {
        "whash": str(imagehash.whash(img)),
        "ahash": str(imagehash.average_hash(img)),
        "phash": str(imagehash.phash(img)),
    }


# ─── Application Lifecycle ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info(f"Hash Calculation service starting on {config.host}:{config.port}")
    logger.info(f"Pillow version: {__import__('PIL').__version__}")
    logger.info(f"imagehash version: {__import__('imagehash').__version__}")
    yield
    logger.info("Hash Calculation service shutting down")


# ─── FastAPI Application ────────────────────────────────────────────────────

app = FastAPI(
    title="Hash Calculation Service",
    description="Microservice for calculating perceptual image hashes (whash, ahash, phash)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for browser access from Nuxt dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags="Health")
async def health_check():
    """Health check endpoint."""
    uptime = time.time() - start_time
    try:
        import PIL
        import imagehash
        deps = {
            "Pillow": PIL.__version__,
            "imagehash": imagehash.__version__,
        }
    except ImportError as e:
        deps = {"error": str(e)}

    return HealthResponse(
        status="healthy",
        uptime_seconds=round(uptime, 2),
        dependencies=deps
    )


@app.post(
    "/api/v1/hash/calculate",
    response_model=HashResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags="Hash"
)
async def calculate_hash_endpoint(request: HashRequest):
    """
    Calculate perceptual hashes for an uploaded image.

    - **image**: Base64-encoded image data (PNG, JPG, GIF, WEBP, etc.)
    - **hashMethod**: Primary hash method to use for ranking (whash, ahash, phash)

    Returns whash, ahash, and phash values that can be used for reverse image search
    against the database.
    """
    import base64

    try:
        # Decode base64 image data
        image_bytes = base64.b64decode(request.image)

        if not image_bytes:
            raise HTTPException(status_code=400, detail="Image data is empty")

        # Calculate hashes
        logger.info(f"Calculating hashes for image: {len(image_bytes)} bytes")
        result = calculate_hashes(image_bytes)
        logger.info(f"Hash calculation complete: whash={result['whash']}, ahash={result['ahash']}, phash={result['phash']}")

        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()

        return HashResponse(
            whash=result["whash"],
            ahash=result["ahash"],
            phash=result["phash"],
            timestamp=timestamp
        )

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Missing required dependency: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Invalid image data: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Hash calculation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Hash calculation failed: {str(e)}"
        )


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "hash_calc.main:app",
        host=config.host,
        port=config.port,
        log_level="info"
    )
