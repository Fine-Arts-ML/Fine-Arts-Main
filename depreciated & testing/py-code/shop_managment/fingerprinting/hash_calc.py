"""
Hash calculation module for the shop management app.
Provides functions for computing and comparing perceptual hashes.
"""

import imagehash
import pandas as pd


def compute_hashes(img):
    """
    Compute perceptual hashes for an image.
    Images are resized to 1080x1080 to match the database hashes.
    
    Parameters:
        img (PIL.Image): Input image
    
    Returns:
        tuple: (whash, ahash, phash) hash strings
    """
    # Resize to 1080x1080 to match database hashes
    img = img.resize((1080, 1080))
    whash = imagehash.whash(img)
    ahash = imagehash.average_hash(img)
    phash = imagehash.phash(img)
    return str(whash), str(ahash), str(phash)


def hamming_distance(hash1, hash2):
    """
    Calculate the Hamming distance between two hash strings.
    
    Parameters:
        hash1 (str): First hash string
        hash2 (str): Second hash string
    
    Returns:
        int: Hamming distance (number of differing bits)
    """
    # Convert hex strings to integers and XOR, then count set bits
    int1 = int(hash1, 16)
    int2 = int(hash2, 16)
    xor_result = int1 ^ int2
    return bin(xor_result).count('1')


def find_closest_matches(df_hashes, query_whash, query_ahash, query_phash, top_n=10):
    """
    Find the closest matches based on hash similarity.
    
    Parameters:
        df_hashes (pandas.DataFrame): DataFrame with hash columns, filename, and preview_url
        query_whash (str): Query whash
        query_ahash (str): Query ahash
        query_phash (str): Query phash
        top_n (int): Number of top results to return
    
    Returns:
        pandas.DataFrame: Top N closest matches with distances
    """
    results = []
    
    for idx, row in df_hashes.iterrows():
        # Calculate Hamming distances for each hash type
        whash_dist = hamming_distance(query_whash, row['w_hash']) if pd.notna(row['w_hash']) else float('inf')
        ahash_dist = hamming_distance(query_ahash, row['a_hash']) if pd.notna(row['a_hash']) else float('inf')
        phash_dist = hamming_distance(query_phash, row['p_hash']) if pd.notna(row['p_hash']) else float('inf')
        
        # Use the minimum distance as the overall similarity score
        min_distance = min(whash_dist, ahash_dist, phash_dist)
        
        # Determine which hash type has the minimum distance
        distances = [whash_dist, ahash_dist, phash_dist]
        best_hash_type = distances.index(min_distance)
        hash_types = ['whash', 'ahash', 'phash']
        if min_distance == float('inf'):
            best_hash_type = 'none'
        else:
            best_hash_type = hash_types[best_hash_type]
        
        results.append({
            'fileid': row['id'],
            'filename': row['filename'],
            'preview_url': row['preview_url'],
            'webdav_path': row['webdav_path'],
            'w_hash': row['w_hash'],
            'a_hash': row['a_hash'],
            'p_hash': row['p_hash'],
            'whash_distance': whash_dist,
            'ahash_distance': ahash_dist,
            'phash_distance': phash_dist,
            'min_distance': min_distance,
            'best_hash_type': best_hash_type
        })
    
    # Convert to DataFrame and sort by minimum distance
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('min_distance').head(top_n)
    
    return results_df
