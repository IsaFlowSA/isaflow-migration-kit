# 07 — Monthly sync (while Sage keeps running)

**Goal:** each month, bring Sage's new month — and any back-dated Sage edits — into IsaFlow, and prove it.

1. Confirm the company (`list_companies` / `company_profile`). Read `data/state.json`: the window is
   `synced_to + 1 day` → last day of the previous month. Tag = `yymm` of the window end.
2. Export from Sage again, **life-to-date** (GL, Bank+CC, TB for the current year) into a new
   `Source Documents/Sage exports <yyyy-mm>/` folder. Parse the new and the previous bank exports with
   `parse_bank.py`.
3. Build with the previous exports so back-dated edits are caught:
   ```
   python -I scripts/build_sync.py --config data/company.json --gl "<new GL>" --bank <work>/bank.json
          --from <from> --to <to> --tag <tag> --out <work>/out
          --prev-gl "<state.last_gl_export>" --prev-bank <work>/bank_prev.json
   ```
   Back-dated edits are booked in the month the Sage line is dated. A bank line Sage deleted stops the build
   (`sage_deleted_bank_line`) — check it against the bank statement; never reverse a reconciled line.
4. Post as in step 05-E. Prove as in step 06.
5. Update `data/state.json` (`synced_to`, last exports, known differences, history) and write
   `outputs/<short>-sync-<tag>-<date>.md`.

When the company stops using Sage, this step ends: process from bank statements and source documents in IsaFlow.
