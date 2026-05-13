import { getCurrentUser } from './authService'
import { request, requestBlob, toQueryString } from './apiClient'

const normalizeWorkspace = (workspace) => {
  return {
    id: workspace.id,
    ownerId: workspace.owner_id,
    name: workspace.name,
    description: workspace.description,
    createdAt: workspace.created_at,
  }
}

const normalizeDocument = (document) => {
  return {
    id: document.id,
    workspaceId: document.workspace_id,
    title: document.title,
    content: document.content,
    createdAt: document.created_at,
  }
}

const normalizeWorkspaceFile = (workspaceFile) => {
  return {
    id: workspaceFile.id,
    workspaceId: workspaceFile.workspace_id,
    fileName: workspaceFile.file_name,
    mimeType: workspaceFile.mime_type,
    sizeBytes: workspaceFile.size_bytes,
    createdAt: workspaceFile.created_at,
  }
}

const requireUserId = () => {
  const user = getCurrentUser()
  if (!user?.id) {
    throw new Error('Invalid session. Please log in again.')
  }

  return user.id
}

const getWorkspaces = async () => {
  const ownerId = requireUserId()
  const query = toQueryString({ owner_id: ownerId })
  const workspaces = await request(`/workspaces${query}`)
  return workspaces.map(normalizeWorkspace)
}

const createWorkspace = async ({ name, description }) => {
  const ownerId = requireUserId()
  const workspace = await request('/workspaces', {
    method: 'POST',
    body: JSON.stringify({
      owner_id: ownerId,
      name,
      description,
    }),
  })

  return normalizeWorkspace(workspace)
}

const getWorkspaceById = async (workspaceId) => {
  const workspace = await request(`/workspaces/${workspaceId}`)
  return normalizeWorkspace(workspace)
}

const deleteWorkspace = async (workspaceId) => {
  await request(`/workspaces/${workspaceId}`, {
    method: 'DELETE',
  })
}

const getDocumentsByWorkspace = async (workspaceId) => {
  const documents = await request(`/workspaces/${workspaceId}/documents`)
  return documents.map(normalizeDocument)
}

const createDocument = async ({ workspaceId, title, content }) => {
  const document = await request(`/workspaces/${workspaceId}/documents`, {
    method: 'POST',
    body: JSON.stringify({
      title,
      content,
    }),
  })

  return normalizeDocument(document)
}

const deleteDocument = async (workspaceId, documentId) => {
  await request(`/workspaces/${workspaceId}/documents/${documentId}`, {
    method: 'DELETE',
  })
}

const getWorkspaceFiles = async (workspaceId) => {
  const files = await request(`/workspaces/${workspaceId}/files`)
  return files.map(normalizeWorkspaceFile)
}

const uploadWorkspaceFile = async (workspaceId, file) => {
  const formData = new FormData()
  formData.append('file', file)

  const uploaded = await request(`/workspaces/${workspaceId}/files`, {
    method: 'POST',
    body: formData,
  })

  return normalizeWorkspaceFile(uploaded)
}

const deleteWorkspaceFile = async (workspaceId, fileId) => {
  await request(`/workspaces/${workspaceId}/files/${fileId}`, {
    method: 'DELETE',
  })
}

const downloadWorkspaceFile = async (workspaceId, fileId) => {
  return requestBlob(`/workspaces/${workspaceId}/files/${fileId}/download`)
}

const downloadWorkspaceArchive = async (workspaceId) => {
  return requestBlob(`/workspaces/${workspaceId}/download`)
}

export {
  getWorkspaces,
  createWorkspace,
  getWorkspaceById,
  deleteWorkspace,
  getDocumentsByWorkspace,
  createDocument,
  deleteDocument,
  getWorkspaceFiles,
  uploadWorkspaceFile,
  deleteWorkspaceFile,
  downloadWorkspaceFile,
  downloadWorkspaceArchive,
}
