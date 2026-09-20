# Implementation Plan（2026-09-20 建立，隨實作進度持續更新）

狀態：Phase 0～2.5 已完成並上線；Phase 3（股價資料管線）與 Phase 4（美股搜尋）進行中。

## 目標

把四個獨立的靜態理財工具合併成一個共用外殼的網站，新增美股搜尋，部署到 GitHub Pages（[SinLiongToo/FINTECH_plan_check](https://github.com/SinLiongToo/FINTECH_plan_check)），原始四個專案資料夾維持完全不動。

## 專案結構（新 repo：`project_claude_FINTECH`）

```
project_claude_FINTECH/
├── index.html                     ← 入口儀表板，4張卡片連到各工具
├── README.md                      ← 專案總覽 + 資料策略決策紀錄
├── IMPLEMENTATION_PLAN.md         ← 本文件
├── assets/
│   ├── shared.css                 ← 統一設計 tokens（色彩/字體/間距）+ 導覽列/footer 樣式
│   └── shared.js                  ← 深/淺色主題切換（localStorage 共用）、導覽列由 JS 動態注入（無需獨立 nav.html 片段，避免子路徑 fetch 問題）
├── tools/
│   ├── stock-drop/index.html      ← 複製自 taiwan_stock_v4.html
│   ├── rebalance/index.html       ← 複製自 rebalance.html
│   ├── retirement/index.html      ← 複製自 retirement simulation.html
│   └── loan/index.html            ← 複製自 fintech_loan_investment_tool.html
├── data/
│   └── stock_data.json            ← 方案 D 產生的股價快取（台股 + 美股）
├── fetch_stock_data.py            ← 改編自既有 dashboard 專案的抓股價腳本
├── .github/workflows/
│   └── daily_stock_update.yml     ← 排程 Action：跑 fetch_stock_data.py 並 commit 回 repo
└── (原本各工具的 server.py / update_*.py 保留在原資料夾，不搬進來 —
     GitHub Pages 正式站改用方案 D 取代這些本機代理腳本)
```

## 分期步驟

### Phase 0 — 驗證（已完成，見 README「工具驗證」章節）
- [x] 確認四個工具皆為自包含單一 HTML 檔，無隱藏的本地檔案依賴
- [x] 確認 Loan Simulator 的 Service Worker 為 Blob URL 動態註冊，非外部 sw.js 檔案
- [x] 確認 Stock Drawdown Explorer 的 `raw_data.js` 為未引用的舊版殘留檔，不需搬遷
- [x] 確認資料策略採用方案 D（GitHub Actions + yfinance + 靜態 JSON）

### Phase 1 — 專案骨架
- [x] 建立 `index.html` 入口儀表板（4 張工具卡片）
- [x] 建立 `assets/shared.css`、`assets/shared.js`：統一設計 tokens（`--ftk-*`）、深淺色主題切換（localStorage `ftk-theme`）、手機版漢堡選單
- [x] `git init`、建立 GitHub repo [`SinLiongToo/FINTECH_plan_check`](https://github.com/SinLiongToo/FINTECH_plan_check)（帳號登入的是 `SinLiongToo`，已跟你確認過就是要用的帳號）、開啟 GitHub Pages，上線網址：https://sinliongtoo.github.io/FINTECH_plan_check/

### Phase 2 — 搬遷四個工具
- [x] 複製四個原始 HTML 進 `tools/*/index.html`（原檔完全未改動，僅複製）
- [x] 每個工具 `<head>` 加一行 `<link>` 引入 `assets/shared.css`，`</body>` 前加 `<script>` 設定 `FTK_ROOT`/`FTK_PAGE` 並載入 `assets/shared.js`（共用導覽列+主題鈕以 `.ftk-` 命名空間注入，不會與各工具原有 CSS/JS 衝突）
- [x] Stock Drawdown Explorer：把它原生的 `.light` 深淺色切換，接到共用主題鈕（隱藏了它自己原本的 Light 按鈕，避免兩個切換鈕重複）
- [x] 導覽列新增常駐的「← 返回總覽」按鈕（只在工具頁顯示，不在首頁顯示），不需要展開手機版漢堡選單就能直接回首頁
- [x] 用 Playwright 起本機靜態伺服器 + headless Chromium 實際截圖驗證（不只是檢查 HTTP 200）：
  - 過程中抓到一個真正的 bug：`shared.js` 檔頭註解裡寫了 `tools/*/index.html` 這個字串，裡面的 `*/` 被 JS 剖析器當成註解結尾，導致整支腳本從那之後全部變成語法錯誤、共用導覽列在所有頁面都完全沒有渲染出來。已修正註解措辭並重新驗證通過（`node --check` + 五個頁面 headless 截圖皆正常）。
  - 桌面 + 手機（375px）雙尺寸、深/淺色雙主題都截圖比對過，四個工具頁面與首頁的導覽列、主題切換、返回按鈕、漢堡選單全部正常運作。
- [x] 手機版初步排版檢查：首頁卡片、Loan 工具的可折疊輸入面板、Retirement 工具的單欄堆疊都正常。**發現一個既有（非本次合併造成）的小瑕疵**：Rebalance Engine 的「股債年齡試算配置」巢狀 3 欄小格在 375px 寬度下會把整個輸入區擠出畫面造成水平溢出；這是原始 `rebalance.html` 本來就有的排版行為，不是搬遷過程造成的迴歸，列為後續可選的優化項目，未動手修正。

### Phase 2.5 — 四個工具的淺色模式（原本列為已知限制，已完成）
- [x] Rebalance Engine：CSS 變數本來就集中管理，直接新增 `html[data-theme="light"]` 覆寫區塊（含修正一個原本用寫死 `rgba(18,24,38,0.8)` 而非變數的頁首列背景，改用新變數 `--header-bg` 才能真正跟著換色）
- [x] Loan Investment Simulator：同樣是 CSS 變數集中管理，直接新增 `html[data-theme="light"]` 覆寫區塊
- [x] Retirement Simulator：這個工具整頁用 Tailwind CDN 工具類寫死深色（`bg-[#0b0f19]`、`text-slate-400` 等），沒有集中的 CSS 變數可覆寫，改成針對約 30 個實際用到的深色系工具類逐一寫 `html[data-theme="light"] .class{...!important}` 覆寫，另外挑出 4 個用 Tailwind 漸層做文字/背景效果的元素（quote 橫幅、頁首區塊、標題漸層文字 ×2）加上 id 直接覆寫 `background-image`，並讓 Chart.js 圖表在每次重繪時依當下主題挑選格線/座標軸顏色
- [x] 全部用 headless Chromium 實際截圖驗證深/淺色下的可讀性（沒有白底白字或黑底黑字的區塊）
- **未處理的小落差（刻意不做，性價比低）**：三個工具裡少數 Chart.js 的座標軸文字/格線顏色是寫死的中性灰／半透明白，在淺色模式下對比度沒有到完美，但仍可讀，跟頁面主體的文字對比策略一致（次要文字接受「還算堪讀」而非追求 WCAG AA 滿分），沒有另外寫程式在每次主題切換時即時重繪所有既有圖表（只有 Retirement 工具的圖表因為本來就是「按需重繪」而做了主題感知；已渲染完的舊圖表要到下次重新試算才會套用新配色）。

### Phase 3 — 股價資料管線（方案 D）
- [ ] 改編 `fetch_stock_data.py`，ticker map 涵蓋現有工具用到的台股代號 + 新增美股代號
- [ ] 建立 `.github/workflows/daily_stock_update.yml` 排程（台股/美股收盤各一次 + 手動觸發）
- [ ] Stock Drawdown Explorer：把「⚡ Server Refresh」改接 `data/stock_data.json`
- [ ] Rebalance Engine：把「🔄 自動抓取即時股價」改接 `data/stock_data.json`

### Phase 4 — 美股搜尋（新功能）
- [ ] 在共用外殼或 Stock Drawdown Explorer 內新增「美股搜尋」輸入框（代號/名稱比對 `data/stock_data.json` 裡的 ticker map）
- [ ] 決定是否需要 on-demand 查詢路徑（使用者輸入不在快取內的代號時的 fallback 行為）

### Phase 5 — 部署與驗收
- [x] Push 到 `SinLiongToo/FINTECH_plan_check`，開啟 GitHub Pages，build 成功、7 個路徑皆回應 200
- [x] Headless Chromium 檢查手機版（375px）+ 桌面版 + 深淺色切換
- [x] 確認四個工具間可自由切換（導覽列 + 返回總覽按鈕），狀態互不干擾（各工具用獨立 `localStorage`/記憶體狀態，僅共用 `ftk-theme`）
- [ ] 真人手機（iOS/Android 實機瀏覽器）尚未測試，僅用 headless Chromium 模擬 375px 視窗驗證

## 待確認事項

- 美股搜尋除了讀取排程快取的 `data/stock_data.json`，是否需要「使用者輸入任意代號都能即時查」的 on-demand 路徑（如果需要，屬於 Phase 4 的延伸討論，可能要回頭考慮方案 A 的 Cloudflare Worker 作為 fallback）。
