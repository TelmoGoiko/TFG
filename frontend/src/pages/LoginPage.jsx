import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import useAuth from '../auth/useAuth'

const LoginPage = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { loginWithEmail, registerWithEmail } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const redirectTarget = location.state?.from?.pathname ?? '/workspaces'

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (mode === 'register' && password !== confirmPassword) {
      setError('Password confirmation does not match.')
      return
    }

    setIsLoading(true)

    try {
      if (mode === 'login') {
        await loginWithEmail({ email, password })
      } else {
        await registerWithEmail({ email, password })
      }
      navigate(redirectTarget, { replace: true })
    } catch (submissionError) {
      setError(submissionError.message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <p className="kicker">Doc Assisted Workflow </p>
        <h1>Welcome to Architectural Editor</h1>
        <p>
          {mode === 'login'
            ? 'Login and start creating and editing your documents with our AI-powered editor.'
            : 'Create your account and start building documents with our AI-powered editor.'}
        </p>

        <div className="auth-switch" role="tablist" aria-label="Authentication mode">
          <button
            type="button"
            className={`auth-switch-option ${mode === 'login' ? 'active' : ''}`}
            onClick={() => {
              setMode('login')
              setError('')
            }}
          >
            Log in
          </button>
          <button
            type="button"
            className={`auth-switch-option ${mode === 'register' ? 'active' : ''}`}
            onClick={() => {
              setMode('register')
              setError('')
            }}
          >
            Register
          </button>
        </div>

        <form onSubmit={onSubmit} className="stack-form">
          <label>
            Mail
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@enterprise.com"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="at least 4 characters"
              required
            />
          </label>

          {mode === 'register' ? (
            <label>
              Confirm password
              <input
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="repeat your password"
                required
              />
            </label>
          ) : null}

          {error ? <p className="error-text">{error}</p> : null}
          <button className="btn" type="submit" disabled={isLoading}>
            {isLoading ? (mode === 'login' ? 'Logging in...' : 'Creating account...') : mode === 'login' ? 'Log in' : 'Register'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
