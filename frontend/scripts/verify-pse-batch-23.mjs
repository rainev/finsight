import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { chromium } from '@playwright/test'

const root = path.resolve('output/pse-valuation-candidates/phase-b-batch-23-candidate-a')
const mode = process.env.PSE_TEST_MODE === 'active' ? 'active' : 'staged'
const frontend = process.env.PSE_TEST_FRONTEND_URL || 'http://127.0.0.1:4003'
const screenshot = name => path.join(root, `ui-${name}-${mode}.png`)
const testEmail = `pse-b23-ui-${randomUUID()}@finsight.localtest.me`
const testPassword = `Test-${randomUUID()}-only`
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
})
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
page.on('pageerror', error => console.log({ browser_page_error: error.message.slice(0, 300) }))
try {
  await page.goto(`${frontend}/register`)
  await page.getByLabel('Email').fill(testEmail)
  await page.getByLabel('Password').fill(testPassword)
  await page.getByRole('button', { name: 'Create account' }).click()
  await page.waitForURL(/\/valuation\//, { timeout: 12000 })

  await page.goto(`${frontend}/pse/CA`)
  await page.getByRole('heading', { name: 'Concrete Aggregates Corporation' }).waitFor({ timeout: 20000 })
  await page.getByText(/238 companies/).waitFor({ timeout: 20000 })
  assert.ok((await page.locator('body').innerText()).toLowerCase().includes('market-relative estimate'))
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱5\.70/).waitFor()
  await page.getByRole('spinbutton', { name: 'Valuation multiple value' }).fill('0.6')
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱6\.85/).waitFor({ timeout: 12000 })
  await page.getByRole('button', { name: 'Browse news for September 24, 2026' }).click()
  await page.getByRole('region', { name: 'Daily company news' }).getByText('September 24, 2026').waitFor()
  await page.getByRole('button', { name: 'Browse news for September 25, 2026' }).click()
  await page.screenshot({ path: screenshot('ca'), fullPage: true })
  await page.getByRole('tab', { name: /Source filing/ }).click()
  assert.ok((await page.getByRole('link', { name: 'Open source' }).count()) >= 3)

  const search = page.getByRole('textbox', { name: 'Search company or ticker' })
  await search.fill('FJP')
  await page.getByRole('button', { name: /F & J Prince Holdings/ }).waitFor({ timeout: 20000 })
  await page.getByRole('button', { name: /F & J Prince Holdings/ }).click()
  await page.waitForURL(/\/pse\/FJP/, { timeout: 12000 })
  await page.getByRole('heading', { name: 'F & J Prince Holdings Corporation' }).waitFor({ timeout: 12000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('same rights and privileges'))
  await page.screenshot({ path: screenshot('fjp-rights'), fullPage: true })

  await page.goto(`${frontend}/pse/LC`)
  await page.getByRole('heading', { name: 'Lepanto Consolidated Mining Company' }).waitFor({ timeout: 20000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('PHP thousands'))

  await page.goto(`${frontend}/pse/ATN`)
  await page.getByRole('heading', { name: 'ATN Holdings, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('March 31'))

  for (const [ticker, name, reason] of [
    ['BC', 'Benguet Corporation', 'convertible preferred'],
    ['OPM', 'Oriental Petroleum and Minerals Corporation', 'USD'],
    ['PRIM', 'Prime Media Holdings, Inc.', 'convertible preferred'],
  ]) {
    await page.goto(`${frontend}/pse/${ticker}`)
    await page.getByRole('heading', { name }).waitFor({ timeout: 20000 })
    await page.getByText(/238 companies/).waitFor({ timeout: 20000 })
    const body = await page.locator('body').innerText()
    assert.ok(body.includes('Valuation unavailable'), ticker)
    assert.ok(body.toLowerCase().includes(reason.toLowerCase()), ticker)
    assert.ok(!body.includes('Save scenario'), ticker)
    await page.screenshot({ path: screenshot(`${ticker.toLowerCase()}-blocked`), fullPage: true })
  }
  console.log({ signed_in_browser: true, catalog_mode: mode, catalog_count: 238, edited_calculator: 'CA 0.60x', calendar: 'September 24 and 25', search_navigation: 'FJP', unit_warning: 'LC', fiscal_period_warning: 'ATN', new_blocked: 'BC/OPM', inherited_blocked: 'PRIM' })
} finally {
  await browser.close()
  execFileSync('python3', ['-c', 'import os,psycopg; connection=psycopg.connect(host="127.0.0.1",port=5442,user=os.environ["POSTGRES_USER"],password=os.environ["POSTGRES_PASSWORD"],dbname=os.environ["POSTGRES_DB"]); cursor=connection.cursor(); cursor.execute("DELETE FROM users WHERE email = %s",(os.environ["FINSIGHT_BATCH23_TEST_EMAIL"],)); connection.commit(); connection.close()'], { env: { ...process.env, FINSIGHT_BATCH23_TEST_EMAIL: testEmail }, stdio: 'pipe' })
}
