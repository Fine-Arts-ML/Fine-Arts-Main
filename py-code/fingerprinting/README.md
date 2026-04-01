# Image Fingerprinting Streamlit App

A Streamlit application for image fingerprinting that allows users to upload an image, compute its perceptual hashes, and find the closest matches in the database.

## Features

- Upload images (JPG, JPEG, PNG)
- Images are resized to 1080x1080 to match database hashes
- Compute three types of perceptual hashes:
  - **WHASH** (Wavelet Hash)
  - **AHASH** (Average Hash)
  - **PHASH** (Perceptual Hash)
- Compare against all hashes in the PostgreSQL database
- Find the top N closest matches based on Hamming distance
- Display the best match next to the uploaded image
- Show other matches in a 3x3 grid layout
- Display filenames and hash distances for all matches

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure your `.env` file is configured with the database connection details:

```
DB_HOST=Your_HOST
DB_NAME=Your_DBNAME
DB_USER=Your_DBUSER
DB_PASSWORD=Your_PWD
```

## Usage

Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

The app will open in your default browser at `http://localhost:8501`.

## How It Works

1. **Image Upload**: Users upload an image through the Streamlit interface
2. **Image Resizing**: The uploaded image is resized to 1080x1080 to match the database hashes
3. **Hash Computation**: The app computes WHASH, AHASH, and PHASH for the resized image
4. **Database Query**: All hashes from the `bre_hashes` table are fetched along with file metadata
5. **Similarity Comparison**: Hamming distance is calculated for each hash type
6. **Results**: The top N closest matches are displayed, sorted by minimum distance

## Hamming Distance Interpretation

- **0**: Identical hashes
- **1-2**: Very similar images
- **3-5**: Similar but not identical images
- **Higher values**: Less similar images

## Database Schema

The app expects a `bre_hashes` table with the following columns:
- `id`: File identifier
- `w_hash`: Wavelet hash
- `a_hash`: Average hash
- `p_hash`: Perceptual hash

## Configuration

- **Number of Results**: Use the sidebar slider to adjust how many results to display (default: 10)
- **Image Size**: Images are resized to 1080x1080 to match the database hashes
