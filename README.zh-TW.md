# tw-jobs-mcp

[English](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/README.md) · **繁體中文**

[![test](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/HsuanC0921/tw-jobs-mcp/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/tw-jobs-mcp)](https://pypi.org/project/tw-jobs-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)

在任何 AI 助理裡直接找台灣的職缺。tw-jobs-mcp 是唯讀的 [MCP](https://modelcontextprotocol.io) server，涵蓋 **104 人力銀行**、**Yourator**，以及外商自家職缺網站上的台灣職缺（Greenhouse、Lever，和 Workday 上的 38 家公司）。用中文或英文講白話就好，助理會把需求轉成精確的篩選條件。

不需要帳號，也不需要 API key。

```bash
claude mcp add tw-jobs -s user -- uvx tw-jobs-mcp
```

> **非官方工具**，與 104 及其他被讀取的網站都沒有關係。它呼叫的是這些網站自己頁面在用的公開端點。請控制使用頻率並遵守各網站的條款。專案不附帶任何職缺資料。

## 可以這樣問

> 幫我找台北市的 .NET 後端職缺，月薪 50000 以上，並說明這類職缺的行情。

> 我有兩年年資，找新北市可以遠端的後端職缺，讀前三個，再比較這三家公司。

> 這個職缺值得投嗎？有多少人應徵、都是什麼背景？

> 新竹有哪些外商半導體在找硬體工程師？

> 這家公司有沒有資料相關的職缺？職稱沒寫的也算。

助理會在背後串接工具。以下輸出僅為示意，公司與 id 都是虛構的。

```text
search_jobs(keyword="後端工程師", keyword_en="backend engineer", area=["台北市"], salary_min=50000)
共 812 筆，第 1/41 頁
id|company_id|職稱|公司|薪資|地點|學歷|技能|刊登
a1b2c|x9y8z7|後端工程師 Backend Engineer|甲科技股份有限公司|月55000~80000|台北市信義區|大學~碩士|C#/.NET/MS SQL|10-18
d3e4f|w6v5u4|資深後端工程師|乙數位股份有限公司|月70000~100000|台北市內湖區|大學|Go/PostgreSQL/Docker|10-17
…

get_job("a1b2c", applicants=true)
後端工程師 Backend Engineer｜甲科技股份有限公司｜電腦軟體服務業 50人
…
HR:2 天內處理過履歷
應徵分析（近兩週）：至少 12 人（由比例推算）
學歷：大學 66.7%、碩士 33.3%
年資：1~3年 41.7%、3~5年 33.3%、無工作經驗 25%
技能：C# 58.3%、MS SQL 41.7%、Docker 25%
```

## 特色

- **找得到 104 上沒有的職缺**：外商常把台灣職缺只貼在自家職缺網站。`source="all"` 一次搜尋 104、Yourator、Greenhouse 與 Lever 職缺板（Appier、Stripe、MongoDB、Pinkoi 等），以及晶片、硬體、藥廠、金融外商的 Workday 網站（NVIDIA、Micron、Applied Materials、KLA、Cisco、Intel、NXP、GSK 等），各來源的結果合併後一起排序。
- **記不清楚也找得到**：結果會依職稱與公司涵蓋你輸入字詞的多寡重新排序。用真實職缺做的 40 次試搜中，目標職缺排第一有 35 次，104 原本的排序只有 18 次。
- **看得到競爭狀況**：104 職缺可用 `get_job(applicants=true)` 看近兩週有多少人應徵，以及這些人的學歷、年資、年齡、科系、語言、技能、證照分布。每個職缺也會顯示 HR 最近一次處理履歷是什麼時候，可以藉此判斷履歷有沒有人在看。
- **篩選條件真的有效**：關鍵字、地區、職類、薪資下限（月薪、年薪、日薪、時薪）、年資、學歷、工作性質、遠端、7 天內刊登，每一項都對真實網站驗證過。某個來源不支援的條件，會在結果下方註明。
- **為夠聰明的模型設計**：所有可選值都寫進 schema，伺服器說明只講原則，不列一長串案例。伺服器只處理模型看不到的部分：地名有歧義就納入相近項目，對不到的職類改當關鍵字，沒有結果時逐一放寬條件。這些假設都會列在結果下方。
- **省 context**：回傳精簡表格而不是 JSON，20 筆職缺約 2,000 字，不到同樣資料用 JSON 的五分之一。六個工具的定義加起來不到 3,000 字。長文預設截斷，要全文再用 `full`。
- **唯讀，對網站友善**：不登入、不投遞、不收藏。對每個網站控制請求間隔（104 每秒最多 1 次），回應快取 5 分鐘，並濾掉 104 每頁固定置頂的 2 筆付費職缺。

## 安裝

需要先安裝 [uv](https://docs.astral.sh/uv/)。以下指令執行的是 [PyPI](https://pypi.org/project/tw-jobs-mcp/) 上的正式版，也已登錄在 [MCP 官方 Registry](https://registry.modelcontextprotocol.io)，名稱為 `io.github.HsuanC0921/tw-jobs-mcp`。

**Claude Code**

```bash
claude mcp add tw-jobs -s user -- uvx tw-jobs-mcp
```

**OpenAI Codex CLI**

```bash
codex mcp add tw-jobs -- uvx tw-jobs-mcp
```

或寫進 `~/.codex/config.toml`：

```toml
[mcp_servers.tw-jobs]
command = "uvx"
args = ["tw-jobs-mcp"]
startup_timeout_sec = 60   # 第一次執行要下載相依套件
```

**Claude Desktop**：從 [Releases](https://github.com/HsuanC0921/tw-jobs-mcp/releases) 下載 `tw-jobs-mcp-<版本>.mcpb` 後開啟，或使用下面的 JSON。

**Gemini CLI、Cursor、Windsurf、Cline 與其他使用 `mcpServers` 的客戶端**：加進 `~/.gemini/settings.json`、`~/.cursor/mcp.json`、Windsurf 的 `mcp_config.json`，或該客戶端對應的設定檔：

```json
{
  "mcpServers": {
    "tw-jobs": { "command": "uvx", "args": ["tw-jobs-mcp"] }
  }
}
```

**VS Code（GitHub Copilot）**：`.vscode/mcp.json` 的根欄位是 `servers`，而且要寫 `type`：

```json
{
  "servers": {
    "tw-jobs": { "type": "stdio", "command": "uvx", "args": ["tw-jobs-mcp"] }
  }
}
```

**遠端（HTTP）與 Docker**，給用網址連線的客戶端，或團隊共用一台 server：

```bash
uvx tw-jobs-mcp --transport streamable-http --port 8000   # http://127.0.0.1:8000/mcp
docker build -t tw-jobs-mcp . && docker run --rm -p 8000:8000 tw-jobs-mcp
```

HTTP 版沒有任何驗證。請只開在本機或內網，或在前面放一層有驗證的反向代理。

**尚未發布的程式碼**：`uvx --from git+https://github.com/HsuanC0921/tw-jobs-mcp tw-jobs-mcp`。

### Agent skill

伺服器本身已經會告訴模型怎麼用。[`skills/tw-jobs`](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/skills/tw-jobs/SKILL.md) 給會載入 skill 的 agent 更多指引：怎麼把需求轉成參數、怎麼挑來源、怎麼解讀註記、怎麼如實回報。格式遵循開放的 Agent Skills 規格。

- **Claude Code**：`/plugin marketplace add HsuanC0921/tw-jobs-mcp`，再 `/plugin install tw-jobs@tw-jobs-mcp`（同時帶入伺服器與 skill）。或把 `skills/tw-jobs` 複製到 `~/.claude/skills/`。
- **Codex 與其他支援 skill 的 agent**：把 `skills/tw-jobs` 複製到 `~/.agents/skills/`。

## 工具

| 工具 | 用途 |
|---|---|
| `search_jobs` | 搜尋職缺。回傳表格：`id`、`company_id`、職稱、公司、薪資、地點、學歷、技能、刊登日。 |
| `get_job` | 完整職缺：職務說明、條件、薪資、工時、假別、福利，以及 HR 最近處理履歷的時間。104 限定：`applicants=true` 附應徵人數與背景分布，`similar=true` 附相似職缺。 |
| `get_company` | 公司簡介。`with_openings=true` 附目前職缺；`keyword` 只列符合的職缺，104 會連職缺內文一起比對。 |
| `salary_overview` | 對 104 搜尋結果的前 1 到 5 頁統計薪資（中位數、四分位數、最低、最高），依薪資單位分組。 |
| `sources` | 即時檢查哪些來源連得上、哪些被擋。 |
| `lookup_code` | 用名稱查 104 地區或職類代碼，或逐層瀏覽分類樹。 |

`search_jobs` 的參數，全部選填：

| 參數 | 說明 |
|---|---|
| `keyword`、`keyword_en` | 1 到 3 個短詞。`keyword` 放中文給 104，`keyword_en` 放英文給外商網站，兩者互為翻譯。助理會兩邊都填，所以用中文也找得到外商職缺。 |
| `source` | `104`（預設）、`yourator`、`boards`、`workday`、`all` |
| `area`、`jobcat` | 中文名稱，例如 `["台北市", "新北市"]`、`["軟體工程師"]` |
| `salary_min`、`salary_unit` | 薪資下限與單位：`月薪`（預設）、`年薪`、`日薪`、`時薪` |
| `include_negotiable` | 搭配 `salary_min`，連沒寫薪資的面議職缺一起列（104 預設不含） |
| `my_years` | 使用者的年資，只列要求不超過它的職缺（含經驗不拘） |
| `education` | `高中職`、`專科`、`大學`、`碩士`、`博士` |
| `job_type` | `全職`、`兼職`、`高階`、`派遣` |
| `remote_only`、`new_only` | 只看遠端；只看 7 天內刊登 |
| `sort` | `relevance`（預設）、`newest`、`salary` |
| `page`、`per_page` | 翻頁，每頁最多 30 筆 |

## 來源

| `source` | 範圍 | 有套用的條件 |
|---|---|---|
| `104` | 台灣最大的人力銀行 | 全部 |
| `yourator` | 新創與外商據點 | `keyword`、`area`、`sort=newest` |
| `boards` | 外商 Greenhouse、Lever 職缺板上的台灣職缺 | `keyword`、`area`、`remote_only` |
| `workday` | 38 家外商在 Workday 上的台灣職缺 | `keyword`、`area` |
| `all` | 以上全部，合併後一起排序 | 依各來源；某個來源失敗只會註明，不影響其他來源 |

id 標示職缺出處：沒有前綴是 104，`y:` 是 Yourator，`g:`／`l:` 是 Greenhouse／Lever，`w:` 是 Workday。請原樣傳回。

用 `TW_JOBS_BOARDS`（`g:gitlab,l:kraken,-g:stripe`）與 `TW_JOBS_WORKDAY`（`acme.wd1/External,-micron`）增減職缺網站，開頭 `-` 代表移除。每次 Workday 搜尋每家公司只讀前 60 筆，要查更深請用關鍵字縮小範圍。

刻意不收：**1111**（性質與 104 相同、規模較小）、**Cake**（每個請求都被 Cloudflare 驗證擋下）、**LinkedIn**（使用條款禁止自動化存取）。

## 設定

| 環境變數 | 預設值 | 說明 |
|---|---|---|
| `TW_JOBS_TRANSPORT` | `stdio` | `stdio` 或 `streamable-http`（等同 `--transport`） |
| `TW_JOBS_HOST`、`TW_JOBS_PORT` | `127.0.0.1`、`8000` | HTTP 的綁定位址 |
| `TW_JOBS_CACHE_TTL` | `300` | 回應快取秒數；`0` 代表關閉快取 |
| `TW_JOBS_BOARDS`、`TW_JOBS_WORKDAY` | 內建清單 | 要增減的職缺網站（見「來源」） |
| `TW_JOBS_FORMAT` | `text` | `json` 改回傳完整欄位的精簡 JSON |

## 運作方式與限制

104 前面有 Cloudflare，一般的 HTTP 請求會直接吃到 403。這裡用 [`curl_cffi`](https://github.com/lexiforest/curl_cffi) 送出真實 Chrome 的 TLS 指紋，才打得進去。地區與職類名稱在本機對照 104 公開的代碼表。

- **唯讀**：不登入、不投遞、不收藏。把求職網站的密碼交給 AI 不值得冒這個險。
- **沒有公司名稱搜尋**：104 擋掉了程式對這個端點的存取。請從職缺的 `company_id` 進入公司，或把公司名稱放進 `keyword`。
- **應徵人數是推算的**：104 只公開百分比，所以人數是符合這些比例的最小值，代表「至少」而不是確切人數。
- `salary_overview` 取的是最相關職缺的樣本，不是全站統計，而且很多職缺不公開薪資。

## 開發

```bash
uv sync
uv run pytest                  # 離線的單元與通訊測試
uv run pytest -m live          # 連真實網站
uv run python scripts/update_codes.py   # 更新 104 的地區與職類代碼表
```

## 授權

[MIT](https://github.com/HsuanC0921/tw-jobs-mcp/blob/main/LICENSE)。依現狀提供，不附任何保證。
