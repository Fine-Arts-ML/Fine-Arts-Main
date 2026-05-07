"""
Test script for RAG search feature.
Takes a natural language query, finds closest matching tags using embedding similarity,
then maps those tags to file IDs via oc_systemtag_object_mapping.
"""
import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create database connection
def create_db_connection():
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    engine = create_engine('postgresql+pg8000://{}:{}@{}:5432/{}'.format(DB_USER, DB_PASSWORD, DB_HOST, DB_NAME))
    return engine

# Load tags and mappings
def get_tags():
    try:
        engine = create_db_connection()
        df_systag = pd.read_sql_table('oc_systemtag', engine)
        df_tagmap = pd.read_sql_table('oc_systemtag_object_mapping', engine)
    except Exception as e:
        print(f"Error loading tags: {e}")
        return None, None
    return df_systag, df_tagmap

# Import the embedding model
from sentence_transformers import SentenceTransformer
import torch

def search_tags_with_nlp(query, top_k=10):
    """
    Takes a natural language query, finds closest matching tags using embedding similarity,
    then maps those tags to file IDs via oc_systemtag_object_mapping.
    
    Args:
        query: Natural language search query (e.g., 'A painting with green landscape scene')
        top_k: Number of top matching tags to return
    
    Returns:
        DataFrame with query, top matching tags, their similarity scores, and associated file IDs
    """
    # Step 1: Embed the user query using the query prompt
    query_embedding = model.encode(query, prompt_name="query")
    
    # Step 2: Embed all tags for comparison
    all_tags = df_systag['name'].tolist()
    tag_embeddings = model.encode(all_tags)
    
    # Step 3: Compute cosine similarity between query and all tags
    similarity = model.similarity(torch.tensor(query_embedding).unsqueeze(0), torch.tensor(tag_embeddings))
    
    # Step 4: Get top-k most similar tags
    top_indices = similarity[0].argsort(descending=True)[:top_k]
    
    # Step 5: Build results DataFrame
    results = pd.DataFrame({
        'tag_id': df_systag.iloc[top_indices]['id'].values,
        'tag_name': df_systag.iloc[top_indices]['name'].values,
        'similarity': similarity[0][top_indices].cpu().numpy()
    })
    
    # Step 6: Map tag IDs to file IDs via oc_systemtag_object_mapping
    results_with_files = results.merge(
        df_tagmap[df_tagmap['systemtagid'].isin(results['tag_id'])][['systemtagid', 'objectid']],
        left_on='tag_id',
        right_on='systemtagid',
        how='left'
    )
    
    # Group file IDs by tag (as a list)
    results_with_files = results_with_files.groupby(['tag_id', 'tag_name', 'similarity'])['objectid'].apply(list).reset_index()
    results_with_files = results_with_files.rename(columns={'objectid': 'file_ids'})
    
    return results_with_files


def get_all_file_ids_from_query(query, top_k=10):
    """
    Returns a unique list of all file IDs matching the query tags.
    """
    results = search_tags_with_nlp(query, top_k=top_k)
    
    # Collect all unique file IDs
    all_file_ids = set()
    for file_ids in results['file_ids']:
        if file_ids:
            all_file_ids.update(file_ids)
    
    return sorted(list(all_file_ids)), results


if __name__ == "__main__":
    print("Loading model...")
    model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
    print("Model loaded!")
    
    print("Loading tags from database...")
    df_systag, df_tagmap = get_tags()
    print(f"Loaded {len(df_systag)} tags and {len(df_tagmap)} mappings")
    
    # Test queries
    test_queries = [
        "A painting with green landscape scene",
        "portrait of a person",
        "abstract art with bright colors",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print(f"{'='*60}")
        
        # Get top matching tags with file IDs
        top_tags = search_tags_with_nlp(query, top_k=10)
        print("\nTop 10 matching tags:")
        print(top_tags.to_string(index=False))
        
        # Get all combined file IDs
        file_ids, _ = get_all_file_ids_from_query(query, top_k=10)
        print(f"\nFound {len(file_ids)} unique files matching query tags:")
        print(file_ids[:20], "..." if len(file_ids) > 20 else "")
