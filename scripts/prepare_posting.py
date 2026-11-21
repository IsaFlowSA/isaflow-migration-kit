"""Turn a payload.json (from build_sync.py or takeon.py) into ready-to-send IsaFlow MCP calls, in posting order.

Each output file is the exact argument object for ONE tool call: helper keys (`_...`) stripped, a company_id guard
added, an idempotency key set, and batches cut to the tool limits. A manifest lists every call in order with the
checks to make after it, and a log template records batch ids as you go.

Usage:
  python -I prepare_posting.py --config data/company.json --payload <work>/out/payload.json --tag 2611 --out <work>/calls
         [--bank-dir <work>/out]      (folder holding bank_<code>.csv from build_sync.py; omit for a take-on)
Exit 2 = something is missing (an id, a company id); calls/stop.json lists it. Nothing is posted by this script.

Send the calls in manifest order. Where a tool has dry_run, send it with dry_run: true first, check the result
against the manifest, then send it again without dry_run.
"""
import argparse, collections, csv, io, json, os, sys
from decimal import Decimal as D

ap = argparse.ArgumentParser()
for a in ('--config', '--payload', '--tag', '--out'):
    ap.add_argument(a, required=True)
ap.add_argument('--bank-dir')
A = ap.parse_args()
os.makedirs(A.out, exist_ok=True)
CFG = json.load(open(A.config, encoding='utf-8'))
BASE = os.path.dirname(os.path.abspath(A.config))
IDS = json.load(open(os.path.join(BASE, CFG['ids']['accounts']), encoding='utf-8'))
K = CFG['isaflow_codes']
CO = CFG['company'].get('isaflow_company_id', '')
SHORT = CFG['company']['short_name']
P = json.load(open(A.payload, encoding='utf-8'))
stop = collections.defaultdict(set)
if not CO:
    stop['isaflow_company_id_missing'].add('set company.isaflow_company_id in company.json (step 03)')

def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items() if not k.startswith('_')}
    if isinstance(o, list):
        return [clean(v) for v in o]
    return o

