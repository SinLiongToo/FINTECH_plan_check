# Implementation Plan（初版，2026-09-20 記錄）

狀態：**規劃階段，尚未開始實作**。此文件記錄目前討論定案的整合方案，作為後續實作的依據；隨實作進度更新。

## 目標

把四個獨立的靜態理財工具合併成一個共用外殼的網站，新增美股搜尋，部署到 GitHub Pages（帳號 `masahltu0322`），原始四個專案資料夾維持完全不動。

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
- [ ] `git init` 新 repo，設定 GitHub Pages（`masahltu0322` 帳號下新建 repo）— 尚未執行，待你確認 repo 名稱後才建立/推送

### Phase 2 — 搬遷四個工具
- [x] 複製四個原始 HTML 進 `tools/*/index.html`（原檔完全未改動，僅複製）
- [x] 每個工具 `<head>` 加一行 `<link>` 引入 `assets/shared.css`，`</body>` 前加 `<script>` 設定 `FTK_ROOT`/`FTK_PAGE` 並載入 `assets/shared.js`（共用導覽列+主題鈕以 `.ftk-` 命名空間注入，不會與各工具原有 CSS/JS 衝突）
- [x] Stock Drawdown Explorer：把它原生的 `.light` 深淺色切換，接到共用主題鈕（隱藏了它自己原本的 Light 按鈕，避免兩個切換鈕重複）
- [x] 本機起了一個暫時的靜態伺服器，確認 7 個頁面（index + 4 工具 + 2 個 assets 檔）都能以正確的相對路徑載入（HTTP 200），沒有壞連結
- [ ] 手機版排版（表格橫向捲動、輸入區可折疊）尚未逐一在四個工具上實機檢查，建議 Phase 5 部署後用手機瀏覽器實測

### 已知限制（尚未處理）
- Rebalance / Retirement / Loan 三個工具**目前完全沒有淺色模式**（原始設計就是深色寫死，顏色多為固定變數但沒有 light 版本的變數值）。目前共用導覽列/首頁的主題切換鈕**只會影響外層的 nav/footer/首頁**，不會改變這三個工具內容區的顏色。只有 Stock Drawdown Explorer 因為原本就有 `.light` 機制，才能真正跟著切換。
  若要讓這三個工具的內容區也支援淺色模式，需要另外幫每個工具新增一組淺色版 CSS 變數（非小工程，建議列為獨立的後續任務，而不是這次順手做）。

### Phase 3 — 股價資料管線（方案 D）
- [ ] 改編 `fetch_stock_data.py`，ticker map 涵蓋現有工具用到的台股代號 + 新增美股代號
- [ ] 建立 `.github/workflows/daily_stock_update.yml` 排程（台股/美股收盤各一次 + 手動觸發）
- [ ] Stock Drawdown Explorer：把「⚡ Server Refresh」改接 `data/stock_data.json`
- [ ] Rebalance Engine：把「🔄 自動抓取即時股價」改接 `data/stock_data.json`

### Phase 4 — 美股搜尋（新功能）
- [ ] 在共用外殼或 Stock Drawdown Explorer 內新增「美股搜尋」輸入框（代號/名稱比對 `data/stock_data.json` 裡的 ticker map）
- [ ] 決定是否需要 on-demand 查詢路徑（使用者輸入不在快取內的代號時的 fallback 行為）

### Phase 5 — 部署與驗收
- [ ] Push 到 `masahltu0322` 的 GitHub repo，開啟 GitHub Pages
- [ ] 實機檢查手機版（iOS/Android 瀏覽器）+ 桌面版 + 深淺色切換
- [ ] 確認四個工具間可自由切換，狀態互不干擾

## 待確認事項

- 美股搜尋除了讀取排程快取的 `data/stock_data.json`，是否需要「使用者輸入任意代號都能即時查」的 on-demand 路徑（如果需要，屬於 Phase 4 的延伸討論，可能要回頭考慮方案 A 的 Cloudflare Worker 作為 fallback）。
- 新 GitHub repo 的名稱尚未決定。
