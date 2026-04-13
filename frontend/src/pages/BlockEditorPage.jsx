import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ChatPanel from '../components/editor/ChatPanel'
import AppShell from '../components/layout/AppShell'
import { getWorkspaceById } from '../services/workspaceContainerService'
import {
  addChatMessage,
  getGeneratedRunById,
  requestMockAssistantEdit,
  updateBlockContent,
} from '../services/workspaceService'

const BlockEditorPage = () => {
  const { workspaceId, runId, blockId } = useParams()
  const contentRef = useRef(null)

  const [workspaceContainer, setWorkspaceContainer] = useState(null)
  const [workspace, setWorkspace] = useState(null)
  const [draftByBlock, setDraftByBlock] = useState({})
  const [selectedSnippet, setSelectedSnippet] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    Promise.all([
      getWorkspaceById(workspaceId),
      getGeneratedRunById({ workspaceId, runId }),
    ]).then(
      ([containerPayload, generatedPayload]) => {
        setWorkspaceContainer(containerPayload)
        setWorkspace(generatedPayload)
      },
    )
  }, [workspaceId, runId])

  const block = useMemo(() => {
    return workspace?.blocks.find((item) => item.id === blockId) ?? null
  }, [workspace, blockId])

  const messages = useMemo(() => {
    return workspace?.chatByBlock?.[blockId] ?? []
  }, [workspace, blockId])

  const contentDraft = draftByBlock[blockId] ?? block?.content ?? ''

  const onTextSelection = () => {
    const selection = window.getSelection()
    const selectedText = selection?.toString().trim() ?? ''

    if (!selectedText || !contentRef.current?.contains(selection.anchorNode)) {
      setSelectedSnippet('')
      return
    }

    setSelectedSnippet(selectedText)
  }

  const onSave = async () => {
    if (!block) {
      return
    }

    setIsSaving(true)
    await updateBlockContent({
      workspaceId,
      runId,
      blockId: block.id,
      content: contentDraft,
    })
    const nextWorkspace = await getGeneratedRunById({ workspaceId, runId })
    setWorkspace(nextWorkspace)
    setIsSaving(false)
  }

  const onSendMessage = async (messageContent) => {
    const mentions = selectedSnippet ? [selectedSnippet] : []

    await addChatMessage({
      workspaceId,
      runId,
      blockId,
      role: 'user',
      content: messageContent,
      mentions,
    })

    await requestMockAssistantEdit({
      workspaceId,
      runId,
      blockId,
      userMessage: messageContent,
    })

    const nextWorkspace = await getGeneratedRunById({ workspaceId, runId })
    setWorkspace(nextWorkspace)
  }

  const sidebar = (
    <div className="workspace-sidebar-block">
      <p className="workspace-sidebar-kicker">Workspace</p>
      <h2>{workspaceContainer?.name ?? 'Workspace'}</h2>
      <p className="hint">Editor mode</p>
      <Link className="btn btn-light" to={`/workspaces/${workspaceId}/generated/${runId}`}>
        Chapter Index
      </Link>
      <ul className="mini-doc-list">
        {workspace?.blocks.map((item) => (
          <li key={item.id} className={item.id === blockId ? 'active' : ''}>
            <Link to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${item.id}`}>
              {item.title}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )

  if (!workspace || !block) {
    return (
      <AppShell title="Document not found" subtitle="The requested content could not be loaded.">
        <article className="panel">
          <Link className="btn btn-light" to={`/workspaces/${workspaceId}`}>
            Back to Workspace
          </Link>
        </article>
      </AppShell>
    )
  }

  return (
    <AppShell
      title={block.title}
      subtitle={block.summary}
      sidebar={sidebar}
      actions={
        <button type="button" className="btn btn-dark" onClick={onSave} disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Chapter'}
        </button>
      }
    >
      <section className="editor-layout-prototype">
        <article className="panel editor-panel" onMouseUp={onTextSelection}>
          <h2>{block.title}</h2>
          <textarea
            ref={contentRef}
            value={contentDraft}
            onChange={(event) => {
              setDraftByBlock((previous) => ({
                ...previous,
                [blockId]: event.target.value,
              }))
            }}
            rows={24}
          />
        </article>

        <ChatPanel messages={messages} onSend={onSendMessage} selectedSnippet={selectedSnippet} />
      </section>
    </AppShell>
  )
}

export default BlockEditorPage
