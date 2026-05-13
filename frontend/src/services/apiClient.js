const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || 'http://127.0.0.1:8010/api/v1'

const getFileNameFromDisposition = (dispositionValue) => {
  if (!dispositionValue) {
    return ''
  }

  const utf8Match = dispositionValue.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }

  const quotedMatch = dispositionValue.match(/filename="([^"]+)"/i)
  if (quotedMatch?.[1]) {
    return quotedMatch[1]
  }

  const plainMatch = dispositionValue.match(/filename=([^;]+)/i)
  if (plainMatch?.[1]) {
    return plainMatch[1].trim()
  }

  return ''
}

const getFallbackFileName = (path) => {
  const cleanPath = path.split('?')[0]
  if (cleanPath.endsWith('/download')) {
    return 'workspace_bundle.zip'
  }

  const segments = cleanPath.split('/').filter(Boolean)
  return segments.at(-1) || 'download.bin'
}

const toQueryString = (params) => {
  const entries = Object.entries(params ?? {}).filter(([, value]) => {
    return value !== undefined && value !== null && value !== ''
  })

  if (entries.length === 0) {
    return ''
  }

  const query = new URLSearchParams()
  entries.forEach(([key, value]) => {
    query.set(key, String(value))
  })

  return `?${query.toString()}`
}

const normalizeErrorDetail = (detail, fallbackMessage) => {
  if (!detail) {
    return fallbackMessage
  }

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item
        }

        if (item?.msg) {
          return item.msg
        }

        return JSON.stringify(item)
      })
      .join(' | ')
  }

  if (typeof detail === 'object') {
    if (detail.message && typeof detail.message === 'string') {
      return detail.message
    }
    return JSON.stringify(detail)
  }

  return fallbackMessage
}

const request = async (path, options = {}) => {
  const isFormDataBody = options.body instanceof FormData
  const defaultHeaders = isFormDataBody ? {} : { 'Content-Type': 'application/json' }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      ...defaultHeaders,
      ...(options.headers ?? {}),
    },
    ...options,
  })

  if (response.status === 204) {
    return null
  }

  const isJson = response.headers.get('content-type')?.includes('application/json')
  const payload = isJson ? await response.json() : null

  if (!response.ok) {
    const detail = normalizeErrorDetail(
      payload?.detail,
      `Request failed with status ${response.status}`,
    )
    throw new Error(detail)
  }

  return payload
}

const requestBlob = async (path, options = {}) => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      ...(options.headers ?? {}),
    },
    ...options,
  })

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`
    const isJson = response.headers.get('content-type')?.includes('application/json')
    if (isJson) {
      const payload = await response.json()
      detail = normalizeErrorDetail(payload?.detail, detail)
    }
    throw new Error(detail)
  }

  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') ?? ''
  const fileName = getFileNameFromDisposition(disposition) || getFallbackFileName(path)

  return { blob, fileName }
}

export { request, requestBlob, toQueryString }
