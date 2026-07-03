<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuth } from '~/composables/useAuth'
import { LogIn, AlertCircle, Loader2 } from 'lucide-vue-next'

const { login, isAuthenticated, user } = useAuth()

const username = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)

// Redirect if already authenticated
const isLoggedIn = computed(() => isAuthenticated.value)

async function handleLogin() {
  isLoading.value = true
  error.value = null

  try {
    await login(username.value, password.value)
    // Redirect based on role
    if (user.value?.role === 'guest') {
      navigateTo('/guest')
    } else {
      navigateTo('/shops')
    }
  } catch (e: any) {
    error.value = e?.data?.statusMessage || e?.statusMessage || 'Login failed. Please check your credentials.'
  } finally {
    isLoading.value = false
  }
}

definePageMeta({
  layout: false,
})

useHead({
  title: 'Login - Art Management',
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
    <div class="max-w-md w-full space-y-8 p-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg">
      <!-- Logo/Title -->
      <div class="text-center">
        <div class="mx-auto h-12 w-12 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
          <LogIn class="h-6 w-6 text-blue-600 dark:text-blue-400" />
        </div>
        <h2 class="mt-6 text-3xl font-bold text-gray-900 dark:text-gray-100">Sign in</h2>
        <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Use your Nextcloud account to sign in
        </p>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="flex items-center gap-2 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <AlertCircle class="h-5 w-5 text-red-500 flex-shrink-0" />
        <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      </div>

      <!-- Login Form -->
      <form class="space-y-6" @submit.prevent="handleLogin">
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Username
          </label>
          <input
            id="username"
            v-model="username"
            type="text"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter your username"
          />
        </div>

        <div>
          <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Password
          </label>
          <input
            id="password"
            v-model="password"
            type="password"
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Enter your password"
          />
        </div>

        <button
          type="submit"
          :disabled="isLoading"
          class="w-full flex justify-center items-center gap-2 py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Loader2 v-if="isLoading" class="h-4 w-4 animate-spin" />
          <LogIn v-else class="h-4 w-4" />
          {{ isLoading ? 'Signing in...' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>
