# Shop Management Streamlit App

A Streamlit application for managing shops, accounts, and their linked files from a PostgreSQL database. The app provides a comprehensive interface for CRUD operations on shops and accounts, file management with search capabilities, and flexible viewing modes.

## Features

### Shop Management
- **Add Shops**: Create new shops via the "Add New Shop" form
- **Edit Shops**: Modify shop names inline with save/cancel functionality
- **Remove Shops**: Delete shops with confirmation
- **View Shop Details**: See shop ID, account count, and file count
- **Account Management**: Link/unlink accounts to/from shops via expandable rows

### Account Management
- **Add Accounts**: Create new accounts globally via the "Account Management" tab
- **Edit Accounts**: Modify account names inline with save/cancel functionality
- **Remove Accounts**: Delete accounts with confirmation
- **Global Account View**: View and manage all accounts in a dedicated tab
- **Link Accounts to Shops**: Select accounts from a dropdown and link them to specific shops

### File Management
- **Add Files**: Link files to shops via multiple search methods:
  - Text search by filename (case-insensitive)
  - Reverse image search using perceptual hashes (WHASH, AHASH, PHASH)
- **View Files**: Display files in table view with preview, filename, and actions
- **Remove Files**: Unlink files from shops
- **File Previews**: View image previews directly in the interface
- **Infinite Scroll**: Load files progressively as you scroll with configurable batch sizes

### Viewing Modes
- **Table View**: Display files in a structured table with preview, filename, and actions
- **Overview Tab**: View all files linked to a shop with account information in a dataframe
- **Account Tabs**: View files linked to specific accounts within a shop

## File Structure

```
py-code/shop_managment/
├── streamlit_app.py      # Main application entry point
├── db_handler.py         # Database connection and query functions
├── ui_components.py      # Reusable UI components
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── forms/
│   ├── __init__.py       # Form components exports
│   ├── shop_form.py      # Shop CRUD forms (add, edit, remove)
│   ├── account_form.py   # Account CRUD forms (add, edit, remove)
│   └── file_form.py      # File search and selection forms
├── tables/
│   ├── __init__.py       # Table components exports
│   ├── shop_table.py     # Shop table rendering
│   ├── account_table.py  # Account table rendering
│   └── file_table.py     # File table rendering
└── utils/
    ├── __init__.py       # Utility exports
    ├── constants.py      # Configuration constants
    ├── helpers.py        # Helper functions
    └── session_state.py  # Session state management
```

## Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```

### Requirements

| Package | Version | Description |
|---------|---------|-------------|
| streamlit | >=1.28.0 | Web framework for data apps |
| sqlalchemy | >=2.0.0 | SQL toolkit and ORM |
| pg8000 | >=1.30.0 | PostgreSQL driver |
| pandas | >=2.0.0 | Data manipulation |
| python-dotenv | >=1.0.0 | Environment variable management |
| requests | >=2.28.0 | HTTP library |
| Pillow | >=10.0.0 | Image processing |

## Environment Variables

The app uses the following environment variables (loaded from `.env` file):

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL database host | `localhost` or `192.168.0.150` |
| `DB_NAME` | Database name | `your_database_name` |
| `DB_USER` | Database user | `your_username` |
| `DB_PASSWORD` | Database password | `your_password` |
| `NC_ACC` | Nextcloud account for preview authentication | `your_nextcloud_user` |
| `NC_PASS` | Nextcloud password for preview authentication | `your_nextcloud_pass` |

Create a `.env` file in the same directory or parent directory with:

```
DB_HOST=localhost
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password
NC_ACC=your_nextcloud_user
NC_PASS=your_nextcloud_pass
```

## Running the App

```bash
streamlit run streamlit_app.py
```

## Database Tables

### bre_shops
Stores shop information.

| Column | Type | Description |
|--------|------|-------------|
| shop_id | bigint | Primary key |
| shop_name | text | Name of the shop |

### bre_shop_account
Stores account information.

| Column | Type | Description |
|--------|------|-------------|
| account_id | bigint | Primary key |
| account_name | text | Name of the account |

### bre_shop_account_matrix
Many-to-many relationship table linking shops and accounts.

| Column | Type | Description |
|--------|------|-------------|
| shop_id | bigint | Foreign key to bre_shops |
| account_id | bigint | Foreign key to bre_shop_account |

### bre_account_index
Links files to accounts.

| Column | Type | Description |
|--------|------|-------------|
| file_id | int | File ID |
| account_id | bigint | Foreign key to bre_shop_account |

