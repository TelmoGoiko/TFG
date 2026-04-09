import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import EmptyState from '../components/common/EmptyState'
import AppShell from '../components/layout/AppShell'
import {
  createWorkspace,
  getWorkspaceFiles,
  getWorkspaces,
} from '../services/repositoryService'
import { getGeneratedRuns } from '../services/workspaceService'

const RepositoriesPage = () => {
  const [workspaces, setWorkspaces] = useState([])
  const [workspaceStats, setWorkspaceStats] = useState({})
  const [recentGeneratedDocs, setRecentGeneratedDocs] = useState([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  const loadDashboard = async () => {
    const workspaces = await getWorkspaces()
    setWorkspaces(workspaces)

    const statsEntries = await Promise.all(
      workspaces.map(async (workspace) => {
        const [files, generated] = await Promise.all([
          getWorkspaceFiles(workspace.id),
          getGeneratedRuns(workspace.id),
        ])

        return [workspace.id, { fileCount: files.length, generatedCount: generated.length }]
      }),
    )

    setWorkspaceStats(Object.fromEntries(statsEntries))

    const allGenerated = await Promise.all(
      workspaces.map(async (workspace) => {
        const generated = await getGeneratedRuns(workspace.id)
        return generated.map((item) => ({
          id: item.id,
          workspaceId: workspace.id,
          workspaceName: workspace.name,
          title: item.prompt,
          createdAt: item.createdAt,
          status: item.status,
        }))
      }),
    )

    const merged = allGenerated
      .flat()
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 6)

    setRecentGeneratedDocs(merged)
  }

  useEffect(() => {
    let isMounted = true

    loadDashboard().catch(() => {
      if (isMounted) {
        setError('No se pudo cargar el dashboard de workspaces.')
      }
    })

    return () => {
      isMounted = false
    }
  }, [])

  const onCreate = async (event) => {
    event.preventDefault()
    setError('')
    setIsCreating(true)

    try {
      await createWorkspace({ name, description })
      setName('')
      setDescription('')
      await loadDashboard()
    } catch (creationError) {
      setError(creationError.message)
    } finally {
      setIsCreating(false)
    }
  }

  const topWorkspace = useMemo(() => workspaces.at(0) ?? null, [workspaces])

  return (
    <AppShell
      title="Your Workspaces"
      subtitle="Selecciona un entorno de proyecto para gestionar knowledge base y documentos generados."
      actions={
        <button className="btn btn-dark" type="submit" form="create-workspace-form">
          + New Workspace
        </button>
      }
    >
      <section className="workspace-dashboard-grid">
        <article className="panel workspace-form-panel">
          <h2>Create Workspace</h2>
          <form id="create-workspace-form" onSubmit={onCreate} className="stack-form">
            <label>
              Name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Project Alpha"
              />
            </label>
            <label>
              Context
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={4}
                placeholder="Workspace scope and architectural purpose"
              />
            </label>
            {error ? <p className="error-text">{error}</p> : null}
            <button className="btn btn-dark" type="submit" disabled={isCreating}>
              {isCreating ? 'Creating...' : 'Create Workspace'}
            </button>
          </form>
        </article>

        <article className="panel">
          <h2>Workspace Snapshot</h2>
          {topWorkspace ? (
            <div className="primary-workspace-card">
              <div>
                <h3>{topWorkspace.name}</h3>
                <p>{topWorkspace.description || 'Workspace activo sin descripcion.'}</p>
              </div>
              <div className="workspace-metrics">
                <div>
                  <strong>{workspaceStats[topWorkspace.id]?.fileCount ?? 0}</strong>
                  <span>Input Documents</span>
                </div>
                <div>
                  <strong>{workspaceStats[topWorkspace.id]?.generatedCount ?? 0}</strong>
                  <span>Generated Outputs</span>
                </div>
              </div>
              <Link className="btn btn-light" to={`/workspaces/${topWorkspace.id}`}>
                Open Workspace
              </Link>
            </div>
          ) : (
            <EmptyState
              title="No workspaces yet"
              description="Crea el primer workspace para empezar con la base documental y la generacion asistida."
            />
          )}
        </article>

        <article className="panel workspace-list-panel">
          <h2>All Workspaces</h2>
          {workspaces.length === 0 ? (
            <p className="hint">Todavia no hay workspaces.</p>
          ) : (
            <ul className="workspace-card-list">
              {workspaces.map((workspace) => (
                <li key={workspace.id}>
                  <div>
                    <h3>{workspace.name}</h3>
                    <p>{workspace.description || 'Sin descripcion'}</p>
                  </div>
                  <div className="workspace-mini-metrics">
                    <span>{workspaceStats[workspace.id]?.fileCount ?? 0} docs</span>
                    <span>{workspaceStats[workspace.id]?.generatedCount ?? 0} generated</span>
                  </div>
                  <div className="row-actions">
                    <Link className="btn btn-light" to={`/workspaces/${workspace.id}`}>
                      Open
                    </Link>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="panel activity-panel">
          <h2>Recent Activity</h2>
          {recentGeneratedDocs.length === 0 ? (
            <p className="hint">Todavia no hay documentos generados.</p>
          ) : (
            <table className="activity-table">
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Workspace</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentGeneratedDocs.map((doc) => (
                  <tr key={doc.id}>
                    <td>{doc.title}</td>
                    <td>{doc.workspaceName}</td>
                    <td>
                      <span className="status-pill">{doc.status.toUpperCase()}</span>
                    </td>
                    <td>
                      <Link
                        className="table-link"
                        to={`/workspaces/${doc.workspaceId}/generated/${doc.id}`}
                      >
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </article>
      </section>
    </AppShell>
  )
}

export default RepositoriesPage
