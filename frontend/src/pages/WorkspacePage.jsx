import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import BlockList from '../components/editor/BlockList'
import AppShell from '../components/layout/AppShell'
import { getRepositoryById } from '../services/repositoryService'
import { getWorkspaceById } from '../services/workspaceService'

const WorkspacePage = () => {
  const { repositoryId, workspaceId } = useParams()
  const [workspaceContainer, setWorkspaceContainer] = useState(null)
  const [generatedDoc, setGeneratedDoc] = useState(null)

  useEffect(() => {
    Promise.all([getRepositoryById(repositoryId), getWorkspaceById(workspaceId)]).then(
      ([containerPayload, generatedPayload]) => {
        setWorkspaceContainer(containerPayload)
        setGeneratedDoc(generatedPayload)
      },
    )
  }, [repositoryId, workspaceId])

  const sidebar = useMemo(() => {
    if (!workspaceContainer) {
      return null
    }

    return (
      <div className="workspace-sidebar-block">
        <p className="workspace-sidebar-kicker">Workspace</p>
        <h2>{workspaceContainer.name}</h2>
        <p className="hint">{workspaceContainer.description || 'No description available.'}</p>
        <Link className="btn btn-light" to={`/workspaces/${repositoryId}`}>
          Back to Workspace
        </Link>
      </div>
    )
  }, [repositoryId, workspaceContainer])

  if (!generatedDoc) {
    return (
      <AppShell title="Generated Document" subtitle="Loading document...">
        <article className="panel">
          <p className="hint">Loading generated workspace content.</p>
        </article>
      </AppShell>
    )
  }

  return (
    <AppShell
      title={generatedDoc.prompt}
      subtitle="Select a chapter to open the editor and Copilot assistance."
      sidebar={sidebar}
      actions={
        <Link className="btn btn-dark" to={`/workspaces/${repositoryId}/generate`}>
          New Generation
        </Link>
      }
    >
      <section className="panel">
        <div className="section-head">
          <h2>Proposal Chapters</h2>
          <span className="hint">{generatedDoc.blocks.length} blocks</span>
        </div>
        <BlockList workspaceId={workspaceId} repositoryId={repositoryId} blocks={generatedDoc.blocks} />
      </section>
    </AppShell>
  )
}

export default WorkspacePage
