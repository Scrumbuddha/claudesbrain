# Building Claude's Brain — Chapter 1: CLAUDE.md
### The constitution every other layer obeys.

---

CLAUDE.md is the first file Claude reads when it opens your project — and the most important one you'll ever write. It is the constitution of your Claude setup: the document that defines who Claude is inside your codebase, what rules it follows, and how it connects to every other layer of your system.

Everything in *Building Claude's Brain* flows from here. Before you configure MCP servers, before you write slash commands, before you define sub-agents — get CLAUDE.md right.

This chapter covers all seven components of a well-built CLAUDE.md, with the exact patterns that make the difference between a file Claude reads once and forgets and one it uses to navigate your project with precision.

---

## 1. Project Identity

CLAUDE.md defines who Claude is inside your project. It sets the persona, communication style, and scope boundaries — turning a general assistant into a project-aware collaborator that knows your stack, your team, and your goals.

The most impactful thing you can do in CLAUDE.md is open with a clear, specific description of what your project is and why it exists. Claude uses this context to orient every single response. The clearer you are upfront, the less you repeat yourself across sessions.

**Pro Tip:** Open with a one-paragraph "About This Project" section. Claude uses it to orient every response — the clearer your context, the less you repeat yourself.

Example:
```
## About This Project
This is a B2B SaaS platform for construction project managers.
It tracks subcontractor bids, manages document approval workflows,
and integrates with QuickBooks for invoicing.
Primary users: project managers and site supervisors.
Current focus: rebuilding the bid comparison module in React.
```

Two sentences that tell Claude the domain, the users, and the current priority. That's it. That's enough for Claude to stop suggesting irrelevant patterns.

---

## 2. Persistent Rules

Any instruction you find yourself typing more than twice belongs in CLAUDE.md. From coding style guides to commit message formats, these rules persist across every session without pasting them into chat.

This is the highest-leverage section of CLAUDE.md for most developers. Every time you type "remember, we use TypeScript strict mode" or "don't forget to use conventional commits", that's a rule that should be in CLAUDE.md.

**Pro Tip:** Use imperative mood: "Always use TypeScript strict mode" not "We prefer TypeScript". Claude follows directives more reliably than preferences.

The difference is subtle but measurable. "We prefer" signals a soft preference that Claude can override when it judges the situation. "Always use" signals a rule. Write rules as rules.

Example rules section:
```
## Rules
- Always use TypeScript strict mode. No `any` types.
- All API responses use the shape `{ data, error, meta }`.
- Never commit directly to `main`. All changes via PR.
- Write tests before marking a story done.
- Use conventional commits: `feat:`, `fix:`, `chore:`, `docs:`.
- Never expose environment variables in logs or responses.
```

Six rules. Each one imperative. Each one specific enough that Claude can't misinterpret it.

---

## 3. Location Hierarchy

Claude reads three CLAUDE.md files in order: global (~/.claude/CLAUDE.md), project root, and sub-directory. More specific files override more general ones — you can set global defaults and project-level exceptions.

This hierarchy is one of the most underused features of Claude Code. Most developers write one CLAUDE.md in the project root and stop there. But the full hierarchy gives you a powerful layering system.

**Pro Tip:** Put team-wide standards (lint rules, PR conventions) in the project root CLAUDE.md. Put component-specific rules in sub-directory files.

The global CLAUDE.md at ~/.claude/CLAUDE.md sets your personal defaults across every project — your communication preferences, your default stack, your output format preferences. It's the file that follows you everywhere.

The project root CLAUDE.md sets team-wide conventions — the rules everyone on the team shares. This file should be committed to git.

Sub-directory CLAUDE.md files set context-specific rules for a specific module or service. The payments/ directory might have different validation rules than the admin/ directory. Put those rules where they live.

```
~/.claude/CLAUDE.md          # Your personal global defaults
project/CLAUDE.md            # Team-wide project rules (committed)
project/src/payments/CLAUDE.md  # Payment-specific rules
```

---

## 4. Architecture Decisions

Embed your Architecture Decision Records (ADRs) or link to them in CLAUDE.md. Claude will reason from your actual decisions rather than proposing patterns that contradict your established architecture.

This is where CLAUDE.md transitions from a style guide into a true knowledge base index. When Claude knows about your architecture decisions, it stops proposing things you've already ruled out.

**Pro Tip:** Add a "Tech Stack" section listing exact versions: "React 18, Vite 5, TanStack Query v5". Claude avoids suggesting deprecated APIs when it knows your versions.

Exact versions matter more than you expect. "We use React" tells Claude almost nothing — React 16, 17, and 18 have significantly different patterns. "React 18 with Concurrent Mode and Suspense" tells Claude which patterns apply.

```
## Tech Stack
- Frontend: React 18, Vite 5, TanStack Query v5, Tailwind 3
- Backend: Node 20, Express 5, Prisma 5, PostgreSQL 16
- Testing: Vitest, Playwright, Testing Library
- Infra: AWS ECS, RDS, S3, CloudFront

## Architecture Decisions
See docs/adr/ for all Architecture Decision Records.
Key decisions:
- ADR-001: We use Prisma as the ORM (not raw SQL)
- ADR-002: Auth is handled by Auth0 — no custom auth
- ADR-003: Feature flags via LaunchDarkly
```

Now when Claude suggests an auth implementation, it knows you use Auth0. When it suggests a database pattern, it knows you use Prisma. The suggestions change immediately.

