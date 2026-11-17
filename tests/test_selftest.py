"""Self-test on synthetic data (no real company data). Run: python -I tests/test_selftest.py

One month: a customer invoice with VAT, a supplier bill with VAT, the customer's receipt and a bank charge.
Checks build_sync.py produces the expected documents, a balanced month-end journal and the bank lines,
and that scaffold.py builds a company folder without overwriting.
"""
import csv, json, os, subprocess, sys, tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = [sys.executable, '-I']
fails = []

def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name)
    if not cond:
        fails.append(name)

with tempfile.TemporaryDirectory() as t:
    gl = os.path.join(t, 'gl.csv')
    rows = [
        ('Trade Receivables', '01/03/2026', 'Acme', 'INV1', 'Tax Invoice', 'Sale', 'R 1,150.00', ''),
        ('Sales', '01/03/2026', 'Acme', 'INV1', 'Tax Invoice', 'Sale', '', 'R 1,000.00'),
        ('VAT Payable', '01/03/2026', 'Acme', 'INV1', 'Tax Invoice', 'Sale', '', 'R 150.00'),
        ('Trade Payables', '05/03/2026', 'Supplier Co', 'B1', 'Supplier Invoice', 'Stock', '', 'R 575.00'),
        ('Purchases', '05/03/2026', 'Supplier Co', 'B1', 'Supplier Invoice', 'Stock', 'R 500.00', ''),
        ('VAT Payable', '05/03/2026', 'Supplier Co', 'B1', 'Supplier Invoice', 'Stock', 'R 75.00', ''),
        ('Bank Main', '10/03/2026', 'Acme', 'R1', 'Customer Receipt', 'Receipt', 'R 1,150.00', ''),
        ('Trade Receivables', '10/03/2026', 'Acme', 'R1', 'Customer Receipt', 'Receipt', '', 'R 1,150.00'),
        ('Bank Main', '15/03/2026', '', 'C1', 'Account Payment', 'Fees', '', 'R 50.00'),
        ('Bank Charges', '15/03/2026', '', 'C1', 'Account Payment', 'Fees', 'R 50.00', ''),
    ]
    with open(gl, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['Account', 'Date', 'Party', 'Reference', 'Type', 'Description', 'Debit', 'Credit', 'Balance'])
        for r in rows: w.writerow(list(r) + [''])
    bank = os.path.join(t, 'bank.json')
    json.dump({'opening': {'Bank Main': 0.0}, 'rows': [
        dict(acct='Bank Main', date='2026-03-10', payee='Acme', desc='Receipt', ref='R1', type='Customer Receipt', alloc='Acme', amt=1150.0, bal=1150.0),
        dict(acct='Bank Main', date='2026-03-15', payee='', desc='Fees', ref='C1', type='Account Payment', alloc='Bank Charges', amt=-50.0, bal=1100.0)]},
        open(bank, 'w'))
    codes = ['1110', '1150', '1175', '1190', '4000', '4100', '4980', '5000', '5700', '5980', '6110']
    json.dump({c: f'id-{c}' for c in codes}, open(os.path.join(t, 'account_ids.json'), 'w'))
    json.dump({'Acme': 'cust-acme'}, open(os.path.join(t, 'customer_ids.json'), 'w'))
    json.dump({'Supplier Co': 'sup-co'}, open(os.path.join(t, 'supplier_ids.json'), 'w'))
    cfg = json.load(open(os.path.join(KIT, 'templates', 'company.json'), encoding='utf-8'))
    cfg['company'].update(name='Test Co', short_name='test')
    cfg['sage']['bank_accounts'] = {'Bank Main': '1110'}
    cfg['account_map'] = {'Sales': '4000', 'Purchases': '5000', 'Bank Charges': '5700'}
    conf = os.path.join(t, 'company.json'); json.dump(cfg, open(conf, 'w'))
    out = os.path.join(t, 'out')
    r = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'build_sync.py'), '--config', conf, '--gl', gl, '--bank', bank,
                             '--from', '2026-03-01', '--to', '2026-03-31', '--tag', '2603', '--out', out], capture_output=True, text=True)
    check('build_sync exits 0', r.returncode == 0)
    if r.returncode == 0:
        s = json.load(open(os.path.join(out, 'summary.json')))
        p = json.load(open(os.path.join(out, 'payload.json')))
        check('one invoice, one bill', s['docs'] == {'inv': 1, 'bill': 1})
        check('invoice gross 1150.00', p['invoices'][0]['_gross'] == '1150.00')
        check('bill gross 575.00 with VAT line', p['bills'][0]['_gross'] == '575.00' and p['bills'][0]['lines'][0]['tax_rate'] == 15)
        j = p['journals'][0]['lines']
        check('month-end journal balances', abs(sum(l.get('debit', 0) - l.get('credit', 0) for l in j)) < 0.005)
        check('bank lines 2, net 1100.00', s['bank_lines'] == {'1110': 2} and s['bank_net'] == {'1110': '1100.00'})
        kinds = sorted(a['alloc_type'] for a in p['allocations'])
        check('allocations: customer receipt + account', kinds == ['account', 'customer'])
    else:
        print(r.stdout, r.stderr)

    root = os.path.join(t, 'clients')
    r1 = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'scaffold.py'), '--root', root, '--name', 'Test Co (Pty) Ltd', '--short', 'test'], capture_output=True, text=True)
    work = os.path.join(root, 'Test Co (Pty) Ltd', '04_Finance', 'Agentic_Accounting')
    check('scaffold creates the brief and settings', r1.returncode == 0 and os.path.exists(os.path.join(work, 'AGENTS.md'))
          and os.path.exists(os.path.join(work, 'data', 'company.json')))
    open(os.path.join(work, 'AGENTS.md'), 'a').write('\nkeep me\n')
    subprocess.run(PY + [os.path.join(KIT, 'scripts', 'scaffold.py'), '--root', root, '--name', 'Test Co (Pty) Ltd', '--short', 'test'], capture_output=True)
    check('scaffold never overwrites', 'keep me' in open(os.path.join(work, 'AGENTS.md')).read())

print('\nALL PASSED' if not fails else f'\n{len(fails)} FAILED')
sys.exit(1 if fails else 0)
