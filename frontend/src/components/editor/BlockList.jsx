import { Link } from 'react-router-dom'

const BlockList = ({ workspaceId, runId, blocks, relationships }) => {
  const blockRelCount = {}
  if (relationships) {
    relationships.forEach((rel) => {
      const ids = [rel.sourceBlockId, rel.targetBlockId]
      ids.forEach((id) => {
        blockRelCount[id] = (blockRelCount[id] || 0) + 1
      })
    })
  }

  return (
    <ul className="block-list">
      {blocks.map((block) => (
        <li key={block.id}>
          <Link to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${block.id}`}>
            <div>
              <strong>{block.title}</strong>
              <p>{block.summary}</p>
            </div>
            <div className="block-list-footer">
              <span>{block.fileName}</span>
              {blockRelCount[block.id] && blockRelCount[block.id] > 0 && (
                <span className="block-rel-badge">
                  {blockRelCount[block.id]} connection{blockRelCount[block.id] > 1 ? 's' : ''}
                </span>
              )}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default BlockList
