import { useState } from 'react'
import { Link } from 'react-router-dom'

const ImpactSuggestions = ({
  suggestions,
  onApply,
  onApplyAll,
  onDismiss,
  onDismissAll,
  onGoTo,
  isApplying,
  isDismissing,
  workspaceId,
  runId,
}) => {
  const [expandedId, setExpandedId] = useState(null)

  if (!suggestions || suggestions.length === 0) {
    return null
  }

  return (
    <div className="impact-suggestions">
      <div className="impact-suggestions-head">
        <div>
          <h4>Impact Suggestions</h4>
          <p className="hint">Changes in this block may affect related blocks.</p>
        </div>
        <div className="impact-bulk-actions">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={isApplying || isDismissing}
            onClick={onDismissAll}
          >
            {isDismissing ? 'Dismissing...' : 'Dismiss all'}
          </button>
          <button
            type="button"
            className="btn btn-sm"
            disabled={isApplying || isDismissing}
            onClick={onApplyAll}
          >
            {isApplying ? 'Applying...' : 'Apply all'}
          </button>
        </div>
      </div>

      {suggestions.map((suggestion) => {
        const isExpanded = expandedId === suggestion.id
        const bodyId = `impact-body-${suggestion.id}`

        return (
          <article
            key={suggestion.id}
            className={`impact-suggestion-card impact-${suggestion.relationshipType} ${
              isExpanded ? 'is-open' : ''
            }`}
          >
            <button
              type="button"
              className="impact-suggestion-header"
              aria-expanded={isExpanded}
              aria-controls={bodyId}
              onClick={() => setExpandedId(isExpanded ? null : suggestion.id)}
            >
              <div className="impact-suggestion-main">
                <span className="impact-suggestion-title">
                  {suggestion.affectedBlockTitle}
                </span>
                <span className="impact-suggestion-summary">{suggestion.reason}</span>
              </div>
              <span className="impact-chevron">{isExpanded ? '▾' : '▸'}</span>
            </button>

            {isExpanded && (
              <div id={bodyId} className="impact-suggestion-body">
                <p className="impact-reason">{suggestion.reason}</p>
                <div className="impact-suggestion-text">
                  <pre>{suggestion.suggestion}</pre>
                </div>
                <div className="impact-actions">
                  {onGoTo ? (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={() => onGoTo(suggestion)}
                    >
                      Go to block
                    </button>
                  ) : (
                    <Link
                      to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${suggestion.affectedBlockId}`}
                      className="btn btn-ghost btn-sm"
                    >
                      Go to block
                    </Link>
                  )}
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={isApplying || isDismissing}
                    onClick={() => onApply(suggestion)}
                  >
                    {isApplying ? 'Applying...' : 'Apply suggestion'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={isApplying || isDismissing}
                    onClick={() => onDismiss(suggestion.id)}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}

export default ImpactSuggestions
