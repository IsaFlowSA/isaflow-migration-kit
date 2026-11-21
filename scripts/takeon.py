"""Build the opening (take-on) payload at the opening date chosen in step 04.

Method (proven on a live take-on, Nov 2026):
  - one journal at the opening date for every balance-sheet account; income and expense balances roll into
    retained earnings (the opening date is the first day of a financial year);
  - the debtors and creditors controls are NOT journalled: each customer gets an opening invoice (or a credit note
    if in credit) and each supplier an opening bill (or credit note if in debit), at 0% VAT, through take-on clearing
    accounts. The journal carries the other side, so both clearing accounts end at R0.00;
  - optional adjustments (e.g. signed-AFS audit adjustments that Sage never got) are added to the journal and must
    net to R0.00 between themselves.

Usage:
  python -I takeon.py --config data/company.json --tb "<Sage TB at the day before the opening date>.csv"
         --customers customers_open.csv --suppliers suppliers_open.csv --date 2024-03-01 --out <work>/takeon
         [--adjustments adjustments.json]
  customers_open.csv / suppliers_open.csv: two columns, Name,Balance - from Sage's detailed ageing at the day before
    the opening date. Customer balance: what they owe (+) or are owed (-). Supplier balance: what we owe them (+)
    or they owe us (-).
  adjustments.json: [{"code": "1139", "amount": 589.65, "why": "AFS audit adjustment"}, ...]  signed Dr+/Cr-.
Writes payload.json (same layout as build_sync.py, so prepare_posting.py handles it), summary.json and, when
something needs a decision, stop.json (exit 2). Nothing is posted by this script.
"""
import argparse, collections, csv, json, os, re, sys
from decimal import Decimal as D

ap = argparse.ArgumentParser()
for a in ('--config', '--tb', '--customers', '--suppliers', '--date', '--out'):
    ap.add_argument(a, required=True)
ap.add_argument('--adjustments')
A = ap.parse_args()
os.makedirs(A.out, exist_ok=True)

CFG = json.load(open(A.config, encoding='utf-8'))
BASE = os.path.dirname(os.path.abspath(A.config))
def load_ids(key):
    return json.load(open(os.path.join(BASE, CFG['ids'][key]), encoding='utf-8'))
IDS, CUST, SUP = load_ids('accounts'), load_ids('customers'), load_ids('suppliers')
S, K = CFG['sage'], CFG['isaflow_codes']
T = CFG.get('takeon', {})
RE = K.get('retained_earnings', '')
CUST_CLR = T.get('customer_clearing', '4990')
SUP_CLR = T.get('supplier_clearing', '5990')
BS_PREFIXES = tuple(T.get('balance_sheet_code_prefixes', ['1', '2', '3']))
FIX = CFG.get('party_fixes', {})
stop = collections.defaultdict(set)

MAP = dict(CFG['account_map']); MAP.update(S['bank_accounts']); MAP.update(CFG.get('tb_names', {}))

def money(s):
    s = re.sub(r'[R ,]', '', s or '')
    return D(s) if s not in ('', '-') else D(0)

def norm_party(name, kind):
    n = name.strip()
    for prefix, target in FIX.get('prefix', {}).items():
        if n.startswith(prefix):
            return target
    if n in FIX.get('exact', {}):
        return FIX['exact'][n]
    if kind == 'supplier':
        if n in FIX.get('supplier_exact', {}):
            return FIX['supplier_exact'][n]
        for p in FIX.get('supplier_strip_prefixes', []):
            if n.startswith(p):
                n = n[len(p):].strip()
        if FIX.get('supplier_strip_trailing_dot'):
            n = n.rstrip('.').strip()
    return n

# ---------- Sage trial balance ----------
tb = collections.defaultdict(D)
ar_tb = ap_tb = D(0)
for x in csv.reader(open(A.tb, encoding='utf-8-sig')):
    if len(x) < 5 or not x[0] or x[0] == 'Name':
        continue
    try:
        amt = money(x[3]) - money(x[4])
    except Exception:
        continue
    if amt == 0:
        continue
    name = x[0].strip()
    if name == S['ar_control']:
        ar_tb += amt; continue
    if name == S['ap_control']:
        ap_tb += amt; continue
    code = MAP.get(name)
    if code is None:
        stop['unmapped_sage_account'].add(name); continue
    if code == 'RE' or not code.startswith(BS_PREFIXES):
        code = RE or 'RE'
    tb[code] += amt
if not RE:
    stop['retained_earnings_code_missing'].add('set isaflow_codes.retained_earnings in company.json')
tb_total = sum(tb.values()) + ar_tb + ap_tb
if tb_total != 0:
    stop['sage_tb_does_not_balance'].add(str(tb_total))

# ---------- ageing -> opening documents ----------
def read_parties(fn, kind):
    out = collections.defaultdict(D)
    for x in csv.DictReader(open(fn, encoding='utf-8-sig')):
        if (x.get('Name') or '').strip():
            out[norm_party(x['Name'], kind)] += money(x.get('Balance'))
    return {k: v for k, v in out.items() if v != 0}

