# FinTech Toolkit（四合一理財工具箱）

把四個原本獨立的理財小工具合併成一個共用外殼（導覽列 / 深淺色主題 / 手機版）的靜態網站，部署在 GitHub Pages（帳號：**masahltu0322**）。

> ⚠️ 這個 repo 是**全新的合併專案**。四個原始工具的原始檔案完全不會被修改或搬移，只會被「複製」進來後再套上共用外殼。原始位置：
> - `Projects_antigravity/taiwan stock label drop`（股價下跌追蹤器）
> - `Projects_antigravity/rebalance_FINTECH`（跨市場再平衡計算機）
> - `Projects_antigravity/退休計算 retire`（退休試算）
> - `LOAN INVESTMENT FINTECH TOOL`（貸款 vs 投資試算）

---

## 四個工具

| 工具 | 來源檔案 | 技術 | 是否需要外部資料 |
|---|---|---|---|
| 📉 Stock Drawdown Explorer | `taiwan_stock_v4.html` | Vanilla JS + Chart.js | 選用（見下方） |
| ⚖️ Rebalance Engine | `rebalance.html` | Vanilla JS + Chart.js + Tailwind CDN | 選用（見下方） |
| 🏖️ Retirement Simulator | `retirement simulation.html` | Vanilla JS + Chart.js | 否，純本地試算 |
| 💰 Loan Investment Simulator | `fintech_loan_investment_tool.html` | Vanilla JS + Chart.js + Service Worker 離線快取 | 否，純本地試算 |

四個檔案都是**單一 HTML、無 build step**，內嵌全部 CSS/JS，天生適合 GitHub Pages。詳細驗證結果見下方「工具驗證」章節。

---

## 股價資料策略：為什麼選 GitHub Actions + yfinance

GitHub Pages 只能放靜態檔案，不能跑 Python，所以「即時抓股價」（含新增的美股搜尋）不能直接沿用原本兩個工具裡的 `server.py`（本機 CORS 代理）。討論過程中比較了 4 種做法：

| 方案 | 做法 | 優點 | 缺點 | 是否採用 |
|---|---|---|---|---|
| A. 雲端代理 (Cloudflare Worker) | 部署一個免費 Worker，功能等同 `server.py`，前端即時呼叫 | 使用者輸入任意美股代號都能「當下」即時查 | 需要額外的 Cloudflare 帳號、多一個服務要維護 | 否 |
| B. 純靜態、無即時資料 | 比照 `update_prices.py`，本地先跑腳本把股價寫死進 HTML | 零額外服務、最穩定 | 股價不即時，美股搜尋功能有限 | 否（可當保底 fallback） |
| C. 公開 CORS Proxy | 直接呼叫 `corsproxy.io` / `allorigins` 等公開代理轉發 Yahoo Finance | 最快實作 | 公開服務不穩定、常被限流或關閉，不適合長期依賴 | 否 |
| **D. GitHub Actions + yfinance（採用）** | 排程 Action 在 GitHub 自己的伺服器上用 `yfinance` 抓資料，算好指標後把結果寫成靜態 `data/stock_data.json` 並 commit 回 repo；網頁只讀這份預先算好的 JSON | 不需要額外帳號/服務、完全留在 GitHub 生態系內、**已有現成可用的實作可以直接複用**（見下） | 資料是「排程快取」而非使用者輸入當下即時抓，最多落後半個交易日；若要做到任意美股代號的即時 autocomplete 查詢，仍需額外設計「on-demand 觸發」路徑 | ✅ 是 |

**方案 D 的實際運作方式**（沿用並改編自既有專案 `FINICIAL ANNUAL REPORT DOWNLOAD TO MD_dashboard/fetch_stock_data.py` 與 `.github/workflows/daily_stock_update.yml`）：

