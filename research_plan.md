## Goal Description
The goal is to conduct a thorough online deep research for the "ThesisClaw" project targeting the NVIDIA Claw Agent Challenge in Berlin. The project aims to build a long-running claw agent that reads new literature, evaluates it against a student's thesis, suggests next steps, and integrates with an ESP32 voice companion and Telegram. The research will clarify technical unknowns, define the exact submission requirements, and validate the proposed architecture (NemoClaw, MCP, Xiaozhi firmware) to ensure it is viable within the remaining ~72-hour timeframe.

## User Review Required
> [!IMPORTANT]
> Please review the research scope below to ensure it aligns with your vision for ThesisClaw.
> the esp32 s3 have the repo in the this directory use this file to understand the code inside the esp32s3 /Users/shyjojose/esp32
> - **Hardware**: Do you already have a specific ESP34 board model in mind or purchased? If so, please provide the exact model so the research can target its specific capabilities.
> - **Accounts**: Do you have existing accounts/API keys for Lambda (GPU hosting), Telegram (for bots), and Xiaozhi.me, or should the research include quick-start setup guides for these?

## Open Questions
> [!WARNING]
> These questions were identified in `goal.md` and need resolution:
> - What is the exact URL of the thesis repository that ThesisClaw will monitor and open PRs against?
> - What is the preferred named HTTPS tunnel provider (e.g., ngrok, Cloudflare Tunnels, pinggy) for the MCP Streamable HTTP?

## Proposed Research Steps

I propose breaking down the research into the following targeted phases to address all constraints and requirements from `goal.md`.

### Phase 1: Challenge Logistics & Rules ignore this 
I will search the web to clarify the exact rules and deadlines for the NVIDIA Claw Agent Challenge: Berlin.
*   **Action**: Find the official Luma page or announcement. no need the page details are already in the goal.md 
*   **Target Output**: The precise deadline hour on October 2, 2026, and the exact fields required for the submission form. i have the submission form

### Phase 2: Tech Stack & Architecture Deep-Dive
I will research the documentation and integration points for the chosen stack.
*   **NemoClaw & OpenClaw**: Look up the latest best practices for setting up OpenClaw with Telegram integration.
*   **Deep Agents Framework**: Research Python integration for the worker nodes.
*   **Model Context Protocol (MCP)**: Research how to securely route `xiaozhi.me` voice commands to the agent using a named HTTPS tunnel and `mcp_pipe`.
*   **Xiaozhi Firmware**: Verify how stock Xiaozhi firmware interacts with MCP endpoints and the required setup.
*   **Lambda GPU Hosting**: Find the exact Lambda API endpoints or CLI commands needed to programmatically launch, snapshot/checkpoint, and terminate instances (crucial for proving the agent is "long-running" across terminations).

### Phase 3: Literature Ingestion Workflow
I will research the most reliable ways to ingest daily literature.
*   **Action**: Investigate arXiv's API, RSS feeds, and HTML-serving capabilities to ensure we can efficiently retrieve and parse new papers without heavy PDF-to-text processing.

## Verification Plan

### Manual Verification
Once the research is complete, I will compile a comprehensive Research Report artifact. You will manually verify that:
1.  All open questions from `goal.md` (deadline hour, tunnel domain, etc.) have definitive answers.
2.  The architecture is confirmed feasible and no "show-stopper" technical blockers were found.
3.  We have the necessary API references and documentation links to begin implementation (building the working agent).
