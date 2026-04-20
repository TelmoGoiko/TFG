import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/layout/AppShell'
import {
  deleteWorkspace,
  deleteWorkspaceFile,
  getWorkspaceById,
  getWorkspaceFiles,
  uploadWorkspaceFile,
} from '../services/workspaceContainerService'
import { deleteGeneratedRun, getGeneratedRuns } from '../services/workspaceService'

const WorkspaceDetailPage = () => {
  const { workspaceId } = useParams()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState(null)
  const [knowledgeBaseFiles, setKnowledgeBaseFiles] = useState([])
  const [generatedDocs, setGeneratedDocs] = useState([])
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState('')
  const [deletingRunId, setDeletingRunId] = useState(null)

  const loadWorkspace = async () => {
    const [workspacePayload, filesPayload, generatedPayload] = await Promise.all([
      getWorkspaceById(workspaceId),
      getWorkspaceFiles(workspaceId),
      getGeneratedRuns(workspaceId),
    ])

    setWorkspace(workspacePayload)
    setKnowledgeBaseFiles(filesPayload)
    setGeneratedDocs(generatedPayload)
  }

  useEffect(() => {
    loadWorkspace().catch((nextError) => setError(nextError.message))
  }, [workspaceId])

  const onUploadFiles = async (event) => {
    event.preventDefault()
    setError('')
    setIsUploading(true)

    if (selectedFiles.length === 0) {
      setError('Please select at least one file.')
      setIsUploading(false)
      return
    }

    try {
      for (const file of selectedFiles) {
        await uploadWorkspaceFile(workspaceId, file)
      }

      setSelectedFiles([])
      await loadWorkspace()
    } catch (creationError) {
      setError(creationError.message)
    } finally {
      setIsUploading(false)
    }
  }

  const onDeleteFile = async (fileId) => {
    await deleteWorkspaceFile(workspaceId, fileId)
    await loadWorkspace()
  }

  const onDeleteWorkspace = async () => {
    if (!workspace) {
      return
    }

    const confirmed = window.confirm(
      `Delete workspace "${workspace.name}"? This also removes files and generated runs.`,
    )
    if (!confirmed) {
      return
    }

    await deleteWorkspace(workspaceId)
    navigate('/workspaces')
  }

  const onDeleteGeneratedDoc = async (runId) => {
    const confirmed = window.confirm('Delete this generated document? This action cannot be undone.')
    if (!confirmed) {
      return
    }

    setError('')
    setDeletingRunId(runId)

    try {
      await deleteGeneratedRun({ workspaceId, runId })
      await loadWorkspace()
    } catch (deletionError) {
      setError(deletionError.message)
    } finally {
      setDeletingRunId(null)
    }
  }

  const generatedSummary = useMemo(() => {
    const latest = generatedDocs
      .slice()
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
      .slice(0, 2)

    return latest
  }, [generatedDocs])

  if (!workspace) {
    return (
      <AppShell title="Workspace" subtitle="Loading workspace...">
        <article className="panel">
          <p className="hint">Cargando informacion del workspace.</p>
        </article>
      </AppShell>
    )
  }

  const sidebar = (
    <div className="workspace-sidebar-block">
      <p className="workspace-sidebar-kicker">Project</p>
      <h2>{workspace.name}</h2>
      <p className="hint">{workspace.description || 'Sin descripcion de workspace.'}</p>
      <Link className="btn btn-dark" to={`/workspaces/${workspaceId}/generate`}>
        + New Document
      </Link>
      <nav className="workspace-sidebar-nav" aria-label="Workspace sections">
        <a className="active" href="#knowledge-base">
          Knowledge Base
        </a>
        <a href="#generated-docs">Generated Documents</a>
      </nav>
    </div>
  )

  return (
    <AppShell
      title={workspace.name}
      subtitle="Manage input sources and generated architectural outputs."
      sidebar={sidebar}
      actions={
        <div className="row-actions">
          <button type="button" className="btn btn-light" onClick={onDeleteWorkspace}>
            Delete Workspace
          </button>
          <Link className="btn btn-dark" to={`/workspaces/${workspaceId}/generate`}>
            Generate Proposal
          </Link>
        </div>
      }
    >
      {error ? (
        <article className="panel">
          <p className="error-text">{error}</p>
        </article>
      ) : null}

      <section className="workspace-detail-grid">
        <article id="knowledge-base" className="panel">
          <div className="section-head">
            <h2>Knowledge Base</h2>
          </div>

          <form className="stack-form" onSubmit={onUploadFiles}>
            <label>
              Upload input files
              <input
                type="file"
                multiple
                onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
              />
            </label>
            <button type="submit" className="btn btn-light" disabled={isUploading}>
              {isUploading ? 'Uploading...' : 'Add Source'}
            </button>
          </form>

          <ul className="knowledge-list">
            {knowledgeBaseFiles.map((file) => (
              <li key={file.id}>
                <div>
                  <strong>{file.fileName}</strong>
                  <p>
                    {file.mimeType} · {Math.max(1, Math.round(file.sizeBytes / 1024))} KB
                  </p>
                </div>
                <button className="btn btn-light" type="button" onClick={() => onDeleteFile(file.id)}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </article>

        <article id="generated-docs" className="panel">
          <div className="section-head">
            <h2>Generated Documents</h2>
            <span className="hint">{generatedDocs.length} total</span>
          </div>

          <div className="generated-list-grid">
            {generatedSummary.map((generatedDoc) => (
              <article className="generated-card" key={generatedDoc.id}>
                <p className="chip">{generatedDoc.status.toUpperCase()}</p>
                <h3>{generatedDoc.prompt}</h3>
                <p className="hint">Last edit: {new Date(generatedDoc.createdAt).toLocaleString()}</p>
                <div className="row-actions">
                  <Link
                    className="btn btn-light"
                    to={`/workspaces/${workspaceId}/generated/${generatedDoc.id}`}
                  >
                    Open Draft
                  </Link>
                  <button
                    className="btn btn-light"
                    type="button"
                    disabled={deletingRunId === generatedDoc.id}
                    onClick={() => onDeleteGeneratedDoc(generatedDoc.id)}
                  >
                    {deletingRunId === generatedDoc.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </article>
      </section>
    </AppShell>
  )
}

export default WorkspaceDetailPage
