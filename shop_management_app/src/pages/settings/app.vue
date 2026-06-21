<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '~/composables/useAuth'
import { Lock, Settings2, Brain, FolderOpen, Users } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const { isAdmin, isAuthenticated } = useAuth()

definePageMeta({
  layout: 'default',
  middleware: 'admin',
})

useHead({
  title: 'App Settings - Art Management',
})

// Sub-menu items
const subMenus = [
  {
    label: 'RAG Search',
    to: '/settings/app/rag',
    icon: Brain,
  },
  {
    label: 'Browse',
    to: '/settings/app/browse',
    icon: FolderOpen,
  },
  {
    label: 'User Management',
    to: '/settings/app/user-management',
    icon: Users,
  },
]

const activeTab = computed(() => route.path)

// Auto-redirect to RAG Search if on parent route
onMounted(() => {
  if (route.path === '/settings/app') {
    router.push('/settings/app/rag')
  }
})
</script>

<template>
  <div class="p-6 max-w-5xl mx-auto">
    <!-- Page Header -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-2">
        <Settings2 class="w-6 h-6 text-gray-600 dark:text-gray-400" />
        <h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">App Settings</h1>
        <Lock class="w-5 h-5 text-gray-400" />
      </div>
      <p class="text-gray-600 dark:text-gray-400">Configure application-wide settings (admin only)</p>
    </div>

    <!-- Access Denied for non-admin users -->
    <div v-if="isAuthenticated && !isAdmin" class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div class="flex items-center gap-3 text-gray-600 dark:text-gray-400">
        <Lock class="w-8 h-8" />
        <div>
          <h3 class="text-lg font-medium">Access Denied</h3>
          <p class="text-sm">Only administrators can access application settings.</p>
        </div>
      </div>
    </div>

    <!-- Sub-menu Navigation (Segmented Control Style) -->
    <div v-if="isAdmin" class="mb-6">
      <div class="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-gray-50 dark:bg-gray-800">
        <NuxtLink
          v-for="menu in subMenus"
          :key="menu.to"
          :to="menu.to"
          :class="[
            'px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2',
            activeTab === menu.to
              ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
              : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
          ]"
        >
          <component :is="menu.icon" class="w-4 h-4" />
          <span>{{ menu.label }}</span>
        </NuxtLink>
      </div>
    </div>

    <!-- Sub-page Content -->
    <div v-if="isAdmin" class="mt-2">
      <NuxtPage />
    </div>
  </div>
</template>
