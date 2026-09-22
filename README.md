# FinTech Toolkit（理財工具箱）

把四個原本獨立的理財小工具 + 一份理財觀念參考頁，合併成一個共用外殼（導覽列 / 深淺色主題 / 手機版）的靜態網站，部署在 GitHub Pages。

**上線網址：https://sinliongtoo.github.io/FINTECH_plan_check/**
Repo：[SinLiongToo/FINTECH_plan_check](https://github.com/SinLiongToo/FINTECH_plan_check)

> ⚠️ 這個 repo 是**全新的合併專案**。四個原始工具的原始檔案完全不會被修改或搬移，只會被「複製」進來後再套上共用外殼。原始位置：
> - `Projects_antigravity/taiwan stock label drop`（股價下跌追蹤器）
> - `Projects_antigravity/rebalance_FINTECH`（跨市場再平衡計算機）
> - `Projects_antigravity/退休計算 retire`（退休試算）
> - `LOAN INVESTMENT FINTECH TOOL`（貸款 vs 投資試算）

---

## 五個頁面

| 頁面 | 來源 | 資料來源 | 備註 |
|---|---|---|---|
| 📉 [股價下跌追蹤](tools/stock-drop/) | `taiwan_stock_v4.html` | `data/stock_data.json`（見下方管線） | 14 檔內建（台股個股 + TAIEX）+ VT/BND/SOXX + 美股搜尋（55 檔資料庫） |
| ⚖️ [再平衡計算](tools/rebalance/) | `rebalance.html` | `data/stock_data.json` → AllOrigins CORS proxy（僅限資料庫沒收錄的自訂代號） | 雙幣別（TWD/USD）獨立投入 or 全球統一再平衡 |
| 🏖️ [退休試算](tools/retirement/) | `retirement simulation.html` | 純本地試算 | 內建中英文切換、巴菲特金句跑馬燈 |
| 💰 [貸款投資試算](tools/loan/) | `fintech_loan_investment_tool.html` | 純本地試算 | 內建 20 句中英雙語理財金句跑馬燈、Help 按鈕直達說明頁 |
| 📜 [人生財務守則](tools/rules/)（新增） | 全新內容 | 純靜態 | 9 條理財法則（72法則、100減年齡、50-30-20、解套公式、複利成長…），內建中英文切換 |

四個原始工具都是**單一 HTML、無 build step**，內嵌全部 CSS/JS，天生適合 GitHub Pages；第 5 個頁面完全用共用設計系統（`assets/shared.css`）新寫。詳細個別驗證結果見下方「工具驗證」章節。

---

## 共用外殼功能

- **導覽列**：所有頁面共用，可在 5 個頁面間自由切換，工具頁另外有常駐的「← 返回總覽」按鈕。
- **深/淺色模式**：全站共用一顆切換鈕（存在 `localStorage`），四個原始工具 + 新增頁面全部都支援（Rebalance/Loan 原本就用 CSS 變數管理色彩，直接加一組淺色變數；Retirement 是 Tailwind 工具類寫死深色，改成針對實際用到的類別逐一覆寫；Stock Drawdown Explorer 本來就有 light/dark class，直接接上共用按鈕）。
- **手機版**：所有頁面在 375px 寬度下都可正常操作（表格橫向捲動、輸入區可折疊、股票 chip 列有 ‹ › 按鈕可左右捲動）。
- **首頁最後更新時間**：用 `document.lastModified` 讀取 GitHub Pages 回報的實際檔案更新時間，不需要手動維護日期字串。

---

## 股價資料策略：為什麼選 GitHub Actions + yfinance

GitHub Pages 只能放靜態檔案，不能跑 Python，所以「即時抓股價」（含美股搜尋）不能直接沿用原本工具裡的 `server.py`（本機 CORS 代理）。討論過程中比較了 4 種做法：

| 方案 | 做法 | 優點 | 缺點 | 是否採用 |
|---|---|---|---|---|
| A. 雲端代理 (Cloudflare Worker) | 部署一個免費 Worker，功能等同 `server.py`，前端即時呼叫 | 使用者輸入任意美股代號都能「當下」即時查 | 需要額外的 Cloudflare 帳號、多一個服務要維護 | 否 |
| B. 純靜態、無即時資料 | 比照 `update_prices.py`，本地先跑腳本把股價寫死進 HTML | 零額外服務、最穩定 | 股價不即時，美股搜尋功能有限 | 否（當作內建 fallback 資料，見下） |
| C. 公開 CORS Proxy | 直接呼叫 `corsproxy.io` / `allorigins` 等公開代理轉發 Yahoo Finance | 最快實作 | **實測證實不穩定**：Rebalance 用這個當備援時，同一批請求裡部分代號成功、部分 `net::ERR_FAILED`，且失敗時沒有任何提示，會靜默顯示舊資料 | 僅保留給不在方案 D 資料庫裡的自訂代號當最後備援 |
| **D. GitHub Actions + yfinance（主要方案）** | 排程 Action 在 GitHub 自己的伺服器上用 `yfinance` 抓資料，寫成靜態 `data/stock_data.json` 並 commit 回 repo；網頁只讀這份預先算好的 JSON，同源請求、無 CORS 問題 | 不需要額外帳號/服務、完全留在 GitHub 生態系內、同源不受 CORS/流量限制 | 資料是「排程快取」而非使用者輸入當下即時抓，最多落後到下一次排程；覆蓋範圍限定在內建的 55 檔 ticker map | ✅ 是，Stock Drawdown Explorer 與 Rebalance Engine 兩個工具共用 |

**方案 D 的實際運作方式**：

1. `fetch_stock_data.py` 用 `yfinance` 抓每檔股票的**週線**完整歷史（`period="max", interval="1wk"`），計算 52 週高低、漲跌幅，寫進 `data/stock_data.json`。改用週線而非日線是刻意的選擇：跟兩個工具內建的「Weekly GBM data」粒度一致，也讓檔案大小可控（55 檔股票、完整歷史，約 7 MB）。內建 ticker map 涵蓋 Stock Drawdown Explorer 的 14 檔台股 + TAIEX、Rebalance 的 VT/BND/0050 預設持股，再加 6 檔大盤 ETF 與美股大型股（共 55 檔）作為美股搜尋的資料庫。
2. GitHub Actions 排程在台股收盤（UTC 06:30）與美股收盤（UTC 22:00）各跑一次，也可手動觸發（`workflow_dispatch`）。
3. 因為抓資料的動作發生在 **GitHub Actions 的伺服器**、不是使用者瀏覽器，完全沒有 CORS 問題。
4. Action 用 `github-actions[bot]` 身分把更新後的 `data/stock_data.json` commit + push 回 repo；GitHub Pages 上線的網頁純粹讀取這份 JSON，頁面載入時不即時打 API。
5. **Stock Drawdown Explorer**：頁面一載入就在背景把所有內建股票的資料換成這份即時資料（不用手動按 Refresh），「Refresh current / Refresh all」按鈕偵測不到本機伺服器時也會自動用這份資料當備援；美股搜尋框直接在這份資料集裡比對代號/公司名稱。
6. **Rebalance Engine**：「🔄 自動抓取即時股價」按鈕依序嘗試本機伺服器 → 這份靜態資料 → AllOrigins 公開代理（僅限資料庫沒收錄的自訂代號）。

### 已知限制

- **資料新鮮度取決於 Yahoo Finance 自己的發布節奏，不是排程有沒有跑**：實測發現台股個股（如台積電、鴻海）通常比 TAIEX 指數或美股 ETF 更新得快；指數/美股某週的資料有時要等 1–2 天才會出現在 Yahoo 的回應裡（查詢當下是 `NaN`），不是我們的 pipeline 壞掉，下一次排程抓到新資料就會自動更新。
- 美股搜尋侷限在 `fetch_stock_data.py` 內建的 ticker map（目前 55 檔），沒有做到「輸入任意代號都能即時查」——如果需要，可以改用方案 A（Cloudflare Worker）擴充。

---

## 工具驗證（Verification）

四個原始檔案在複製進來之前先做過結構檢查，確認是否為「可直接搬遷」的自包含檔案：

### 📉 Stock Drawdown Explorer (`taiwan_stock_v4.html`)
- ✅ 完全自包含：股價資料以 `const RAW = {...}` 直接內嵌在 `<script>` 裡。
- ✅ 頁面載入時自動把所有內建股票換成 `data/stock_data.json` 的即時資料（不用手動按 Refresh），「Refresh current / Refresh all」在部署站上一樣能正確 fallback。
- ✅ 美股搜尋：chip 列下方新增搜尋框，即時比對美股代號/公司名稱，選取後動態加一個 chip 並載入真實歷史跌幅分析。
- ✅ chip 列加了左右 ‹ › 捲動按鈕（原本靠隱藏捲軸手動滑動，容易滑過去後不知道怎麼滑回來）。
- ✅ RANGE 篩選（3M/6M/1Y…）改成以資料本身最後一筆日期為基準往回算，而不是用瀏覽當下的真實時間——避免資料略舊時篩窄範圍會整個顯示空白。新增 1W / 1M 兩個更短的範圍選項。
- ✅ 已有 light/dark class 機制，已接到全站共用的主題切換鈕上。

### ⚖️ Rebalance Engine (`rebalance.html`)
- ✅ 完全自包含：只依賴外部 CDN（Chart.js + Google Fonts）。
- ✅ 「🔄 自動抓取即時股價」已接上 `data/stock_data.json`（見上方資料策略章節），不再只依賴不穩定的公開 CORS 代理。
- ✅ 新增淺色模式（含修正一處寫死深色、沒有跟著變數換色的頁首列背景）。

### 🏖️ Retirement Simulator (`retirement simulation.html`)
- ✅ 完全自包含：只依賴 Chart.js CDN，純本地試算。
- ✅ 新增淺色模式：這個工具是用 Tailwind CDN 工具類寫死深色（沒有集中的 CSS 變數），改成針對實際用到的深色工具類逐一覆寫，另外處理了 4 個用漸層做視覺效果的元素。

### 💰 Loan Investment Simulator (`fintech_loan_investment_tool.html`)
- ✅ 完全自包含：只依賴 Chart.js CDN，純本地試算。
- ⚠️ Service Worker 用 Blob URL 動態產生並註冊，不是外部 `sw.js` 檔案；部分瀏覽器可能靜默不支援，離線快取屬於錦上添花，不影響主功能。
- ✅ 新增淺色模式、常駐的「❓ 使用說明 Help」按鈕（直接跳到原本就有、但藏在 9 個分頁裡容易被忽略的 README/Changelog 分頁）、20 句中英雙語理財金句跑馬燈。

**四個工具都是可以直接複製進新專案、不需要修改內部邏輯的自包含檔案**，唯一的串接工作是把兩個工具裡「呼叫本機 `localhost` 代理」的按鈕改接方案 D 的 `data/stock_data.json`。

---

## 部署

- Repo/GitHub Pages 建立在 **SinLiongToo** 這個 GitHub 帳號下
- 上線網址：https://sinliongtoo.github.io/FINTECH_plan_check/
- 靜態站台（`index.html` + `tools/*`）由 GitHub Pages 直接發布
- 股價資料管線（`fetch_stock_data.py` + `.github/workflows/daily_stock_update.yml`）與站台在同一個 repo 內，排程自動更新、自動 commit

詳細分期實作步驟與每個修正的完整脈絡，見 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)。