### bre_shops_index
Links files to shops.

| Column | Type | Description |
|--------|------|-------------|
| id | text | File ID (links to files) |
| shop_id | bigint | Shop ID (foreign key) |

### bre_advance_index
Stores file metadata including previews.

| Column | Type | Description |
|--------|------|-------------|
| fileid | int | File ID |
| name | text | Filename |
| preview_url | text | URL for preview image |

## Usage

### Main Navigation

The app has three main tabs:

1. **Shops & Accounts**: Manage shops and accounts
2. **Files**: View and manage files linked to shops
3. **Owl**: Placeholder for future features

### Shop Management Tab

The "Shop Managment" sub-tab displays:
- Add new shop form
- Interactive table with shop details
- Expandable rows showing accounts and file counts
- Edit and remove buttons for each shop

**To add a shop:**
1. Enter a shop name in the "Add New Shop" form
2. Click "Add Shop"
3. The shop appears in the table with a new ID

**To edit a shop:**
1. Click the ✏️ button next to the shop
2. Enter the new name
3. Click "💾 Save" or "❌ Cancel"

**To remove a shop:**
1. Click the 🗑️ button next to the shop
2. The shop is removed immediately

**To manage accounts for a shop:**
1. Click the 👤 button to expand account management
2. Select an account from the dropdown
3. Click "Link Account to Shop"

### Account Management Tab

The "Account Managment" sub-tab displays:
- Add new account form
- Global account table with edit/remove functionality
- Inline editing for account names

**To add an account:**
1. Enter an account name in the "Add Account" form
2. Click "Add Account"
3. The account appears in the table with a new ID

**To edit an account:**
1. Click the ✏️ button next to the account
2. Enter the new name
3. Click "💾 Save" or "❌ Cancel"

**To remove an account:**
1. Click the 🗑️ button next to the account
2. The account is removed immediately

### Files Tab

The Files tab shows:
- Shop tabs (one per shop)
- For each shop: Overview, Add Files, and Account tabs

**Overview Tab:**
- Table view of all files linked to the shop
- Shows preview, filename, display name, account name, and file ID
- Remove files with account selection

**Add Files Tab:**
- Search files by text or reverse image
- Select files to add to the shop
- Choose which accounts to link files to

**Account Tabs:**
- Files linked to specific accounts within a shop
- Table view with pagination
- Search within account files

### Adding Files

1. **Text Search:**
   - Enter search term in the text search field
   - Select files from results
   - Choose accounts to link to
   - Click "Confirm" to add files

2. **Reverse Image Search:**
   - Upload an image
   - Select hash type (WHASH, AHASH, PHASH)
   - Find similar files
   - Select and link files

### Removing Files

**From Table View:**
1. Click the 🗑️ button next to a file
2. File is removed from the shop

**From Overview Tab:**
1. Select a file from the dropdown
2. Select account(s) to unlink
3. Optionally check "Also remove shop link"
4. Click "Remove"

## Configuration Constants

The app uses the following constants defined in [`utils/constants.py`](utils/constants.py):

| Constant | Values | Description |
|----------|--------|-------------|
| `PAGE_SIZES` | small: 10, medium: 20, large: 50, xlarge: 100 | Pagination sizes |
| `FILES_PER_ROW` | 3 | Files per row in grid view |
| `IMAGES_PER_ROW` | 2 | Images per row in grid view |
| `BATCH_SIZES` | [10, 20, 50, 100] | Files per load for infinite scroll |
| `HASH_TYPES` | ["WHASH", "AHASH", "PHASH"] | Perceptual hash types |
| `DEFAULT_DB_HOST` | "192.168.0.150" | Default database host |
| `IMAGE_RESIZE_1080` | (1080, 1080) | Image resize dimensions |
| `IMAGE_RESIZE_540` | (540, 540) | Image resize dimensions |
| `IMAGE_PREVIEW_200` | (200, 200) | Preview dimensions |
| `IMAGE_PREVIEW_100` | (100, 100) | Preview dimensions |

## Functions Reference

### db_handler.py

#### Generic CRUD Functions
- [`create_db_connection()`](db_handler.py:17) - Create database engine with connection pooling
- [`get_all_entities(table_name, id_column, name_column)`](db_handler.py:43) - Fetch all entities from a table
- [`add_entity(table_name, id_column, name_column, name_value)`](db_handler.py:81) - Add a new entity
- [`remove_entity(table_name, id_column, id_value)`](db_handler.py:137) - Remove an entity
- [`update_entity(table_name, id_column, name_column, id_value, new_name)`](db_handler.py:164) - Update an entity's name

