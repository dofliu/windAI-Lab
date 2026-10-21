#!/usr/bin/env node
/**
 * WindAI Lab 實機 E2E 冒煙測試（手動執行，不進 CI）
 *
 * 逐一巡覽 5 個分頁與其子頁面，並檢查：
 *   - 無 API 4xx/5xx 回應
 *   - 無 JS 例外（pageerror）
 *   - 另以 API 驗證「建立工單 → 結案 → /api/cases 自動 +1」
 *
 * 前置：後端 (uvicorn :5800) 與前端 (vite :5173) 已啟動；
 *       Playwright 需自行提供（本專案未將其列為依賴，屬供應鏈決策待授權）：
 *         NODE_PATH=<含 playwright 的 node_modules 目錄> node scripts/e2e_smoke.mjs
 *       Chromium 路徑可由 CHROMIUM_PATH 指定（預設使用 Playwright 內建）。
 *
 * 環境變數：FRONTEND_URL（預設 http://localhost:5173）、BACKEND_URL（預設 http://localhost:5800）
 */
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const { chromium } = require('playwright')

const FRONTEND = process.env.FRONTEND_URL ?? 'http://localhost:5173'
const BACKEND = process.env.BACKEND_URL ?? 'http://localhost:5800'

const TABS = [
  { label: '團隊', subs: ['代理詳情', '人事管理'] },
  { label: '分析', subs: ['SCADA 資料', 'ML Pipeline', '流程圖'] },
  { label: '知識', subs: [] },
  { label: '紀錄', subs: ['工作日誌', '歷史記錄', '維運報告'] },
  { label: '警報', subs: ['警報列表', '工單管理', '資料對接'] },
]

const failures = []

async function browseAllTabs() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.CHROMIUM_PATH || undefined,
  })
  const page = await browser.newPage()
  // 環境無任何 SCADA 資料時，SCADA 頁對 fallback 風機的 404 屬預期（UI 會顯示找不到風機）
  const { turbines = [] } = await api('/api/scada/turbines')
  page.on('response', (res) => {
    const noDataScada404 =
      turbines.length === 0 && res.status() === 404 && res.url().includes('/api/scada/')
    if (res.url().includes('/api/') && res.status() >= 400 && !noDataScada404) {
      failures.push(`API ${res.status()} ${res.request().method()} ${res.url()}`)
    }
  })
  page.on('pageerror', (err) => failures.push(`JS 例外: ${err.message}`))

  await page.goto(FRONTEND, { waitUntil: 'networkidle' })
  for (const tab of TABS) {
    await page.getByRole('button', { name: tab.label, exact: false }).first().click()
    await page.waitForLoadState('networkidle')
    for (const sub of tab.subs) {
      await page.getByRole('button', { name: sub, exact: true }).first().click()
      await page.waitForLoadState('networkidle')
    }
    console.log(`✓ 分頁「${tab.label}」${tab.subs.length} 個子頁面巡覽完成`)
  }
  await browser.close()
}

async function api(path, init) {
  const res = await fetch(`${BACKEND}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${path} → ${res.status}`)
  return res.json()
}

async function caseCount() {
  const body = await api('/api/cases')
  return body.total
}

async function closeWorkOrderFlow() {
  const before = await caseCount()
  const alert = await api('/api/alerts', {
    method: 'POST',
    body: JSON.stringify({
      title: 'e2e-smoke 告警',
      severity: 'warning',
      turbine_id: 'Kelmarsh_1',
      source: 'manual',
    }),
  })
  const alertId = alert.alert_id
  const wo = await api('/api/work-orders', {
    method: 'POST',
    body: JSON.stringify({ alert_id: alertId, title: 'e2e-smoke 工單' }),
  })
  const woId = wo.work_order_id
  await api(`/api/work-orders/${woId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status: 'completed' }),
  })
  const after = await caseCount()
  if (after !== before + 1) failures.push(`結案後案例數應 +1（${before} → ${after}）`)
  else console.log(`✓ 工單結案自動建案例（${before} → ${after}）`)
}

try {
  await browseAllTabs()
  await closeWorkOrderFlow()
} catch (err) {
  failures.push(`執行中斷: ${err.message}`)
}

if (failures.length > 0) {
  console.error('\n✗ E2E 冒煙測試失敗：')
  for (const f of failures) console.error(`  - ${f}`)
  process.exit(1)
}
console.log('\n✓ E2E 冒煙測試全部通過')
