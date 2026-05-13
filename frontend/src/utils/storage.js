const readJson = (key, fallback) => {
  try {
    const rawValue = localStorage.getItem(key)
    if (!rawValue) {
      return fallback
    }

    return JSON.parse(rawValue)
  } catch {
    return fallback
  }
}

const writeJson = (key, value) => {
  localStorage.setItem(key, JSON.stringify(value))
}

const randomId = (prefix) => {
  const random = Math.random().toString(36).slice(2, 8)
  return `${prefix}_${Date.now()}_${random}`
}

const nowIso = () => new Date().toISOString()

export { readJson, writeJson, randomId, nowIso }
