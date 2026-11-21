"""Prepare bank reconciliations against real bank statements (step 06), oldest first.

You (or the person) read each statement PDF and type its closing balance into statements.csv - the bank's figure,
never Sage's. This script checks each against the running balance of the imported lines and writes one
perform_bank_reconciliation call per statement, in date order.

Usage:
  python -I bank_rec_prep.py --config data/company.json --bank <work>/bank.json --statements data/statements.csv
         --out <work>/recs [--opening 1110=879255.73 ...]
  statements.csv: code,statement_date,closing_balance,source_file   (template: templates/statements.csv)
  --opening: the account's balance at the opening date when the import window starts after Sage's first line
             (default: Sage's opening plus every line before the first statement).
For each statement: expected = opening + imported lines up to the statement date. A difference means a line is
missing, duplicated or dated differently - find it before reconciling. Each call is written with dry_run: true;
check IsaFlow's reported difference is R0.00, then send it again with dry_run removed and complete: true.
Exit 1 if any statement differs.
"""
import argparse, collections, csv, json, os, sys
from decimal import Decimal as D

ap = argparse.ArgumentParser()
for a in ('--config', '--bank', '--statements', '--out'):
    ap.add_argument(a, required=True)
ap.add_argument('--opening', action='append', default=[])
A = ap.parse_args()
os.makedirs(A.out, exist_ok=True)
CFG = json.load(open(A.config, encoding='utf-8'))
BASE = os.path.dirname(os.path.abspath(A.config))
IDS = json.load(open(os.path.join(BASE, CFG['ids']['accounts']), encoding='utf-8'))
CO = CFG['company'].get('isaflow_company_id', '')
SHORT = CFG['company']['short_name']
BANKS = CFG['sage']['bank_accounts']
B = json.load(open(A.bank, encoding='utf-8'))

lines = collections.defaultdict(list)
opening = collections.defaultdict(D)
for name, v in B.get('opening', {}).items():
    if name in BANKS:
        opening[BANKS[name]] += D(str(v))
for x in B['rows']:
    if x['acct'] in BANKS:
        lines[BANKS[x['acct']]].append((x['date'], D(str(x['amt']))))
override = {k: D(v) for k, v in (o.split('=', 1) for o in A.opening)}

stmts = sorted(csv.DictReader(open(A.statements, encoding='utf-8-sig')), key=lambda r: (r['code'], r['statement_date']))
out, diffs, n = [], 0, 0
for r in stmts:
    code, dt, bal = r['code'].strip(), r['statement_date'].strip(), D(r['closing_balance'].replace(',', '').replace(' ', ''))
    exp = override.get(code, opening[code]) + sum(a for d, a in lines[code] if d <= dt)
    diff = bal - exp
    diffs += diff != 0
    n += 1
    fn = f'{n:03d}_perform_bank_reconciliation.json'
    json.dump({'bank_account_id': IDS.get(code), 'statement_date': dt, 'statement_balance': float(bal), 'dry_run': True,
               'complete': False, 'company_id': CO, 'idempotency_key': f'{SHORT}-stmtrec-{code}-{dt}'},
              open(os.path.join(A.out, fn), 'w'), indent=1)
    out.append(f'| {n} | {code} | {dt} | {bal:,.2f} | {exp:,.2f} | {diff:,.2f} | {r.get("source_file", "")} | {fn} |')
    if IDS.get(code) is None:
        out[-1] += ' account id missing'

with open(os.path.join(A.out, 'bank-rec-check.md'), 'w', encoding='utf-8') as f:
    f.write('| # | Code | Statement date | Statement | Imported lines | Difference | Source | Call |\n|---|---|---|---|---|---|---|---|\n')
    f.write('\n'.join(out) + '\n')
print('\n'.join(out))
print(f'\nstatements: {n}   differing: {diffs}')
sys.exit(1 if diffs else 0)
