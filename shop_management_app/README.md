# Shop Management App

A Vue 3 + Nuxt 3 + TypeScript application for managing shops, accounts, and their linked files from a PostgreSQL database.

## Features

- **Shop Management**: CRUD operations for shops
- **Account Management**: CRUD operations for accounts
- **Shop-Account Linking**: Many-to-many relationship management
- **File Management**: Link files to shops and accounts
- **File Search**: Text search by filename + reverse image search using perceptual hashes
- **File Previews**: Fetch preview images from Nextcloud

## Tech Stack

- **Framework**: [Nuxt 3](https://nuxt.com/) - Vue 3 full-stack framework
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **UI**: [Tailwind CSS](https://tailwindcss.com/) + [Radix Vue](https://www.radix-vue.com/)
- **State Management**: [Pinia](https://pinia.vuejs.org/)
- **Server State**: [TanStack Query](https://tanstack.com/query/latest) for Vue
- **Database**: [Drizzle ORM](https://orm.drizzle.team/) + PostgreSQL
- **Forms**: [VeeValidate](https://vee-validate.logaretm.com/) + Zod
- **Tables**: [TanStack Table](https://tanstack.com/table/latest) for Vue

## Getting Started

### Prerequisites

- Node.js 20+ 
- PostgreSQL 16+

### Installation

1. Clone the repository and navigate to the project directory:
   ```bash
   cd typescript/shop_management
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Copy the example environment file and configure it:
   ```bash
   cp .env.example .env.local
   ```

4. Edit `.env.local` with your database and Nextcloud credentials:
   ```env
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=shop_management
   DB_USER=postgres
   DB_PASSWORD=your_password
   NC_ACC=your_nextcloud_user
   NC_PASS=your_nextcloud_pass
   ```

5. Set up the database (if using Drizzle):
   ```bash
   npm run db:push
   ```

6. Start the development server:
   ```bash
   npm run dev
   ```

The application will be available at [http://localhost:3000](http://localhost:3000).

### Docker Development

1. Start the application with Docker Compose:
   ```bash
   docker-compose up
   ```

2. The application will be available at [http://localhost:3000](http://localhost:3000)

3. To run in detached mode:
   ```bash
   docker-compose up -d
   ```

4. To stop:
   ```bash
   docker-compose down
   ```

## Project Structure

```
typescript/shop_management/
├── server/                    # Nuxt server directory
│   └── api/                   # API routes
├── src/
│   ├── app.vue               # Root component
│   ├── app.config.ts         # App configuration
│   ├── assets/               # Static assets
│   │   └── css/
│   │       └── global.css    # Global styles
│   ├── components/           # Vue components
│   │   ├── ui/              # shadcn/ui components
│   │   ├── shops/           # Shop-related components
│   │   ├── files/           # File-related components
│   │   └── layout/          # Layout components
│   ├── composables/         # Vue composables
│   ├── layouts/             # Layout files
│   ├── pages/               # Page components
│   ├── stores/              # Pinia stores
│   ├── types/               # TypeScript types
│   └── utils/               # Utility functions
├── nuxt.config.ts           # Nuxt configuration
├── tailwind.config.ts       # Tailwind CSS configuration
├── drizzle.config.ts        # Drizzle ORM configuration
├── docker-compose.yml       # Docker Compose for development
├── Dockerfile               # Production Docker image
└── Dockerfile.dev           # Development Docker image
```

## Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run generate` | Generate static site |
| `npm run preview` | Preview production build |
| `npm run db:generate` | Generate database migrations |
| `npm run db:migrate` | Run database migrations |
| `npm run db:push` | Push schema to database |
| `npm run db:studio` | Open Drizzle Studio |

## Database Schema

The application uses the following database tables:

| Table | Purpose |
|-------|---------|
| `bre_shops` | Shop information |
| `bre_shop_account` | Account information |
| `bre_shop_account_matrix` | Shop-Account relationships |
| `bre_account_index` | File-Account links |
| `bre_shops_index` | File-Shop links |
| `bre_advance_index` | File metadata |
| `bre_display_name` | Display names |
| `bre_display_name_matrix` | Display name relationships |

## License

MIT
