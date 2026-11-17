"""Compare IsaFlow's trial balance with Sage's, per IsaFlow account code, to the cent.

Usage: python -I compare_tb.py --config COMPANY.json --sage SAGE_TB.csv --isaflow ISAFLOW_TB.json
  SAGE_TB.csv      Sage One Trial Balance export (account name in column 1, Debit/Credit in columns 4-5).
  ISAFLOW_TB.json  {"1110": 151318.83, "2110": -7291408.14, ...}  signed Dr+/Cr-, built from IsaFlow's
                   trial_balance for the same date and period basis as the Sage TB.
Prints every code that differs and the net residual. Exit 1 if anything differs.
"""
import argparse, csv, json, sys, collections
from decimal import Decimal as D

ap = argparse.ArgumentParser()
ap.add_argument('--config', required=True); ap.add_argument('--sage', required=True); ap.add_argument('--isaflow', required=True)
A = ap.parse_args()
CFG = json.load(open(A.config, encoding='utf-8'))
MAP = dict(CFG['account_map']); MAP.update(CFG['sage']['bank_accounts']); MAP.update(CFG.get('tb_names', {}))
VAT_GROUP = set(CFG.get('vat_group_codes', []))

sage = collections.defaultdict(D)
for x in csv.reader(open(A.sage, encoding='utf-8-sig')):
    if len(x) >= 5 and x[0] and x[0] != 'Name':
        try:
            amt = (D(x[3]) if x[3] else D(0)) - (D(x[4]) if x[4] else D(0))
        except Exception:
            continue
        sage[MAP.get(x[0], '?' + x[0])] += amt
isa = {k: D(str(v)) for k, v in json.load(open(A.isaflow)).items()}

def grp(c):   # VAT is often split differently in the two systems; compare those accounts as one
    return 'VAT(' + '+'.join(sorted(VAT_GROUP)) + ')' if c in VAT_GROUP else c

s, i = collections.defaultdict(D), collections.defaultdict(D)
for k, v in sage.items(): s[grp(k)] += v
for k, v in isa.items(): i[grp(k)] += v
diffs = {k: i[k] - s[k] for k in sorted(set(s) | set(i)) if abs(i[k] - s[k]) >= D('0.01')}
for k, v in diffs.items():
    print(f'{k:24} isaflow {i[k]:>18,.2f}  sage {s[k]:>18,.2f}  diff {v:>16,.2f}')
print('accounts differing:', len(diffs), ' net residual:', sum(diffs.values()))
sys.exit(1 if diffs else 0)
