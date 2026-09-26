import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { chromium } from '@playwright/test'

const root = path.resolve('output/pse-valuation-candidates/phase-b-batch-24-candidate-a')
const mode = process.env.PSE_TEST_MODE === 'active' ? 'active' : 'staged'
const frontend = process.env.PSE_TEST_FRONTEND_URL || 'http://127.0.0.1:4004'
const screenshot = name => path.join(root, `ui-${name}-${mode}.png`)
const testEmail = `pse-b24-ui-${randomUUID()}@finsight.localtest.me`
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

  await page.goto(`${frontend}/pse/BH`)
  await page.getByRole('heading', { name: 'BHI Holdings, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByText(/248 companies/).waitFor({ timeout: 20000 })
  assert.ok((await page.locator('body').innerText()).toLowerCase().includes('market-relative estimate'))
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱69\.68/).waitFor()
  await page.getByRole('spinbutton', { name: 'Valuation multiple value' }).fill('0.5')
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱87\.10/).waitFor({ timeout: 12000 })
  await page.getByRole('button', { name: 'Browse news for September 24, 2026' }).click()
  await page.getByRole('region', { name: 'Daily company news' }).getByText('September 24, 2026').waitFor()
  await page.getByRole('button', { name: 'Browse news for September 25, 2026' }).click()
  await page.screenshot({ path: screenshot('bh'), fullPage: true })
  await page.getByRole('tab', { name: /Source filing/ }).click()
  assert.ok((await page.getByRole('link', { name: 'Open source' }).count()) >= 2)

  const search = page.getByRole('textbox', { name: 'Search company or ticker' })
  await search.fill('MA')
  await page.getByRole('button', { name: /Manila Mining Corporation/ }).waitFor({ timeout: 20000 })
  await page.getByRole('button', { name: /Manila Mining Corporation/ }).click()
  await page.waitForURL(/\/pse\/MA/, { timeout: 12000 })
  await page.getByRole('heading', { name: 'Manila Mining Corporation' }).waitFor({ timeout: 12000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('both outstanding A and B'))
  await page.screenshot({ path: screenshot('ma-classes'), fullPage: true })

  await page.goto(`${frontend}/pse/FPI`)
  await page.getByRole('heading', { name: 'Forum Pacific, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByText(/248 companies/).waitFor({ timeout: 20000 })
  assert.ok((await page.locator('body').innerText()).toLowerCase().includes('market-relative estimate'))

  for (const [ticker, name, reason] of [
    ['AB', 'Atok-Big Wedge Co., Inc.', 'parent equity'],
    ['MFC', 'Manulife Financial Corporation', 'CAD/PHP'],
    ['BC', 'Benguet Corporation', 'convertible preferred'],
  ]) {
    await page.goto(`${frontend}/pse/${ticker}`)
    await page.getByRole('heading', { name }).waitFor({ timeout: 20000 })
    await page.getByText(/248 companies/).waitFor({ timeout: 20000 })
    const body = await page.locator('body').innerText()
    assert.ok(body.includes('Valuation unavailable'), ticker)
    assert.ok(body.toLowerCase().includes(reason.toLowerCase()), ticker)
    assert.ok(!body.includes('Save scenario'), ticker)
    if (['AB', 'MFC', 'BC'].includes(ticker)) {
      await page.screenshot({ path: screenshot(`${ticker.toLowerCase()}-blocked`), fullPage: true })
    }
  }
  console.log({ signed_in_browser: true, catalog_mode: mode, catalog_count: 248, edited_calculator: 'BH 0.50x', calendar: 'September 24 and 25', search_navigation: 'MA', class_warning: 'MA', representative_new_blocked: 'AB/MFC', inherited_blocked: 'BC' })
} finally {
  await browser.close()
  execFileSync('python3', ['-c', 'import os,psycopg; connection=psycopg.connect(host="127.0.0.1",port=5442,user=os.environ["POSTGRES_USER"],password=os.environ["POSTGRES_PASSWORD"],dbname=os.environ["POSTGRES_DB"]); cursor=connection.cursor(); cursor.execute("DELETE FROM users WHERE email = %s",(os.environ["FINSIGHT_BATCH24_TEST_EMAIL"],)); connection.commit(); connection.close()'], { env: { ...process.env, FINSIGHT_BATCH24_TEST_EMAIL: testEmail }, stdio: 'pipe' })
}
