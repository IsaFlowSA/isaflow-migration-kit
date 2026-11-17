# isaflow-migration-kit

Move a company's books from **Sage One (South Africa)** to **IsaFlow** with an AI agent — Claude, Codex, Cursor or
any agent that can read files, run Python and use MCP. Balanced to the cent, with every step proven.

**New here? Read [`START_HERE.md`](START_HERE.md).**

| Path | What |
|---|---|
| `START_HERE.md` | For the person: what you need, how to start, the prompt to paste |
| `AGENTS.md` | For the agent: hard rules and how to work (read automatically by most agents) |
| `playbook/` | The steps, 01 folder → 07 monthly sync, plus `pitfalls.md` |
| `scripts/` | `scaffold.py` (folder), `parse_bank.py`, `build_sync.py`, `compare_tb.py`, `sage_gl_export.js` |
| `templates/` | Company brief, document register, `company.json` settings, MCP setup per agent |
| `tests/` | Synthetic self-test — no real data |

This repository holds **no company data**. Company documents, exports, IDs and write-ups live in each company's
own folder, never here.

The method was proven on a 32-month rebuild (Mar 2024 → Oct 2026): IsaFlow's trial balance equals Sage's per
account, customer and supplier ledgers reconcile, residual R0.00.
