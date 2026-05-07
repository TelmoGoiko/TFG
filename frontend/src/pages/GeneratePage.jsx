import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/layout/AppShell'
import { getWorkspaceById, getWorkspaceFiles } from '../services/workspaceContainerService'
import { createGeneratedRun, deleteGeneratedRun, getGeneratedRuns } from '../services/workspaceService'

const GeneratePage = () => {
  const { workspaceId } = useParams()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState(null)
  const [workspaceFiles, setWorkspaceFiles] = useState([])
  const [generatedDocs, setGeneratedDocs] = useState([])
  const [selectedFileIds, setSelectedFileIds] = useState([])
  const [prompt, setPrompt] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [deletingRunId, setDeletingRunId] = useState(null)

  useEffect(() => {
    Promise.all([
      getWorkspaceById(workspaceId),
      getWorkspaceFiles(workspaceId),
      getGeneratedRuns(workspaceId),
    ])
      .then(([workspacePayload, filesPayload, generatedPayload]) => {
        setWorkspace(workspacePayload)
        setWorkspaceFiles(filesPayload)
        setGeneratedDocs(generatedPayload)
      })
      .catch((nextError) => setError(nextError.message))
  }, [workspaceId])

  const selectedFiles = useMemo(() => {
    return workspaceFiles.filter((file) => selectedFileIds.includes(file.id))
  }, [workspaceFiles, selectedFileIds])

  const toggleFileSelection = (fileId) => {
    setSelectedFileIds((previous) => {
      if (previous.includes(fileId)) {
        return previous.filter((id) => id !== fileId)
      }
      return [...previous, fileId]
    })
  }

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (!prompt.trim()) {
      setError('Please provide a generation prompt.')
      return
    }

    setIsSubmitting(true)

    try {
      const generatedDoc = await createGeneratedRun({
        workspaceId,
        prompt: prompt.trim(),
        referenceFiles: selectedFiles,
      })
      navigate(`/workspaces/${workspaceId}/generated/${generatedDoc.id}`)
    } catch (submissionError) {
      setError(submissionError.message)
    } finally {
      setIsSubmitting(false)
    }
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
      setGeneratedDocs((previous) => previous.filter((generatedDoc) => generatedDoc.id !== runId))
    } catch (deletionError) {
      setError(deletionError.message)
    } finally {
      setDeletingRunId(null)
    }
  }

  return (
    <AppShell
      title="Generate Proposal"
      subtitle={workspace ? `${workspace.name} · Synthesize a new draft` : 'Workspace generation'}
      actions={
        <Link className="btn btn-light" to={`/workspaces/${workspaceId}`}>
          Back to Workspace
        </Link>
      }
    >
      <section className="panel generate-panel">
        <form onSubmit={onSubmit} className="stack-form">
          <label>
            Describe the document you want to generate
            <textarea
              rows={7}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Describe objective, audience, constraints and expected structure..."
            />
          </label>

          <div>
            <p className="section-label">Selected Knowledge Sources</p>
            <ul className="knowledge-chip-list">
              {workspaceFiles.map((file) => {
                const isSelected = selectedFileIds.includes(file.id)
                return (
                  <li key={file.id}>
                    <button
                      className={`chip-toggle ${isSelected ? 'selected' : ''}`}
                      type="button"
                      onClick={() => toggleFileSelection(file.id)}
                    >
                      {file.fileName}
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>

          {error ? <p className="error-text">{error}</p> : null}

          <div className="generate-actions">
            <p className="hint">{selectedFiles.length} context files selected</p>
            <button type="submit" className="btn btn-dark" disabled={isSubmitting}>
              {isSubmitting ? 'Generating...' : 'Generate Proposal'}
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Recent Activity</h2>
          <Link className="table-link" to={`/workspaces/${workspaceId}`}>
            View workspace
          </Link>
        </div>

        <div className="generated-list-grid">
          {generatedDocs.slice(0, 4).map((generatedDoc) => (
            <article className="generated-card" key={generatedDoc.id}>
              <p className="chip">{generatedDoc.status.toUpperCase()}</p>
              <h3>{generatedDoc.prompt}</h3>
              <p className="hint">{new Date(generatedDoc.createdAt).toLocaleString()}</p>
              <div className="row-actions">
                <Link
                  className="btn btn-light"
                  to={`/workspaces/${workspaceId}/generated/${generatedDoc.id}`}
                >
                  Open Draft
                </Link>
                <button
                  type="button"
                  className="btn btn-light"
                  disabled={deletingRunId === generatedDoc.id}
                  onClick={() => onDeleteGeneratedDoc(generatedDoc.id)}
                >
                  {deletingRunId === generatedDoc.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  )
}

export default GeneratePage
