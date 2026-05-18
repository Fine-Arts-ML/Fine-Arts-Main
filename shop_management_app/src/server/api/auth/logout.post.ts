// Logout API Endpoint
// Clears the user session

export default defineEventHandler(async (event) => {
  // clearUserSession is auto-imported by nuxt-auth-utils
  await clearUserSession(event)
  return { success: true }
})
