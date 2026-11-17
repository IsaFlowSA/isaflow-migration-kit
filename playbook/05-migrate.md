# 05 — Migrate

**Goal:** IsaFlow holds every transaction from the opening date to the latest Sage date.
Read `pitfalls.md` first.

## A. Export from Sage (into `Source Documents/Sage exports <yyyy-mm>/`)
Exports are **life-to-date** so later syncs can detect back-dated edits.

| Export | Sage report | How |
|---|---|---|
| GL | Reports → Account Transactions, all accounts, company start → today | Render as HTML, then run `scripts/sage_gl_export.js` in the browser (agent's browser tool, or the person pastes it into DevTools → Console). Set `FILE` first. Save as `Sage GL life-to-date at <date>.csv` |
| Bank + cards + petty cash | Reports → Banks and Credit Cards Transactions, all accounts, life to date | Sage's own CSV export |
| Trial balance | Reports → Trial Balance, one per financial year + current year to date | Sage's own CSV export |
| Ageing | Customer and supplier ageing (detailed) at the opening date | CSV |
| Chart | Accounts list | CSV |

Then: `python -I scripts/parse_bank.py "<bank csv>" <work>/bank.json`
(prints per account: lines, opening, net, closing — compare with Sage's bank balances).

## B. Map and set up (in `data/`)
1. `company.json`: every Sage account name → an IsaFlow code (`account_map`), bank accounts, the Sage names of the
   debtors/creditors control, VAT and forex accounts, and any party-name fixes. Create missing IsaFlow accounts
   (`create_gl_account`) and refresh `account_ids.json`.
2. Create customers and suppliers (`create_customer` / `create_supplier`); save name → id to
   `customer_ids.json` / `supplier_ids.json`.

## C. Opening balances (only if step 04 chose an AFS take-on)
One journal at the opening date for every non-subledger account, plus opening invoices/bills per customer/supplier
for the debtors and creditors, through clearing accounts that net to R0.00. Check: TB balances, AR and AP
sub-ledgers equal their controls (residual R0.00), every AFS line agrees.

## D. Build
```
python -I scripts/build_sync.py --config data/company.json --gl "<GL csv>" --bank <work>/bank.json
       --from <opening date> --to <last date> --tag rb --out <work>/out
```
Exit 2 = `out/stop.json` lists what needs a decision. **Post nothing until it is empty.**

| Stop reason | Fix |
|---|---|
| `unmapped_sage_account` | add to `account_map` (create the IsaFlow account if needed), rebuild |
| `unknown_customer` / `unknown_supplier` | create the party, add to the ids file, rebuild |
| `control_line_without_party` | e.g. a Sage forex revaluation on the control account — needs a decision; ask |
| `multi_party_group` | one Sage entry touching several parties — split by hand |
| `vat_unresolved` | bank group whose VAT can't be matched to lines — inspect, set `vat_code` by hand |
| `account_id_missing` | refresh `account_ids.json` |
| `journal_imbalance` | a bug — stop and report |

## E. Post — in this order, keeping every batch id and idempotency key
Strip the `_`-prefixed helper keys before sending. Dry run first wherever the tool supports it.
**Show the person the dry-run totals before the first bulk post.**
1. Customer invoices → create in bulk → finalise. Each total must equal `_gross`.
2. Supplier bills → create in bulk → approve.
3. Credit notes → create (customer line to sales, supplier line to supplier clearing) → approve. Total = `_gross`.
4. Month-end journals → draft → post.
5. Bank lines: each `out/bank_<code>.csv` → `import_bank_statement` (≤300 rows per call). The account's line count
   and net movement must move by exactly `summary.json` → `bank_lines` / `bank_net`.
6. Allocations → bulk allocate in date order (≤300 per call). All-or-nothing: on a refusal, isolate the line,
   carry on, deal with it after.
7. Refunds (`payload.refunds`) last, one at a time.
8. Apply unapplied cash and credit notes FIFO (oldest first).

Record every batch id and key in `outputs/<short>-migration-<date>.md` as you go.
