import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('./')
  await page.evaluate(() => localStorage.clear())
  await page.reload()
})

const showFullReferenceLibrary = async (page) => {
  await page.getByRole('button', { name: /Full reference library/ }).click()
}

test('defaults to authenticated menu choices and clearly marks reference-only terms', async ({ page }) => {
  await expect(page.locator('.rail-summary')).toContainText('Available relationship choices')
  await expect(page.locator('.rail-summary')).toContainText('73 of 73')
  await expect(page.getByRole('button', { name: /Available choices 73/ })).toHaveAttribute('aria-pressed', 'true')

  const search = page.getByRole('searchbox', { name: 'Search catalog' })
  await search.fill('Protecting')
  await expect(page.locator('.rail-result-copy strong').getByText('Protecting', { exact: true })).toHaveCount(0)

  await showFullReferenceLibrary(page)
  await expect(page.locator('.rail-summary')).toContainText('73 selectable')
  await expect(page.locator('.rail-result').filter({ hasText: 'Protecting' }).first()).toContainText('Reference only')
  await page.locator('.rail-result').filter({ hasText: 'Protecting' }).first().click()
  await expect(page.locator('.selection-scope-status')).toContainText('Reference-only term')
  await expect(page.locator('.selection-scope-status')).toContainText('may not be selectable')

  await page.getByRole('button', { name: 'D/s & Profile Roles' }).click()
  await expect(page.locator('.rail-summary')).toContainText('606 of 606')
  await expect(page.getByRole('button', { name: /Full reference library 1,202/ })).toHaveAttribute('aria-pressed', 'false')
})

