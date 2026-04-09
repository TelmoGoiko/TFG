import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import useAuth from '../auth/useAuth'

const LoginPage = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { loginWithEmail } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const redirectTarget = location.state?.from?.pathname ?? '/workspaces'

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await loginWithEmail({ email, password })
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
          Login and start creating and editing your documents with our AI-powered editor.
        </p>

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

          {error ? <p className="error-text">{error}</p> : null}
          <button className="btn" type="submit" disabled={isLoading}>
            {isLoading ? 'Logging in...' : 'Log in'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default LoginPage
