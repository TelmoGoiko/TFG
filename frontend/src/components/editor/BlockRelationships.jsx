import { useState } from 'react'
import { Link } from 'react-router-dom'

const RELATIONSHIP_TYPES = [
  { value: 'references', label: 'References' },
  { value: 'depends_on', label: 'Depends on' },
  { value: 'contradicts', label: 'Contradicts' },
  { value: 'extends', label: 'Extends' },
]

const typeColor = (type) => {
  switch (type) {
    case 'references': return 'var(--deep)'
    case 'depends_on': return 'var(--accent)'
    case 'contradicts': return 'var(--danger)'
    case 'extends': return 'var(--muted)'
    default: return 'var(--text)'
  }
}

const BlockRelationships = ({
  block,
  blocks,
  relationships,
  onCreate,
  onDelete,
  workspaceId,
  runId,
}) => {
  const [showForm, setShowForm] = useState(false)
  const [targetBlockId, setTargetBlockId] = useState('')
  const [relationshipType, setRelationshipType] = useState('references')
  const [description, setDescription] = useState('')

  const incoming = relationships.filter((r) => r.direction === 'incoming')
  const outgoing = relationships.filter((r) => r.direction === 'outgoing')

  const handleCreate = () => {
    if (!targetBlockId) return
    onCreate({ targetBlockId, relationshipType, description })
    setTargetBlockId('')
    setDescription('')
    setShowForm(false)
  }

  const otherBlocks = blocks.filter((b) => b.id !== block.id)

  return (
    <div className="block-relationships">
      <div className="relationships-header">
        <h4>Connections</h4>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : '+ Add'}
        </button>
      </div>

      {showForm && (
        <div className="relationship-form">
          <select
            value={targetBlockId}
            onChange={(e) => setTargetBlockId(e.target.value)}
          >
            <option value="">Select block...</option>
            {otherBlocks.map((b) => (
              <option key={b.id} value={b.id}>{b.title}</option>
            ))}
          </select>
          <select
            value={relationshipType}
            onChange={(e) => setRelationshipType(e.target.value)}
          >
            {RELATIONSHIP_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button type="button" className="btn btn-sm" onClick={handleCreate}>
            Create
          </button>
        </div>
      )}

      {outgoing.length === 0 && incoming.length === 0 && !showForm && (
        <p className="hint">No connections yet.</p>
      )}

      {outgoing.length > 0 && (
        <div className="relationship-group">
          <span className="relationship-group-label">References</span>
          <ul>
            {outgoing.map((rel) => (
              <li key={rel.id} className="relationship-item">
                <Link
                  to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${rel.otherBlock?.id}`}
                  className="relationship-link"
                  style={{ borderLeftColor: typeColor(rel.relationshipType) }}
                >
                  <span className="relationship-type-badge" style={{ background: typeColor(rel.relationshipType) }}>
                    {rel.relationshipType}
                  </span>
                  <span className="relationship-target">{rel.otherBlock?.title}</span>
                </Link>
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  onClick={() => onDelete(rel.id)}
                  title="Delete relationship"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {incoming.length > 0 && (
        <div className="relationship-group">
          <span className="relationship-group-label">Referenced by</span>
          <ul>
            {incoming.map((rel) => (
              <li key={rel.id} className="relationship-item">
                <Link
                  to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${rel.otherBlock?.id}`}
                  className="relationship-link"
                  style={{ borderLeftColor: typeColor(rel.relationshipType) }}
                >
                  <span className="relationship-type-badge" style={{ background: typeColor(rel.relationshipType) }}>
                    {rel.relationshipType}
                  </span>
                  <span className="relationship-target">{rel.otherBlock?.title}</span>
                </Link>
                <button
                  type="button"
                  className="btn btn-ghost btn-xs"
                  onClick={() => onDelete(rel.id)}
                  title="Delete relationship"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default BlockRelationships
