# Fine Arts Shop Management App

A full-stack Nuxt 3 application for managing art shops, accounts, files, galleries, and AI-powered tag generation. Integrates with PostgreSQL, Nextcloud, and Python RAG services.

## Features

| Feature | Description |
|---------|-------------|
| **Shop Management** | CRUD operations for art shops via [`shops.vue`](src/pages/shops.vue) |
| **Account Management** | Create, read, and delete accounts linked to shops |
| **Shop-Account Linking** | Many-to-many relationship management |
| **File Search** | Four search modes: semantic (RAG), name-based, browse-all, reverse image search |
| **Linked Files Browser** | Hierarchical browsing of files by shop and account with pagination |
| **File Linking/Unlinking** | Link files to shops/accounts via `bre_file_junction` triadic relationship (optimized query layer) |
| **Gallery Management** | Create, manage, and share image galleries with guest access |
| **Tag Pipeline** | Scan files, generate AI tags/descriptions, review and sync to Nextcloud |
| **Knowledge Graph** | Visualize tag relationships and file associations |
| **Reverse Image Search** | Perceptual hash-based image similarity search (whash, ahash, phash) |
| **RAG Semantic Search** | Natural language search using embedding models and TF-IDF |
| **User Management** | Admin-only user role management and Nextcloud sync |
| **Theme Support** | Light/dark mode with system preference detection |
| **Nextcloud Integration** | Fetch preview images from Nextcloud servers |

## Tech Stack

| Category | Technology | Version |
|----------|------------|---------|
| Framework | Nuxt 3 | 3.13+ |
| Language | TypeScript | 5.5+ |
| UI Framework | Vue 3 | 3.4+ |
| CSS Framework | Tailwind CSS | 3.4+ |
| UI Components | Radix Vue | 1.9+ |
| State Management | Pinia | 2.1+ |
| Server State | TanStack Query | 5.51+ |
| Database ORM | Drizzle ORM | 0.33+ |
| Database Client | PostgreSQL (pg) | 8.20+ |
| Database | PostgreSQL | 16+ |
| Icon Library | Lucide Vue Next | 0.400+ |
| Date Handling | date-fns | 3.6+ |
| Image Processing | JIMP | 0.22+ |
| Python Framework | FastAPI | (RAG service) |

## Getting Started

### Prerequisites

- Node.js 20+
- PostgreSQL 16+
- Nextcloud instance (for file previews and user sync)
- Python 3.10+ (for RAG and hash calculation services)

### Installation

