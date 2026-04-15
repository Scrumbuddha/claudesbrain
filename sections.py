SECTIONS = [
    {
        "slug": "claude-md",
        "title": "CLAUDE.md",
        "icon": "🧬",
        "color": "#C9A227",
        "chapter": 1,
        "tagline": "The constitution every other layer obeys.",
        "description": "Identity, rules, persistent memory, architecture decisions and team conventions — CLAUDE.md is the first file Claude reads and the last one it forgets.",
        "layers": [
            {
                "title": "Project Identity",
                "description": "CLAUDE.md defines who Claude is inside your project. It sets the persona, communication style, and scope boundaries — turning a general assistant into a project-aware collaborator that knows your stack, your team, and your goals.",
                "pro_tip": "Open with a one-paragraph 'About This Project' section. Claude uses it to orient every response — the clearer your context, the less you repeat yourself."
            },
            {
                "title": "Persistent Rules",
                "description": "Any instruction you find yourself typing more than twice belongs in CLAUDE.md. From coding style guides to commit message formats, these rules persist across every session without pasting them into chat.",
                "pro_tip": "Use imperative mood: 'Always use TypeScript strict mode' not 'We prefer TypeScript'. Claude follows directives more reliably than preferences."
            },
            {
                "title": "Location Hierarchy",
                "description": "Claude reads three CLAUDE.md files in order: global (~/.claude/CLAUDE.md), project root, and sub-directory. More specific files override more general ones — you can set global defaults and project-level exceptions.",
                "pro_tip": "Put team-wide standards (lint rules, PR conventions) in the project root CLAUDE.md. Put component-specific rules in sub-directory files."
            },
            {
                "title": "Architecture Decisions",
                "description": "Embed your Architecture Decision Records (ADRs) or link to them in CLAUDE.md. Claude will reason from your actual decisions rather than proposing patterns that contradict your established architecture.",
                "pro_tip": "Add a 'Tech Stack' section listing exact versions: 'React 18, Vite 5, TanStack Query v5'. Claude avoids suggesting deprecated APIs when it knows your versions."
            },
            {
                "title": "Team Conventions",
                "description": "Document naming conventions, folder structures, testing patterns, and git workflows. When every team member and every Claude session starts from the same conventions file, consistency compounds.",
                "pro_tip": "Include examples, not just rules. 'Feature folders: src/features/auth/components/, src/features/auth/hooks/' beats 'Use feature-based folder structure'."
            },
            {
                "title": "Memory & Persistence",
                "description": "Unlike chat history, CLAUDE.md survives session resets. It is the mechanism for true project memory — everything that should survive a new terminal window, a new day, or a new team member onboarding.",
                "pro_tip": "Ask Claude to update CLAUDE.md as a final step after significant decisions: 'Update CLAUDE.md to reflect the auth approach we just decided on'."
            },
            {
                "title": "Connections to Other Layers",
                "description": "CLAUDE.md tells Claude which MCP servers are active, where the Knowledge Base lives, which Slash Commands are in scope, and which Skills are available. It is the index for every other layer.",
                "pro_tip": "Add a 'Layer Map' section: a bullet list of which other layers are configured and where their files live. Claude uses it to self-navigate your setup."
            }
        ]
    },
    {
        "slug": "settings",
        "title": "Settings & Config",
        "icon": "⚙️",
        "color": "#2980B9",
        "chapter": 2,
        "tagline": "The three-tier hierarchy that governs what Claude can do.",
        "description": "From global defaults to project-level permissions, settings control tool access, model selection, auto-approve rules, and hook execution — the operating system beneath every session.",
        "layers": [
            {
                "title": "Three-Tier Hierarchy",
                "description": "Settings cascade from Enterprise (locked) → User (~/.claude/settings.json) → Project (.claude/settings.json). Project settings override user settings, which override enterprise defaults. Each tier can restrict but not expand permissions above it.",
                "pro_tip": "Put shared project settings in .claude/settings.json and commit it to git. Every team member inherits the same baseline without manual setup."
            },
            {
                "title": "Model Selection",
                "description": "You can specify which Claude model to use per-project. Pin a faster model for quick iterations and switch to a more powerful one for complex architectural work — without changing your workflow.",
                "pro_tip": "Set 'model': 'claude-sonnet-4-6' in project settings for the best balance of speed and capability. Use Opus for planning agents that need deep reasoning."
            },
            {
                "title": "Tool Allowlists",
                "description": "The allowedTools array controls exactly which tools Claude can use without asking. Explicitly listing tools is safer than wildcard approval — it prevents accidental file system or network access outside your intended scope.",
                "pro_tip": "Start restrictive, then expand. Begin with Read and Glob only, then add Edit and Bash once you trust the context. Add Write last, with specific path restrictions."
            },
            {
                "title": "Auto-Approve Rules",
                "description": "Permission rules with patterns let you auto-approve specific commands (e.g., 'npm test', 'git status') while requiring confirmation for destructive ones. Fine-grained rules eliminate interruptions without sacrificing safety.",
                "pro_tip": "Use prefix patterns: allow 'git ' (with trailing space) to approve all git read commands, but keep 'git push' and 'git reset' requiring confirmation."
            },
            {
                "title": "Hooks Configuration",
                "description": "Hooks are shell commands that fire on specific Claude events — before a tool runs, after it completes, when a session starts. They are the bridge between Claude's actions and your external systems.",
                "pro_tip": "Use a PreToolUse hook on Bash to log all commands to a file. You get a full audit trail of everything Claude executed in your project."
            },
            {
                "title": "Environment Variables",
                "description": "API keys, feature flags, and environment-specific config can be injected via settings without hardcoding them. Claude can read env vars but cannot expose them in output — a safe channel for secrets. New feature flags like CLAUDE_CODE_ENABLE_AWAY_SUMMARY (for /recap auto-trigger) are also set here.",
                "pro_tip": "Never put secrets in CLAUDE.md. Use env vars in settings.json combined with a .gitignore rule — settings.json with secrets should never be committed."
            },
            {
                "title": "Connections to Other Layers",
                "description": "Settings is where MCP server connections are registered, where hook scripts reference Skill files, and where tool permissions govern what Sub-Agents can execute. It is the control plane for the whole system.",
                "pro_tip": "Review .claude/settings.json after adding any new layer (MCP server, agent, skill). Each addition should have its permissions explicitly scoped here."
            }
        ]
    },
    {
        "slug": "mcp-servers",
        "title": "MCP Servers",
        "icon": "🔌",
        "color": "#8E44AD",
        "chapter": 3,
        "tagline": "The open standard that connects Claude to everything.",
        "description": "Model Context Protocol turns Claude from a text assistant into an agent with live access to your tools — Gmail, Jira, GitHub, databases, Slack, and any custom API you expose as an MCP server.",
        "layers": [
            {
                "title": "What MCP Is",
                "description": "MCP is an open protocol that defines how AI models discover and call external tools. An MCP server exposes a set of typed functions; Claude calls them like any other tool. The server handles authentication, rate limiting, and API translation.",
                "pro_tip": "Think of MCP servers as adapters. One server for each system (Jira, GitHub, database) keeps concerns separated and makes individual servers testable and replaceable."
            },
            {
                "title": "GitHub Integration",
                "description": "The GitHub MCP server gives Claude read/write access to repositories, issues, PRs, and actions. Claude can create branches, open pull requests, comment on reviews, and query CI status — all from a single prompt.",
                "pro_tip": "Scope the GitHub token to only the repos your project needs. A fine-grained PAT with repo-specific access is safer than an org-wide token."
            },
            {
                "title": "Jira & Project Tools",
                "description": "Connect Claude to Jira to read sprint backlogs, create issues from requirements, update story status, and generate sprint reports. The same pattern works for Linear, Asana, Trello, and any tool with an API.",
                "pro_tip": "Create a read-only Jira API token for exploration tasks and a read-write token for update tasks. Pass the appropriate token via env var based on the task type."
            },
            {
                "title": "Gmail & Communication",
                "description": "The Gmail MCP server lets Claude draft, read, and send emails — useful for generating stakeholder reports, following up on action items, or triaging inboxes based on project context.",
                "pro_tip": "Use a dedicated project Gmail account for Claude access rather than your personal inbox. Easier to audit, easier to revoke."
            },
            {
                "title": "Database Connections",
                "description": "MCP servers can wrap database connections — PostgreSQL, SQLite, MongoDB. Claude can run read queries, inspect schemas, and generate reports without direct credential exposure. The server enforces which queries are allowed.",
                "pro_tip": "Expose only SELECT-equivalent operations through the MCP server for any production database. Writes should go through your application layer, not directly via MCP."
            },
            {
                "title": "Custom API Servers",
                "description": "Any internal tool, microservice, or API can be wrapped as an MCP server. Write a thin adapter in Node.js or Python that translates your API into the MCP tool schema — Claude handles the rest.",
                "pro_tip": "Start with your most-used internal tool. One well-configured internal MCP server saves more time than five external integrations you rarely need."
            },
            {
                "title": "Connections to Other Layers",
                "description": "MCP servers are registered in Settings and available to Sub-Agents. A Jira MCP server used by a PO Agent, combined with a GitHub MCP server used by a Dev Agent, creates a cross-system workflow that would otherwise require manual copy-paste.",
                "pro_tip": "Document which MCP servers each Sub-Agent uses in CLAUDE.md. When an agent has the wrong server, it's immediately obvious from the map."
            }
        ]
    },
    {
        "slug": "sub-agents",
        "title": "Sub-Agents",
        "icon": "🤖",
        "color": "#27AE60",
        "chapter": 4,
        "tagline": "Isolated context windows that multiply what Claude can hold.",
        "description": "Sub-agents are specialized Claude instances launched mid-task. Each gets its own clean context window, its own tools, and its own mandate — enabling parallel execution and deep specialization without context bleed.",
        "layers": [
            {
                "title": "Why Isolated Context",
                "description": "Every sub-agent starts with a fresh context window, keeping the parent session clean. Even with Opus 4.6's 1M token context window, isolated agents deliver two things a single session cannot: true parallelism and clean domain separation. Multiple agents can research, write, and review simultaneously — each expert in its slice.",
                "pro_tip": "The primary value of sub-agents is now parallel execution and specialization, not just overflow handling. Run your Dev Agent and QA Agent simultaneously — their combined wall-clock time beats running them sequentially every time."
            },
            {
                "title": "Product Owner Agent",
                "description": "The PO Agent specializes in requirements, user stories, and backlog management. It reads Jira via MCP, interprets stakeholder input, and produces acceptance criteria — grounded in your team's definition of done.",
                "pro_tip": "Give the PO Agent a CLAUDE.md section with your user story template and DoD checklist. It will produce output that matches your format without prompting."
            },
            {
                "title": "Business Analyst Agent",
                "description": "The BA Agent maps business processes, identifies gaps, and translates domain requirements into technical specifications. It draws on the Knowledge Base layer — ADRs, domain models, and API docs — to stay grounded in reality.",
                "pro_tip": "Pair the BA Agent with a domain-specific Knowledge Base. A BA Agent with no domain docs produces generic analysis. With your ADRs loaded, it reasons from your actual constraints."
            },
            {
                "title": "Developer Agent",
                "description": "The Dev Agent writes, edits, and reviews code. It has full tool access — file system, bash, git — and can execute tests, run linters, and iterate on failures without human intervention between steps.",
                "pro_tip": "Scope the Dev Agent's working directory explicitly. An agent with unrestricted file system access in a monorepo will roam. Use allowedTools path restrictions to keep it focused."
            },
            {
                "title": "QA Agent",
                "description": "The QA Agent writes test cases, executes test suites, and reports failures with reproduction steps. It can run the full test suite in isolation without polluting the parent session's context with test output noise.",
                "pro_tip": "Run the QA Agent after the Dev Agent completes, passing the list of changed files. The agent targets its tests to what actually changed rather than running everything blindly."
            },
            {
                "title": "Scrum Master Agent",
                "description": "The SM Agent facilitates ceremonies — daily standups, sprint retrospectives, velocity tracking. It reads sprint data from Jira, generates summaries, identifies blockers, and formats outputs for Slack or email via MCP.",
                "pro_tip": "Schedule the SM Agent as a recurring task using a cron hook. Automated standup summaries generated from Jira data before the team meeting arrive pre-populated and accurate."
            },
            {
                "title": "Architect Agent",
                "description": "The Architect Agent reviews designs for alignment with existing ADRs, proposes system designs, and authors new Architecture Decision Records. It is the custodian of the Knowledge Base layer.",
                "pro_tip": "Always give the Architect Agent read access to all existing ADRs before asking it to propose a new architecture. Without prior decisions, it will propose patterns that contradict what you've already decided."
            },
            {
                "title": "Defining Agents in .claude/agents/",
                "description": "Custom sub-agents are now defined as Markdown files in .claude/agents/ with YAML frontmatter specifying name, model, tools, and system prompt. Committed to git, they become version-controlled team infrastructure — every developer gets the same agent team when they pull the repo.",
                "pro_tip": "Right-size each agent's model. Use claude-haiku-4-5 for file-scanning QA agents, claude-sonnet-4-6 for Dev agents writing code, and claude-opus-4-6 for Architect agents reasoning over ADRs. Model budget is the highest-leverage setting in the frontmatter."
            },
            {
                "title": "Parallel Sessions in the Desktop App",
                "description": "The redesigned Claude Code desktop app (April 2026) manages all sub-agent sessions from a single sidebar. Filter sessions by status, project, or environment. Open a side chat (⌘+;) mid-task to ask questions that pull parent context without bleeding back in. Three view modes — Verbose, Normal, Summary — let you dial from full transparency to results-only.",
                "pro_tip": "Run your Dev Agent and QA Agent as parallel sessions in the desktop app. Watch both in Summary mode; switch to Verbose only when one fails. You get the benefit of parallel execution with readable signal, not noise."
            },
            {
                "title": "Connections to Other Layers",
                "description": "Sub-agents are defined in .claude/agents/, governed by Settings, inherit rules from CLAUDE.md, and are invoked via Slash Commands or automatically. The agent definition file is the bridge between all layers — it names the tools, the model, and the mandate in one place.",
                "pro_tip": "Model your agent team on your real team structure. If you have a dedicated QA person, you need a QA Agent. Agents without human counterparts tend to have unclear mandates."
            }
        ]
    },
    {
        "slug": "knowledge-base",
        "title": "Knowledge Base",
        "icon": "📚",
        "color": "#E67E22",
        "chapter": 5,
        "tagline": "The domain memory Claude draws on every session.",
        "description": "ADRs, API documentation, team standards, Agile frameworks, and domain models — the Knowledge Base is the long-term memory that keeps Claude grounded in your reality rather than generic best practices.",
        "layers": [
            {
                "title": "Architecture Decision Records",
                "description": "ADRs are the highest-value Knowledge Base documents. They capture the 'why' behind technical choices — context, options considered, the decision, and consequences. Claude uses them to reason from your history, not from abstract principles.",
                "pro_tip": "Store ADRs as Markdown in docs/adr/ and reference them from CLAUDE.md. A single sentence in CLAUDE.md ('See docs/adr/ for all architecture decisions') is enough for Claude to load them on demand."
            },
            {
                "title": "API Documentation",
                "description": "Paste or link internal API specs (OpenAPI, GraphQL schemas, gRPC definitions) into the Knowledge Base. Claude can generate correct client code, write integration tests, and spot breaking changes when it knows your exact API contracts.",
                "pro_tip": "Include your internal APIs, not just public ones. The internal user-service API that every team uses but nobody documents is exactly where Claude makes the most mistakes without it."
            },
            {
                "title": "Domain Models",
                "description": "Entities, relationships, and business rules expressed as diagrams or structured Markdown. When Claude understands your domain model — what a Customer is, what an Order contains, what a Shipment constrains — it generates code that fits naturally into your system.",
                "pro_tip": "Include edge cases and business rules, not just entity definitions. 'An Order can only be cancelled if its status is PENDING or PROCESSING' is the kind of rule Claude otherwise has to guess."
            },
            {
                "title": "Team Standards",
                "description": "Code review checklists, branching strategies, deployment runbooks, incident response playbooks — any standard your team follows consistently. Claude applies them without being reminded when they're in the Knowledge Base.",
                "pro_tip": "Keep standards documents short and specific. A 200-line code review checklist will be ignored. A 20-line checklist with the 5 most important rules will be followed every time."
            },
            {
                "title": "Agile Frameworks",
                "description": "Your team's specific interpretation of Scrum, SAFe, Kanban, or Shape Up — including your ceremonies, your Definition of Done, your sprint length, your story point scale. Claude facilitates Agile ceremonies correctly when it knows your flavor.",
                "pro_tip": "Include what's different about your process, not the standard definition. Claude already knows what Scrum is. It needs to know that your team does 2-week sprints with planning on Monday."
            },
            {
                "title": "Memory Files (Auto Memory)",
                "description": "Claude Code's auto memory writes learned facts to a MEMORY.md file in .claude/. These persist across sessions — project insights, debugging patterns, user preferences — accumulating as a living knowledge base from real interactions.",
                "pro_tip": "Prompt Claude explicitly after important sessions: 'Update your memory file with what we learned about the auth service today.' Explicitly triggered memory updates are more accurate than passive accumulation."
            },
            {
                "title": "Connections to Other Layers",
                "description": "The Knowledge Base feeds every other layer. CLAUDE.md references it, Sub-Agents draw from it, and Slash Commands are often designed to query it. It is the foundation that makes everything else domain-specific rather than generic.",
                "pro_tip": "Audit your Knowledge Base quarterly. Outdated ADRs are worse than no ADRs — they cause Claude to reason from superseded decisions. Mark deprecated decisions explicitly."
            }
        ]
    },
    {
        "slug": "slash-commands",
        "title": "Slash Commands",
        "icon": "💬",
        "color": "#C0392B",
        "chapter": 6,
        "tagline": "Multi-step workflows packaged into shareable team shortcuts.",
        "description": "/plan · /review · /standup — Slash Commands turn complex, multi-step processes into a single invocation. They are reusable, shareable, and version-controllable prompt programs.",
        "layers": [
            {
                "title": "What Slash Commands Are",
                "description": "A Slash Command is a Markdown file stored in .claude/commands/ that becomes a callable prompt when prefixed with /. Typing /standup expands to a full ceremony facilitation prompt, pre-loaded with context and format instructions.",
                "pro_tip": "Name commands after verbs, not nouns. /review, /plan, /deploy-check — commands describe actions. /standards, /adr, /sprint are confusing because they could mean 'show me' or 'generate' or 'run'."
            },
            {
                "title": "/plan — Sprint Planning",
                "description": "The /plan command pulls the product backlog, applies estimation heuristics, checks team capacity, and produces a structured sprint plan with story assignments, risks, and dependency ordering.",
                "pro_tip": "Pass sprint capacity as an argument: /plan --capacity=60 --team=5. Parameterized commands are more reusable than hardcoded values inside the command file."
            },
            {
                "title": "/review — Code Review",
                "description": "The /review command runs your full code review checklist against a PR or set of changed files. It checks for security issues, test coverage, naming conventions, and architectural alignment — producing a structured review comment.",
                "pro_tip": "Chain /review with your QA Agent: /review generates the review comment; the QA Agent runs the test suite. The combination replaces most of a manual PR review cycle."
            },
            {
                "title": "/standup — Daily Standup",
                "description": "The /standup command reads yesterday's commits and Jira updates, formats them into standup format (done/doing/blocked), identifies blockers, and produces a team-ready summary for async or live ceremonies.",
                "pro_tip": "Schedule /standup as a hook that runs automatically at 9am via a cron job. The summary is ready before the team meeting without anyone remembering to run it."
            },
            {
                "title": "/recap — Session Context Recovery",
                "description": "The built-in /recap command generates a summary of what happened in a session when you return after being away. Configurable in /config to auto-trigger on resume, or invoke manually. In long-running agent workflows, /recap gives sub-agents re-entry context without re-reading the full transcript.",
                "pro_tip": "Set /recap to auto-run on session resume for any agent doing multi-hour work. Enable via CLAUDE_CODE_ENABLE_AWAY_SUMMARY or /config. A sub-agent that re-reads its own recap resumes cleanly without repeating steps it already completed."
            },
            {
                "title": "Custom Workflow Commands",
                "description": "Any repeating process can become a command: /release-notes, /onboard-engineer, /incident-report. Commands can accept arguments (via $ARGUMENTS), include sub-agent launches, and produce structured output for downstream tools.",
                "pro_tip": "Build commands from real pain points. When a team member says 'I always have to do X, Y, Z before a release', that's a /release-check command waiting to be written."
            },
            {
                "title": "Team Sharing",
                "description": "Commands stored in .claude/commands/ and committed to git are automatically available to every team member. No installation, no sharing a gist — pull the repo and /review works for everyone immediately.",
                "pro_tip": "Create a COMMANDS.md in .claude/ that documents each command, its arguments, and example output. New team members can scan it in 5 minutes and understand your entire command library."
            },
            {
                "title": "Connections to Other Layers",
                "description": "Slash Commands are the orchestration layer. A single command can launch Sub-Agents, query MCP servers, apply Knowledge Base context, and invoke Skills — packaging a complete workflow into one invocation.",
                "pro_tip": "Design commands to be composable: /plan uses /estimate and /capacity internally. Composable commands are easier to test and maintain than monolithic commands that do everything."
            }
        ]
    },
    {
        "slug": "skills",
        "title": "Skills",
        "icon": "⚡",
        "color": "#1ABC9C",
        "chapter": 7,
        "tagline": "The layer Claude activates without being asked.",
        "description": "Skills (SKILL.md) are auto-invoked behaviors, bundled scripts, and team plugins that fire based on context — not commands. They are what Claude does automatically, not what you tell it to do.",
        "layers": [
            {
                "title": "What Skills Are",
                "description": "A Skill is a Markdown file in .claude/skills/ that describes a behavior Claude should invoke autonomously when specific conditions are met. Unlike Slash Commands (triggered by the user), Skills are triggered by Claude based on context matching.",
                "pro_tip": "Distinguish Skills from Commands by who triggers them. If the user invokes it, it's a Command. If Claude decides to invoke it, it's a Skill. Design each accordingly."
            },
            {
                "title": "Auto-Invoked Behaviors",
                "description": "A Skill like 'When editing a React component, always run the component's test file afterward' fires without user instruction. Claude recognizes the context (React component edit) and applies the behavior (run tests) automatically.",
                "pro_tip": "Start with your most common 'always do X after Y' patterns. These are the highest-value Skills — they eliminate the most repeated instructions."
            },
            {
                "title": "Bundled Scripts",
                "description": "Skills can bundle shell scripts, configuration templates, and prompt fragments into a single reusable unit. A 'TypeScript Component' Skill might include the file template, the test file template, and the storybook story template as a bundle.",
                "pro_tip": "Version your Skill scripts with the rest of your codebase. When your component template changes, update the Skill — Claude will use the new template on the next invocation."
            },
            {
                "title": "Team Plugins",
                "description": "Skills shared across the team via git act as plugins to Claude's behavior. A 'PR Description Generator' Skill installed by every developer means every PR description follows the same format without individual setup.",
                "pro_tip": "Treat team Skills like npm packages. Have one person own each Skill, review changes via PR, and document breaking changes. Discipline here prevents 'why did Claude suddenly change behavior?' questions."
            },
            {
                "title": "User-Invocable Skills",
                "description": "Some Skills are invocable via the /skill-name syntax (the Skill tool in the Agent SDK). These bridge the line between Skills and Commands — they're reusable behaviors that can be triggered either by Claude or by the user.",
                "pro_tip": "Mark user-invocable Skills clearly in CLAUDE.md. Users shouldn't have to discover Skills by accident — document the ones they're allowed to invoke directly."
            },
            {
                "title": "Context Matching",
                "description": "Skills activate when their context conditions match the current session state. Conditions can match file types, active MCP servers, user roles, or explicit flags in CLAUDE.md. Precise conditions prevent Skills from firing in the wrong context.",
                "pro_tip": "Be specific with context conditions. A Skill with condition 'when working in this project' fires constantly. A Skill with condition 'when editing files in src/payments/' fires precisely when needed."
            },
            {
                "title": "Routines — Cloud-Hosted Automation",
                "description": "Routines (April 2026) are saved Claude Code configurations — a prompt, one or more repos, and a set of connectors — that run on Anthropic-managed cloud infrastructure. Three trigger modes: scheduled (cron-style), API trigger (HTTP POST with bearer token), and GitHub trigger (fires on matching repo events like push or PR). Your laptop doesn't need to be on.",
                "pro_tip": "Start with a GitHub trigger Routine: on PR opened → run /review → post comment. This is the highest-ROI first Routine for any dev team. Limits: Pro=5/day, Max=15/day, Team/Enterprise=25/day — budget accordingly."
            },
            {
                "title": "Connections to Other Layers",
                "description": "Skills are the capstone layer — they can invoke Slash Commands, launch Sub-Agents, query MCP servers, and reference the Knowledge Base. Routines extend this further: a Skill packaged as a Routine runs your full 7-layer system automatically on a schedule, without any human trigger.",
                "pro_tip": "Map your Skills to the radial diagram. Each Skill that touches multiple outer layers is a high-leverage automation. Skills that only touch one layer might be better implemented as part of that layer directly."
            }
        ]
    }
]
