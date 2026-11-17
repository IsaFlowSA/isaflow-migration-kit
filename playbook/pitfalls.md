# Pitfalls — learned on earlier migrations

**Allocation ≠ application.** Allocating a bank line to a supplier posts Dr creditors / Cr bank but applies to no
bill, so the aged creditors don't move. Apply it to the bill (FIFO) as a separate step. Same for receipts.

**Bulk allocation is all-or-nothing on a real fault** (max ~500 per call, supports dry run, skips lines already
allocated). One bad line rolls back the whole batch. **Zero-amount lines roll back the batch** — filter R0.00 out.

**Keep every batch id.** Bulk allocations and imports can be undone by batch id; without it, it's line by line.

**Bank import de-duplication ignores the running balance across imports.** Two genuine identical lines (same
date, amount, description) in different imports: the second is dropped. `build_sync.py` adds a unique reference
to every description to prevent this.

**Refunds need cash on account at the refund date.** A supplier refund (money in) or customer refund (money out)
is refused if there is no unapplied cash at that date; credit notes don't count. Fix by re-application (unapply an
earlier payment → apply the credit note → re-apply) — no journals. Run refunds last, one at a time.

**A refund dated before its payment** can't be recorded in IsaFlow. Book both lines to suspense (net R0.00) and say so.

**Reconciled bank lines can't be reversed.** To fix a line inside a completed reconciliation, post a correcting
journal; don't reopen and reverse.

**A bank reconciliation claims every unreconciled line up to its statement date.** Reconcile statements in date
order, oldest first.

**VAT cents.** IsaFlow computes credit-note VAT on the total; other systems often per line. Split documents so the
VAT hits the source figure to the cent. Supplier bills round VAT per line.

**Reverse journal = contra.** The original stays "posted" and flagged. Reversals are for genuine errors only.

**Sage forex.** Sage can post realised forex one-sided (no debtor leg) and revalue the debtors control with no
customer. Expect a control-account difference in Sage itself; don't copy Sage's error into IsaFlow — pair the
forex with the customer and explain the difference.

**Sage's year-end edits.** Sage figures change after the fact (late journals, revaluations). Management packs and
earlier exports are point-in-time; IsaFlow should equal Sage **as it stands now**, and back-dated edits are picked
up by the monthly sync.

**Large tool results** may be written to a file instead of returned; parse them with a script.

**Search tools can return nothing spuriously** on a narrow date window — widen the window or filter by account.

**One IsaFlow login, several companies.** Always confirm the company before posting.
