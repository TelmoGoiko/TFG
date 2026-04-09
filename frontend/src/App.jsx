import { BrowserRouter } from 'react-router-dom'
import AppRouter from './app/Router'
import { AuthProvider } from './auth/AuthContext'

const App = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
