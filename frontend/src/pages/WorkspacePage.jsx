import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import BlockList from '../components/editor/BlockList'
import AppShell from '../components/layout/AppShell'
import { getWorkspaceById } from '../services/repositoryService'
import { getGeneratedRunById } from '../services/workspaceService'

const WorkspacePage = () => {
  const { workspaceId, runId } = useParams()
  const [workspaceContainer, setWorkspaceContainer] = useState(null)
  const [generatedDoc, setGeneratedDoc] = useState(null)

  useEffect(() => {
    Promise.all([
      getWorkspaceById(workspaceId),
      getGeneratedRunById({ workspaceId, runId }),
    ]).then(
      ([containerPayload, generatedPayload]) => {
        setWorkspaceContainer(containerPayload)
        setGeneratedDoc(generatedPayload)
      },
    )
  }, [workspaceId, runId])

  const sidebar = useMemo(() => {
    if (!workspaceContainer) {
      return null
    }

    return (
      <div className="workspace-sidebar-block">
        <p className="workspace-sidebar-kicker">Workspace</p>
        <h2>{workspaceContainer.name}</h2>
        <p className="hint">{workspaceContainer.description || 'No description available.'}</p>
        <Link className="btn btn-light" to={`/workspaces/${workspaceId}`}>
          Back to Workspace
        </Link>
      </div>
    )
  }, [workspaceId, workspaceContainer])

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
        <Link className="btn btn-dark" to={`/workspaces/${workspaceId}/generate`}>
          New Generation
        </Link>
      }
    >
      <section className="panel">
        <div className="section-head">
          <h2>Proposal Chapters</h2>
          <span className="hint">{generatedDoc.blocks.length} blocks</span>
        </div>
        <BlockList workspaceId={workspaceId} runId={runId} blocks={generatedDoc.blocks} />
      </section>
    </AppShell>
  )
}

export default WorkspacePage
