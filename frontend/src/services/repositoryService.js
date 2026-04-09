import { getCurrentUser } from './authService'
import { request, requestBlob, toQueryString } from './apiClient'

const normalizeRepository = (repository) => {
  return {
    id: repository.id,
    ownerId: repository.owner_id,
    name: repository.name,
    description: repository.description,
    createdAt: repository.created_at,
  }
}

const normalizeDocument = (document) => {
  return {
    id: document.id,
    repositoryId: document.repository_id,
    title: document.title,
    content: document.content,
    createdAt: document.created_at,
  }
}

const normalizeRepositoryFile = (repositoryFile) => {
  return {
    id: repositoryFile.id,
    repositoryId: repositoryFile.repository_id,
    fileName: repositoryFile.file_name,
    mimeType: repositoryFile.mime_type,
    sizeBytes: repositoryFile.size_bytes,
    createdAt: repositoryFile.created_at,
  }
}

const requireUserId = () => {
  const user = getCurrentUser()
  if (!user?.id) {
    throw new Error('Invalid session. Please log in again.')
  }

  return user.id
}

const getRepositories = async () => {
  const ownerId = requireUserId()
  const query = toQueryString({ owner_id: ownerId })
  const repositories = await request(`/repositories${query}`)
  return repositories.map(normalizeRepository)
}

const createRepository = async ({ name, description }) => {
  const ownerId = requireUserId()
  const repository = await request('/repositories', {
    method: 'POST',
    body: JSON.stringify({
      owner_id: ownerId,
      name,
      description,
    }),
  })

  return normalizeRepository(repository)
}

const getRepositoryById = async (repositoryId) => {
  const repository = await request(`/repositories/${repositoryId}`)
  return normalizeRepository(repository)
}

const deleteRepository = async (repositoryId) => {
  await request(`/repositories/${repositoryId}`, {
    method: 'DELETE',
  })
}

const getDocumentsByRepository = async (repositoryId) => {
  const documents = await request(`/repositories/${repositoryId}/documents`)
  return documents.map(normalizeDocument)
}

const createDocument = async ({ repositoryId, title, content }) => {
  const document = await request(`/repositories/${repositoryId}/documents`, {
    method: 'POST',
    body: JSON.stringify({
      title,
      content,
    }),
  })

  return normalizeDocument(document)
}

const deleteDocument = async (repositoryId, documentId) => {
  await request(`/repositories/${repositoryId}/documents/${documentId}`, {
    method: 'DELETE',
  })
}

const getRepositoryFiles = async (repositoryId) => {
  const files = await request(`/repositories/${repositoryId}/files`)
  return files.map(normalizeRepositoryFile)
}

const uploadRepositoryFile = async (repositoryId, file) => {
  const formData = new FormData()
  formData.append('file', file)

  const uploaded = await request(`/repositories/${repositoryId}/files`, {
    method: 'POST',
    body: formData,
  })

  return normalizeRepositoryFile(uploaded)
}

const deleteRepositoryFile = async (repositoryId, fileId) => {
  await request(`/repositories/${repositoryId}/files/${fileId}`, {
    method: 'DELETE',
  })
}

const downloadRepositoryFile = async (repositoryId, fileId) => {
  return requestBlob(`/repositories/${repositoryId}/files/${fileId}/download`)
}

const downloadRepositoryArchive = async (repositoryId) => {
  return requestBlob(`/repositories/${repositoryId}/download`)
}

export {
  getRepositories,
  createRepository,
  getRepositoryById,
  deleteRepository,
  getDocumentsByRepository,
  createDocument,
  deleteDocument,
  getRepositoryFiles,
  uploadRepositoryFile,
  deleteRepositoryFile,
  downloadRepositoryFile,
  downloadRepositoryArchive,
}
