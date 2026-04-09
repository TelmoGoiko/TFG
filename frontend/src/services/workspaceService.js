import { request, toQueryString } from './apiClient'

const normalizeWorkspace = (workspace) => {
  return {
    id: workspace.id,
    repositoryId: workspace.repository_id,
    prompt: workspace.prompt,
    status: workspace.status,
    createdAt: workspace.created_at,
  }
}

const normalizeBlock = (block) => {
  return {
    id: block.id,
    workspaceId: block.workspace_id,
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

const getWorkspaces = async (repositoryId) => {
  const query = toQueryString({ repository_id: repositoryId })
  const payload = await request(`/workspaces${query}`)
  return payload.map(normalizeWorkspace)
}

const getWorkspaceById = async (workspaceId) => {
  const workspace = await request(`/workspaces/${workspaceId}`)
  const blocksPayload = await request(`/workspaces/${workspaceId}/blocks`)
  const blocks = blocksPayload.map(normalizeBlock)

  const messagesByBlock = await Promise.all(
    blocks.map(async (block) => {
      const messagesPayload = await request(
        `/workspaces/${workspaceId}/blocks/${block.id}/messages`,
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

const createWorkspace = async ({ repositoryId, prompt, referenceFiles }) => {
  const payload = await request('/workspaces', {
    method: 'POST',
    body: JSON.stringify({
      repository_id: repositoryId,
      prompt,
      reference_document_ids: [],
      reference_file_ids: referenceFiles.map((file) => file.id),
    }),
  })

  return normalizeWorkspace(payload)
}

const updateBlockContent = async ({ workspaceId, blockId, content }) => {
  const payload = await request(`/workspaces/${workspaceId}/blocks/${blockId}`, {
    method: 'PATCH',
    body: JSON.stringify({
      content,
    }),
  })

  return normalizeBlock(payload)
}

const addChatMessage = async ({ workspaceId, blockId, role, content, mentions }) => {
  const payload = await request(`/workspaces/${workspaceId}/blocks/${blockId}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      role,
      content,
      mentions: mentions ?? [],
    }),
  })

  return normalizeMessage(payload)
}

const requestMockAssistantEdit = async ({ workspaceId, blockId, userMessage }) => {
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
    blockId,
    role: 'assistant',
    content: assistantResponse,
  })

  return assistantResponse
}

export {
  getWorkspaces,
  getWorkspaceById,
  createWorkspace,
  updateBlockContent,
  addChatMessage,
  requestMockAssistantEdit,
}
