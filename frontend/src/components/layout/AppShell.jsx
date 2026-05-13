import { Link, NavLink, useNavigate } from 'react-router-dom'
import useAuth from '../../auth/useAuth'

const AppShell = ({ title, subtitle, children, actions, sidebar }) => {
  const navigate = useNavigate()
  const { currentUser, logout } = useAuth()

  const onLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-left">
          <Link className="brand" to="/workspaces">
            Architectural Editor
          </Link>
          <nav className="topbar-nav" aria-label="Main navigation">
            <NavLink to="/workspaces">Workspaces</NavLink>
          </nav>
        </div>

        <div className="topbar-right">
          <span className="user-pill">{currentUser?.email ?? 'User'}</span>
          <button className="btn btn-dark" onClick={onLogout}>
            Sign out
          </button>
        </div>
      </header>

      <div className={`shell-grid ${sidebar ? 'with-sidebar' : 'without-sidebar'}`}>
        {sidebar ? <aside className="left-sidebar">{sidebar}</aside> : null}

        <main className="content-area">
          <section className="page-head">
            <div>
              <h1>{title}</h1>
              {subtitle ? <p>{subtitle}</p> : null}
            </div>
            {actions ? <div className="page-actions">{actions}</div> : null}
          </section>

          {children}
        </main>
      </div>
    </div>
  )
}

export default AppShell
