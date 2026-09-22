# Implementation Plan（2026-09-20 建立，隨實作進度持續更新）

狀態：Phase 0～6 已完成並上線。剩下真人手機實機測試與少數列為刻意不做/後續可選的項目。

## 目標

把四個獨立的靜態理財工具合併成一個共用外殼的網站，新增美股搜尋，部署到 GitHub Pages（[SinLiongToo/FINTECH_plan_check](https://github.com/SinLiongToo/FINTECH_plan_check)），原始四個專案資料夾維持完全不動。

## 專案結構（新 repo：`project_claude_FINTECH`）

```
project_claude_FINTECH/
├── index.html                     ← 入口儀表板，5張卡片連到各頁面 + 最後更新時間
├── README.md                      ← 專案總覽 + 資料策略決策紀錄
├── IMPLEMENTATION_PLAN.md         ← 本文件
├── assets/
│   ├── shared.css                 ← 統一設計 tokens（色彩/字體/間距）+ 導覽列/footer 樣式
│   └── shared.js                  ← 深/淺色主題切換（localStorage 共用）、導覽列由 JS 動態注入（無需獨立 nav.html 片段，避免子路徑 fetch 問題）
├── tools/
│   ├── stock-drop/index.html      ← 複製自 taiwan_stock_v4.html
│   ├── rebalance/index.html       ← 複製自 rebalance.html
│   ├── retirement/index.html      ← 複製自 retirement simulation.html
│   ├── loan/index.html            ← 複製自 fintech_loan_investment_tool.html
│   └── rules/index.html           ← 全新頁面：人生財務守則（9 條，中英文切換）
├── data/
│   └── stock_data.json            ← 方案 D 產生的股價快取（台股 + 美股，55 檔）
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
- [x] 寫 `fetch_stock_data.py`：ticker map 涵蓋 Stock Drawdown Explorer 內建的 15 檔台股 + TAIEX、Rebalance 預設的 VT/BND/0050，另外加了 6 檔大盤 ETF（VOO/VTI/QQQ/SPY 等）+ 33 檔美股大型股，共 55 檔。**改用週線（`interval="1wk"`, `period="max"`）而不是日線**：跟兩個工具內建的「Weekly GBM data」資料粒度一致，也讓 `data/stock_data.json` 保持在合理大小（55 檔 × 完整歷史約 6.8 MB），避免排程一天兩次 commit 造成 repo 過度膨脹；沒有沿用原本 dashboard 專案版本會抓的 intraday 分鐘線和 MA20/MA60，因為這兩個工具目前都用不到。
- [x] 本機實際跑過 `python fetch_stock_data.py --all`：55/55 成功，驗證過 JSON 結構（`data/stock_data.json`，每檔股票同時用 `symbol`／小寫代號／台股去點號代號 3 種 key 存取）。
- [x] 建立 `.github/workflows/daily_stock_update.yml`：台股收盤（UTC 06:30）與美股收盤（UTC 22:00）各跑一次 + `workflow_dispatch` 手動觸發，跑完用 `github-actions[bot]` 身分 commit + push `data/stock_data.json`。
- [x] Stock Drawdown Explorer：「⚡ Refresh current」與「⚡⚡ Refresh all 15」現在都會在偵測不到本機 `server.py`（GitHub Pages 上一定偵測不到）時，自動 fallback 改讀 `data/stock_data.json`，用 headless Chromium 實測過兩個按鈕在完全沒有本機伺服器的情況下都能正確載入真實股價、更新圖表與 chip 上的價格。
- [x] Rebalance Engine：原本刻意沒接（理由：本來就有 allorigins.win CORS proxy 當 fallback，先不重工）。**上線後使用者實測回報「還是舊資料」**，用 Playwright 監看正式站的網路請求直接抓到證據：同一批請求裡 VT 抓成功、BND 和 0050.TW 都是 `net::ERR_FAILED`，公開代理不穩定且失敗時沒有任何提示。已改接：本機伺服器 → `data/stock_data.json` → allorigins.win（僅限資料庫沒收錄的自訂代號）。詳見 Phase 6。

### Phase 4 — 美股搜尋（新功能，已完成）
- [x] 在 Stock Drawdown Explorer 的 chip 列下方新增「🔍 Search US stocks」輸入框，即時比對 `data/stock_data.json` 裡幣別為 USD 的所有代號 + 公司名稱（大小寫不敏感、代號或名稱局部比對皆可，如打 `nvda` 或 `apple` 都能找到），下拉最多顯示 8 筆結果。
- [x] 點選結果後：動態新增一個 chip（跟內建 15 檔台股長得一模一樣，沿用同一套 CSS），把該股票的完整週線歷史從 `data/stock_data.json` 灌進 `liveRAW`，並直接切換圖表顯示該股票的真實跌幅分析（不是內建的 GBM 模擬資料）。用 headless Chromium 實測過搜尋 NVDA、Apple，圖表、最大回撤、標籤文字（正確顯示「Static live data」而非誤植「Weekly GBM data」）都正確。
- [x] 沒有做「使用者輸入任意不在快取內的代號也能即時查」的 on-demand 路徑（待確認事項裡提過的方案 A/Cloudflare Worker）——目前搜尋範圍限定在 `fetch_stock_data.py` 的 ticker map 內建的美股清單（33 檔大型股 + 6 檔 ETF），這是刻意的範圍收斂，不是遺漏。

### Phase 5 — 部署與驗收
- [x] Push 到 `SinLiongToo/FINTECH_plan_check`，開啟 GitHub Pages，build 成功、7 個路徑皆回應 200
- [x] Headless Chromium 檢查手機版（375px）+ 桌面版 + 深淺色切換
- [x] 確認四個工具間可自由切換（導覽列 + 返回總覽按鈕），狀態互不干擾（各工具用獨立 `localStorage`/記憶體狀態，僅共用 `ftk-theme`）
- [ ] 真人手機（iOS/Android 實機瀏覽器）尚未測試，僅用 headless Chromium 模擬 375px 視窗驗證

### Phase 6 — 上線後的使用者回報修正與強化

上線之後陸續收到的實際使用回報與追加需求，逐項記錄：

- [x] **鴻海錯字**：STOCKS 陣列裡的中文名稱用錯 Unicode 碼點寫成「鉤海」，修正為「鴻海」（正確碼點 U+9D3B，不是 U+9D3F=「鴿」）。
- [x] **Loan 工具新增 Help 按鈕**：原本就有完整的 README/Changelog 分頁，但排在 9 個分頁裡的最後一個很容易被忽略；標題列加一顆常駐按鈕直接跳過去並捲動到可見範圍。
- [x] **Loan 工具新增金句跑馬燈**：仿照 Retirement 工具的巴菲特金句跑馬燈，但改成中英文同一行顯示（跟 Loan 工具原本「中文 / English」並列的風格一致，不是切換語言）；先做 10 句，後續依需求擴充到 20 句（愛因斯坦複利、巴菲特、查理蒙格、戴夫·拉姆齊等）。
- [x] **股價下跌追蹤：日期標籤誤導**：「Static live data」標籤原本顯示的是「腳本抓取當天」的日期（`as_of`），但因為資料是週線，這個日期常常跟圖表最後一筆的實際日期對不上（使用者回報「圖表明明是 9/14，標籤卻寫 9/20」）。改成直接讀圖表最後一筆的實際日期；過程中還修正了一個用 `toISOString()` 造成的時區位移 bug（會因為轉 UTC 而讓日期整個誤差一天）。
- [x] **股價下跌追蹤：RANGE 篩選在資料略舊時顯示空白**：3M/6M 等範圍原本是用「瀏覽當下的真實時間」往回算，但內建 GBM 資料的最後一筆是固定日期（不會跟著今天走），資料越舊、篩選範圍越窄就越容易整個落在資料範圍之外變成空白。改成以資料本身最後一筆為基準往回算。新增 1W / 1M 兩個更短的範圍選項（因為資料本身是週線，1W 通常只有 1–2 個點，這是資料粒度的先天限制，不是 bug）。
- [x] **股價下跌追蹤：調整內建股票清單**：移除大立光(3008)、富邦金(2881)、中信金(2891)、兆豐金(2886)；新增 VT、BND、SOXX（這三檔沒有內建的 GBM 模擬資料，改成頁面載入時自動從 `data/stock_data.json` 抓真實資料）。頁面底部加上版本標示。
- [x] **股價下跌追蹤：chip 列捲動不明顯**：新增的 VT/BND/SOXX 因為 chip 列變寬，超出畫面的部分要靠隱藏捲軸（`scrollbar-width:none`，刻意設計但沒有替代提示）才能滑到，使用者反應「新增的怎麼不見了」。先加了一個淡出漸層提示，使用者又回報「滑過去後滑不回來」——因為單純用滑鼠滾輪本來就無法左右捲動這種容器。最後改成真正的 ‹ › 按鈕，點擊即可雙向捲動，用程式驗證過滑到底再滑回起點確實能回到 `scrollLeft:0`。
- [x] **新增第 5 個頁面「人生財務守則」**：使用者提供一張「7 Personal Finance Rules」資訊圖，翻譯成中文並建成新頁面（用共用設計系統 `assets/shared.css` 從零寫成，不是搬移既有工具，因此深淺色主題是免費繼承來的）。加進首頁卡片與全站導覽列。後續依需求追加第 8 條（解套公式：`解套所需報酬率 = 虧損% ÷ (1-虧損%)`）與第 9 條（複利成長法則：`(1.01)^365 ≈ 37.8`）。最後把整頁改成 JS 資料驅動（`RULES` 陣列 + `render()`），加上真正的中英文切換按鈕（不是原本只有中文內文 + 英文小標籤，是重新寫了完整的英文翻譯）。
- [x] **首頁新增最後更新時間**：用 `document.lastModified` 讀取 GitHub Pages 實際回報的檔案更新時間（已用 `curl -I` 驗證過這個 header 準確可靠），不需要每次改動都手動更新日期字串。
- [x] **股價下跌追蹤：預設只有部分股票是即時資料**：使用者回報「資料倒退回 4-5 月了」——原因是頁面預設一律顯示寫死在 HTML 裡的 GBM 模擬資料（固定停在 2026-06-01 左右），只有手動按 Refresh 或用搜尋加入的股票才會換成即時資料，不是排程沒 push（用 `gh run list` 查過排程一直都成功執行）。改成頁面一載入就在背景把「所有」內建股票（不只是 VT/BND/SOXX）換成 `data/stock_data.json` 的即時資料，點擊任何 chip 都會優先使用即時資料，找不到才退回 GBM 模擬資料。
- [x] **Rebalance Engine：自動抓取即時股價回報「還是舊資料」**：用 Playwright 監看正式站按下「🔄 自動抓取即時股價」後的實際網路請求，抓到 AllOrigins 公開代理對同一批請求裡部分成功、部分 `net::ERR_FAILED`（BND、0050.TW 失敗），且失敗時完全沒有錯誤提示。改接 `data/stock_data.json` 當中間備援（本機伺服器 → 靜態資料管線 → AllOrigins，AllOrigins 只保留給資料庫沒收錄的自訂代號）。
- [x] **美股資料回報「停留在 9/14」**：先用 `gh run list` 確認排程本身一直有成功執行，再直接問 yfinance「現在」的資料，發現 Yahoo 那週的資料回的是 `NaN`（還沒發布），不是我們的問題。等了一段時間後重新查詢，確認 Yahoo 已經補上資料，手動觸發 workflow 兩次讓正式站资料追上（`gh workflow run` + 輪詢 `gh run view --json status`）。順便把 `current_price`／`day_change` 改成優先用短天期日線資料計算（不再單純依賴週線本身，週線的發布節奏比日線慢），新增 `quote_date` 欄位標明價格實際對應日期；同時修正了一個附帶發現的問題：`day_change` 原本其實是週對週差異，被誤標成日漲跌，現在改成真正的日對日變化。

## 後續可選的加強項目（非阻塞，未動手做）

- 美股搜尋擴大到「任意代號都能即時查」而非侷限在 `fetch_stock_data.py` 內建的清單，需要方案 A（Cloudflare Worker）或擴充 ticker map。
- Rebalance Engine「股債年齡試算配置」在 375px 手機寬度下的水平溢出（Phase 2 驗證時發現的既有瑕疵，非本次合併造成）。
- 真人手機（iOS/Android 實機瀏覽器）測試，目前只用 headless Chromium 模擬 375px 視窗驗證過。
