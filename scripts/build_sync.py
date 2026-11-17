"""Build IsaFlow payloads for one Sage One -> IsaFlow window (any company).

Method (proven on a 32-month live rebuild, Nov 2026):
  - non-bank Sage entries per party per month -> one invoice / bill / credit note per party, month and VAT rate,
    to a clearing account, then a month-end journal clears it to Sage's real accounts;
  - every other non-bank Sage entry -> the same month-end journal;
  - bank, card and petty-cash lines -> one CSV per IsaFlow bank account + a 1:1 allocation payload.
With --prev-gl / --prev-bank it also picks up Sage edits dated BEFORE --from (lines added or removed since the
previous export) and books the delta in the month the Sage line is dated.

Everything company-specific is in the company's settings file (templates/company.json):
account map, bank accounts, control/VAT/forex account names, party-name fixes, IsaFlow ids.

Usage:
  python -I build_sync.py --config COMPANY.json --gl GL.csv --bank BANK.json --from 2026-11-01 --to 2026-11-30
         --tag 2611 --out DIR [--prev-gl OLD_GL.csv --prev-bank OLD_BANK.json]
Exit 2 = something needs a decision before posting; DIR/stop.json lists it. Nothing is posted by this script.
"""
import argparse, calendar, collections, csv, itertools, json, math, os, re, sys
from datetime import date, datetime
from decimal import Decimal as D, ROUND_HALF_UP

ap = argparse.ArgumentParser()
for a in ('--config', '--gl', '--bank', '--from', '--to', '--tag', '--out'):
    ap.add_argument(a, required=True)
ap.add_argument('--prev-gl'); ap.add_argument('--prev-bank')
A = ap.parse_args()
START, END = date.fromisoformat(getattr(A, 'from')), date.fromisoformat(A.to)
OUT = A.out; os.makedirs(OUT, exist_ok=True)
C = D('0.01')

CFG = json.load(open(A.config, encoding='utf-8'))
BASE = os.path.dirname(os.path.abspath(A.config))
def load_ids(key):
    return json.load(open(os.path.join(BASE, CFG['ids'][key]), encoding='utf-8'))
IDS, CUST, SUP = load_ids('accounts'), load_ids('customers'), load_ids('suppliers')
MAP = CFG['account_map']
S = CFG['sage']
K = CFG['isaflow_codes']
BANKS = set(S['bank_accounts'])
TRANSFER = S['transfer_account']
AR, AP = S['ar_control'], S['ap_control']
VATACC = set(S['vat_accounts'])
FX = set(S['forex_accounts'])
FIX = CFG.get('party_fixes', {})
OVR = {(o['account'], o['date']): o['code'] for o in CFG.get('line_overrides', [])}

def money(s):
    s = re.sub(r'[R ,]', '', s or '')
    return D(s) if s not in ('', '-') else D(0)

def q(x):
    return x.quantize(C, ROUND_HALF_UP)

stop = collections.defaultdict(set)

def code_of(acct, d=None):
    if d is not None and (acct, d.isoformat()) in OVR:
        return OVR[(acct, d.isoformat())]
    if acct in S['bank_accounts']:
        return S['bank_accounts'][acct]
    if acct not in MAP:
        stop['unmapped_sage_account'].add(acct)
        return K['suspense']
    return MAP[acct]

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

# ---------- GL rows: the window, plus back-dated Sage edits since the previous export ----------
def read_gl(fn):
    rows = []
    for x in csv.DictReader(open(fn, encoding='utf-8-sig')):
        if x['Date'] == 'OPENING':
            continue
        x['d'] = datetime.strptime(x['Date'], '%d/%m/%Y').date()
        x['amt'] = money(x['Debit']) - money(x['Credit'])
        rows.append(x)
    return rows

FIELDS = ('Account', 'Date', 'Party', 'Reference', 'Type', 'Description', 'Debit', 'Credit')
def rkey(x):
    return tuple(x[f] for f in FIELDS)

new_gl = read_gl(A.gl)
REFPARTY = {}
for x in new_gl:   # all dates: a forex line in the window can belong to an older invoice
    if x['Account'] == AR and x['Party']:
        REFPARTY.setdefault(x['Reference'], norm_party(x['Party'], 'customer'))