#### Shop Functions
- [`get_all_shops()`](db_handler.py:201) - Fetch all shops
- [`add_shop(shop_name)`](db_handler.py:211) - Add a new shop
- [`remove_shop(shop_id)`](db_handler.py:224) - Remove a shop
- [`update_shop(shop_id, new_shop_name)`](db_handler.py:237) - Update a shop's name

#### Account Functions
- [`get_all_accounts()`](db_handler.py:251) - Fetch all accounts
- [`add_account(account_name)`](db_handler.py:261) - Add a new account
- [`link_account_to_shop(shop_id, account_id)`](db_handler.py:274) - Link an account to a shop
- [`remove_account_from_shop(shop_id, account_id)`](db_handler.py:320) - Remove an account from a shop

#### File Functions
- [`link_file_to_account(file_id, account_id)`](db_handler.py:347) - Link a file to an account
- [`unlink_file_from_account(file_id, account_id)`](db_handler.py:392) - Remove a file link from an account
- [`get_accounts_for_file(file_id)`](db_handler.py:420) - Get all accounts linked to a file
- [`get_shop_for_file(file_id, shop_id)`](db_handler.py:459) - Check if a file is linked to a shop
- [`get_accounts_for_file_in_shop(file_id, shop_id)`](db_handler.py:491) - Get accounts for a file within a shop
- [`unlink_file_from_account_with_shop_check(file_id, account_id, shop_id)`](db_handler.py:531) - Unlink file with shop check
- [`get_file_count_for_shop(shop_id)`](db_handler.py:655) - Get file count for a shop
- [`get_files_for_shop(shop_id)`](db_handler.py:681) - Get all files for a shop
- [`link_file_to_shop(file_id, shop_id)`](db_handler.py:732) - Link a file to a shop
- [`unlink_file_from_shop(file_id, shop_id)`](db_handler.py:778) - Remove a file link from a shop
- [`get_accounts_for_shop(shop_id)`](db_handler.py:613) - Get accounts for a shop

### ui_components.py

- [`render_files_view(shop_id, tab_context, show_files)`](ui_components.py:22) - Render the files view for a shop
- [`render_overview_tab(shop_id, account_tabs, tab_index, shops_df)`](ui_components.py:72) - Render the Overview tab
- [`render_file_row(file_data, shop_id, is_infinite_scroll, files_list)`](ui_components.py:184) - Render a single file row
- [`render_add_files_tab(shop_id, account_tabs, tab_index)`](ui_components.py:229) - Render the Add Files tab
- [`render_account_tab(shop_id, shop_name, account_id, account_name, account_tabs, tab_index)`](ui_components.py:244) - Render an account tab
- [`render_account_files_table(shop_id, shop_name, account_id, account_name, files_df, total_files, files_per_page)`](ui_components.py:328) - Render account files table
- [`render_account_file_row(file_data, shop_id, account_id)`](ui_components.py:397) - Render an account file row
- [`render_shop_selector(shops_df)`](ui_components.py:450) - Render shop selector with nested account tabs

### forms/shop_form.py

- [`render_add_shop_form()`](forms/shop_form.py:9) - Render add shop form
- [`render_edit_shop_form(shop_id, current_name)`](forms/shop_form.py:28) - Render edit shop form
- [`render_remove_shop_form(shop_id, shop_name)`](forms/shop_form.py:59) - Render remove shop form

### forms/account_form.py

- [`render_add_account_form()`](forms/account_form.py:9) - Render add account form
- [`render_edit_account_form(account_id, current_name)`](forms/account_form.py:28) - Render edit account form
- [`render_remove_account_form(account_id, account_name)`](forms/account_form.py:60) - Render remove account form

### forms/file_form.py

- [`render_file_select_expander(shop_id, selected_file, idx, col_idx, unique_key_suffix)`](forms/file_form.py:23) - Render file selection modal
- [`render_add_file_form(shop_id, tab_context)`](forms/file_form.py:138) - Render add file form
- [`render_text_search_files(shop_id, tab_context)`](forms/file_form.py:162) - Render text search form
- [`render_reverse_image_search(shop_id)`](forms/file_form.py:250) - Render reverse image search form
- [`show_file_selection_modal(shop_id, file_data, idx, col_idx)`](forms/file_form.py:330) - Show file selection modal

### tables/shop_table.py

- [`render_shops_table(shops_df)`](tables/shop_table.py:12) - Render shops table

