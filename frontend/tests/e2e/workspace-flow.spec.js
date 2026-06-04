import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173'
const authStorageKey = process.env.E2E_AUTH_STORAGE_KEY ?? 'tfg_auth_user'
const unique = Date.now()
const workspaceName = `E2E Workspace ${unique}`
const workspaceContext = 'E2E workspace for functional testing.'
const prompt = `Generate a brief contract for ${workspaceName}.`
const chatMessage = 'Review the other blocks and generate a chart with the data you find and put it here.'
const fixturePath = path.join(__dirname, 'fixtures', 'sample.txt')

const authUser = {
  id: `1`,
  email: `admin@test.com`,
  displayName: `Test`,
  createdAt: `2026-05-14 14:53:03.258 +0200`,
}

let workspaceId
let runId

const acceptNextDialog = (page) => {
  page.once('dialog', (dialog) => dialog.accept())
}

const toUrl = (path) => new URL(path, baseURL).toString()

const seedAuth = async (page) => {
  await page.addInitScript(
    ({ key, user }) => {
      localStorage.setItem(key, JSON.stringify(user))
    },
    { key: authStorageKey, user: authUser },
  )
}

const parseIdFromUrl = (url, pattern, label) => {
  const match = url.match(pattern)
  if (!match) {
    throw new Error(`Could not parse ${label} from URL: ${url}`)
  }
  return match[1]
}

test.describe.serial('workspace flow', () => {
  test.describe.configure({ timeout: 240000 })

  test.beforeEach(async ({ page }) => {
    await seedAuth(page)
  })

  test('create workspace and upload context', async ({ page }) => {
    await page.goto(toUrl('/workspaces'))
    await page.getByLabel('Name').fill(workspaceName)
    await page.getByLabel('Context').fill(workspaceContext)
    await page.getByRole('button', { name: 'Create Workspace' }).click()

    const workspaceCard = page.locator('.workspace-card-list li', { hasText: workspaceName })
    await expect(workspaceCard).toBeVisible({ timeout: 20000 })
    await workspaceCard.getByRole('link', { name: 'Open' }).click()
    await page.waitForURL(/\/workspaces\/[^/]+$/)
    await expect(page.locator('.page-head h1')).toHaveText(workspaceName)

    workspaceId = parseIdFromUrl(page.url(), /\/workspaces\/([^/]+)/, 'workspace id')

    await page.getByLabel('Upload input files').setInputFiles(fixturePath)
    await page.getByRole('button', { name: 'Add Source' }).click()
    await expect(page.getByText('sample.txt')).toBeVisible({ timeout: 20000 })
  })

  test('generate document from context', async ({ page }) => {
    await page.goto(toUrl(`/workspaces/${workspaceId}`))
    await page.getByRole('link', { name: 'Generate Proposal' }).click()
    await expect(page.getByRole('heading', { name: 'Generate Proposal' })).toBeVisible()

    await page.getByLabel('Describe the document you want to generate').fill(prompt)
    await page.getByRole('button', { name: 'sample.txt' }).click()
    await page.getByRole('button', { name: 'Generate Proposal' }).click()

    await page.waitForURL(/\/generated\/.+\/blocks\//, {
      timeout: 180000,
      waitUntil: 'domcontentloaded',
    })
    runId = parseIdFromUrl(page.url(), /\/generated\/([^/]+)/, 'run id')
    await expect(page.locator('.editor-input textarea')).toBeVisible({ timeout: 180000 })
  })

  test('create, chat, delete block and re-enter workspace', async ({ page }) => {
    await page.goto(toUrl(`/workspaces/${workspaceId}/generated/${runId}`))
    await page.waitForURL(/\/generated\/.+\/blocks\//, { timeout: 60000 })

    const newBlockTitle = `New Block Test ${unique}`
    await page.getByRole('button', { name: 'Add block' }).click()

    const dialog = page.getByRole('dialog', { name: 'Add block' })
    await expect(dialog).toBeVisible()
    await dialog.getByLabel('Title').fill(newBlockTitle)
    await dialog.getByLabel('Summary').fill('New block for E2E testing.')
    await dialog.getByLabel('Initial content').fill('## New Block\nTest content.')
    await dialog.getByRole('button', { name: 'Create block' }).click()

    await expect(page.getByRole('heading', { level: 1, name: newBlockTitle })).toBeVisible({ timeout: 20000 })

    const chatBox = page.getByPlaceholder('Ask for specific changes to this block...')
    await chatBox.fill(chatMessage)
    await page.getByRole('button', { name: 'Send' }).click()
    await expect(page.locator('.chat-stream')).toContainText(chatMessage, { timeout: 30000 })

    acceptNextDialog(page)
    await page.getByRole('button', { name: 'Delete Block' }).click()
    await expect(page.getByRole('heading', { level: 1, name: newBlockTitle })).toHaveCount(0)

    await page.getByRole('link', { name: 'Workspaces' }).click()
    await expect(page).toHaveURL(/\/workspaces/)

    const workspaceCard = page.locator('.workspace-card-list li', { hasText: workspaceName })
    await expect(workspaceCard).toBeVisible({ timeout: 20000 })
    await workspaceCard.getByRole('link', { name: 'Open' }).click()
    await page.waitForURL(/\/workspaces\/[^/]+$/)
    await expect(page.locator('.page-head h1')).toHaveText(workspaceName)
  })
})
