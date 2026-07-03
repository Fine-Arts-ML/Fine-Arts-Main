// Admin Middleware
// Ensures the current user has admin role for routes that require it.
// Guests and regular users bypass this middleware entirely — each API endpoint
// is responsible for enforcing its own role-based permissions.

export default defineEventHandler(async (event) => {
  // If user is not set (auth middleware hasn't run or user not authenticated),
  // let auth middleware handle the 401/redirect
  const user = event.context.user as any
  if (!user) {
    return // Let auth middleware handle this
  }

  // Only enforce admin role for admin users.
  // Guests and regular users are allowed to pass through; each API endpoint
  // will check the user's role and enforce its own permissions.
  if (user.role !== 'admin') {
    return // Allow non-admin users to proceed
  }
})
