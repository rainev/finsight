import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { chromium } from '@playwright/test'

const root = path.resolve('output/pse-valuation-candidates/phase-b-batch-19-candidate-a')
const mode = process.env.PSE_TEST_MODE === 'active' ? 'active' : 'staged'
const frontend = process.env.PSE_TEST_FRONTEND_URL || 'http://127.0.0.1:4002'
const screenshot = name => path.join(root, `ui-${name}-${mode}.png`)
const testEmail = `pse-b19-ui-${randomUUID()}@finsight.localtest.me`
const testPassword = `Test-${randomUUID()}-only`
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
})
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.on('response', response => {
  if (response.url().endsWith('/api/pse-valuations')) console.log({ list_api_status: response.status(), page: page.url() })
})
page.on('requestfailed', request => {
  if (request.url().includes('/api/pse-valuations')) console.log({ failed_api_request: request.url(), error: request.failure()?.errorText })
})
try {
  await page.goto(`${frontend}/register`)
  await page.getByLabel('Email').fill(testEmail)
  await page.getByLabel('Password').fill(testPassword)
  await page.getByRole('button', { name: 'Create account' }).click()
  try {
    await page.waitForURL(/\/valuation\//, { timeout: 8000 })
  } catch (error) {
    await page.screenshot({ path: screenshot('register-diagnostic'), fullPage: true })
    console.log({ registration_url: page.url(), visible_message: (await page.locator('body').innerText()).slice(0, 500) })
    throw error
  }
  await page.goto(`${frontend}/pse/TBGI`)
  await page.getByRole('heading', { name: 'Transpacific Broadband Group International, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByText(/198 companies/).waitFor({ timeout: 20000 })
  assert.ok((await page.locator('body').innerText()).toLowerCase().includes('market-relative estimate'))
  assert.ok((await page.locator('body').innerText()).includes('screening estimate, not the unavailable specialist intrinsic value'))
  await page.getByRole('spinbutton', { name: 'Valuation multiple value' }).fill('0.6')
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱0\.09/).waitFor({ timeout: 12000 })
  await page.getByRole('button', { name: 'Browse news for September 24, 2026' }).click()
  await page.getByRole('region', { name: 'Daily company news' }).getByText('September 24, 2026').waitFor()
  await page.getByRole('button', { name: 'Browse news for September 25, 2026' }).click()
  await page.screenshot({ path: screenshot('tbgi'), fullPage: true })

  const search = page.getByRole('textbox', { name: 'Search company or ticker' })
  await search.fill('ABA')
  await page.getByRole('button', { name: /AbaCore Capital Holdings/ }).waitFor({ timeout: 20000 })
  await page.getByRole('button', { name: /AbaCore Capital Holdings/ }).click()
  await page.waitForURL(/\/pse\/ABA/, { timeout: 12000 })
  await page.getByRole('heading', { name: 'AbaCore Capital Holdings, Inc.' }).waitFor({ timeout: 12000 })

  await page.goto(`${frontend}/pse/LODE`)
  await page.getByRole('heading', { name: 'Lodestar Investment Holdings Corporation' }).waitFor({ timeout: 20000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('PHP0.80 BVPS'))
  assert.ok((await page.locator('body').innerText()).includes('PHP0.0751'))

  for (const [ticker, name, reason] of [
    ['IS', 'Island Information & Technology, Inc.', 'Negative equity'],
    ['PAX', 'Paxys, Inc.', 'does not reconcile'],
    ['PRIM', 'Prime Media Holdings, Inc.', 'convertible preferred'],
  ]) {
    await page.goto(`${frontend}/pse/${ticker}`)
    await page.getByRole('heading', { name }).waitFor({ timeout: 20000 })
    try {
      await page.getByText(/198 companies/).waitFor({ timeout: 20000 })
    } catch (error) {
      console.log({ ticker, footer: (await page.locator('footer').allInnerTexts()).slice(-1), url: page.url() })
      throw error
    }
    const body = await page.locator('body').innerText()
    assert.ok(body.includes('Valuation unavailable'), `${ticker}: unavailable state missing`)
    assert.ok(body.includes(reason), `${ticker}: missing blocker`)
    assert.ok(!body.includes('Save scenario'), `${ticker}: blocked calculator unexpectedly visible`)
    assert.ok(body.includes('198 companies'), `${ticker}: catalog count missing`)
    await page.screenshot({ path: screenshot(ticker.toLowerCase()), fullPage: true })
  }
  console.log({ signed_in_browser: true, catalog_mode: mode, catalog_count: 198, edited_calculator: 'TBGI 0.60x', calendar: 'September 24 and 25', search_navigation: 'ABA', corrected_book_warning: 'LODE', blocked_ui: 'IS/PAX/PRIM' })
} finally {
  await browser.close()
  execFileSync('python3', ['-c', 'import os,psycopg; connection=psycopg.connect(host="127.0.0.1",port=5442,user=os.environ["POSTGRES_USER"],password=os.environ["POSTGRES_PASSWORD"],dbname=os.environ["POSTGRES_DB"]); cursor=connection.cursor(); cursor.execute("DELETE FROM users WHERE email = %s",(os.environ["FINSIGHT_BATCH19_TEST_EMAIL"],)); connection.commit(); connection.close()'], { env: { ...process.env, FINSIGHT_BATCH19_TEST_EMAIL: testEmail }, stdio: 'pipe' })
}
