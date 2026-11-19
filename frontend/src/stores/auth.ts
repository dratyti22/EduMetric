import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'
import type { RegisterData, User } from '../types'

const USER_KEY = 'edumetric_user'
const TOKEN_KEY = 'edumetric_token'
const REFRESH_KEY = 'edumetric_refresh'

function readUser(): User | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(readUser())
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))

  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isTeacher = computed(() => user.value?.role === 'teacher')
  const isStudent = computed(() => user.value?.role === 'student')

  const userFullName = computed(() => {
    if (!user.value) return ''
    return [user.value.last_name, user.value.first_name, user.value.middle_name]
      .filter(Boolean)
      .join(' ')
  })

  function persist(nextUser: User, access: string, refresh?: string) {
    user.value = nextUser
    token.value = access
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser))
    localStorage.setItem(TOKEN_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  }

  function normalizeUser(raw: Omit<User, 'firstName' | 'lastName' | 'middleName'> & { first_name: string; last_name: string; middle_name?: string | null }): User {
    return {
      ...raw,
      firstName: raw.first_name,
      lastName: raw.last_name,
      middleName: raw.middle_name,
      name: [raw.last_name, raw.first_name, raw.middle_name].filter(Boolean).join(' '),
    }
  }

  async function login(email: string, password: string): Promise<boolean> {
    try {
      const { data } = await api.post('/user/login/', {
        email: email.trim(),
        password,
      })
      persist(normalizeUser(data.user), data.access, data.refresh)
      return true
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Неверный email или пароль'))
    }
  }

  async function restoreSession() {
    if (!token.value) return false
    try {
      const { data } = await api.get('/user/me/')
      const normalized = normalizeUser(data)
      user.value = normalized
      localStorage.setItem(USER_KEY, JSON.stringify(normalized))
      return true
    } catch {
      logout()
      return false
    }
  }

  async function register(payload: RegisterData): Promise<boolean> {
    try {
      await api.post('/user/register/', payload)
      await login(payload.email, payload.password)
      return true
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Ошибка регистрации'))
    }
  }

  async function updateProfile(data: Partial<User>) {
    try {
      const { data: updated } = await api.patch('/user/me/', {
        email: data.email,
        first_name: data.first_name,
        last_name: data.last_name,
        middle_name: data.middle_name,
        position: data.position,
        subject: data.subject,
        school: data.school,
        phone: data.phone,
        bio: data.bio,
      })
      const normalized = normalizeUser(updated)
      user.value = normalized
      localStorage.setItem(USER_KEY, JSON.stringify(normalized))
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось обновить профиль'))
    }
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    try {
      await api.post('/user/me/change-password/', {
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPassword,
      })
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось сменить пароль'))
    }
  }

  function logout() {
    user.value = null
    token.value = null
    localStorage.removeItem(USER_KEY)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
  }

  return {
    user,
    token,
    isAuthenticated,
    isTeacher,
    isStudent,
    userFullName,
    login,
    restoreSession,
    register,
    updateProfile,
    changePassword,
    logout,
  }
})
