# Goal Is to Win the Hackathon
## NVIDIA Claw Agent Challenge: Berlin 🇩🇪
​Build a long-running claw agent. Win real prizes. Do it from anywhere in Germany.

​Ahead of NVIDIA Build-a-Claw in Berlin, we’re inviting developers across Germany to start building.
​The Berlin Claw Agent Challenge is fully remote and open to anyone living in Germany—there’s no in-person hackathon, fixed schedule, or team requirement. Pick an idea, build a long-running agent around it, and submit your project before the challenge closes.

## 🏆 What You Can Win
### 1st Place
​🎫 GTC Berlin Golden Ticket

​⚡ NVIDIA DGX Spark Founders Edition ($4,000 value)

​🎤 Opportunity to showcase your agent at NVIDIA Build-a-Claw in Berlin

### 2nd Place
​🎫 GTC Berlin Golden Ticket

​🎤 Opportunity to showcase your agent at NVIDIA Build-a-Claw in Berlin

## 🦞 Ready to Build?
​Register here on Luma to join the challenge.

​After registering, you’ll get access to the full challenge details, submission requirements, inspiration, and resources to help you start building your Claw Agent—including NVIDIA Build model endpoints and getting-started guides.

# Initial Plan

## 1. Verdict: Do Not Pivot

Do not pivot; sharpen the idea. There are about three days left. The official deadline is October 2, but the hour is unknown, so target submission by 12:00 CEST on October 2.

"Research summarizer" is already on the organizers' inspiration list, so many entries may be similar. ThesisClaw is different because:

- It knows the user's thesis.
- Its memory grows across several projects.
- It gives a concrete next step and can open a pull request.
- It includes an edge device, fitting an edge-AI thesis.

One-liner: "ThesisClaw reads the new literature every night and tells a thesis student which papers support, extend, or threaten their thesis, with the next experiment and a citable paragraph."

### Loop Findings
I checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates.
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML. arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?
### Loop Findings
I checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates.
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML. arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?
## 4. Proving It Is Long-Running

- Start the clock immediately so real history accumulates.
- Run a large backfill job that saves checkpoints.
- Terminate the instance through the API, relaunch it, and show it resuming on camera.
- Show autonomous messages, such as a morning briefing or a "you might be scooped" alert.
- Show `agent.md` versions and a project folder created by the agent.
- Show the context funnel: tokens read versus the size of the final briefing.
- Show a LangSmith trace tree for one analysis.
- Show a timeline of host sessions on the public page.

## 5. Financial
### Loop Findings
I checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates.
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML. arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?
## 6. Risk

The top five of 21 failure modes are scored by severity x occurrence x detection:

- Hallucination: RPN 336.
- Context overflow: RPN 210.
- Prompt injection: RPN 189.
- Budget: RPN 180.
- Relaunch failure: RPN 144.

## 7. Things Missing

- Confirm the submission form's exact fields and deadline hour.
- Host the public page on GitHub Pages so it works while Lambda is terminated.
- Add a Telegram allowlist, login protection for the notes page, and a GitHub token limited to one repository. Otherwise, a stranger or malicious paper could steer pull requests.
- Do not republish full papers. Show analysis, short quotes, and links.
- xiaozhi.me is a third-party cloud; keep unpublished thesis text out of voice tools.
- Prepare a booth kit for October 17: phone hotspot, power bank, and offline mode.

## 8. Plan: ThesisClaw Playbook + Judge Site

Build a static site with no external libraries in two parts:

- A private playbook covering strategy, the four-skill loop, the 72-hour plan, calculators, and the risk table.
- A public judge page deployable to GitHub Pages, showing long-running statistics.

Also seed the agent's memory files. Building the working agent is the next implementation plan.

## 9. Steps

1. Validate the idea with three short labmate conversations and label 30 papers.
2. Report precision@10 against the agent; one real number is stronger than adjectives.
3. Build the memory and paper-page workflow.
4. Connect Telegram, the Deep Agents worker, MCP, and the ESP32 companion.
5. Add approval gates before code changes or pull requests.
6. Run the backfill, checkpoint it, terminate and relaunch the host, then capture the evidence.
7. Deploy the public judge page and submit before the internal deadline.

Verdict: don't pivot, sharpen the idea. You're starting from nothing and there are about 3 days left. The official deadline is Oct 2 but the hour isn't stated, so aim to submit by 12:00 CEST that day.
"Research summarizer" is the first idea on the organizers' inspiration list, so expect many entries like it. What sets yours apart:
• It knows your thesis.
• Its memory grows across several projects.
• It gives you a concrete next step and can open a pull request.
• It has an edge device, which fits an edge-Al thesis.
### Four-Skill Loop Findings
1 checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?"
• Label 30 papers yourself and report precision@10 against the agent. Judges trust one real number over adjectives.
• One-liner: "ThesisClaw reads the new literature

