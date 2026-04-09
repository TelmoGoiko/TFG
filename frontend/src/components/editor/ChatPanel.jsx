import { useMemo, useState } from 'react'

const ChatPanel = ({ messages, onSend, selectedSnippet }) => {
  const [draft, setDraft] = useState('')

  const mentionLabel = useMemo(() => {
    if (!selectedSnippet) {
      return 'No text selected'
    }
    return `Current selection: "${selectedSnippet.slice(0, 96)}"`
  }, [selectedSnippet])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!draft.trim()) {
      return
    }

    await onSend(draft)
    setDraft('')
  }

  const addSnippetToDraft = () => {
    if (!selectedSnippet) {
      return
    }

    const mention = `@snippet: "${selectedSnippet}"`
    setDraft((previous) => (previous ? `${previous}\n${mention}` : mention))
  }

  return (
    <aside className="chat-panel">
      <div className="chat-head">
        <h3>Editing agent</h3>
        <p>{mentionLabel}</p>
      </div>

      <div className="chat-stream">
        {messages.length === 0 ? (
          <p className="hint">There are no messages in this block yet.</p>
        ) : (
          messages.map((message) => (
            <article key={message.id} className={`bubble ${message.role}`}>
              <strong>{message.role === 'user' ? 'You' : 'Agent'}</strong>
              <p>{message.content}</p>
            </article>
          ))
        )}
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Ask for specific changes to this block..."
          rows={5}
        />
        <div className="chat-actions">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={addSnippetToDraft}
            disabled={!selectedSnippet}
          >
            Mention selection
          </button>
          <button className="btn" type="submit">
            Send
          </button>
        </div>
      </form>
    </aside>
  )
}

export default ChatPanel
