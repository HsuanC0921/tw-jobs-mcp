# tw-jobs-mcp

[English](README.md) · **繁體中文**

[![test](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![MCP](https://img.shields.io/badge/MCP-stdio%20%7C%20streamable--http-green)

**台灣求職網站的唯讀 [MCP（Model Context Protocol）](https://modelcontextprotocol.io) server。** 讓 Claude、Codex、Gemini、Cursor 等支援 MCP 的 AI 助理與 agent，直接搜尋 **104 人力銀行**、**Yourator**，以及外商自家職缺網站（Greenhouse、Lever、Workday）上的台灣職缺與公司資料，之後可能會加入更多來源。

地區、職類直接寫中文名稱（`台北市大安區`、`軟體工程師`），server 會自動轉成 104 的代碼。不需要帳號，也不需要 API key。

> **非官方工具**，與 104 無關。它呼叫的是 104 網站公開的網頁端點，請控制使用頻率並遵守 104 的使用條款。專案不附帶任何職缺資料。

## 特色

- **四個互補的來源**：104 量最大；Yourator 偏新創與外商據點；外商職缺板（Appier、Ubiquiti、Canonical、Stripe、MongoDB、Pinkoi、Binance 等）收的是外商只貼在自家網站、104 上找不到的職缺；Workday 則涵蓋半導體、硬體與藥廠外商（NVIDIA、Micron、Applied Materials、KLA、Cisco、Intel、Marvell、NXP、HP、GSK、Novartis 等）。用 `source` 指定其一，或 `source="all"` 一次全搜。
- **六個工具，全部唯讀**：`search_jobs`、`get_job`、`get_company`、`salary_overview`、`lookup_code`、`sources`。每個工具都標了 MCP 的唯讀註記，會讀這個註記的客戶端可以不必逐次確認。
- **篩選條件真的有效**：關鍵字、地區、職類、薪資下限（月薪、年薪、日薪、時薪）、工作性質、遠端、7 天內刊登、年資、學歷，每一項都對真實網站驗證過。
- **中文名稱進、代碼出**：名稱有歧義時回傳候選清單，不亂猜。`lookup_code` 可以逐層瀏覽整棵地區與職類樹。
- **為夠聰明的模型設計**：使用者講白話，由模型負責轉換。參數的可選值直接寫進 schema，伺服器說明只講原則（各來源是什麼、關鍵字如何準備中英文兩份、單位如何換算），不列案例清單；伺服器只處理模型看不到的部分：有歧義的地名自動納入相近項目、對不到的職類改當關鍵字、分頁上限自動調整，搜尋沒有結果時逐一放寬選填條件，再改查其他來源。所有假設都列在結果下方的註記。
- **記得不清楚也找得到**：104 的相關度搜尋結果，會再依職稱與公司涵蓋你輸入的字詞多寡重新排序。40 次試搜中，目標職缺排第一的有 35 次，104 原本的排序只有 18 次。同時搜尋多個來源時，合併後的結果也用同樣方式排序。
- **串得起來**：每筆搜尋結果都帶 `id` 與 `company_id`，agent 可以從職缺一路接到詳細內容與公司，不必多查。
- **薪資行情**：`salary_overview` 對一批職缺統計薪資（中位數、四分位數、最低、最高），依薪資單位分組。
- **省 context**：回傳的是精簡文字，不是 JSON。一頁 20 筆職缺只是 20 行、約 2,000 字的表格（同樣資料用精簡 JSON 超過五倍），六個工具的定義加起來也只有約 2,000 字。長文預設截斷，要全文再用 `full`。設 `TW_JOBS_FORMAT=json` 可取得完整結構化資料。
- **結果乾淨**：預設濾掉 104 每頁固定置頂的 2 筆付費職缺。
- **對網站友善**：每秒最多 1 次請求，回應快取 5 分鐘。
- **多種執行方式**：本機用 stdio，遠端用 streamable HTTP，另有 Dockerfile 與 Claude Desktop 的 `.mcpb` 套件。

## 安裝

需要先安裝 [uv](https://docs.astral.sh/uv/)。以下指令直接從 GitHub 執行，不會永久安裝任何東西。

### Claude Code

```bash
claude mcp add tw-jobs -s user -- uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp
```

### OpenAI Codex CLI

```bash
codex mcp add tw-jobs -- uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp
```

或編輯 `~/.codex/config.toml`：

```toml
[mcp_servers.tw-jobs]
command = "uvx"
args = ["--from", "git+https://github.com/HsuanC0921/tw-jobs-mcp", "tw-jobs-mcp"]
startup_timeout_sec = 60   # 第一次執行要下載相依套件
```

### Claude Desktop

從 [Releases](https://github.com/HsuanC0921/tw-jobs-mcp/releases) 下載 `tw-jobs-mcp-<版本>.mcpb` 後開啟，或把下面的 JSON 加進 `claude_desktop_config.json`。

### Gemini CLI、Cursor、Windsurf、Cline 與其他使用 `mcpServers` 的客戶端

加進 `~/.gemini/settings.json`、`~/.cursor/mcp.json`（或專案內的 `.cursor/mcp.json`）、Windsurf 的 `mcp_config.json`，或該客戶端對應的設定檔：

```json
{
  "mcpServers": {
    "tw-jobs": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/HsuanC0921/tw-jobs-mcp", "tw-jobs-mcp"]
    }
  }
}
```

### VS Code（GitHub Copilot）

`.vscode/mcp.json` 的根欄位是 `servers`，而且要寫 `type`：

```json
{
  "servers": {
    "tw-jobs": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/HsuanC0921/tw-jobs-mcp", "tw-jobs-mcp"]
    }
  }
}
```

### 遠端（HTTP）與 Docker

給用網址連線的客戶端，或團隊共用一台 server：

```bash
uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp --transport streamable-http --port 8000
# 端點：http://127.0.0.1:8000/mcp
```

```bash
docker build -t tw-jobs-mcp .
docker run --rm -p 8000:8000 tw-jobs-mcp
```

```bash
claude mcp add --transport http tw-jobs http://127.0.0.1:8000/mcp
codex mcp add tw-jobs --url http://127.0.0.1:8000/mcp
```

HTTP 版沒有任何驗證。請只開在本機或內網，或在前面放一層有驗證的反向代理。

### 從本機資料夾執行

```bash
git clone https://github.com/HsuanC0921/tw-jobs-mcp
cd tw-jobs-mcp
claude mcp add tw-jobs -- uv run --project "$PWD" tw-jobs-mcp
```

## 工具

| 工具 | 用途 |
|---|---|
| `search_jobs` | 搜尋職缺。回傳表格：`id`、`company_id`、職稱、公司、薪資、地點、學歷、技能、刊登日 |
| `get_job` | 完整職缺：職務說明、條件、技能、薪資、工時、假別、出差、福利。說明超過 1,500 字會截斷，`full=true` 看全文 |
| `get_company` | 公司簡介；`with_openings=true` 附上目前的職缺；`full=true` 取消截斷 |
| `salary_overview` | 對一次搜尋的前 1 到 5 頁（每頁 30 筆）統計薪資，依薪資單位分組 |
| `sources` | 即時檢查 104、Yourator 與各職缺板目前哪些連得上、哪些被擋。 |
| `lookup_code` | 用名稱查地區或職類代碼，或用 `parent` 逐層瀏覽分類樹 |

`search_jobs` 的參數（全部選填）：

| 參數 | 說明 |
|---|---|
| `keyword`、`keyword_en` | 關鍵字，1 到 3 個短詞。`keyword` 放中文（給 104），`keyword_en` 放英文（給其他來源，外商網站的職缺標題是英文）。AI 會兩邊都填並互相翻譯，所以用中文也找得到外商職缺，用英文也找得到 104 職缺；使用者不必知道這兩個欄位 |
| `area`、`jobcat` | 中文名稱清單，例如 `["台北市", "新北市"]`、`["軟體工程師"]` |
| `salary_min`、`salary_unit` | 薪資下限與單位：`月薪`（預設）、`年薪`、`日薪`、`時薪`，由伺服器端篩選 |
| `education` | `高中職`、`專科`、`大學`、`碩士`、`博士`：學歷條件涵蓋該學歷（或不拘）的職缺 |
| `my_years` | 你的年資，只列出要求年資不超過它的職缺 |
| `job_type` | `全職`、`兼職`、`高階`、`派遣` |
| `remote_only` | 只看完全或部分遠端 |
| `new_only` | 只看 7 天內刊登的 |
| `sort` | `relevance`（預設）、`newest`、`salary` |
| `page`、`per_page` | 翻頁，每頁最多 30 筆 |

### 來源

`source` 決定搜哪裡。結果的 id 標示職缺出處，`get_job`、`get_company` 依此分流：沒有前綴是 104，`y:` 是 Yourator，`g:`、`l:` 是 Greenhouse、Lever 職缺板，`w:` 是 Workday。id 請原樣傳回。

| `source` | 範圍 | 有套用的條件 |
|---|---|---|
| `104`（預設） | 台灣最大人力銀行 | 全部 |
| `yourator` | 新創、外商據點 | `keyword`、`area`、`sort=newest` |
| `boards` | 外商 Greenhouse／Lever 職缺板上的台灣職缺 | `keyword`、`area`、`remote_only` |
| `workday` | 約 20 家大型外商在 Workday 上的台灣職缺 | `keyword`、`area` |
| `all` | 以上四者交錯合併 | 依各來源；某個來源失敗只會在註記中說明，不影響其他來源 |

來源不支援的條件會列在表格下方的 `註：…未套用`，不會默默忽略。`salary_overview` 與 `lookup_code` 只支援 104。

用 `TW_JOBS_BOARDS` 增減職缺板，例如 `g:gitlab,l:kraken,-g:stripe`（`g:` Greenhouse、`l:` Lever、開頭 `-` 代表移除）。沒有台灣職缺的板子只會回傳空結果。

`TW_JOBS_WORKDAY` 對 Workday 的用法相同：`acme.wd1/External,-micron`（`tenant.wdN/site`，開頭 `-` 代表移除）。每次 Workday 搜尋每家公司只讀前 60 筆，要查更深請用關鍵字縮小範圍。這些是各公司自家職缺頁面本來就在呼叫的無需登入端點，大量使用前請先確認各公司的使用條款。

刻意不收：**1111**（性質與 104 相同、規模較小）、**Cake**（每個請求都被 Cloudflare 驗證擋下）、**LinkedIn**（使用條款禁止自動化存取）。

## 使用範例

> 幫我找台北市的 .NET 後端職缺，月薪 50000 以上，並說明這類職缺的行情。

> 我有兩年年資，找新北市可以遠端的後端職缺，讀前三個，再比較這三家公司。

```text
search_jobs(keyword="後端工程師", area=["台北市"])
共 1716 筆，第 1/86 頁
id|company_id|職稱|公司|薪資|地點|學歷|技能|刊登
8mve7|1a2x6bmz67|後端工程師|途銳資訊股份有限公司|月45000~70000|台北市南港區|專科~碩士|PHP/MySQL/AWS/Linux/Git|10-02
…
```

## 設定

| 環境變數 | 預設值 | 說明 |
|---|---|---|
| `TW_JOBS_TRANSPORT` | `stdio` | `stdio` 或 `streamable-http`（等同 `--transport`） |
| `TW_JOBS_HOST`、`TW_JOBS_PORT` | `127.0.0.1`、`8000` | HTTP 傳輸的綁定位址 |
| `TW_JOBS_CACHE_TTL` | `300` | 回應快取秒數；`0` 代表關閉快取 |
| `TW_JOBS_BOARDS` | 內建清單 | 額外的職缺板，以逗號分隔（見「來源」） |
| `TW_JOBS_WORKDAY` | 內建清單 | 額外的 Workday 職缺網站，`tenant.wdN/site`（見「來源」） |
| `TW_JOBS_FORMAT` | `text` | `json` 會改回傳完整欄位的精簡 JSON，而不是文字表格 |

## 運作方式

104 前面有 Cloudflare，一般的 HTTP 請求會直接吃到 403。這裡用 [`curl_cffi`](https://github.com/lexiforest/curl_cffi) 送出真實 Chrome 的 TLS 指紋，才打得進去。地區與職類名稱則在本機對照 104 公開的代碼表（`src/tw_jobs_mcp/j104/data/`）。

## 刻意的限制

- **唯讀**：沒有登入、投遞、收藏。把求職網站的密碼交給 AI 不值得冒這個險。
- **沒有公司名稱搜尋**：104 在那個端點前面放了 Cloudflare 驗證。請從職缺的 `company_id` 進入公司。
- `salary_overview` 是最相關職缺的樣本，不是全站統計，而且很多職缺不公開薪資（見 `undisclosed_share`）。

## 開發

```bash
uv sync
uv run pytest                  # 離線：單元測試，加上 stdio 與 HTTP 通訊測試
uv run pytest -m live          # 連真實的 104
uv run python scripts/update_codes.py   # 更新地區與職類代碼表
```

## 授權

[MIT](LICENSE)。依現狀提供，不附任何保證。
