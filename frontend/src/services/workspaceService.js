import { request } from './apiClient'

const normalizeWorkspace = (workspace) => {
  return {
    id: workspace.id,
    workspaceId: workspace.workspace_id,
    prompt: workspace.prompt,
    status: workspace.status,
    createdAt: workspace.created_at,
  }
}

const normalizeBlock = (block) => {
  return {
    id: block.id,
    workspaceRunId: block.workspace_run_id,
    order: block.order_index,
    title: block.title,
    type: block.block_type,
    summary: block.summary,
    fileName: block.file_name,
    content: block.content,
    meta: block.meta || '{}',
  }
}

const normalizeMessage = (message) => {
  return {
    id: message.id,
    blockId: message.block_id,
    role: message.role,
    content: message.content,
    mentions: message.mentions,
    createdAt: message.created_at,
  }
}

const normalizeImpactSuggestion = (s) => {
  return {
    affectedBlockId: s.affected_block_id,
    affectedBlockTitle: s.affected_block_title,
    suggestion: s.suggestion,
    reason: s.reason,
    relationshipType: s.relationship_type,
  }
}

const normalizeBlockAgentChat = (payload) => {
  return {
    assistantMessage: payload.assistant_message,
    conversationId: payload.conversation_id,
    applied: payload.applied,
    proposedContent: payload.proposed_content,
    updatedContent: payload.updated_content,
    impactSuggestions: (payload.impact_suggestions || []).map(normalizeImpactSuggestion),
  }
}

const normalizeRelationship = (rel) => {
  return {
    id: rel.id,
    sourceBlockId: rel.source_block_id,
    targetBlockId: rel.target_block_id,
    relationshipType: rel.relationship_type,
    description: rel.description,
    autoCreated: rel.auto_created,
    createdAt: rel.created_at,
    direction: rel.direction,
    otherBlock: rel.other_block,
  }
}

const getGeneratedRuns = async (workspaceId) => {
  const payload = await request(`/workspaces/${workspaceId}/generated`)
  return payload.map(normalizeWorkspace)
}

const getGeneratedRunById = async ({ workspaceId, runId }) => {
  const workspace = await request(`/workspaces/${workspaceId}/generated/${runId}`)
  const blocksPayload = await request(`/workspaces/${workspaceId}/generated/${runId}/blocks`)
  const blocks = blocksPayload.map(normalizeBlock)

  const messagesByBlock = await Promise.all(
    blocks.map(async (block) => {
      const messagesPayload = await request(
        `/workspaces/${workspaceId}/generated/${runId}/blocks/${block.id}/messages`,
      )
      return [block.id, messagesPayload.map(normalizeMessage)]
    }),
  )

  return {
    ...normalizeWorkspace(workspace),
    blocks,
    chatByBlock: Object.fromEntries(messagesByBlock),
  }
}

const createGeneratedRun = async ({ workspaceId, prompt, referenceFiles }) => {
  const payload = await request(`/workspaces/${workspaceId}/generated`, {
    method: 'POST',
    body: JSON.stringify({
      prompt,
      reference_document_ids: [],
      reference_file_ids: referenceFiles.map((file) => file.id),
    }),
  })

  return normalizeWorkspace(payload)
}

const deleteGeneratedRun = async ({ workspaceId, runId }) => {
  await request(`/workspaces/${workspaceId}/generated/${runId}`, {
    method: 'DELETE',
  })
}

const updateBlockContent = async ({ workspaceId, runId, blockId, content }) => {
  const payload = await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        content,
      }),
    },
  )

  return normalizeBlock(payload)
}

const createBlock = async ({
  workspaceId,
  runId,
  title,
  summary,
  content,
  blockType,
  fileName,
  orderIndex,
  insertBeforeBlockId,
  insertAfterBlockId,
}) => {
  const payload = await request(`/workspaces/${workspaceId}/generated/${runId}/blocks`, {
    method: 'POST',
    body: JSON.stringify({
      title,
      summary: summary ?? '',
      content: content ?? '',
      block_type: blockType ?? 'chapter',
      file_name: fileName ?? null,
      order_index: typeof orderIndex === 'number' ? orderIndex : null,
      insert_before_block_id: insertBeforeBlockId ?? null,
      insert_after_block_id: insertAfterBlockId ?? null,
    }),
  })

  return normalizeBlock(payload)
}

const deleteBlock = async ({ workspaceId, runId, blockId }) => {
  await request(`/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}`, {
    method: 'DELETE',
  })
}

const addChatMessage = async ({ workspaceId, runId, blockId, role, content, mentions }) => {
  const payload = await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({
        role,
        content,
        mentions: mentions ?? [],
      }),
    },
  )

  return normalizeMessage(payload)
}

const chatWithBlockAgent = async ({
  workspaceId,
  runId,
  blockId,
  userMessage,
  conversationId,
}) => {
  const response = await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/agent-chat`,
    {
      method: 'POST',
      body: JSON.stringify({
        user_message: userMessage,
        auto_apply: false,
        conversation_id: conversationId ?? null,
      }),
    },
  )

  return normalizeBlockAgentChat(response)
}

const clearBlockMessages = async ({ workspaceId, runId, blockId }) => {
  await request(`/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/messages`, {
    method: 'DELETE',
  })
}

const getBlockRelationships = async ({ workspaceId, runId, blockId }) => {
  const payload = await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/relationships`,
  )
  return payload.map(normalizeRelationship)
}

const createBlockRelationship = async ({ workspaceId, runId, blockId, targetBlockId, relationshipType, description }) => {
  const payload = await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/relationships`,
    {
      method: 'POST',
      body: JSON.stringify({
        target_block_id: targetBlockId,
        relationship_type: relationshipType,
        description: description || '',
      }),
    },
  )
  return normalizeRelationship(payload)
}

const deleteBlockRelationship = async ({ workspaceId, runId, blockId, relationshipId }) => {
  await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/relationships/${relationshipId}`,
    { method: 'DELETE' },
  )
}

const checkBlockImpact = async ({ workspaceId, runId, blockId, newContent }) => {
  const payload = await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/check-impact`,
    {
      method: 'POST',
      body: JSON.stringify({ content: newContent }),
    },
  )
  return payload.map(normalizeImpactSuggestion)
}

const applyImpactSuggestion = async ({ workspaceId, runId, blockId, suggestion }) => {
  const payload = await request(
    `/workspaces/${workspaceId}/generated/${runId}/blocks/${blockId}/apply-suggestion`,
    {
      method: 'POST',
      body: JSON.stringify({ suggestion }),
    },
  )
  return normalizeBlock(payload)
}

export {
  getGeneratedRuns,
  getGeneratedRunById,
  createGeneratedRun,
  deleteGeneratedRun,
  updateBlockContent,
  createBlock,
  deleteBlock,
  addChatMessage,
  chatWithBlockAgent,
  clearBlockMessages,
  getBlockRelationships,
  createBlockRelationship,
  deleteBlockRelationship,
  checkBlockImpact,
  applyImpactSuggestion,
}
