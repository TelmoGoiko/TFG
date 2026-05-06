import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
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
  deleteBlockRelationship,
  getBlockRelationships,
  getGeneratedRunById,
  updateBlockContent,
} from '../services/workspaceService'

const BlockEditorPage = () => {
  const { workspaceId, runId, blockId } = useParams()

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

  const contentDraft = draftByBlock[blockId] ?? block?.content ?? ''
  const proposedContent = proposalByBlock[blockId] ?? null

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
        <div className="editor-main-column">
          <article className="panel editor-panel">
            <h2>{block.title}</h2>
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
    </AppShell>
  )
}

export default BlockEditorPage
