<script setup lang="ts">
// The root route is no longer prerendered.
// Auth-dependent redirects are handled by the global guest middleware (guest.global.ts).
// The middleware will redirect guests to /guest and non-guests based on their role.
// No client-side redirect logic needed here — the middleware handles it.
</script>

<template>
  <div class="flex items-center justify-center h-screen">
    <div class="text-center">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
      <p class="mt-4 text-gray-600">Loading...</p>
    </div>
  </div>
</template>
