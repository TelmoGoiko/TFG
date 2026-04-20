import { useState } from 'react'

const ChatPanel = ({ messages, onSend, onClear, isClearing, isSending }) => {
  const [draft, setDraft] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (!draft.trim() || isSending) {
      return
    }

    await onSend(draft)
    setDraft('')
  }

  return (
    <aside className="chat-panel">
      <div className="chat-head">
        <h3>Editing agent</h3>
        <p>Chat scoped to this block only.</p>
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
          <button type="button" className="btn btn-ghost" onClick={onClear} disabled={isClearing}>
            {isClearing ? 'Clearing...' : 'Clear history'}
          </button>
          <button className="btn" type="submit" disabled={isSending || !draft.trim()}>
            {isSending ? 'Thinking...' : 'Send'}
          </button>
        </div>
      </form>
    </aside>
  )
}

export default ChatPanel