gl = [x for x in new_gl if START <= x['d'] <= END]
delta = []
if A.prev_gl:
    old_gl = [x for x in read_gl(A.prev_gl) if x['d'] < START]
    old = collections.Counter(rkey(x) for x in old_gl)
    new = collections.Counter(rkey(x) for x in new_gl if x['d'] < START)
    proto = {rkey(x): x for x in old_gl}
    proto.update({rkey(x): x for x in new_gl if x['d'] < START})
    for k in sorted(set(old) | set(new)):   # sorted: stable output across runs
        n = new[k] - old[k]
        for _ in range(abs(n)):
            x = dict(proto[k]); x['amt'] = x['amt'] if n > 0 else -x['amt']; x['delta'] = 'added' if n > 0 else 'removed'
            delta.append(x)
    json.dump([{f: x[f] for f in FIELDS} | {'delta': x['delta']} for x in delta],
              open(os.path.join(OUT, 'sage_backdated_edits.json'), 'w'), indent=1)

groups = collections.defaultdict(list)
for x in gl + delta:
    groups[(x['d'], x['Reference'], x['Type'])].append(x)

def month_of(d):
    return date(d.year, d.month, 1)

journal = collections.defaultdict(lambda: collections.defaultdict(D))
docs = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(D)))
bank_groups = []
for key, rows in groups.items():
    d, ref, typ = key
    if any(r['Account'] in BANKS or r['Account'] == TRANSFER for r in rows):
        bank_groups.append((key, rows))
        continue
    m = month_of(d)
    ctrl = [r for r in rows if r['Account'] in (AR, AP)]
    if not ctrl and rows and all(r['Account'] in FX for r in rows) and ref in REFPARTY:
        # Sage files the realised forex line under the invoice reference; its other leg is the debtor
        fx = sum(r['amt'] for r in rows)
        b = docs[m][('customer', REFPARTY[ref])]
        b['g0p' if -fx >= 0 else 'g0m'] += abs(fx)
        b['acc:' + K['forex']] += fx
        continue
    if not ctrl:
        for r in rows:
            journal[m][code_of(r['Account'], d)] += r['amt']
        continue
    if any(not r['Party'].strip() for r in ctrl):
        # e.g. Sage's forex revaluation posts to the debtor control with no customer: needs a judgement, not a document
        stop['control_line_without_party'].add(f"{d} {ref} {typ} " + '; '.join(f"{r['Account']} {r['Description']} {r['amt']}" for r in rows))
        continue
    by_party = collections.defaultdict(list)
    for r in ctrl:
        kind = 'customer' if r['Account'] == AR else 'supplier'
        by_party[(kind, norm_party(r['Party'], kind))].append(r)
    if len(by_party) > 1:
        stop['multi_party_group'].add(f'{d} {ref} {typ}')
        continue
    (kind, party), crs = next(iter(by_party.items()))
    gross = sum(r['amt'] for r in crs) - sum(r['amt'] for r in rows)   # absorb Sage forex/rounding imbalance into the control leg
    vat = sum(r['amt'] for r in rows if r['Account'] in VATACC)
    b = docs[m][(kind, party)]
    inc = gross if kind == 'customer' else -gross
    vg = min(q(abs(vat) / D('0.15') * D('1.15')) if vat != 0 else D(0), abs(gross))
    if inc >= 0:
        b['g15p'] += vg; b['g0p'] += abs(gross) - vg
    else:
        b['g15m'] += vg; b['g0m'] += abs(gross) - vg
    b['vat'] += vat
    for r in rows:
        if r['Account'] not in (AR, AP) and r['Account'] not in VATACC:
            b['acc:' + code_of(r['Account'], d)] += r['amt']

# ---------- documents + month-end journals ----------
def r2(x): return x.quantize(C, ROUND_HALF_UP)
def vat15(n): return r2(n * D('0.15'))
def jsvat(n):   # IsaFlow's per-line VAT rounding on supplier bills
    lt = math.floor(float(n) * 100 + 0.5) / 100
    return D(str(math.floor(lt * 15 / 100 * 100 + 0.5) / 100)).quantize(C)

