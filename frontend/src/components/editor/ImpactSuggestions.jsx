import { useState } from 'react'
import { Link } from 'react-router-dom'

const ImpactSuggestions = ({
  suggestions,
  onApply,
  onDismiss,
  workspaceId,
  runId,
}) => {
  const [expandedId, setExpandedId] = useState(null)

  if (!suggestions || suggestions.length === 0) {
    return null
  }

  return (
    <div className="impact-suggestions">
      <h4>Impact Suggestions</h4>
      <p className="hint">Changes in this block may affect related blocks.</p>

      {suggestions.map((suggestion) => (
        <article key={suggestion.affectedBlockId} className="impact-suggestion-card">
          <div
            className="impact-suggestion-header"
            onClick={() => setExpandedId(expandedId === suggestion.affectedBlockId ? null : suggestion.affectedBlockId)}
          >
            <span className="impact-suggestion-title">
              {suggestion.affectedBlockTitle}
            </span>
            <span className={`impact-type-badge impact-${suggestion.relationshipType}`}>
              {suggestion.relationshipType}
            </span>
            <span className="impact-chevron">
              {expandedId === suggestion.affectedBlockId ? '▾' : '▸'}
            </span>
          </div>

          {expandedId === suggestion.affectedBlockId && (
            <div className="impact-suggestion-body">
              <p className="impact-reason">{suggestion.reason}</p>
              <div className="impact-suggestion-text">
                <pre>{suggestion.suggestion}</pre>
              </div>
              <div className="impact-actions">
                <Link
                  to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${suggestion.affectedBlockId}`}
                  className="btn btn-ghost btn-sm"
                >
                  Go to block
                </Link>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onApply(suggestion)}
                >
                  Apply suggestion
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => onDismiss(suggestion.affectedBlockId)}
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}
        </article>
      ))}
    </div>
  )
}

export default ImpactSuggestions
