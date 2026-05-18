// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2024-11-01',
  devtools: {
    enabled: true,

    timeline: {
      enabled: true,
    },
  },
  srcDir: 'src/',
  serverDir: 'src/server/',

  modules: [
    '@nuxtjs/tailwindcss',
    '@pinia/nuxt',
    'nuxt-auth-utils',
  ],

  css: ['~/assets/css/global.css'],

  runtimeConfig: {
    db: {
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT) || 5432,
      database: process.env.DB_NAME || 'shop_management',
      user: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASSWORD || 'postgres',
    },
    nextcloud: {
      host: process.env.NC_HOST || 'localhost',
      user: process.env.NC_ACC || '',
      password: process.env.NC_PASS || '',
    },
    // Auth session config
    sessionSecret: process.env.SESSION_SECRET || 'change-this-to-a-random-secret',
    public: {
      defaultRole: process.env.DEFAULT_ROLE || 'user',
      isProduction: process.env.NODE_ENV === 'production',
    },
  },

  // Session cookie configuration
  // Secure cookies are only sent over HTTPS (enabled in production with Cloudflare Tunnel)
  session: {
    cookie: {
      // Set to true in production with HTTPS
      secure: process.env.SESSION_COOKIE_SECURE === 'true',
      // SameSite=Lax provides CSRF protection while allowing top-level navigation
      sameSite: process.env.SESSION_COOKIE_SAMESITE || 'lax',
      // HTTP-only cookies are not accessible via JavaScript (prevents XSS attacks)
      httpOnly: true,
      // Cookie path
      path: '/',
      // Max age: 7 days by default
      maxAge: 7 * 24 * 60 * 60,
    },
    // Session name (used for cookie name)
    name: 'shop_session',
  },

  devServer: {
    port: 3000,
  },

  future: {
    compatibilityVersion: 4,
  },

  routeRules: {
    '/': { prerender: true },
  },

  app: {
    head: {
      title: 'Shop Management',
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Shop Management Application' },
      ],
      script: [
        {
          // Synchronous inline script to apply saved theme BEFORE Vue renders (prevents FOUC)
          innerHTML: '(function(){try{var t=localStorage.getItem("theme")||"light";document.documentElement.classList.toggle("dark",t==="dark");document.documentElement.setAttribute("data-theme",t)}catch(e){}})();',
          tagPosition: 'head',
          tagPriority: 'high',
        },
      ],
    },
  },

  nitro: {
    storage: {
      session: {
        driver: 'fs',
        base: './data/sessions',
      },
    },
  },
})