cust, sup = read_parties(A.customers, 'customer'), read_parties(A.suppliers, 'supplier')
for p in cust:
    if p not in CUST: stop['unknown_customer'].add(p)
for p in sup:
    if p not in SUP: stop['unknown_supplier'].add(p)
if sum(cust.values()) != ar_tb:
    stop['customer_ageing_not_equal_control'].add(f'ageing {sum(cust.values())} vs Sage control {ar_tb}')
if sum(sup.values()) != -ap_tb:
    stop['supplier_ageing_not_equal_control'].add(f'ageing {sum(sup.values())} vs Sage control {-ap_tb}')

d = A.date
payload = {'invoices': [], 'bills': [], 'customer_credit_notes': [], 'supplier_credit_notes': [], 'journals': [],
           'allocations': [], 'refunds': []}
inv_total = ccn_total = bill_total = scn_total = D(0)
for p, v in sorted(cust.items()):
    if v > 0:
        inv_total += v
        payload['invoices'].append({'customer_id': CUST.get(p), 'invoice_date': d, 'due_date': d, 'tax_rate': 0,
            'items': [{'description': 'Opening balance', 'unit_price': float(v), 'quantity': 1, 'gl_account_id': IDS.get(CUST_CLR)}],
            '_party': p, '_gross': str(v)})
    else:   # a customer credit note posts to the default sales account; the journal carries the other side
        ccn_total += -v
        payload['customer_credit_notes'].append({'party_id': CUST.get(p), 'date': d, 'net': float(-v), 'tax_rate': 0,
                                                 '_party': p, '_gross': str(-v)})
for i, (p, v) in enumerate(sorted(sup.items()), 1):
    if v > 0:
        bill_total += v
        payload['bills'].append({'supplier_id': SUP.get(p), 'invoice_number': f'TAKEON-{d}-{i}', 'invoice_date': d, 'due_date': d,
            'tax_rate': 0, 'lines': [{'description': 'Opening balance', 'quantity': 1, 'unit_price': float(v), 'tax_rate': 0,
                                      'gl_account_id': IDS.get(SUP_CLR)}], '_party': p, '_gross': str(v)})
    else:
        scn_total += -v
        payload['supplier_credit_notes'].append({'party_id': SUP.get(p), 'date': d, 'net': float(-v), 'tax_rate': 0,
                                                 'gl_account_id': IDS.get(SUP_CLR), '_party': p, '_gross': str(-v)})

# ---------- the take-on journal ----------
J = collections.defaultdict(D, tb)
J[CUST_CLR] += inv_total            # invoices credit customer clearing
J[K['sales']] -= ccn_total          # customer credit notes debit sales
J[SUP_CLR] -= bill_total - scn_total   # bills debit supplier clearing, supplier credit notes credit it
adj = json.load(open(A.adjustments, encoding='utf-8')) if A.adjustments else []
if sum(D(str(a['amount'])) for a in adj) != 0:
    stop['adjustments_do_not_net_to_zero'].add(str(sum(D(str(a['amount'])) for a in adj)))
for a in adj:
    J[a['code']] += D(str(a['amount']))
if sum(J.values()) != 0:
    stop['journal_imbalance'].add(str(sum(J.values())))
lines = []
for code, v in sorted(J.items()):
    if v == 0:
        continue
    if code not in IDS:
        stop['account_id_missing'].add(code); continue
    lines.append({'account_id': IDS[code], 'description': f'Opening balance ({code})', 'debit' if v > 0 else 'credit': float(abs(v))})
short = CFG['company']['short_name']
payload['journals'].append({'date': d, 'memo': f'Take-on at {d}: opening balances (Sage TB, debtors and creditors via clearing)',
                            'idempotency_key': f'{short}-takeon-{d}-jnl', 'lines': lines})
json.dump(payload, open(os.path.join(A.out, 'payload.json'), 'w'), indent=1)

summary = {'company': CFG['company']['name'], 'opening_date': d,
           'journal_lines': len(lines), 'journal_debits': str(sum(v for v in J.values() if v > 0)),
           'retained_earnings': str(J.get(RE, D(0))),
           'customers': {'invoices': len(payload['invoices']), 'invoice_total': str(inv_total),
                         'credit_notes': len(payload['customer_credit_notes']), 'credit_total': str(ccn_total), 'control': str(ar_tb)},
           'suppliers': {'bills': len(payload['bills']), 'bill_total': str(bill_total),
                         'credit_notes': len(payload['supplier_credit_notes']), 'credit_total': str(scn_total), 'control': str(-ap_tb)},
           'adjustments': len(adj),
           'after_posting_expect': {CUST_CLR: '0.00', SUP_CLR: '0.00', 'AR subledger = control': str(ar_tb),
                                    'AP subledger = control': str(-ap_tb)}}
json.dump(summary, open(os.path.join(A.out, 'summary.json'), 'w'), indent=1)
print(json.dumps(summary, indent=1))
if stop:
    json.dump({k: sorted(v) for k, v in stop.items()}, open(os.path.join(A.out, 'stop.json'), 'w'), indent=1)
    print('STOP - resolve before posting:', json.dumps({k: sorted(v) for k, v in stop.items()}, indent=1))
    sys.exit(2)
