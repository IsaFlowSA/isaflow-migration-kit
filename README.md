# isaflow-migration-kit

Move a company's books from **Sage One (South Africa)** to **IsaFlow** with an AI agent — Claude, Codex, Cursor or
any agent that can read files, run Python and use MCP. Balanced to the cent, with every step proven.

**New here? Read [`START_HERE.md`](START_HERE.md).**

| Path | What |
|---|---|
| `START_HERE.md` | For the person: what you need, how to start, the prompt to paste |
| `AGENTS.md` | For the agent: hard rules and how to work (read automatically by most agents) |
| `playbook/` | The steps, 01 folder → 07 monthly sync, plus `pitfalls.md` |
| `scripts/` | `scaffold.py` (folder), `sage_gl_export.js` + `parse_bank.py` (exports), `map_accounts.py` (chart mapping), `takeon.py` (opening balances), `build_sync.py` (transactions), `prepare_posting.py` (ready-to-send IsaFlow calls), `compare_tb.py` + `bank_rec_prep.py` (proof) |
| `templates/` | Company brief, document register, `company.json` settings, `statements.csv`, MCP setup per agent |
| `tests/` | Synthetic self-test — no real data. Runs on every push (GitHub Actions, Linux + Windows) |

This repository holds **no company data**. Company documents, exports, IDs and write-ups live in each company's
own folder, never here.

The method was proven on a 32-month rebuild (Mar 2024 → Oct 2026): IsaFlow's trial balance equals Sage's per
account, customer and supplier ledgers reconcile, residual R0.00.

## Contributing
Issues and pull requests are welcome. Never include real company data (documents, exports, IDs, figures) — use
synthetic examples like `tests/test_selftest.py`.

## Licence
MIT — see [`LICENSE`](LICENSE).
