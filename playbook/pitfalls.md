# Working notes — how IsaFlow and Sage behave during a migration

Read before step 05. Each note says how the system works and what to do about it.

## IsaFlow

**Allocating and applying are separate steps.** Allocating a bank line to a supplier posts Dr creditors / Cr bank
and leaves the payment on account. Applying it to a bill (oldest first) is what moves the aged creditors. The same
holds for customer receipts.

**Bulk allocation is all-or-nothing.** It takes up to ~500 lines per call, supports a dry run and skips lines already
allocated. If one line fails validation, the whole batch rolls back, so nothing is half-posted. Filter out R0.00
lines first, and on a refusal isolate the line and carry on.

**Every bulk import and allocation returns a batch id.** Keep it: a batch can be reversed in one call.

**Bank imports de-duplicate on date, amount and description.** Two genuine identical lines in different imports
look like a duplicate. `build_sync.py` adds a unique reference to every description so each line is distinct.

**A refund needs cash on account at its date.** A supplier refund (money in) or customer refund (money out) is
matched against unapplied cash at that date; credit notes are not cash. If there isn't any, re-apply: unapply an
earlier payment → apply the credit note → re-apply the payment. No journals needed. Process refunds last, one at a time.

**A refund dated before its payment** can't be matched. Book both lines to suspense (net R0.00) and note it.

**Reconciled bank lines are locked.** To correct a line inside a completed reconciliation, post a correcting
journal rather than reopening the reconciliation.

**A bank reconciliation takes every unreconciled line up to its statement date.** Reconcile statements in date
order, oldest first.

**VAT on credit notes is calculated on the total; on supplier bills, per line.** If the source system rounded
differently, split the document so the VAT matches the source to the cent.

**Reversing a journal posts a contra entry.** The original stays posted and is marked reversed. Use reversals only
for genuine errors.

**One login can hold several companies.** Always confirm the company (`list_companies` / `company_profile`) before
posting.

## Sage One

**Forex.** Sage can post realised forex without the debtor leg and revalue the debtors control without naming a
customer, so Sage's own control account may not match its customer ledger. In IsaFlow, pair the forex with the
customer and record the difference against Sage in writing.

**Figures change after the fact.** Late journals and revaluations change earlier periods. Management packs and
earlier exports are point-in-time; IsaFlow should equal Sage as it stands now, and the monthly sync picks up
back-dated edits.

## Agent tools

**Large tool results** may be written to a file rather than returned; parse them with a script.

**Searches on a very narrow date window** can come back empty; widen the window or filter by account.
