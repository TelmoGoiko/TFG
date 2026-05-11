import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from '../auth/ProtectedRoute'
import BlockEditorPage from '../pages/BlockEditorPage'
import DocumentViewPage from '../pages/DocumentViewPage'
import GeneratePage from '../pages/GeneratePage'
import LoginPage from '../pages/LoginPage'
import MainPage from '../pages/MainPage'
import WorkspaceDetailPage from '../pages/WorkspaceDetailPage'
import WorkspacePage from '../pages/WorkspacePage'

const AppRouter = () => {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/workspaces" replace />} />
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/workspaces" element={<MainPage />} />
        <Route path="/workspaces/:workspaceId" element={<WorkspaceDetailPage />} />
        <Route path="/workspaces/:workspaceId/generate" element={<GeneratePage />} />
        <Route
          path="/workspaces/:workspaceId/generated/:runId"
          element={<WorkspacePage />}
        />
        <Route
          path="/workspaces/:workspaceId/generated/:runId/blocks/:blockId"
          element={<BlockEditorPage />}
        />
        <Route
          path="/workspaces/:workspaceId/generated/:runId/view"
          element={<DocumentViewPage />}
        />

        <Route path="/repositories" element={<Navigate to="/workspaces" replace />} />
        <Route path="/generate" element={<Navigate to="/workspaces" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/workspaces" replace />} />
    </Routes>
  )
}

export default AppRouter