---

## 5. Team Conventions

Document naming conventions, folder structures, testing patterns, and git workflows. When every team member and every Claude session starts from the same conventions file, consistency compounds.

Conventions are the rules that don't need justification — they just need to be followed consistently. File naming, folder structure, test file location, PR title format. Put them all here.

**Pro Tip:** Include examples, not just rules. "Feature folders: src/features/auth/components/, src/features/auth/hooks/" beats "Use feature-based folder structure".

Abstract naming rules are hard to follow. Concrete examples are easy. Show the folder structure. Show the naming pattern. Show the test file next to the source file. Claude will match the pattern.

```
## Conventions
Naming:
- Components: PascalCase (UserProfile.tsx)
- Hooks: camelCase with use prefix (useUserProfile.ts)
- Utils: camelCase (formatCurrency.ts)
- API routes: kebab-case (/api/user-profile)

Folder structure:
src/features/[feature]/components/
src/features/[feature]/hooks/
src/features/[feature]/api/
src/features/[feature]/types.ts

Testing:
- Unit tests co-located with source (.test.ts)
- Integration tests in src/__tests__/
- Minimum coverage: 80% for new code
```

---

## 6. Memory & Persistence

Unlike chat history, CLAUDE.md survives session resets. It is the mechanism for true project memory — everything that should survive a new terminal window, a new day, or a new team member onboarding.

This is the conceptual shift that unlocks everything else. Chat history is ephemeral. CLAUDE.md is permanent.

When you close the terminal and reopen it tomorrow, chat history is gone. CLAUDE.md is still there. When a new developer joins the team and clones the repo, they get your CLAUDE.md automatically. When Claude starts a sub-agent in a fresh context window, the sub-agent reads CLAUDE.md on startup.

**Pro Tip:** Ask Claude to update CLAUDE.md as a final step after significant decisions: "Update CLAUDE.md to reflect the auth approach we just decided on."

This single habit — treating CLAUDE.md as a living document that Claude helps maintain — is what separates a CLAUDE.md that gets stale from one that gets better over time.

Claude Code's auto-memory system (the MEMORY.md file in .claude/) complements this. The auto-memory captures session-specific learnings. CLAUDE.md captures intentional, durable rules. Use both.

---

## 7. Connections to Other Layers

CLAUDE.md tells Claude which MCP servers are active, where the Knowledge Base lives, which Slash Commands are in scope, and which Skills are available. It is the index for every other layer.

This is the final and most important function of CLAUDE.md: it is the map of your entire setup.

**Pro Tip:** Add a "Layer Map" section: a bullet list of which other layers are configured and where their files live. Claude uses it to self-navigate your setup.

Without a Layer Map, Claude has to discover your setup by exploring the file system. With a Layer Map, it knows exactly where to look.

```
## Layer Map
- Agents:   .claude/agents/  (dev, qa, architect, po, sm)
- Commands: .claude/commands/ (/review, /standup, /plan, /retro)
- Skills:   .claude/skills/  (auto-test, pr-description)
- MCP:      GitHub, Jira (see .claude/settings.json)
- Knowledge Base: docs/ (ADRs, domain model, API contracts)
```

Six lines that orient any Claude session — human-triggered or agent-triggered — to your full system. When Claude sees this Layer Map, it knows it can look at .claude/agents/ to find specialized agents, that /review is available as a command, and that GitHub and Jira are live connections.

---

## Putting It Together

A complete CLAUDE.md for a mid-sized project looks like this:

```
# CLAUDE.md — [Project Name]

## About This Project
[2-3 sentences: what it does, who uses it, why it exists.]

## Tech Stack
- Frontend: [exact versions]
- Backend: [exact versions]
- Testing: [frameworks]
- Infra: [cloud provider, key services]

## Rules
- [imperative rules, one per line]

## Architecture Decisions
See docs/adr/ for all ADRs.
Key decisions:
- ADR-001: [decision]
- ADR-002: [decision]

## Conventions
[naming, folder structure, testing patterns]

## Team
- [name]: [role and ownership area]

## Layer Map
- Agents: .claude/agents/
- Commands: .claude/commands/
- Skills: .claude/skills/
- MCP: [list active servers]
- Knowledge Base: docs/
```

Start here. Fill in the brackets. Commit it. Every other chapter builds on this foundation.

---

## What's Next

Chapter 1 is the foundation. The remaining six chapters build outward:

- **Chapter 2 — Settings & Config:** The three-tier permission hierarchy that governs what Claude can do.
- **Chapter 3 — MCP Servers:** Connecting Claude to GitHub, Jira, Gmail, databases, and your own APIs.
- **Chapter 4 — Sub-Agents:** Specialized Claude instances with isolated context, parallel execution, and deep domain focus.
- **Chapter 5 — Knowledge Base:** ADRs, domain models, and team standards that keep Claude grounded in your reality.
- **Chapter 6 — Slash Commands:** Multi-step workflows packaged into shareable team shortcuts.
- **Chapter 7 — Skills:** The layer Claude activates without being asked — auto-invoked behaviors and cloud-hosted automation.

The full book, interactive web app, and Pro Bundle (prompt library, CLAUDE.md templates, slash command library, sub-agent templates) are available at **claudesbrain.com**.

---

*Building Claude's Brain — St. Pete AI · claudesbrain.com*
