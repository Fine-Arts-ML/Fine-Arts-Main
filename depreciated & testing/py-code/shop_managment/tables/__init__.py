"""
Table components for the Shop Management app.
"""

from .shop_table import render_shops_table
from .account_table import render_accounts_table, render_account_table

__all__ = [
    # Shop table
    "render_shops_table",
    # Account table
    "render_accounts_table",
    "render_account_table",
]
