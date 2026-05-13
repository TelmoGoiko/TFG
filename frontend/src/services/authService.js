import { request } from './apiClient'

const AUTH_USER_KEY = import.meta.env.VITE_AUTH_USER_STORAGE_KEY?.trim() || 'tfg_auth_user'

const loginWithEmail = async ({ email, password }) => {
  if (!email || !password) {
    throw new Error('Email and password are required.')
  }

  if (password.length < 4) {
    throw new Error('Password must be at least 4 characters long.')
  }

  const payload = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
    }),
  })

  const user = {
    id: payload.user.id,
    email: payload.user.email,
    createdAt: payload.user.created_at,
    displayName: payload.user.email.split('@')[0],
  }

  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
  return user
}

const logout = () => {
  localStorage.removeItem(AUTH_USER_KEY)
}

const getCurrentUser = () => {
  try {
    const rawUser = localStorage.getItem(AUTH_USER_KEY)
    return rawUser ? JSON.parse(rawUser) : null
  } catch {
    return null
  }
}

const registerWithEmail = async ({ email, password }) => {
  if (!email || !password) {
    throw new Error('Email and password are required.')
  }
  if (password.length < 4) {
    throw new Error('Password must be at least 4 characters long.')
  }

  const payload = await request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
    }),
  })
}
  

export { loginWithEmail, logout, getCurrentUser, registerWithEmail }
