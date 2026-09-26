import assert from 'node:assert/strict'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { chromium } from '@playwright/test'

const root = path.resolve('output/pse-valuation-candidates/phase-b-batch-22-candidate-a')
const mode = process.env.PSE_TEST_MODE === 'active' ? 'active' : 'staged'
const frontend = process.env.PSE_TEST_FRONTEND_URL || 'http://127.0.0.1:4002'
const screenshot = name => path.join(root, `ui-${name}-${mode}.png`)
const testEmail = `pse-b22-ui-${randomUUID()}@finsight.localtest.me`
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

  await page.goto(`${frontend}/pse/CSB`)
  await page.getByRole('heading', { name: 'Citystate Savings Bank, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByText(/228 companies/).waitFor({ timeout: 20000 })
  assert.ok((await page.locator('body').innerText()).toLowerCase().includes('market-relative estimate'))
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱6\.75/).waitFor()
  await page.getByRole('spinbutton', { name: 'Valuation multiple value' }).fill('1.0')
  await page.locator('.intrinsic-hero .value-reveal').getByText(/₱8\.43/).waitFor({ timeout: 12000 })
  await page.getByRole('button', { name: 'Browse news for September 24, 2026' }).click()
  await page.getByRole('region', { name: 'Daily company news' }).getByText('September 24, 2026').waitFor()
  await page.getByRole('button', { name: 'Browse news for September 25, 2026' }).click()
  await page.screenshot({ path: screenshot('csb'), fullPage: true })
  await page.getByRole('tab', { name: /Source filing/ }).click()
  assert.ok((await page.getByRole('link', { name: 'Open source' }).count()) >= 2)

  const search = page.getByRole('textbox', { name: 'Search company or ticker' })
  await search.fill('ORE')
  try {
    await page.getByRole('button', { name: /Oriental Peninsula Resources Group/ }).waitFor({ timeout: 20000 })
  } catch (error) {
    await page.screenshot({ path: screenshot('search-diagnostic'), fullPage: true })
    console.log({ search_view: (await page.locator('body').innerText()).slice(0, 650) })
    throw error
  }
  await page.getByRole('button', { name: /Oriental Peninsula Resources Group/ }).click()
  await page.waitForURL(/\/pse\/ORE/, { timeout: 12000 })
  await page.getByRole('heading', { name: 'Oriental Peninsula Resources Group, Inc.' }).waitFor({ timeout: 12000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('parent results were losses'))
  await page.screenshot({ path: screenshot('ore-warning'), fullPage: true })

  await page.goto(`${frontend}/pse/ENEX`)
  await page.getByRole('heading', { name: 'ENEX Energy Corp.' }).waitFor({ timeout: 20000 })
  await page.getByText(/228 companies/).waitFor({ timeout: 20000 })
  assert.ok((await page.locator('body').innerText()).includes('2026-06-30'))
  await page.screenshot({ path: screenshot('enex-period'), fullPage: true })

  await page.goto(`${frontend}/pse/ECVC`)
  await page.getByRole('heading', { name: 'East Coast Vulcan Mining Corporation' }).waitFor({ timeout: 20000 })
  await page.getByRole('tab', { name: /Cross-checks/ }).click()
  assert.ok((await page.locator('body').innerText()).includes('parent-equity field is zero'))

  await page.goto(`${frontend}/pse/PRIM`)
  await page.getByRole('heading', { name: 'Prime Media Holdings, Inc.' }).waitFor({ timeout: 20000 })
  await page.getByText(/228 companies/).waitFor({ timeout: 20000 })
  const blockedBody = await page.locator('body').innerText()
  assert.ok(blockedBody.includes('Valuation unavailable'))
  assert.ok(blockedBody.includes('convertible preferred'))
  assert.ok(!blockedBody.includes('Save scenario'))
  await page.screenshot({ path: screenshot('prim-blocked'), fullPage: true })
  console.log({ signed_in_browser: true, catalog_mode: mode, catalog_count: 228, edited_calculator: 'CSB 1.00x', calendar: 'September 24 and 25', search_navigation: 'ORE', loss_warning: 'ORE', enex_period: 'ENEX', total_proxy_warning: 'ECVC', inherited_blocked: 'PRIM' })
} finally {
  await browser.close()
  execFileSync('python3', ['-c', 'import os,psycopg; connection=psycopg.connect(host="127.0.0.1",port=5442,user=os.environ["POSTGRES_USER"],password=os.environ["POSTGRES_PASSWORD"],dbname=os.environ["POSTGRES_DB"]); cursor=connection.cursor(); cursor.execute("DELETE FROM users WHERE email = %s",(os.environ["FINSIGHT_BATCH22_TEST_EMAIL"],)); connection.commit(); connection.close()'], { env: { ...process.env, FINSIGHT_BATCH22_TEST_EMAIL: testEmail }, stdio: 'pipe' })
}