1. `fetch_stock_data.py` 用 `yfinance` 抓每檔股票的 5 年日線 + 近 5 天 15 分鐘線，計算 MA20/MA60、52 週高低、漲跌幅，寫進 `data/stock_data.json`。內建的 ticker map 已經涵蓋大量美股代號（`NVDA`/`AAPL`/`MSFT`…）與台股代號（`2330.TW`…），也支援任意代號 fallback。
2. GitHub Actions 排程在台股收盤（UTC 06:30）與美股收盤（UTC 22:00）各跑一次，也可手動觸發（`workflow_dispatch`）。
3. 因為抓資料的動作發生在 **GitHub Actions 的伺服器**、不是使用者瀏覽器，完全沒有 CORS 問題。
4. Action 用 `github-actions[bot]` 身分把更新後的 `data/stock_data.json` commit + push 回 repo；GitHub Pages 上線的網頁純粹讀取這份寫死的 JSON，頁面載入時不即時打 API。

合併後的四個工具會共用同一份 `data/stock_data.json` 作為股價資料底層：Stock Drawdown Explorer 用它畫走勢圖、Rebalance Engine 用它抓最新價格試算，新增的「美股搜尋」也是在這份資料集裡做代號/名稱比對搜尋。

---

## 工具驗證（Verification）

四個原始檔案在複製進來之前先做過結構檢查，確認是否為「可直接搬遷」的自包含檔案：

### 📉 Stock Drawdown Explorer (`taiwan_stock_v4.html`)
- ✅ 完全自包含：股價資料以 `const RAW = {...}` 直接內嵌在 `<script>` 裡，**不是**從外部 `raw_data.js` 載入。
- ⚠️ 同資料夾裡的 `raw_data.js` 與 `DRAWNDOWN EXPLORER/taiwan_stock_v3 (1).html` 是舊版殘留檔案，目前的 v4 沒有引用它們，合併時**不需要一併複製**。
- ℹ️ 內建「⚡ Server Refresh」按鈕會呼叫 `localhost:8765`（`server.py`），這條路徑部署到 GitHub Pages 後會失效，需改接方案 D 的 `data/stock_data.json`。
- ✅ 已有 light/dark class 機制，可直接擴充成全站共用主題。

### ⚖️ Rebalance Engine (`rebalance.html`)
- ✅ 完全自包含：只依賴外部 CDN（Chart.js + Google Fonts），沒有任何本地相對路徑檔案依賴。
- ℹ️ `prototype/REALANCE.html` 是較早期的原型版本，合併時採用根目錄的 `rebalance.html`（新版，含雙模式再平衡邏輯）。
- ℹ️ 「🔄 自動抓取即時股價」按鈕同樣呼叫本機 `server.py`（TWSE + Yahoo Finance 代理），部署後需改接方案 D。
- ✅ 已有深色玻璃質感設計系統，可作為共用設計語言的參考基準之一。

### 🏖️ Retirement Simulator (`retirement simulation.html`)
- ✅ 完全自包含：只依賴 Chart.js CDN，純本地試算，無任何外部資料依賴，可直接搬遷、無需改動任何資料串接邏輯。

### 💰 Loan Investment Simulator (`fintech_loan_investment_tool.html`)
- ✅ 完全自包含：只依賴 Chart.js CDN，純本地試算。
- ⚠️ **Service Worker 用 Blob URL 動態產生並註冊**（`URL.createObjectURL` + `navigator.serviceWorker.register(swUrl)`），不是外部 `sw.js` 檔案，所以搬移路徑不會有「檔案找不到」問題；但部分瀏覽器對 blob URL 註冊 Service Worker 的支援不一致，可能靜默失敗（程式碼有 `.catch(()=>{})` 吞掉錯誤）——離線快取功能屬於錦上添花，失敗也不影響主功能，可視為已知風險、無需修正。

**結論：四個工具都是可以直接複製進新專案、不需要修改內部邏輯的自包含檔案。** 唯二需要新增串接的地方，是把 Stock Drawdown Explorer 與 Rebalance Engine 裡「呼叫 localhost:8765 本機代理」的按鈕，改成讀取方案 D 產生的 `data/stock_data.json`。

---

## 部署

- GitHub 帳號：**masahltu0322**（新建 repo，用 GitHub Pages 發布）
- 靜態站台（`index.html` + `tools/*`）由 GitHub Pages 直接發布
- 股價資料管線（`fetch_stock_data.py` + Actions workflow）與站台在同一個 repo 內，排程自動更新、自動 commit

詳細分期實作步驟見 [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)。
