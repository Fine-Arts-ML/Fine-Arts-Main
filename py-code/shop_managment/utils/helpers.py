"""
Helper functions for the Shop Management app.
"""

import streamlit as st
import pandas as pd


def render_columns(ratios: list = None, **kwargs) -> list:
    """
    Render columns with optional ratio specification.
    
    Parameters:
        ratios: List of ratios for columns (e.g., [2, 1]) or None for equal columns
        **kwargs: Additional arguments for st.columns
        
    Returns:
        List of column containers
    """
    if ratios:
        return st.columns(ratios, **kwargs)
    num_cols = kwargs.get('num_columns', len(ratios) if ratios else 1)
    return st.columns(num_cols, **kwargs)


def render_info_table(data: dict, title: str = "Information") -> None:
    """
    Render an information table.
    
    Parameters:
        data: Dictionary of metric -> value pairs
        title: Table title
    """
    df = pd.DataFrame({
        'Metric': list(data.keys()),
        'Value': list(data.values())
    })
    st.dataframe(df, hide_index=True, use_container_width=True)