test('explains definition semantics, attribution, and noncommercial licensing', async ({ page }) => {
  await page.getByRole('button', { name: 'About', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('Verbatim FetLife excerpt')
  await expect(dialog).toContainText('Adapted summary')
  await expect(dialog).toContainText('noncommercial educational reference')
  await expect(dialog.getByRole('link', { name: 'Kinktionary license' })).toHaveAttribute('href', 'https://fetlife.com/kinktionary/license-zcfzz')
})

test('searches a relationship, shows separate evidence, and saves a pairing', async ({ page }) => {
  await expect(page).toHaveTitle('Relationship Atlas')
  await expect(page.getByRole('button', { name: 'Relationships', exact: true })).toHaveAttribute('aria-current', 'page')
  await showFullReferenceLibrary(page)
  await page.getByRole('searchbox', { name: 'Search catalog' }).fill('Protecting')
  await page.locator('.rail-result').filter({ hasText: 'Protecting' }).first().click()
  await expect(page.locator('.pair-node.target')).toContainText('Under Protection')
  await expect(page.locator('.pair-structure')).toHaveText('Atlas two-way pair suggestion')
  await expect(page.locator('.pair-direction')).toHaveText('Atlas maps both labels to each other')
  await expect(page.getByText('FetLife definition')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Copy link' })).toBeVisible()
  await expect(page).toHaveURL(/#relationships\/relationship-protecting-/)
  await page.reload()
  await expect(page.locator('.pair-node.origin')).toContainText('Protecting')
  await expect(page.locator('.pair-node.target')).toContainText('Under Protection')
  await expect(page.locator('body')).not.toContainText('Exact reciprocal')
  await page.getByRole('button', { name: 'Add to My Pairing' }).click()
  await page.getByRole('button', { name: 'My Pairing', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Protecting', exact: true })).toBeVisible()
  await page.getByLabel('Decision').selectOption('Use')
  await expect(page.getByLabel('Final partner label')).toHaveValue('Under Protection')
})

test('leaves independently chosen partner labels blank for agreement', async ({ page }) => {
  await showFullReferenceLibrary(page)
  await page.getByRole('searchbox', { name: 'Search catalog' }).fill('Alterous Attraction')
  await page.locator('.rail-result').filter({ hasText: 'Alterous Attraction' }).first().click()
  await expect(page.locator('.pair-node.target')).toContainText('Partner chooses their own label')
  await page.getByRole('button', { name: 'Add to My Pairing' }).click()
  await page.getByRole('button', { name: 'My Pairing', exact: true }).click()
  await page.getByLabel('Decision').selectOption('Use')
  await expect(page.getByLabel('Final partner label')).toHaveValue('')
  await expect(page.getByLabel('Final partner label')).toHaveAttribute('placeholder', 'Agree on a label')
})

test('filters the role catalog and updates the visual evidence', async ({ page }) => {
  await page.getByRole('button', { name: 'D/s & Profile Roles' }).click()
  const search = page.getByRole('searchbox', { name: 'Search catalog' })
  await expect(search).toHaveAttribute('placeholder', 'Search roles or partners…')
  await search.fill('Biter')
  await page.locator('.rail-result-copy strong').getByText('Biter', { exact: true }).click()
  await expect(page.locator('.pair-node.origin')).toContainText('Biter')
  await expect(page.getByRole('link', { name: 'Open on FetLife' })).toBeVisible()
  await page.getByText('Why does the Atlas suggest this?').click()
  await expect(page.getByLabel('Biter details').getByText('Authenticated D/s relationship menu')).toBeVisible()
})

test('recovers misspellings, explains the match field, and keeps relevance stable', async ({ page }) => {
  await showFullReferenceLibrary(page)
  const search = page.getByRole('searchbox', { name: 'Search catalog' })
  await search.fill('protectin')
  await expect(page.locator('.rail-result').first()).toContainText('Protecting')
  await expect(page.locator('.rail-result').first().locator('.search-match')).toContainText('Label')
  await search.fill('long distnce relashionship')
  await expect(page.locator('.rail-result').first()).toContainText('Long-Distance Relationship')
  await expect(page.locator('.rail-summary')).toContainText('relevance ranked')
  await expect(page.getByLabel('Sort catalog')).toHaveValue('relevance')
})

test('searches every current D/s menu type through source-aware vocabulary', async ({ page }) => {
  await page.getByRole('button', { name: 'D/s & Profile Roles' }).click()
  await page.getByRole('searchbox', { name: 'Search catalog' }).fill('authenticated ds relationship')
  await expect(page.locator('.rail-summary')).toContainText('606 of 606')
  await expect(page.locator('.rail-result').first().locator('.search-match')).toContainText('Source membership')
})

test('finds any label across both catalogs from one search surface', async ({ page }) => {
  await page.getByRole('button', { name: /Find any label/ }).click()
  const globalSearch = page.getByRole('searchbox', { name: 'Search all labels' })
  await page.keyboard.press('Escape')
  await expect(globalSearch).toBeHidden()
  await page.keyboard.press('Control+K')
  await expect(globalSearch).toBeVisible()
  await globalSearch.fill('partner')
  const firstActive = await page.locator('.global-search-result.active strong').textContent()
  await globalSearch.press('ArrowDown')
  await expect(page.locator('.global-search-result.active strong')).not.toHaveText(firstActive)
  await globalSearch.fill('KTP')
  await page.getByRole('option', { name: /Polyamory/ }).click()
  await expect(page.getByRole('button', { name: 'Relationships', exact: true })).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('.pair-node.origin')).toContainText('Polyamory')
  await expect(page).toHaveURL(/#relationships\/relationship-polyamory-/)

  await page.keyboard.press('Control+K')
  await expect(globalSearch).toBeVisible()
  await globalSearch.fill('tasks in our dynamic')
  await page.getByRole('option', { name: /Taskmaster/ }).click()
  await expect(page.getByRole('button', { name: 'D/s & Profile Roles' })).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('.pair-node.origin')).toContainText('Taskmaster')
  await expect(page).toHaveURL(/#roles\/role-taskmaster-/)
})

test('opens a deterministic correlation comparison from a selected pair', async ({ page }) => {
  await showFullReferenceLibrary(page)
  await page.getByRole('searchbox', { name: 'Search catalog' }).fill('Protecting')
  await page.locator('.rail-result').filter({ hasText: 'Protecting' }).first().click()
  await page.locator('.evidence-actions').getByRole('button', { name: 'Compare' }).click()
  await expect(page.getByRole('heading', { name: 'Compare Atlas relationships' })).toBeVisible()
  await page.waitForTimeout(150)
  expect(await page.evaluate(() => window.scrollY)).toBe(0)
  await expect(page.getByRole('heading', { name: 'Correlation ledger' })).toBeVisible()
  await expect(page.getByLabel('Correlation ledger').getByText('Atlas two-way reference', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Correlation ledger')).toContainText('Interpretation boundary')
  await expect(page.getByText('Protecting compared with Under Protection')).toBeVisible()
})

test('serves install metadata and service worker', async ({ request }) => {
  const manifest = await request.get('./manifest.webmanifest')
  const worker = await request.get('./service-worker.js')
  const icon192 = await request.get('./icon-192.png')
  const icon512 = await request.get('./icon-512.png')
  expect(manifest.ok()).toBeTruthy()
  expect(worker.ok()).toBeTruthy()
  expect(icon192.ok()).toBeTruthy()
  expect(icon512.ok()).toBeTruthy()
  const metadata = await manifest.json()
  expect(metadata.display).toBe('standalone')
  expect(metadata.id).toBe('./')
  expect(metadata.icons.some((icon) => icon.type === 'image/png' && icon.sizes === '192x192')).toBeTruthy()
  expect(metadata.icons.some((icon) => icon.type === 'image/png' && icon.sizes === '512x512')).toBeTruthy()
  expect(await (await request.get('./')).text()).toContain('Content-Security-Policy')
})

test('reloads the catalog offline after the first visit', async ({ page }) => {
  await page.waitForFunction(() => Boolean(navigator.serviceWorker?.controller), null, { timeout: 15_000 })
  await page.reload()
  await page.context().setOffline(true)
  try {
    await page.reload({ waitUntil: 'domcontentloaded' })
    await expect(page).toHaveTitle('Relationship Atlas')
    await expect(page.getByRole('button', { name: 'Relationships', exact: true })).toHaveAttribute('aria-current', 'page')
    await expect(page.getByRole('searchbox', { name: 'Search catalog' })).toHaveAttribute('placeholder', 'Search relationships or partners…')
    await expect(page.locator('.pair-node.origin')).toContainText('Partner')
  } finally {
    await page.context().setOffline(false)
  }
})

test('keeps filters collapsed until requested', async ({ page }) => {
  const disclosure = page.locator('.filter-disclosure')
  await expect(disclosure).not.toHaveAttribute('open', '')
  await expect(disclosure.locator('select').first()).not.toBeVisible()
  await disclosure.locator('summary').click()
  await expect(disclosure.locator('select').first()).toBeVisible()
  await disclosure.locator('summary').click()
  await expect(disclosure.locator('select').first()).not.toBeVisible()
})

test('puts the visual correlation before search on mobile', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'mobile')
  const pairBox = await page.locator('.pair-map').boundingBox()
  const searchBox = await page.getByRole('searchbox', { name: 'Search catalog' }).boundingBox()
  expect(pairBox).not.toBeNull()
  expect(searchBox).not.toBeNull()
  expect(pairBox.y).toBeLessThan(searchBox.y)
  await expect(page.locator('.pair-line.vertical')).toBeVisible()
})

test('shows the search jump only on mobile', async ({ page }, testInfo) => {
  const jump = page.getByRole('button', { name: 'Find another label' })
  if (testInfo.project.name === 'mobile') await expect(jump).toBeVisible()
  else await expect(jump).toBeHidden()
})

test('keeps internal inference tiers out of every customer-facing workflow', async ({ page }) => {
  for (const tab of ['Relationships', 'D/s & Profile Roles', 'My Pairing']) {
    await page.getByRole('navigation', { name: 'Primary' }).getByRole('button', { name: tab, exact: true }).click()
    await expect(page.locator('body')).not.toContainText(/Exact reciprocal|Strong convention|Context required|None inherent/)
    await expect(page.getByText('Confidence', { exact: true })).toHaveCount(0)
  }
})

test('sanitizes browser-local pairing state before rendering', async ({ page }) => {
  await page.evaluate(() => localStorage.setItem('relationship-atlas:pairing:v2', JSON.stringify([
    { id: 'relationship-protecting-1vumt64', decision: 'Override', finalLabel: '=UNTRUSTED'.repeat(40), injected: true },
    { id: 'relationship-protecting-1vumt64', decision: 'Use', finalLabel: 'duplicate' },
    { id: 'missing-label', decision: 'Use', finalLabel: 'ignored' },
  ])))
  await page.reload()
  await page.getByRole('button', { name: 'My Pairing', exact: true }).click()
  await expect(page.getByText('1 saved label')).toBeVisible()
  await expect(page.getByLabel('Decision')).toHaveValue('Review')
  await expect(page.getByLabel('Final partner label')).toBeDisabled()
})
