console.log('[test-handler] MODULE LOADED')
export default defineEventHandler((event) => {
  console.log('[test-handler] REQUEST RECEIVED')
  return { message: 'test works' }
})