### tables/account_table.py

- [`render_accounts_table(accounts_df)`](tables/account_table.py:15) - Render accounts table
- [`render_account_table(shop_id, shops_df)`](tables/account_table.py:90) - Render account table for a shop

### tables/file_table.py

- [`render_files_table(shop_id, total_files)`](tables/file_table.py:10) - Render files table
- [`render_file_overview(shop_id, total_files)`](tables/file_table.py:55) - Render file overview
- [`render_file_row(file_data, shop_id, is_infinite_scroll, files_list)`](tables/file_table.py:72) - Render a file row
- [`render_infinite_scroll_file_list(shop_id, total_files)`](tables/file_table.py:115) - Render infinite scroll file list

### utils/helpers.py

- [`render_columns(ratios, **kwargs)`](utils/helpers.py:9) - Render columns with optional ratios
- [`render_info_table(data, title)`](utils/helpers.py:26) - Render an information table

### utils/session_state.py

- [`get_files_loaded(shop_id)`](utils/session_state.py:8) - Get files loaded count
- [`set_files_loaded(shop_id, count)`](utils/session_state.py:15) - Set files loaded count
- [`get_files_list(shop_id)`](utils/session_state.py:20) - Get files list
- [`set_files_list(shop_id, files)`](utils/session_state.py:27) - Set files list
- [`get_editing_state(key, default)`](utils/session_state.py:32) - Get editing state
- [`set_editing_state(key, value)`](utils/session_state.py:39) - Set editing state
- [`get_selected_file(shop_id)`](utils/session_state.py:44) - Get selected file
- [`set_selected_file(shop_id, file_data)`](utils/session_state.py:50) - Set selected file
- [`clear_selected_file(shop_id)`](utils/session_state.py:55) - Clear selected file
- [`get_account_files_loaded(account_id)`](utils/session_state.py:62) - Get account files loaded
- [`set_account_files_loaded(account_id, count)`](utils/session_state.py:69) - Set account files loaded
- [`get_account_total_files(account_id)`](utils/session_state.py:74) - Get account total files
- [`set_account_total_files(account_id, count)`](utils/session_state.py:81) - Set account total files

## Session State Keys

The app uses the following session state keys:

| Key | Type | Description |
|-----|------|-------------|
| `editing_{shop_id}` | bool | Shop editing state |
| `showing_accounts_{shop_id}` | bool | Show accounts for shop |
| `loaded_{shop_id}` | int | Files loaded count for infinite scroll |
| `files_{shop_id}` | list | Files list for infinite scroll |
| `selected_file_{shop_id}` | dict | Selected file data |
| `selected_account_{shop_id}_{idx}_{col_idx}` | list | Selected accounts for file add |
| `page_{shop_id}_{account_id}` | int | Current page for account view |
| `filtered_page_{shop_id}_{account_id}` | int | Current page for filtered search |
| `editing_acc_global_{account_id}` | bool | Global account editing state |
| `files_loaded_{account_id}` | int | Account files loaded count |
| `total_files_{account_id}` | int | Account total files count |

## Architecture

### Database Layer
The [`db_handler.py`](db_handler.py) module provides:
- Generic CRUD functions for any table
- Shop-specific functions
- Account-specific functions
- File-specific functions
- Relationship management between entities

### UI Layer
The [`ui_components.py`](ui_components.py) module provides:
- Reusable rendering functions
- Tab management
- File display components

### Form Layer
The [`forms/`](forms/) module provides:
- Shop CRUD forms
- Account CRUD forms
- File search and selection forms

### Table Layer
The [`tables/`](tables/) module provides:
- Shop table rendering
- Account table rendering
- File table rendering

### Utility Layer
The [`utils/`](utils/) module provides:
- Configuration constants
- Helper functions
- Session state management

## Troubleshooting

### Database Connection Issues
- Verify `.env` file exists with correct credentials
- Check database host is accessible
- Ensure PostgreSQL service is running

### File Preview Issues
- Verify the preview server is running on the configured host
- Check that preview URLs are correctly formatted
- Ensure image files exist in the database
- Verify Nextcloud credentials (`NC_ACC`, `NC_PASS`) are set

### Pagination Issues
- Clear session state if pagination gets stuck
- Verify page size is appropriate for data volume
- Check that file count matches displayed files

### Infinite Scroll Issues
- Clear session state if infinite scroll gets stuck
- Verify batch size is appropriate for data volume
- Check that files are being loaded correctly

## License

See the main project [`LICENSE`](../LICENSE) file.