1. Navigate to the project directory:
   ```bash
   cd shop_management_app
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy the example environment file and configure it:
   ```bash
   cp .env.example .env.local
   ```

4. Edit `.env.local` with your credentials:
   ```env
   # Database
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=shop_management
   DB_USER=postgres
   DB_PASSWORD=your_password

   # Nextcloud
   NC_HOST=localhost
   NC_ACC=your_nextcloud_user
   NC_PASS=your_nextcloud_pass

   # Auth
   SESSION_SECRET=change-this-to-a-random-secret
   SESSION_COOKIE_SECURE=false
   SESSION_COOKIE_SAMESITE=lax

   # Production
   NODE_ENV=development
   DEFAULT_ROLE=user
   ```

5. Set up the database:
   ```bash
   npm run db:push
   ```

6. Start the development server:
   ```bash
   npm run dev
   ```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Docker Development

```bash
docker-compose up
# Access at http://localhost:3000
docker-compose down
```

## Project Structure

```
shop_management_app/
├── src/
│   ├── app.vue                 # Root component
│   ├── app.config.ts           # App configuration
│   ├── assets/css/             # Static assets
│   │   └── global.css          # Global styles
│   ├── components/             # Vue components
│   │   ├── FileBrowserTree.vue # File/folder tree browser
│   │   ├── ImagePreviewModal.vue # Full-screen image preview
│   │   ├── PipelineNavBar.vue  # Tag pipeline navigation
│   │   ├── TreeNode.vue        # Tree node component
│   │   ├── gallery/            # Gallery-specific panels
│   │   │   ├── AccessManagementPanel.vue
│   │   │   └── ImageAssignmentPanel.vue
│   │   └── ui/                 # UI primitives (shadcn-inspired)
│   │       ├── Button.vue
│   │       ├── Dialog.vue
│   │       ├── DialogContent.vue
│   │       ├── DialogHeader.vue
│   │       ├── DialogTitle.vue
│   │       ├── Input.vue
│   │       ├── Textarea.vue
│   │       └── useDialog.ts
│   ├── composables/            # Vue composables
│   │   ├── useAuth.ts          # Authentication
│   │   ├── useGalleries.ts     # Gallery CRUD
│   │   ├── useGalleryAccess.ts # Gallery access management
│   │   ├── useGalleryImages.ts # Gallery image management
│   │   ├── useImagePreview.ts  # Image preview modal
│   │   ├── useLinkedFiles.ts   # Linked files browsing
│   │   ├── useRagSearch.ts     # RAG semantic search
│   │   ├── useRAGSettings.ts   # RAG model settings
│   │   ├── useShops.ts         # Shop CRUD
│   │   ├── useTagPipeline.ts   # Tag pipeline operations
│   │   └── useTheme.ts         # Theme management
│   ├── layouts/                # Layout components
│   │   └── default.vue         # Main layout with sidebar
│   ├── lib/                    # Database schemas and utilities
│   │   ├── auth-schema.ts      # Auth table definitions
│   │   ├── constants.ts        # App constants
│   │   ├── db.ts               # Database connection
│   │   ├── gallery-schema.ts   # Gallery table definitions
│   │   ├── nextcloud-schema.ts # Nextcloud table references
│   │   ├── schema.ts           # Core table definitions
│   │   └── utils.ts            # Utility functions
│   ├── middleware/             # Route middleware
│   │   ├── admin.ts            # Admin-only protection
│   │   └── tags-pipeline.ts    # Tag pipeline access control
│   ├── pages/                  # Page components
│   │   ├── index.vue           # Landing page (redirects to /shops)
│   │   ├── login.vue           # Login page
│   │   ├── shops.vue           # Shop & account management
│   │   ├── files.vue           # File search (all modes)
│   │   ├── linked-files.vue    # Linked files browser
│   │   ├── galleries.vue       # Gallery overview
│   │   ├── gallery/[id].vue    # Individual gallery view (public)
│   │   ├── access-denied.vue   # Error page
│   │   ├── performance.vue     # Placeholder page
│   │   ├── settings/           # Settings pages
│   │   │   ├── app.vue         # App settings hub (admin)
│   │   │   ├── user.vue        # User preferences
│   │   │   └── app/
│   │   │       ├── browse.vue       # Browse folders (admin)
│   │   │       ├── rag.vue          # RAG settings (admin)
│   │   │       ├── re-index.vue     # Redirect to browse
│   │   │       └── user-management.vue # User management (admin)
│   │   └── tags-and-tagging/   # Tag pipeline pages
│   │       ├── index.vue          # Redirect to scan-files
│   │       ├── scan-files.vue     # File selection
│   │       ├── tags.vue           # AI tag generation
│   │       ├── review-data.vue    # Review & push staged data
│   │       └── sync.vue           # Tag management (admin)
│   ├── plugins/                # Nuxt plugins
│   │   ├── auth.ts             # Auth initialization
│   │   └── theme.ts            # Theme initialization
│   ├── server/                 # Nuxt server directory
│   │   ├── api/                # API routes
│   │   │   ├── auth/           # Authentication endpoints
│   │   │   ├── shops/          # Shop endpoints
│   │   │   ├── accounts/       # Account endpoints
│   │   │   ├── files/          # File search/linking endpoints
│   │   │   ├── galleries/      # Gallery endpoints
│   │   │   ├── settings/       # Settings endpoints
│   │   │   ├── users/          # User management endpoints
│   │   │   └── tags-and-tagging/ # Tag pipeline endpoints
│   │   ├── db/migrations/      # Database migrations
│   │   ├── middleware/         # Server middleware
│   │   │   ├── aa-auth.ts      # API auth middleware
│   │   │   └── admin.ts        # Admin middleware
│   │   └── utils/              # Server utilities
│   │       ├── auth.ts
│   │       ├── directoryScanner.ts
│   │       └── preview.ts
│   ├── types/                  # TypeScript type definitions
│   │   ├── account.ts
│   │   ├── gallery.ts
│   │   ├── index.ts
│   │   ├── linkedFile.ts
│   │   ├── linkFiles.ts
│   │   └── shop.ts
│   └── py-code/                # Python services
│       └── rag_search/         # RAG search service
├── .env.example                # Environment variables template
├── docker-compose.yml          # Docker development setup
├── docker-compose.deploy.yml   # Docker deployment setup
├── Dockerfile                  # Production Docker image
├── Dockerfile.dev              # Development Docker image
├── drizzle.config.ts           # Drizzle ORM configuration
├── nuxt.config.ts              # Nuxt configuration
├── package.json                # Dependencies and scripts
├── postcss.config.mjs          # PostCSS configuration
├── build.sh                    # Docker build script
├── export-images.sh            # Export Docker images
├── import-images.sh            # Import Docker images
└── DOCUMENTATION.md            # Detailed technical documentation
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server on port 3000 |
| `npm run build` | Build for production |
| `npm run generate` | Generate static site |
| `npm run preview` | Preview production build |
| `npm run db:generate` | Generate Drizzle migrations |
| `npm run db:migrate` | Run database migrations |
| `npm run db:push` | Push schema directly to database |
| `npm run db:studio` | Open Drizzle Studio (database GUI) |