def split(G, vat=vat15):
    if G <= 0: return D(0), D(0), G
    base = r2(G / D('1.15')); best = None
    for k in range(-5, 6):
        N = base + C * k
        if N <= 0: continue
        t = N + vat(N)
        if t == G: return N, vat(N), D(0)
        if t < G and (best is None or t > best[0] + best[1]): best = (N, vat(N))
    N, V = best
    return N, V, G - N - V

def doc_date(m):   # window months: first day inside the window; back-dated months: the 1st
    return max(m, START).isoformat() if m >= month_of(START) else m.isoformat()

def jnl_date(m):   # window months: month end, capped at --to; back-dated months: month end
    last = date(m.year, m.month, calendar.monthrange(m.year, m.month)[1])
    return min(last, END).isoformat() if m >= month_of(START) else last.isoformat()

out_docs, journals = [], {}
for m in sorted(set(docs) | set(journal)):
    J = collections.defaultdict(D)
    for code, a in journal[m].items():
        J[code] += a
    dd = doc_date(m)
    for (kind, party), b in docs[m].items():
        if party not in (CUST if kind == 'customer' else SUP):
            stop['unknown_' + kind].add(party)
        for p_, m_ in (('g15p', 'g15m'), ('g0p', 'g0m')):   # net within the month, per VAT rate (balance level)
            net_ = b.get(p_, D(0)) - b.get(m_, D(0))
            b[p_], b[m_] = (net_, D(0)) if net_ >= 0 else (D(0), -net_)
        vat_isa = D(0); clr = D(0)
        for sign, g15, g0 in ((1, b.get('g15p', D(0)), b.get('g0p', D(0))), (-1, b.get('g15m', D(0)), b.get('g0m', D(0)))):
            N, V, rem = split(g15, jsvat if (kind == 'supplier' and sign == 1) else vat15)
            g0 = g0 + rem
            if kind == 'customer':
                if sign == 1:
                    if N > 0: out_docs.append(dict(k='inv', p=party, d=dd, n=str(N), rate=15, g=str(N + V))); vat_isa -= V; clr += N
                    if g0 > 0: out_docs.append(dict(k='inv', p=party, d=dd, n=str(g0), rate=0, g=str(g0))); clr += g0
                else:
                    if N > 0: out_docs.append(dict(k='ccn', p=party, d=dd, n=str(N), rate=15, g=str(N + V))); vat_isa += V; J[K['sales']] -= N
                    if g0 > 0: out_docs.append(dict(k='ccn', p=party, d=dd, n=str(g0), rate=0, g=str(g0))); J[K['sales']] -= g0
            else:
                if sign == 1:
                    lines = []
                    if N > 0: lines.append((str(N), 15))
                    if g0 > 0: lines.append((str(g0), 0))
                    if lines: out_docs.append(dict(k='bill', p=party, d=dd, lines=lines, g=str(N + V + g0))); vat_isa += V; clr -= (N + g0)
                else:
                    if N > 0: out_docs.append(dict(k='scn', p=party, d=dd, n=str(N), rate=15, g=str(N + V))); vat_isa -= V; clr += N
                    if g0 > 0: out_docs.append(dict(k='scn', p=party, d=dd, n=str(g0), rate=0, g=str(g0))); clr += g0
        J[K['customer_clearing'] if kind == 'customer' else K['supplier_clearing']] += clr
        for k, v in b.items():
            if k.startswith('acc:'):
                J[k[4:]] += v
        J[K['vat_control']] += b.get('vat', D(0)) - vat_isa
    if sum(J.values()) != 0:
        stop['journal_imbalance'].add(f'{m} {sum(J.values())}')
    lines = {k: v for k, v in J.items() if v != 0}
    if lines:
        journals[jnl_date(m)] = lines

# ---------- bank lines ----------
def read_bank(fn):
    return [x for x in json.load(open(fn))['rows'] if x['acct'] != TRANSFER]