def none_ids(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if v is None and (k.endswith('_id') or k == 'entity_id'):
                yield f'{path}.{k}'
            yield from none_ids(v, f'{path}.{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from none_ids(v, f'{path}[{i}]')

def chunks(xs, n):
    return [xs[i:i + n] for i in range(0, len(xs), n)]

manifest, n = [], 0
def emit(tool, args, check, items=None):
    global n
    n += 1
    args = dict(args, company_id=CO)
    bad = list(none_ids(args))
    if bad:
        stop['missing_id'].add(f'call {n:03d} {tool}: ' + ', '.join(bad[:5]) + (' ...' if len(bad) > 5 else ''))
    fn = f'{n:03d}_{tool}.json'
    json.dump(args, open(os.path.join(A.out, fn), 'w'), indent=1)
    manifest.append({'n': n, 'file': fn, 'tool': tool, 'items': items, 'check': check})

def gross(xs):
    return str(sum(D(x['_gross']) for x in xs))

key = lambda *p: '-'.join([SHORT, A.tag] + [str(x) for x in p])

# 1. customer invoices -> bulk create (100), then finalise each
for i, c in enumerate(chunks(P['invoices'], 100), 1):
    emit('bulk_create_customer_invoices', {'idempotency_key': key('inv', i), 'invoices': clean(c)},
         f'{len(c)} drafts created; total of their gross = {gross(c)}. Then bulk_finalize_invoices on the returned ids.', len(c))
# 2. supplier bills -> bulk create (100), then approve
for i, c in enumerate(chunks(P['bills'], 100), 1):
    emit('bulk_create_supplier_invoices', {'idempotency_key': key('bill', i), 'invoices': clean(c)},
         f'{len(c)} drafts created; total gross = {gross(c)}; none skipped. Then bulk_approve_supplier_invoices on the ids.', len(c))
# 3. credit notes -> one create each, then approve
sup_clr = IDS.get(K['supplier_clearing'])
for i, x in enumerate(P['customer_credit_notes'], 1):
    emit('create_credit_note', {'type': 'customer', 'client_id': x['party_id'], 'credit_date': x['date'], 'subtotal': x['net'],
                                'tax_rate': x['tax_rate'], 'reason': f'Sage {x["date"][:7]}', 'idempotency_key': key('ccn', i)},
         f'total = {x["_gross"]} ({x["_party"]}). Then approve_credit_note (bulk_approve_credit_notes for many).', 1)
for i, x in enumerate(P['supplier_credit_notes'], 1):
    emit('create_credit_note', {'type': 'supplier', 'supplier_id': x['party_id'], 'credit_date': x['date'], 'subtotal': x['net'],
                                'tax_rate': x['tax_rate'], 'gl_account_id': x.get('gl_account_id', sup_clr),
                                'reason': f'Sage {x["date"][:7]}', 'idempotency_key': key('scn', i)},
         f'total = {x["_gross"]} ({x["_party"]}). Then approve_credit_note.', 1)
# 4. journals -> draft, then post
for j in P['journals']:
    dr = sum(D(str(l.get('debit', 0))) for l in j['lines']); cr = sum(D(str(l.get('credit', 0))) for l in j['lines'])
    if dr != cr:
        stop['journal_imbalance'].add(f'{j["date"]} Dr {dr} Cr {cr}')
    emit('create_draft_journal', clean(j), f'draft created, debits = credits = {dr}. Then post_journal on its id.', len(j['lines']))
# 5. bank lines -> import (300 rows per call)
if A.bank_dir:
    for f in sorted(os.listdir(A.bank_dir)):
        if not (f.startswith('bank_') and f.endswith('.csv')):
            continue
        code = f[5:-4]
        bid = IDS.get(code)
        rows = list(csv.reader(open(os.path.join(A.bank_dir, f), encoding='utf-8')))
        head, body = rows[0], rows[1:]
        for i, c in enumerate(chunks(body, 300), 1):
            s = io.StringIO(); w = csv.writer(s, lineterminator='\n'); w.writerow(head); w.writerows(c)
            net = sum(D(r[2]) for r in c)
            emit('import_bank_statement', {'bank_account_id': bid, 'file_type': 'csv', 'bank_format': 'generic', 'content': s.getvalue(),
                                           'statement_date': max(r[0] for r in c), 'idempotency_key': key('bank', code, i)},
                 f'{code}: {len(c)} new, 0 duplicates (dry run first); account net moves by {net}.', len(c))
# 6. allocations (300, date order, zero lines out); 7. refunds one at a time, last
alloc = sorted([a for a in P['allocations'] if D(a['_amt']) != 0], key=lambda a: a['_date'])
for i, c in enumerate(chunks(alloc, 300), 1):
    emit('bulk_allocate_bank_transactions', {'idempotency_key': key('alloc', i), 'allocations': clean(c)},
         f'dry run: {len(c)} would post, 0 skipped. Live: keep the batch_id.', len(c))
for i, a in enumerate(sorted(P['refunds'], key=lambda a: a['_date']), 1):
    emit('bulk_allocate_bank_transactions', {'idempotency_key': key('refund', i), 'allocations': clean([a])},
         f'refund {a["_date"]} {a["_amt"]}: needs cash on account at that date (see playbook/pitfalls.md). Keep the batch_id.', 1)

json.dump(manifest, open(os.path.join(A.out, 'manifest.json'), 'w'), indent=1)
with open(os.path.join(A.out, 'posting-log.md'), 'w', encoding='utf-8') as f:
    f.write(f'# Posting log - {CFG["company"]["name"]} - {A.tag}\n\nCompany id checked with list_companies: ____ (must be {CO})\n\n'
            '| # | Tool | Items | Check | Dry run OK | Batch / document ids |\n|---|---|---|---|---|---|\n')
    for m in manifest:
        f.write(f'| {m["n"]} | {m["tool"]} | {m["items"]} | {m["check"]} | | |\n')
print(f'{len(manifest)} calls written to {A.out}')
for tool, c in collections.Counter(m['tool'] for m in manifest).items():
    print(f'  {tool}: {c}')
if stop:
    json.dump({k: sorted(v) for k, v in stop.items()}, open(os.path.join(A.out, 'stop.json'), 'w'), indent=1)
    print('STOP - resolve before posting:', json.dumps({k: sorted(v) for k, v in stop.items()}, indent=1))
    sys.exit(2)
