// Simple test handler to isolate the route issue
export default defineEventHandler((event) => {
  return { message: 'simple test works' }
})
