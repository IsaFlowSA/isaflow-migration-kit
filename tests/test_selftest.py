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
    codes = ['1110', '1150', '1175', '1190', '1500', '2200', '3100', '4000', '4100', '4980', '4990', '5000', '5700', '5980', '5990', '6110']
    json.dump({c: f'id-{c}' for c in codes}, open(os.path.join(t, 'account_ids.json'), 'w'))
    json.dump({'Acme': 'cust-acme'}, open(os.path.join(t, 'customer_ids.json'), 'w'))
    json.dump({'Supplier Co': 'sup-co'}, open(os.path.join(t, 'supplier_ids.json'), 'w'))
    cfg = json.load(open(os.path.join(KIT, 'templates', 'company.json'), encoding='utf-8'))
    cfg['company'].update(name='Test Co', short_name='test', isaflow_company_id='co-test')
    cfg['sage']['bank_accounts'] = {'Bank Main': '1110'}
    cfg['account_map'] = {'Sales': '4000', 'Purchases': '5000', 'Bank Charges': '5700', 'Equipment': '1500', 'Loan': '2200',
                          'VAT Payable': '1175'}
    cfg['isaflow_codes']['retained_earnings'] = '3100'
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

    # ---- prepare_posting.py on the sync output ----
    calls = os.path.join(t, 'calls')
    r = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'prepare_posting.py'), '--config', conf, '--payload', os.path.join(out, 'payload.json'),
                             '--tag', '2603', '--out', calls, '--bank-dir', out], capture_output=True, text=True)
    check('prepare_posting exits 0', r.returncode == 0)
    if r.returncode == 0:
        man = json.load(open(os.path.join(calls, 'manifest.json')))
        tools = [m['tool'] for m in man]
        check('posting order: invoices, bills, journal, bank import, allocations',
              tools == ['bulk_create_customer_invoices', 'bulk_create_supplier_invoices', 'create_draft_journal',
                        'import_bank_statement', 'bulk_allocate_bank_transactions'])
        texts = [open(os.path.join(calls, m['file'])).read() for m in man]
        check('no helper keys, company guard on every call', all('"_' not in x and '"company_id": "co-test"' in x for x in texts))
        imp = json.load(open(os.path.join(calls, man[3]['file'])))
        check('bank import carries both lines with references', len(imp['content'].strip().splitlines()) == 3
              and 'S1110-2603-0001' in imp['content'] and 'S1110-2603-0002' in imp['content'])
    else:
        print(r.stdout, r.stderr)

    # ---- takeon.py ----
    tbf = os.path.join(t, 'tb.csv')
    with open(tbf, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['Name', 'Category', 'Type', 'Debit', 'Credit'])
        for n_, dr, cr in (('Bank Main', '1000.00', ''), ('Equipment', '5000.00', ''), ('Trade Receivables', '1150.00', ''),
                           ('Trade Payables', '', '575.00'), ('Loan', '', '2000.00'), ('Retained Income', '', '3000.00'),
                           ('Sales', '', '2000.00'), ('Purchases', '425.00', '')):
            w.writerow([n_, '', '', dr, cr])
    for fn, rows_ in (('cust.csv', [('Acme', '1200.00'), ('Beta', '-50.00')]), ('sup.csv', [('Supplier Co', '600.00'), ('Sup Two', '-25.00')])):
        with open(os.path.join(t, fn), 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(['Name', 'Balance']); w.writerows(rows_)
    json.dump({'Acme': 'cust-acme', 'Beta': 'cust-beta'}, open(os.path.join(t, 'customer_ids.json'), 'w'))
    json.dump({'Supplier Co': 'sup-co', 'Sup Two': 'sup-two'}, open(os.path.join(t, 'supplier_ids.json'), 'w'))
    tko = os.path.join(t, 'takeon')
    r = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'takeon.py'), '--config', conf, '--tb', tbf, '--customers', os.path.join(t, 'cust.csv'),
                             '--suppliers', os.path.join(t, 'sup.csv'), '--date', '2026-03-01', '--out', tko], capture_output=True, text=True)
    check('takeon exits 0', r.returncode == 0)
    if r.returncode == 0:
        p = json.load(open(os.path.join(tko, 'payload.json')))
        check('takeon: 1 invoice 1200, 1 customer CN 50, 1 bill 600, 1 supplier CN 25',
              [x['_gross'] for x in p['invoices']] == ['1200.00'] and [x['_gross'] for x in p['customer_credit_notes']] == ['50.00']
              and [x['_gross'] for x in p['bills']] == ['600.00'] and [x['_gross'] for x in p['supplier_credit_notes']] == ['25.00'])
        bal = {l['account_id']: l.get('debit', 0) - l.get('credit', 0) for l in p['journals'][0]['lines']}
        check('takeon journal: P&L rolled into RE -4575, clearing legs 1200 / -575, balanced',
              bal.get('id-3100') == -4575 and bal.get('id-4990') == 1200 and bal.get('id-5990') == -575
              and bal.get('id-4100') == -50 and abs(sum(bal.values())) < 0.005)
        r2 = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'prepare_posting.py'), '--config', conf, '--payload', os.path.join(tko, 'payload.json'),
                                  '--tag', 'takeon', '--out', os.path.join(t, 'calls-takeon')], capture_output=True, text=True)
        check('prepare_posting handles the take-on (5 calls, supplier CN to clearing)', r2.returncode == 0 and
              len(json.load(open(os.path.join(t, 'calls-takeon', 'manifest.json')))) == 5 and
              json.load(open(os.path.join(t, 'calls-takeon', '004_create_credit_note.json')))['gl_account_id'] == 'id-5990')
    else:
        print(r.stdout, r.stderr)
    with open(os.path.join(t, 'sup_bad.csv'), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([['Name', 'Balance'], ['Supplier Co', '600.00']])
    r = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'takeon.py'), '--config', conf, '--tb', tbf, '--customers', os.path.join(t, 'cust.csv'),
                             '--suppliers', os.path.join(t, 'sup_bad.csv'), '--date', '2026-03-01', '--out', os.path.join(t, 'takeon-bad')],
                       capture_output=True, text=True)
    check('takeon stops when the ageing does not equal the control',
          r.returncode == 2 and 'supplier_ageing_not_equal_control' in json.load(open(os.path.join(t, 'takeon-bad', 'stop.json'))))

    # ---- map_accounts.py ----
    chartf = os.path.join(t, 'chart.json')
    json.dump([{'code': c, 'name': n_} for c, n_ in (('1110', 'Bank'), ('1175', 'VAT Control'), ('1500', 'Equipment'), ('2200', 'Loans'),
               ('3100', 'Retained Earnings'), ('4000', 'Sales'), ('4100', 'Sales Returns'), ('5000', 'Purchases'), ('5700', 'Bank Charges'),
               ('6200', 'Telephone and Internet'))], open(chartf, 'w'))
    tb2 = os.path.join(t, 'tb2.csv')
    with open(tb2, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerows([['Name', '', '', 'Debit', 'Credit'], ['Telephone & Internet', '', '', '99.00', '']])
    sugf = os.path.join(t, 'sug.json')
    r = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'map_accounts.py'), '--config', conf, '--isaflow-chart', chartf, '--gl', gl,
                             '--tb', tb2, '--out', sugf], capture_output=True, text=True)
    sug = json.load(open(sugf)) if os.path.exists(sugf) else {}
    check('map_accounts flags the unmapped account and suggests 6200', r.returncode == 1 and list(sug) == ['Telephone & Internet']
          and sug['Telephone & Internet']['suggested'] == '6200')
    if not sug:
        print(r.stdout, r.stderr)

    # ---- bank_rec_prep.py ----
    for name_, bal_, want in (('ok', '1,100.00', 0), ('bad', '1100.50', 1)):
        st = os.path.join(t, f'st_{name_}.csv')
        with open(st, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerows([['code', 'statement_date', 'closing_balance', 'source_file'], ['1110', '2026-03-31', bal_, 'synthetic.pdf']])
        r = subprocess.run(PY + [os.path.join(KIT, 'scripts', 'bank_rec_prep.py'), '--config', conf, '--bank', bank, '--statements', st,
                                 '--out', os.path.join(t, 'recs_' + name_)], capture_output=True, text=True)
        check(f'bank_rec_prep: statement {bal_} -> exit {want}', r.returncode == want)
    rec = json.load(open(os.path.join(t, 'recs_ok', '001_perform_bank_reconciliation.json')))
    check('bank rec call is a dry run on the right account', rec['dry_run'] is True and rec['bank_account_id'] == 'id-1110')

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
