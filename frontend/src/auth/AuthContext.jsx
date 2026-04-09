import { createContext, useMemo, useState } from 'react'
import {
  getCurrentUser,
  loginWithEmail as loginWithEmailService,
  logout as logoutService,
} from '../services/authService'

const AuthContext = createContext(null)

const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(getCurrentUser)

  const loginWithEmail = async (credentials) => {
    const user = await loginWithEmailService(credentials)
    setCurrentUser(user)
    return user
  }

  const logout = () => {
    logoutService()
    setCurrentUser(null)
  }

  const value = useMemo(() => {
    return {
      currentUser,
      isAuthenticated: Boolean(currentUser),
      loginWithEmail,
      logout,
    }
  }, [currentUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export { AuthContext, AuthProvider }