BK = ('acct', 'date', 'payee', 'desc', 'ref', 'type', 'alloc', 'amt')
bankrows = [x for x in read_bank(A.bank) if START.isoformat() <= x['date'] <= END.isoformat()]
if A.prev_bank:
    oldb = collections.Counter(tuple(x[k] for k in BK) for x in read_bank(A.prev_bank) if x['date'] < START.isoformat())
    newb = [x for x in read_bank(A.bank) if x['date'] < START.isoformat()]
    seen = collections.Counter()
    for x in newb:
        k = tuple(x[f] for f in BK); seen[k] += 1
        if seen[k] > oldb[k]:
            x['backdated'] = True; bankrows.append(x)
    gone = oldb - collections.Counter(tuple(x[k] for k in BK) for x in newb)
    if gone:   # a bank line Sage deleted is already imported in IsaFlow: fix by hand, never auto-reverse
        stop['sage_deleted_bank_line'] |= {' | '.join(map(str, k)) for k in gone.elements()}

gl_vat = collections.defaultdict(D)
for (d, ref, typ), rows in bank_groups:
    gl_vat[(d.isoformat(), ref, typ)] += sum(r['amt'] for r in rows if r['Account'] in VATACC)

alloc, csvs, seq = [], collections.defaultdict(list), collections.Counter()
by_grp = collections.defaultdict(list)
for x in bankrows:
    by_grp[(x['date'], x['ref'], x['type'])].append(x)
for (dt, ref, typ_), rows in sorted(by_grp.items()):
    vtot = gl_vat.get((dt, ref, typ_), D(0))
    calc = [q(abs(D(str(r['amt']))) * 15 / 115) for r in rows]
    flags = [False] * len(rows)
    if vtot != 0:   # which account lines carry Sage's VAT: the combination whose 15/115 sums to the GL VAT
        acct_rows = [i for i, r in enumerate(rows) if r['type'] in ('Account Payment', 'Account Receipt')]
        signed = {i: (calc[i] if D(str(rows[i]['amt'])) < 0 else -calc[i]) for i in acct_rows}
        found = None
        for k in range(len(acct_rows), 0, -1):
            for comb in itertools.combinations(acct_rows, k):
                if sum(signed[i] for i in comb) == vtot:
                    found = comb; break
            if found: break
        if found:
            for i in found: flags[i] = True
        elif not any(r['type'] in ('VAT Payment', 'VAT Refund') for r in rows):
            stop['vat_unresolved'].add(f'{dt} {ref[:40]} {vtot}')
    for i, r in enumerate(rows):
        code = code_of(r['acct'])
        seq[code] += 1
        our = f'S{code}-{A.tag}-{seq[code]:04d}'   # e.g. S1110-2611-0001; the tag keeps refs unique across syncs
        amt = D(str(r['amt']))
        # ref suffix on every description: IsaFlow's import dedupe ignores balance across imports
        csvs[code].append((r['date'], f"{(r['desc'] or r['ref'])[:100]} {our}", amt, D(str(r['bal'])), our))
        t, bid = r['type'], IDS.get(code)
        if bid is None:
            stop['account_id_missing'].add(code)
        if t in ('Transfer In', 'Transfer Out'):
            a = dict(alloc_type='account', contra_account_id=IDS.get(K['interbank']), vat_code='none')
        elif t in ('Supplier Payment', 'Customer Receipt'):
            kind = 'supplier' if t == 'Supplier Payment' else 'customer'
            ids = SUP if kind == 'supplier' else CUST
            p = norm_party(r['alloc'], kind)
            if p not in ids:
                stop['unknown_' + kind].add(p)
            a = dict(alloc_type=kind, entity_id=ids.get(p))
            # refunds (supplier money in / customer money out) need cash on account: run them last, singly
            a['_refund'] = (kind == 'supplier' and amt > 0) or (kind == 'customer' and amt < 0)
        elif t in ('VAT Payment', 'VAT Refund'):
            a = dict(alloc_type='account', contra_account_id=IDS.get(K['vat_control']), vat_code='none')
        else:
            a = dict(alloc_type='account', contra_account_id=IDS.get(code_of(r['alloc'])), vat_code='standard' if flags[i] else 'none')
        a.update(bank_reference=our, bank_account_id=bid, _amt=str(amt), _date=r['date'], _backdated=r.get('backdated', False))
        alloc.append(a)

