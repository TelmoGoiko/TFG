import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppShell from '../components/layout/AppShell'
import {
  deleteRepositoryFile,
  getRepositoryById,
  getRepositoryFiles,
  uploadRepositoryFile,
} from '../services/repositoryService'
import { getWorkspaces } from '../services/workspaceService'

const RepositoryDetailPage = () => {
  const { repositoryId } = useParams()
  const [workspace, setWorkspace] = useState(null)
  const [knowledgeBaseFiles, setKnowledgeBaseFiles] = useState([])
  const [generatedDocs, setGeneratedDocs] = useState([])
  const [selectedFiles, setSelectedFiles] = useState([])
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState('')

  const loadWorkspace = async () => {
    const [repositoryPayload, filesPayload, generatedPayload] = await Promise.all([
      getRepositoryById(repositoryId),
      getRepositoryFiles(repositoryId),
      getWorkspaces(repositoryId),
    ])

    setWorkspace(repositoryPayload)
    setKnowledgeBaseFiles(filesPayload)
    setGeneratedDocs(generatedPayload)
  }

  useEffect(() => {
    loadWorkspace().catch((nextError) => setError(nextError.message))
  }, [repositoryId])

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
        await uploadRepositoryFile(repositoryId, file)
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
    await deleteRepositoryFile(repositoryId, fileId)
    await loadWorkspace()
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
      <Link className="btn btn-dark" to={`/workspaces/${repositoryId}/generate`}>
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
        <Link className="btn btn-dark" to={`/workspaces/${repositoryId}/generate`}>
          Generate Proposal
        </Link>
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
                <Link
                  className="btn btn-light"
                  to={`/workspaces/${repositoryId}/generated/${generatedDoc.id}`}
                >
                  Open Draft
                </Link>
              </article>
            ))}
          </div>
        </article>
      </section>
    </AppShell>
  )
}

export default RepositoryDetailPage
