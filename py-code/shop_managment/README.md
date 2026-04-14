# Shop Management Streamlit App

A Streamlit application for managing shops and their linked files from the PostgreSQL database.

## Features

- **Shop Management**: Add and remove shops from the `bre_shops` table
- **File Overview**: View the total number of files linked to each shop
- **File Management**: 
  - Add files to shops via the `bre_shops_index` table
  - Remove files from shops
  - View file previews
- **Flexible File Viewing**:
  - Pagination mode: Click through pages of files
  - Infinite scroll mode: Load files as you scroll

## File Structure

```
py-code/shop_managment/
├── streamlit_app.py    # Main application entry point
├── db_handler.py       # Database connection and query functions
├── ui_components.py    # Reusable UI components
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

## Environment Variables

The app uses the following environment variables (loaded from `.env` file):

- `DB_HOST` - PostgreSQL database host
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password

Create a `.env` file in the same directory or parent directory with:

```
DB_HOST=localhost
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
```

## Running the App

```bash
streamlit run streamlit_app.py
```

## Database Tables

### bre_shops
| Column     | Type    | Description           |
|------------|---------|-----------------------|
| shop_id    | bigint  | Primary key           |
| shop_name  | text    | Name of the shop      |

### bre_shops_index
| Column | Type   | Description              |
|--------|--------|--------------------------|
| id     | text   | File ID (links to files) |
| shop_id| bigint | Shop ID (foreign key)    |

## Usage

1. **Add a Shop**: Use the "Add New Shop" expander in the table view
2. **Remove a Shop**: Click the trash icon next to any shop in the table
3. **View Shop Details**: Select a shop from the sidebar
4. **Add Files**: Use the "Add Files to Shop" expander
5. **View Files**: Expand the "View Linked Files" section
   - Choose between Pagination or Infinite Scroll mode
   - In pagination mode, navigate between pages
   - In infinite scroll mode, click "Load More" to load additional files
6. **Remove Files**: Click the trash icon next to any file

## Functions

### db_handler.py

- `create_db_connection()` - Create database engine
- `get_all_shops()` - Fetch all shops
- `add_shop(shop_name)` - Add a new shop
- `remove_shop(shop_id)` - Remove a shop
- `get_file_count_for_shop(shop_id)` - Get file count for a shop
- `get_files_for_shop(shop_id, page_size, offset)` - Get paginated files
- `link_file_to_shop(file_id, shop_id)` - Link a file to a shop
- `unlink_file_from_shop(file_id, shop_id)` - Unlink a file from a shop
- `get_all_file_ids()` - Get all available file IDs
- `get_file_info(file_id)` - Get file information

### ui_components.py

- `render_shop_table(shops_df)` - Render shop management table
- `render_file_overview(shop_id, total_files)` - Render file overview
- `render_add_files_section(shop_id)` - Render file add section
- `render_file_list(shop_id, use_pagination)` - Render file list
- `render_paginated_file_list(shop_id, total_files)` - Render paginated view
- `render_infinite_scroll_file_list(shop_id, total_files)` - Render infinite scroll view
- `render_shop_selector(shops_df)` - Render shop selector dropdown
