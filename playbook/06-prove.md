# 06 — Prove

**Goal:** evidence that IsaFlow equals Sage (and the bank), with the residual stated.

1. **Trial balance per account** at every year-end and at the latest date: write IsaFlow's `trial_balance` to
   `isa_tb.json` as `{code: signed balance}`, then
   ```
   python -I scripts/compare_tb.py --config data/company.json --sage "<Sage TB csv>" --isaflow isa_tb.json
   ```
   Every difference must be explained in writing (e.g. a known Sage defect) or fixed. No plugs.
2. **Sub-ledgers:** customer and supplier ledgers reconcile to their control accounts; the difference is only
   named cash/credits on account. Unexplained: R0.00. Clearing accounts (customer, supplier, opening) at R0.00.
3. **Integrity checks** (`data_integrity_checks` or equivalent): clean.
4. **Intercompany:** balances with other group companies agree to their books (read only).
5. **External targets** where available: loan statements, signed AFS, management packs.
6. **Bank reconciliations** against real bank statements only. If statements are not in yet, say so and leave the
   reconciliation open — never reconcile to Sage's balance. Read each statement PDF and type its closing balance
   into `data/statements.csv` (template `templates/statements.csv`), then
   ```
   python -I scripts/bank_rec_prep.py --config data/company.json --bank <work>/bank.json
          --statements data/statements.csv --out <work>/recs
   ```
   It checks each statement against the imported lines and writes one `perform_bank_reconciliation` call per
   statement (dry run), oldest first. Fix any difference before reconciling; then send each call with
   `dry_run` removed and `complete: true`.
7. Write `outputs/<short>-migration-<date>.md`: what was posted (counts, batch ids, keys), every difference and
   its explanation, the residual in rand and cents, open items. Update the brief and the register.

**Stop:** report to the person in a few lines, with the residual.
