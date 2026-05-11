import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link, useNavigate, useParams } from 'react-router-dom'
import remarkGfm from 'remark-gfm'
import BlockRelationships from '../components/editor/BlockRelationships'
import ChatPanel from '../components/editor/ChatPanel'
import ImpactSuggestions from '../components/editor/ImpactSuggestions'
import AppShell from '../components/layout/AppShell'
import { getWorkspaceById } from '../services/workspaceContainerService'
import {
  applyImpactSuggestion,
  checkBlockImpact,
  clearBlockMessages,
  chatWithBlockAgent,
  createBlockRelationship,
  createBlock,
  deleteBlock,
  deleteBlockRelationship,
  getBlockRelationships,
  getGeneratedRunById,
  updateBlockContent,
} from '../services/workspaceService'

const BlockEditorPage = () => {
  const { workspaceId, runId, blockId } = useParams()
  const navigate = useNavigate()

  const [workspaceContainer, setWorkspaceContainer] = useState(null)
  const [workspace, setWorkspace] = useState(null)
  const [draftByBlock, setDraftByBlock] = useState({})
  const [proposalByBlock, setProposalByBlock] = useState({})
  const [conversationIdByBlock, setConversationIdByBlock] = useState({})
  const [relationships, setRelationships] = useState([])
  const [impactSuggestions, setImpactSuggestions] = useState([])
  const [isSaving, setIsSaving] = useState(false)
  const [isApplyingProposal, setIsApplyingProposal] = useState(false)
  const [isClearingChat, setIsClearingChat] = useState(false)
  const [isSendingMessage, setIsSendingMessage] = useState(false)
  const [isApplyingImpact, setIsApplyingImpact] = useState(false)
  const [isCreatingBlock, setIsCreatingBlock] = useState(false)
  const [isDeletingBlock, setIsDeletingBlock] = useState(false)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newBlockTitle, setNewBlockTitle] = useState('')
  const [newBlockSummary, setNewBlockSummary] = useState('')
  const [newBlockContent, setNewBlockContent] = useState('')
  const [newBlockType, setNewBlockType] = useState('chapter')

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

  useEffect(() => {
    if (!blockId || !workspaceId || !runId) return
    getBlockRelationships({ workspaceId, runId, blockId }).then(setRelationships)
  }, [blockId, workspaceId, runId, workspace])

  const block = useMemo(() => {
    return workspace?.blocks.find((item) => item.id === blockId) ?? null
  }, [workspace, blockId])

  const messages = useMemo(() => {
    return workspace?.chatByBlock?.[blockId] ?? []
  }, [workspace, blockId])

  const orderedBlocks = useMemo(() => {
    if (!workspace?.blocks) return []
    return [...workspace.blocks].sort((a, b) => a.order - b.order)
  }, [workspace])

  const contentDraft = draftByBlock[blockId] ?? block?.content ?? ''
  const proposedContent = proposalByBlock[blockId] ?? null
  const isDirty = Boolean(block && contentDraft !== block.content)

  const normalizeFileName = (value) => {
    if (!value) return ''
    return value
      .toLowerCase()
      .replace(/^[./]+/, '')
      .split('/')
      .pop()
  }

  const blockByFileName = useMemo(() => {
    const map = new Map()
    ;(workspace?.blocks ?? []).forEach((item) => {
      if (!item.fileName) return
      const normalized = normalizeFileName(item.fileName)
      if (normalized) {
        map.set(normalized, item)
        if (!normalized.endsWith('.md')) {
          map.set(`${normalized}.md`, item)
        }
      }
    })
    return map
  }, [workspace])

  const isExternalLink = (href) => /^(https?:)?\/\//i.test(href) || href.startsWith('mailto:')

  const loadRelationships = () => {
    if (blockId) {
      getBlockRelationships({ workspaceId, runId, blockId }).then(setRelationships)
    }
  }

  const refreshWorkspace = async () => {
    const nextWorkspace = await getGeneratedRunById({ workspaceId, runId })
    setWorkspace(nextWorkspace)
  }

  const onSave = async () => {
    if (!block) {
      return
    }

    setIsSaving(true)
    try {
      const impact = await checkBlockImpact({
        workspaceId,
        runId,
        blockId: block.id,
        newContent: contentDraft,
      })
      setImpactSuggestions(impact)

      await updateBlockContent({
        workspaceId,
        runId,
        blockId: block.id,
        content: contentDraft,
      })
      await refreshWorkspace()
      loadRelationships()
    } finally {
      setIsSaving(false)
    }
  }

  useEffect(() => {
    if (!block || !blockId) return
    if (isSaving) return
    if (contentDraft === block.content) return

    const timeoutId = setTimeout(() => {
      onSave()
    }, 1500)

    return () => clearTimeout(timeoutId)
  }, [block, blockId, contentDraft, isSaving])

  const onSendMessage = async (messageContent) => {
    setIsSendingMessage(true)

    try {
      const response = await chatWithBlockAgent({
        workspaceId,
        runId,
        blockId,
        userMessage: messageContent,
        conversationId: conversationIdByBlock[blockId],
      })

      if (response.conversationId !== undefined && response.conversationId !== null) {
        setConversationIdByBlock((previous) => ({
          ...previous,
          [blockId]: response.conversationId,
        }))
      }

      if (response.applied && typeof response.updatedContent === 'string') {
        setDraftByBlock((previous) => ({
          ...previous,
          [blockId]: response.updatedContent,
        }))
      }

      if (!response.applied && typeof response.proposedContent === 'string') {
        setProposalByBlock((previous) => ({
          ...previous,
          [blockId]: response.proposedContent,
        }))
      }

      if (Array.isArray(response.impactSuggestions)) {
        setImpactSuggestions(response.impactSuggestions)
      }

      await refreshWorkspace()
    } finally {
      setIsSendingMessage(false)
    }
  }

  const onApplyProposal = async () => {
    if (!block || !proposedContent) {
      return
    }

    setIsApplyingProposal(true)
    try {
      const updatedBlock = await updateBlockContent({
        workspaceId,
        runId,
        blockId: block.id,
        content: proposedContent,
      })

      setDraftByBlock((previous) => ({
        ...previous,
        [block.id]: updatedBlock.content,
      }))

      setProposalByBlock((previous) => {
        const next = { ...previous }
        delete next[block.id]
        return next
      })

      await refreshWorkspace()
    } finally {
      setIsApplyingProposal(false)
    }
  }

  const onRejectProposal = () => {
    if (!blockId) {
      return
    }

    setProposalByBlock((previous) => {
      const next = { ...previous }
      delete next[blockId]
      return next
    })
  }

  const onClearMessages = async () => {
    if (!blockId) {
      return
    }

    const confirmed = window.confirm('This will delete all previous messages in this block. Continue?')
    if (!confirmed) {
      return
    }

    setIsClearingChat(true)
    await clearBlockMessages({ workspaceId, runId, blockId })
    setConversationIdByBlock((previous) => {
      const next = { ...previous }
      delete next[blockId]
      return next
    })
    await refreshWorkspace()
    setIsClearingChat(false)
  }

  const onCreateRelationship = async ({ targetBlockId, relationshipType, description }) => {
    await createBlockRelationship({
      workspaceId,
      runId,
      blockId,
      targetBlockId,
      relationshipType,
      description,
    })
    loadRelationships()
  }

  const onDeleteRelationship = async (relationshipId) => {
    await deleteBlockRelationship({ workspaceId, runId, blockId, relationshipId })
    loadRelationships()
  }

  const onApplyImpact = async (suggestion) => {
    setIsApplyingImpact(true)
    try {
      await applyImpactSuggestion({
        workspaceId,
        runId,
        blockId: suggestion.affectedBlockId,
        suggestion: suggestion.suggestion,
      })
      setImpactSuggestions((prev) => prev.filter((s) => s.affectedBlockId !== suggestion.affectedBlockId))
    } finally {
      setIsApplyingImpact(false)
    }
  }

  const onDismissImpact = (affectedBlockId) => {
    setImpactSuggestions((prev) => prev.filter((s) => s.affectedBlockId !== affectedBlockId))
  }

  const onCreateBlock = async (event) => {
    event.preventDefault()
    if (!newBlockTitle.trim()) {
      return
    }

    const targetId = blockId || orderedBlocks[orderedBlocks.length - 1]?.id || null

    setIsCreatingBlock(true)
    try {
      const created = await createBlock({
        workspaceId,
        runId,
        title: newBlockTitle.trim(),
        summary: newBlockSummary,
        content: newBlockContent,
        blockType: newBlockType,
        insertAfterBlockId: targetId,
      })

      setNewBlockTitle('')
      setNewBlockSummary('')
      setNewBlockContent('')
      setIsCreateModalOpen(false)
      await refreshWorkspace()

      if (created?.id) {
        navigate(`/workspaces/${workspaceId}/generated/${runId}/blocks/${created.id}`)
      }
    } finally {
      setIsCreatingBlock(false)
    }
  }

  const onDeleteBlock = async () => {
    if (!blockId) {
      return
    }

    const confirmed = window.confirm('This will delete the current block. Continue?')
    if (!confirmed) {
      return
    }

    const currentIndex = orderedBlocks.findIndex((item) => item.id === blockId)
    const nextBlockId =
      orderedBlocks[currentIndex + 1]?.id || orderedBlocks[currentIndex - 1]?.id || null

    setIsDeletingBlock(true)
    try {
      await deleteBlock({ workspaceId, runId, blockId })
      await refreshWorkspace()

      if (nextBlockId) {
        navigate(`/workspaces/${workspaceId}/generated/${runId}/blocks/${nextBlockId}`)
      } else {
        navigate(`/workspaces/${workspaceId}/generated/${runId}`)
      }
    } finally {
      setIsDeletingBlock(false)
    }
  }

  const sidebar = (
    <div className="workspace-sidebar-block">
      <p className="workspace-sidebar-kicker">Workspace</p>
      <h2>{workspaceContainer?.name ?? 'Workspace'}</h2>
      <p className="hint">Editor mode</p>
      <ul className="mini-doc-list">
        {orderedBlocks.map((item) => (
          <li key={item.id} className={item.id === blockId ? 'active' : ''}>
            <Link to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${item.id}`}>
              {item.title}
            </Link>
          </li>
        ))}
      </ul>
      <section className="panel">
        <p className="section-label">Add block</p>
        <p className="hint">Create a new chapter in this run.</p>
        <button className="btn btn-dark" type="button" onClick={() => setIsCreateModalOpen(true)}>
          Add block
        </button>
      </section>
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
        <>
          <Link
            className="btn btn-light"
            to={`/workspaces/${workspaceId}/generated/${runId}/view`}
          >
            See Full Document
          </Link>
          <button type="button" className="btn btn-light" onClick={onDeleteBlock} disabled={isDeletingBlock}>
            {isDeletingBlock ? 'Deleting...' : 'Delete Block'}
          </button>
          <span className="hint">{isSaving ? 'Saving...' : isDirty ? 'Not Saved' : 'Saved'}</span>
        </>
      }
    >
      <section className="editor-layout-prototype">
        <div className="editor-main-column">
          <article className="panel editor-panel">
            <h2>{block.title}</h2>
            <div className="editor-split">
              <div className="editor-input">
                <div className="editor-label">Markdown</div>
                <textarea
                  value={contentDraft}
                  onChange={(event) => {
                    setDraftByBlock((previous) => ({
                      ...previous,
                      [blockId]: event.target.value,
                    }))
                  }}
                  rows={24}
                />
              </div>
              <div className="editor-preview">
                <div className="editor-label">Preview</div>
                <div className="markdown-preview">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      a: ({ href, children }) => {
                        if (!href) return <span>{children}</span>
                        if (href.startsWith('#')) {
                          return <a href={href}>{children}</a>
                        }
                        if (isExternalLink(href)) {
                          return (
                            <a href={href} target="_blank" rel="noreferrer">
                              {children}
                            </a>
                          )
                        }
                        const [path] = href.split('#')
                        const normalized = normalizeFileName(path)
                        const target = blockByFileName.get(normalized)
                        if (target) {
                          return (
                            <Link
                              to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${target.id}`}
                            >
                              {children}
                            </Link>
                          )
                        }
                        return <span className="broken-link">{children}</span>
                      },
                    }}
                  >
                    {contentDraft || ''}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </article>

          <aside className="side-panel">
            <ImpactSuggestions
              suggestions={impactSuggestions}
              onApply={onApplyImpact}
              onDismiss={onDismissImpact}
              workspaceId={workspaceId}
              runId={runId}
            />
            <BlockRelationships
              block={block}
              blocks={workspace.blocks}
              relationships={relationships}
              onCreate={onCreateRelationship}
              onDelete={onDeleteRelationship}
              workspaceId={workspaceId}
              runId={runId}
            />
          </aside>
        </div>

        <ChatPanel
          messages={messages}
          proposedContent={proposedContent}
          onSend={onSendMessage}
          onApplyProposal={onApplyProposal}
          onRejectProposal={onRejectProposal}
          onClear={onClearMessages}
          isApplyingProposal={isApplyingProposal}
          isClearing={isClearingChat}
          isSending={isSendingMessage}
        />
      </section>
      {isCreateModalOpen && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="Add block"
          onClick={() => setIsCreateModalOpen(false)}
        >
          <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
            <header className="modal-header">
              <div>
                <p className="section-label">Add block</p>
                <h3>Create a new chapter</h3>
              </div>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setIsCreateModalOpen(false)}
              >
                Close
              </button>
            </header>
            <form className="stack-form" onSubmit={onCreateBlock}>
              <label>
                Title
                <input
                  value={newBlockTitle}
                  onChange={(event) => setNewBlockTitle(event.target.value)}
                  placeholder="New chapter title"
                  required
                />
              </label>
              <label>
                Summary
                <input
                  value={newBlockSummary}
                  onChange={(event) => setNewBlockSummary(event.target.value)}
                  placeholder="Optional summary"
                />
              </label>
              <label>
                Type
                <select
                  value={newBlockType}
                  onChange={(event) => setNewBlockType(event.target.value)}
                >
                  <option value="chapter">Chapter</option>
                  <option value="index">Index</option>
                  <option value="closing">Closing</option>
                </select>
              </label>
              <label>
                Initial content
                <textarea
                  value={newBlockContent}
                  onChange={(event) => setNewBlockContent(event.target.value)}
                  rows={6}
                  placeholder="Starter markdown..."
                />
              </label>
              <div className="modal-actions">
                <button
                  className="btn btn-ghost"
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                >
                  Cancel
                </button>
                <button className="btn btn-dark" type="submit" disabled={isCreatingBlock}>
                  {isCreatingBlock ? 'Creating...' : 'Create block'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  )
}

export default BlockEditorPage
