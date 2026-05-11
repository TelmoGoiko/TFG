import { useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link, useParams } from 'react-router-dom'
import remarkGfm from 'remark-gfm'
import AppShell from '../components/layout/AppShell'
import { getWorkspaceById } from '../services/workspaceContainerService'
import { getGeneratedRunById } from '../services/workspaceService'

const DocumentViewPage = () => {
  const { workspaceId, runId } = useParams()
  const [workspaceContainer, setWorkspaceContainer] = useState(null)
  const [workspace, setWorkspace] = useState(null)

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

  const orderedBlocks = useMemo(() => {
    if (!workspace?.blocks) return []
    return [...workspace.blocks].sort((a, b) => a.order - b.order)
  }, [workspace])

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

  if (!workspace) {
    return (
      <AppShell title="Documento completo" subtitle="Cargando documento...">
        <article className="panel">
          <p className="hint">Preparando el documento generado.</p>
        </article>
      </AppShell>
    )
  }

  return (
    <AppShell
      title={workspace.prompt || 'Documento completo'}
      subtitle={workspaceContainer?.name ? `${workspaceContainer.name} · Vista completa` : 'Vista completa'}
      actions={
        <Link className="btn btn-light" to={`/workspaces/${workspaceId}/generated/${runId}`}>
          Volver al editor
        </Link>
      }
    >
      <section className="panel">
        <div className="section-head">
          <h2>Documento completo</h2>
          <span className="hint">{orderedBlocks.length} bloques</span>
        </div>

        <div className="markdown-preview">
          {orderedBlocks.map((block) => (
            <article key={block.id} className="panel" style={{ marginTop: '1.5rem' }}>
              <div className="section-head">
                <h3>{block.title}</h3>
                <Link
                  className="table-link"
                  to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${block.id}`}
                >
                  Abrir bloque
                </Link>
              </div>
              {block.summary ? <p className="hint">{block.summary}</p> : null}
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
                {block.content || ''}
              </ReactMarkdown>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  )
}

export default DocumentViewPage
