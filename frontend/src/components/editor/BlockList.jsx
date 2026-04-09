import { Link } from 'react-router-dom'

const BlockList = ({ workspaceId, runId, blocks }) => {
  return (
    <ul className="block-list">
      {blocks.map((block) => (
        <li key={block.id}>
          <Link to={`/workspaces/${workspaceId}/generated/${runId}/blocks/${block.id}`}>
            <div>
              <strong>{block.title}</strong>
              <p>{block.summary}</p>
            </div>
            <span>{block.fileName}</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}

export default BlockList
