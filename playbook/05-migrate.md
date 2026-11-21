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
   debtors/creditors control, VAT and forex accounts, and any party-name fixes. Save IsaFlow's chart
   (`list_gl_accounts`) as `data/isaflow_chart.json` (`[{"code", "name"}]`) and run
   ```
   python -I scripts/map_accounts.py --config data/company.json --isaflow-chart data/isaflow_chart.json
          --gl "<GL csv>" --tb "<Sage TB csv>" --out data/account_map_suggestions.json
   ```
   It lists every unmapped Sage account with the closest IsaFlow account. Suggestions are a starting point: decide
   each one (Sage's category and the AFS note settle it), write it into `account_map`, create missing IsaFlow
   accounts (`create_gl_account`), refresh `account_ids.json`, and re-run until it exits 0.
2. Create customers and suppliers (`create_customer` / `create_supplier`); save name → id to
   `customer_ids.json` / `supplier_ids.json`.

## C. Opening balances (only if step 04 chose an AFS take-on)
One journal at the opening date for every non-subledger account, plus opening invoices/bills per customer/supplier
for the debtors and creditors, through clearing accounts that net to R0.00.

1. Inputs: the Sage TB at the day before the opening date; `customers_open.csv` and `suppliers_open.csv`
   (`Name,Balance`, from Sage's detailed ageing at that date — customers: owed to us +; suppliers: owed by us +);
   if the take-on follows the signed AFS rather than Sage, an `adjustments.json` with each AFS-vs-Sage difference
   (`[{"code", "amount", "why"}]`, netting to R0.00). Agree every adjustment with the person first.
2. Set `isaflow_codes.retained_earnings` and the `takeon` clearing codes in `company.json` (customer clearing must
   be a revenue account, supplier clearing an expense account).
3. Build:
   ```
   python -I scripts/takeon.py --config data/company.json --tb "<Sage TB>" --customers customers_open.csv
          --suppliers suppliers_open.csv --date <opening date> --out <work>/takeon [--adjustments adjustments.json]
   ```
   Exit 2 = `takeon/stop.json` (unmapped account, unknown party, ageing ≠ control, TB doesn't balance).
4. Post it with section E (`prepare_posting.py --tag takeon`, no `--bank-dir`). After posting: TB balances, both
   take-on clearing accounts R0.00, AR and AP sub-ledgers equal their controls (residual R0.00), every AFS line
   agrees (state any AFS rounding in cents).

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
```
python -I scripts/prepare_posting.py --config data/company.json --payload <work>/out/payload.json --tag <tag>
       --out <work>/calls --bank-dir <work>/out
```
It writes one file per tool call (`calls/NNN_<tool>.json`: helper keys stripped, `company_id` guard and idempotency
key set, batches cut to the tool limits), `manifest.json` (order + the check after each call) and `posting-log.md`
(fill in batch ids as you go). Send each file's contents as the tool's arguments, in number order. Dry run first
wherever the tool supports it. **Show the person the dry-run totals before the first bulk post.**
The order it writes, and what each step means:
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
