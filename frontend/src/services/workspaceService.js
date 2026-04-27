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

const normalizeBlockAgentChat = (payload) => {
  return {
    assistantMessage: payload.assistant_message,
    conversationId: payload.conversation_id,
    applied: payload.applied,
    proposedContent: payload.proposed_content,
    updatedContent: payload.updated_content,
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

export {
  getGeneratedRuns,
  getGeneratedRunById,
  createGeneratedRun,
  deleteGeneratedRun,
  updateBlockContent,
  addChatMessage,
  chatWithBlockAgent,
  clearBlockMessages,
}
