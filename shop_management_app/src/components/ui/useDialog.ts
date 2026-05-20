import { inject, InjectionKey } from 'vue'

export const DIALOG_INJECTION_KEY = Symbol('dialog') as InjectionKey<{
  isOpen: boolean
  close: () => void
  open: () => void
}>

export function useDialog() {
  const dialog = inject(DIALOG_INJECTION_KEY)
  if (!dialog) {
    throw new Error('useDialog must be used within Dialog')
  }
  return dialog
}