## Database Schema

The application uses 20 `bre_` prefixed tables in PostgreSQL:

### Core Tables (Shop/Account/File Management)

| Table | Purpose |
|-------|---------|
| `bre_shops` | Shop/art account entities (user-input) |
| `bre_shop_account` | Individual art accounts (user-input) |
| `bre_shop_account_matrix` | Many-to-many shop-account relationships |
| `bre_account_index` | File-to-account links (critical data storage) |
| `bre_shops_index` | File-to-shop links (critical data storage) |
| `bre_advance_index` | File metadata (name, preview URL) |
| `bre_file_junction` | Triadic shop-file-account relationships (query optimization) |
| `bre_display_names` | Display name definitions |
| `bre_display_name_index` | Display name to entity relationships |
| `bre_hashes` | Perceptual hash values for reverse search |

### Authentication Tables

| Table | Purpose |
|-------|---------|
| `bre_user_accounts` | App user accounts with roles (guest/user/admin) |
| `bre_sessions` | Server-side session storage |

### Gallery Tables

| Table | Purpose |
|-------|---------|
| `bre_galleries` | Gallery master records |
| `bre_gallery_access` | Gallery guest access mappings |
| `bre_gallery_images` | Gallery-to-image mappings |

### Tag Pipeline Tables

| Table | Purpose |
|-------|---------|
| `bre_tags_staging` | Staged tags per session |
| `bre_tag_map_staging` | Staged tag-to-file mappings |
| `bre_descriptions_staging` | Staged descriptions per session |
| `bre_descriptions` | Production descriptions with pinning |
| `bre_index_config` | Re-index configuration |

## User Roles

| Role | Permissions |
|------|------------|
| **Guest** | View files, browse, view galleries (read-only) |
| **User** | All guest + tag operations, create galleries |
| **Admin** | All user + user management, settings, RAG configuration |

## Documentation

| Document | Description |
|----------|-------------|
| [DOCUMENTATION.md](DOCUMENTATION.md) | Comprehensive technical documentation |
| [DEPLOY.md](DEPLOY.md) | Docker deployment guide |
| [docs/pages.md](docs/pages.md) | All page components documentation |
| [docs/database-schema.md](docs/database-schema.md) | Database tables and relationships |
| [docs/authentication.md](docs/authentication.md) | Auth flow, RBAC, and middleware |
| [docs/depreciated-code.md](docs/depreciated-code.md) | Deprecated and unused code inventory |

## License

MIT
