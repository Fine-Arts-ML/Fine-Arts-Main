/**
 * Composable for authentication management.
 * Handles login state, user info, and authentication operations.
 */

import type { UserAccount } from '~/lib/auth-schema'

export interface AuthUser {
  id: number
  username: string
  displayName: string
  role: 'guest' | 'user' | 'admin'
  allowedGalleryIds: number[]
}

interface UseAuthReturn {
  user: Ref<AuthUser | null>
  isAuthenticated: Ref<boolean>
  isLoading: Ref<boolean>
  error: Ref<string | null>
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkSession: () => Promise<void>
  hasRole: (requiredRole: 'guest' | 'user' | 'admin') => boolean
  isAdmin: ComputedRef<boolean>
  isUser: ComputedRef<boolean>
  isGuest: ComputedRef<boolean>
}

export function useAuth(): UseAuthReturn {
  const user = useState<AuthUser | null>('auth-user', () => null)
  const isLoading = useState('auth-loading', () => false)
  const error = useState('auth-error', () => null)

  // Computed role checks
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isUser = computed(() => user.value?.role === 'user' || user.value?.role === 'admin')
  const isGuest = computed(() => user.value?.role === 'guest')

  // Check if user has required role (admin > user > guest hierarchy)
  function hasRole(requiredRole: 'guest' | 'user' | 'admin'): boolean {
    if (!user.value) return false
    
    const roleHierarchy = { guest: 0, user: 1, admin: 2 }
    const userLevel = roleHierarchy[user.value.role] ?? -1
    const requiredLevel = roleHierarchy[requiredRole] ?? -1
    
    return userLevel >= requiredLevel
  }

  // Check session from server
  async function checkSession(): Promise<void> {
    if (user.value) return // Already loaded
    
    isLoading.value = true
    error.value = null

    try {
      const result = await $fetch<{ authenticated: boolean; user?: AuthUser }>('/api/auth/session')
      
      if (result.authenticated && result.user) {
        user.value = result.user
      } else {
        user.value = null
      }
    } catch (e) {
      console.error('[auth] Session check failed:', e)
      user.value = null
    } finally {
      isLoading.value = false
    }
  }

  // Login
  async function login(username: string, password: string): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      await $fetch('/api/auth/login', {
        method: 'POST',
        body: { username, password },
      })

      await checkSession()
    } catch (e: any) {
      error.value = e?.data?.statusMessage || e?.statusMessage || 'Login failed'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // Logout
  async function logout(): Promise<void> {
    try {
      await $fetch('/api/auth/logout', { method: 'POST' })
    } catch (e) {
      console.error('[auth] Logout error:', e)
    } finally {
      user.value = null
      navigateTo('/login')
    }
  }

  // Initialize session on composable creation
  if (typeof window !== 'undefined') {
    checkSession()
  }

  return {
    user,
    isAuthenticated: computed(() => user.value !== null),
    isLoading,
    error,
    login,
    logout,
    checkSession,
    hasRole,
    isAdmin,
    isUser,
    isGuest,
  }
}
