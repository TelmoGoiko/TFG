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

const requestMockAssistantEdit = async ({ workspaceId, runId, blockId, userMessage }) => {
  const response = await request(`/agents/blocks/${blockId}/suggest-edit`, {
    method: 'POST',
    body: JSON.stringify({
      user_message: userMessage,
      selected_snippet: null,
    }),
  })

  const assistantResponse = response.assistant_message

  await addChatMessage({
    workspaceId,
    runId,
    blockId,
    role: 'assistant',
    content: assistantResponse,
  })

  return assistantResponse
}

export {
  getGeneratedRuns,
  getGeneratedRunById,
  createGeneratedRun,
  updateBlockContent,
  addChatMessage,
  requestMockAssistantEdit,
}