# ---------- write ----------
for code, rows in csvs.items():
    rows.sort(key=lambda t: (t[0], t[4]))
    with open(os.path.join(OUT, f'bank_{code}.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['Date', 'Description', 'Amount', 'Balance', 'Reference'])
        for dt, desc, amt, bal, our in rows:
            w.writerow([dt, desc, f'{amt:.2f}', f'{bal:.2f}', our])

def jlines(m, ls):
    out = []
    for code, v in sorted(ls.items()):
        if code not in IDS:
            stop['account_id_missing'].add(code); continue
        out.append({'account_id': IDS[code], 'description': f'Sage {m[:7]} non-bank movements ({code})',
                    'debit' if v > 0 else 'credit': float(abs(v))})
    return out

short = CFG['company']['short_name']
seq_b = collections.Counter()
payload = {'invoices': [], 'bills': [], 'customer_credit_notes': [], 'supplier_credit_notes': [], 'journals': [], 'allocations': [], 'refunds': []}
for d in sorted(out_docs, key=lambda d: (d['d'], d['k'], d['p'])):
    if d['k'] == 'inv':
        payload['invoices'].append({'customer_id': CUST.get(d['p']), 'invoice_date': d['d'], 'due_date': d['d'], 'tax_rate': d['rate'],
            'items': [{'description': 'Sage ' + d['d'][:7], 'unit_price': float(d['n']), 'quantity': 1, 'gl_account_id': IDS.get(K['customer_clearing'])}],
            '_party': d['p'], '_gross': d['g']})
    elif d['k'] == 'bill':
        seq_b[(d['p'], d['d'])] += 1
        payload['bills'].append({'supplier_id': SUP.get(d['p']), 'invoice_number': f"SAGE-{d['d'][:7]}-{A.tag}-{seq_b[(d['p'], d['d'])]}",
            'invoice_date': d['d'], 'due_date': d['d'], 'tax_rate': 15,
            'lines': [{'description': 'Sage ' + d['d'][:7], 'quantity': 1, 'unit_price': float(n), 'tax_rate': r, 'gl_account_id': IDS.get(K['supplier_clearing'])}
                      for n, r in d['lines']],
            '_party': d['p'], '_gross': d['g']})
    else:
        lst = 'customer_credit_notes' if d['k'] == 'ccn' else 'supplier_credit_notes'
        payload[lst].append({'party_id': (CUST if d['k'] == 'ccn' else SUP).get(d['p']), 'date': d['d'], 'net': float(d['n']),
                             'tax_rate': d['rate'], '_party': d['p'], '_gross': d['g']})
for dl, ls in sorted(journals.items()):
    payload['journals'].append({'date': dl, 'memo': f'Sage sync {A.tag} {dl[:7]}: non-bank GL movements, clearing to Sage accounts',
                                'idempotency_key': f'{short}-sync-{A.tag}-jnl-{dl[:7]}', 'lines': jlines(dl, ls)})
for a in alloc:
    (payload['refunds'] if a.pop('_refund', False) else payload['allocations']).append(a)
json.dump(payload, open(os.path.join(OUT, 'payload.json'), 'w'), indent=1)

summary = {'company': CFG['company']['name'], 'window': [START.isoformat(), END.isoformat()], 'tag': A.tag,
           'backdated_gl_lines': len(delta), 'backdated_bank_lines': sum(1 for a in alloc if a['_backdated']),
           'docs': dict(collections.Counter(d['k'] for d in out_docs)), 'journals': len(journals),
           'bank_lines': {k: len(v) for k, v in sorted(csvs.items())},
           'bank_net': {k: str(q(sum(t[2] for t in v))) for k, v in sorted(csvs.items())},
           'allocations': len(payload['allocations']), 'refunds': len(payload['refunds'])}
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)
print(json.dumps(summary, indent=1))
if stop:
    json.dump({k: sorted(v) for k, v in stop.items()}, open(os.path.join(OUT, 'stop.json'), 'w'), indent=1)
    print('STOP - resolve before posting:', json.dumps({k: sorted(v) for k, v in stop.items()}, indent=1))
    sys.exit(2)
