import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { chromium } from '@playwright/test'

const root = path.resolve('output/pse-valuation-candidates/phase-b-batch-20-candidate-a')
const mode = process.env.PSE_TEST_MODE === 'active' ? 'active' : 'staged'
const frontend = process.env.PSE_TEST_FRONTEND_URL || 'http://127.0.0.1:4002'
const screenshot = name => path.join(root, `ui-${name}-${mode}.png`)
const testEmail = `pse-b20-ui-${randomUUID()}@finsight.localtest.me`
const testPassword = `Test-${randomUUID()}-only`
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
})
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.on('response', async response => {
  if (response.url().endsWith('/api/pse-valuations') || response.url().endsWith('/api/us-valuations')) {
    const body = await response.json().catch(() => null)
    console.log({ list_api_status: response.status(), url: response.url(), items: Array.isArray(body?.items) ? body.items.length : null, cors: response.headers()['access-control-allow-origin'], page: page.url() })
  }
})
page.on('pageerror', error => console.log({ browser_page_error: error.message.slice(0, 300) }))
page.on('console', message => {
  if (message.type() === 'error') console.log({ browser_console_error: message.text().slice(0, 300) })
})
try {
  await page.goto(`${frontend}/register`)
  await page.getByLabel('Email').fill(testEmail)
  await page.getByLabel('Password').fill(testPassword)
  await page.getByRole('button', { name: 'Create account' }).click()
  try {
    await page.waitForURL(/\/valuation\//, { timeout: 10000 })
  } catch (error) {
    await page.screenshot({ path: screenshot('register-diagnostic'), fullPage: true })
    console.log({ registration_url: page.url(), visible_message: (await page.locator('body').innerText()).slice(0, 500) })
    throw error
  }

  await page.goto(`${frontend}/pse/TOP`)
  await page.getByRole('heading', { name: 'Top Line Business Development Corp.' }).waitFor({ timeout: 20000 })
  await page.getByText(/208 companies/).waitFor({ timeout: 20000 })
  assert.ok((await page.locator('body').innerText()).toLowerCase().includes('market-relative estimate'))
  assert.ok((await page.locator('body').innerText()).includes('screening estimate, not the unavailable specialist intrinsic value'))
  await page.getByRole('spinbutton', { name: 'Valuation multiple value' }).fill('0.6')
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱0\.18/).waitFor({ timeout: 12000 })
  await page.getByRole('button', { name: 'Browse news for September 24, 2026' }).click()
  await page.getByRole('region', { name: 'Daily company news' }).getByText('September 24, 2026').waitFor()
  await page.getByRole('button', { name: 'Browse news for September 25, 2026' }).click()
  await page.screenshot({ path: screenshot('top'), fullPage: true })
  await page.getByRole('tab', { name: /Source filing/ }).click()
  assert.ok((await page.getByRole('link', { name: 'Open source' }).count()) >= 2)

  const search = page.getByRole('textbox', { name: 'Search company or ticker' })
  await search.fill('REDC')
  try {
    await page.getByRole('button', { name: /Repower Energy Development/ }).waitFor({ timeout: 20000 })
  } catch (error) {
    await page.screenshot({ path: screenshot('search-diagnostic'), fullPage: true })
    console.log({ search_view: (await page.locator('body').innerText()).slice(0, 750) })
    throw error
  }
  await page.getByRole('button', { name: /Repower Energy Development/ }).click()
  await page.waitForURL(/\/pse\/REDC/, { timeout: 12000 })
  await page.getByRole('heading', { name: 'Repower Energy Development Corporation' }).waitFor({ timeout: 12000 })

  await page.goto(`${frontend}/pse/HI`)
  await page.getByRole('heading', { name: 'House of Investments, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('PHP40.85 BVPS'))
  assert.ok((await page.locator('body').innerText()).includes('parent equity'))
  await page.screenshot({ path: screenshot('hi-warning'), fullPage: true })

  await page.goto(`${frontend}/pse/PRIM`)
  await page.getByRole('heading', { name: 'Prime Media Holdings, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByText(/208 companies/).waitFor({ timeout: 20000 })
  const blockedBody = await page.locator('body').innerText()
  assert.ok(blockedBody.includes('Valuation unavailable'))
  assert.ok(blockedBody.includes('convertible preferred'))
  assert.ok(!blockedBody.includes('Save scenario'))
  await page.screenshot({ path: screenshot('prim-blocked'), fullPage: true })
  console.log({ signed_in_browser: true, catalog_mode: mode, catalog_count: 208, edited_calculator: 'TOP 0.60x', calendar: 'September 24 and 25', search_navigation: 'REDC', parent_claim_warning: 'HI', inherited_blocked: 'PRIM' })
} finally {
  await browser.close()
  execFileSync('python3', ['-c', 'import os,psycopg; connection=psycopg.connect(host="127.0.0.1",port=5442,user=os.environ["POSTGRES_USER"],password=os.environ["POSTGRES_PASSWORD"],dbname=os.environ["POSTGRES_DB"]); cursor=connection.cursor(); cursor.execute("DELETE FROM users WHERE email = %s",(os.environ["FINSIGHT_BATCH20_TEST_EMAIL"],)); connection.commit(); connection.close()'], { env: { ...process.env, FINSIGHT_BATCH20_TEST_EMAIL: testEmail }, stdio: 'pipe' })
}