Verdict: don't pivot, sharpen the idea. You're starting from nothing and there are about 3 days left. The official deadline is Oct 2 but the hour isn't stated, so aim to submit by 12:00 CEST that day.
"Research summarizer" is the first idea on the organizers' inspiration list, so expect many entries like it. What sets yours apart:
• It knows your thesis.
• Its memory grows across several projects.
• It gives you a concrete next step and can open a pull request.
• It has an edge device, which fits an edge-Al thesis.
### Four-Skill Loop Findings
1 checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?"
• Label 30 papers yourself and report precision@10 against the agent. Judges trust one real number over adjectives.
• One-liner: "ThesisClaw reads the new literature
Verdict: don't pivot, sharpen the idea. You're starting from nothing and there are about 3 days left. The official deadline is Oct 2 but the hour isn't stated, so aim to submit by 12:00 CEST that day.
"Research summarizer" is the first idea on the organizers' inspiration list, so expect many entries like it. What sets yours apart:
• It knows your thesis.
• Its memory grows across several projects.
• It gives you a concrete next step and can open a pull request.
• It has an edge device, which fits an edge-Al thesis.
### Four-Skill Loop Findings
1 checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?"
• Label 30 papers yourself and report precision@10 against the agent. Judges trust one real number over adjectives.
• One-liner: "ThesisClaw reads the new literature
Verdict: don't pivot, sharpen the idea. You're starting from nothing and there are about 3 days left. The official deadline is Oct 2 but the hour isn't stated, so aim to submit by 12:00 CEST that day.
"Research summarizer" is the first idea on the organizers' inspiration list, so expect many entries like it. What sets yours apart:
• It knows your thesis.
• Its memory grows across several projects.
• It gives you a concrete next step and can open a pull request.
• It has an edge device, which fits an edge-Al thesis.
### Four-Skill Loop Findings
1 checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?"
• Label 30 papers yourself and report precision@10 against the agent. Judges trust one real number over adjectives.
• One-liner: "ThesisClaw reads the new literature

## Verdict: Don't Pivot
Don't pivot, sharpen the idea. You're starting from nothing and there are about 3 days left. The official deadline is Oct 2 but the hour isn't stated, so aim to submit by 12:00 CEST that day.
"Research summarizer" is the first idea on the organizers' inspiration list, so expect many entries like it. What sets yours apart:
• It knows your thesis.
• Its memory grows across several projects.
• It gives you a concrete next step and can open a pull request.
• It has an edge device, which fits an edge-Al thesis.
### Four-Skill Loop Findings
1 checked the tool facts below against the current NemoClaw, Lambda, Deep Agents and xiaozhi docs. The alternative scores and risk scores are my own estimates
#### 1. Hackathon (Mom Test) and Real-World Value
• Weakest part converting a paper to HTML arXiv already serves HTML for most new papers. Keep the pages, but pitch them as your personal, versioned pages that you can annotate.
• Riskiest assumption: that you'd use a voice box on your desk every day. Treat Telegram as the main channel and the ESP32 as a companion that looks great in the demo.
• Validate before Oct 2:
• Have three short chats with labmates about what they actually did. Example: "When did you last find a key paper too late?"
• Label 30 papers yourself and report precision@10 against the agent. Judges trust one real number over adjectives.
• One-liner: "ThesisClaw reads the new literature
## 19. State Serialization Block

```yaml
state_version: 1
updated: 2026-09-29
project: ThesisClaw
working_name: ThesisClaw
deadline:
	official: "2026-10-02 (hour unknown)"
	internal: "2026-10-02T12:00:00+02:00"
status: planning; nothing built
decisions:
	idea: keep and sharpen
	roadmap: paper-to-experiment on ESP32
	folded_in: voice notes and budget guard
stack:
	orchestration: NemoClaw + OpenClaw (Telegram and automations)
	worker: Python Deep Agents outside the sandbox
	tool_spine: MCP Streamable HTTP through a named HTTPS tunnel
	models:
		default: nvidia/nemotron-3-super-120b-a12b
		critic: nvidia/nemotron-3-ultra-550b-a55b
	voice: stock xiaozhi firmware -> xiaozhi.me MCP endpoint -> mcp_pipe
hosting:
	provider: Lambda
	gpu: 1x A10
	region: europe-central-1
	lifecycle: API launch and terminate
memory:
	shared: research/agent.md
	projects: projects/<slug>/(agent.md,timeline.md)
	pages: versioned per paper
workflow: notes -> re-process -> approve -> draft PR
site:
	public: site/public
	private: site/playbook
budget_usd:
	cap: 75
	pre_deadline: 41
	judging: 10
	booth: 13
	storage: 3
	buffer: 8
top_risks_rpn:
	hallucination: 336
	context_overflow: 210
	prompt_injection: 189
	budget: 180
	relaunch: 144
open_questions:
	- deadline hour
	- exact board model
	- thesis repository URL
	- tunnel domain
```