# ThesisClaw Research Report

This document contains the findings from the deep online research conducted for the ThesisClaw project, targeting the NVIDIA Claw Agent Challenge: Berlin.

## Phase 1: Challenge Logistics & Rules
*   **Deadline:** The official deadline is October 2, 2026. As the hour is unspecified, the internal target of **12:00 CEST** remains the safest approach.
*   **Nature:** The challenge is fully remote (no in-person requirement) and focuses on building **long-running autonomous agents** using the OpenClaw framework. 
*   **Registration & Submission:** Hosted on Luma. Submissions will typically require a project description, video demo, and links to the code or public logs. Your idea of a public "judge site" (GitHub Pages) showing long-running statistics perfectly aligns with this.

## Phase 2: Tech Stack & Architecture

### 1. NemoClaw & Telegram Integration
NemoClaw has a built-in, secure Telegram bridge that solves the "login protection" and "allowlist" requirements natively:
*   **Command:** `nemoclaw channels add telegram`
*   **Configuration:** You must set the `TELEGRAM_BOT_TOKEN` and crucially, `TELEGRAM_ALLOWED_IDS` (your Telegram user ID) to ensure strangers cannot steer the agent.
*   **Policies:** Use `TELEGRAM_GROUP_POLICY="allowlist"` and `TELEGRAM_REQUIRE_MENTION=1` so the agent only acts when explicitly requested.

### 2. Deep Agents Python Framework
"Deep Agents" is an open-source harness by the LangChain team designed specifically for long-running workflows.
*   **Why it fits:** It handles state persistence (via LangGraph), context compression, and sub-agent delegation out-of-the-box.
*   **Usage:** Install via `pip install deepagents`. It natively supports filesystem operations (useful for your `projects/<slug>/agent.md` memory files) and human-in-the-loop approvals (for the "draft PR -> approve" workflow).

### 3. MCP Streamable HTTP & Tunnels
The Model Context Protocol (MCP) has moved away from the dual-endpoint SSE model to **Streamable HTTP** (a single bidirectional endpoint).
*   **Tunneling:** To securely expose your local/Lambda MCP server to the internet (or Xiaozhi backend), use **Cloudflare Tunnels** (`cloudflared tunnel --url http://localhost:<port>`) or **ngrok** (`ngrok http <port>`). Cloudflare is recommended for stability without session timeouts.

### 4. Xiaozhi Firmware & `mcp_pipe`
The XiaoZhi ESP32 ecosystem uses a specific Python client script called `mcp_pipe.py` to connect the voice hardware to standard MCP servers.
*   **Flow:** ESP32 Voice -> XiaoZhi Cloud -> `mcp_pipe.py` (running locally/Lambda) -> ThesisClaw MCP Server.
*   **Requirement:** Your MCP server must properly handle the `initialize` handshake and return a `notifications/initialized` message, otherwise the voice device will drop the connection.

### 5. Lambda GPU Hosting API
Lambda Cloud provides a straightforward REST API for programmatic control, allowing you to prove the "long-running" resumption capability.
*   **Authentication:** Generate an API key from the Lambda dashboard.
*   **Launch:** `POST https://cloud.lambdalabs.com/api/v1/instance-operations/launch` with `region_name`, `instance_type_name` (e.g., `gpu_1x_a10`), and `ssh_key_names`.
*   **Terminate:** `POST https://cloud.lambdalabs.com/api/v1/instance-operations/terminate` with the instance ID.
*   *Note: Do not use `sudo shutdown` in the terminal, as it will leave the instance in an alert state and continue billing.*

## Phase 3: Literature Ingestion (arXiv)
Instead of converting PDFs to text (which is slow and error-prone), you can use native or community text endpoints:
1.  **arxiv-txt.org:** A community service that provides clean, LLM-friendly text. Simply replace `arxiv.org` in the URL with `arxiv-txt.org` (e.g., `https://arxiv-txt.org/abs/1706.03762`).
2.  **Experimental HTML:** arXiv now natively serves experimental HTML for most new papers at `arxiv.org/html/<id>`.
3.  **Library:** The `arxiv2text` Python library can automate this fetching process.

## Conclusion & Next Steps
The proposed architecture is technically sound and highly feasible within the 72-hour window. 
- The native NemoClaw Telegram bridge eliminates custom auth code.
- `arxiv-txt` eliminates complex PDF parsing.
- Lambda's simple REST API makes the backfill/relaunch demo straightforward.

**add this file for reading donot start building pending skill making is there **
