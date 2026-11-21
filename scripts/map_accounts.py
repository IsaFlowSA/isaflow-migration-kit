"""Show which Sage accounts still need an IsaFlow code, with a suggestion for each (step 05-B).

Usage:
  python -I map_accounts.py --config data/company.json --isaflow-chart data/isaflow_chart.json
         [--gl "<Sage GL csv>"] [--tb "<Sage TB csv>" ...] [--out data/account_map_suggestions.json]
  isaflow_chart.json: [{"code": "1110", "name": "Bank - Main"}, ...] saved from IsaFlow's list_gl_accounts.
Lists: Sage accounts not in account_map (with the closest IsaFlow account by name), account_map targets that do not
exist in the IsaFlow chart, and IsaFlow codes missing from account_ids.json. Suggestions are only suggestions: the
person (or you, from the AFS and Sage's account categories) decides, and you write the choice into account_map.
Exit 1 while anything is unmapped or missing.
"""
import argparse, csv, difflib, json, os, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('--config', required=True); ap.add_argument('--isaflow-chart', required=True)
ap.add_argument('--gl'); ap.add_argument('--tb', action='append', default=[]); ap.add_argument('--out')
A = ap.parse_args()
CFG = json.load(open(A.config, encoding='utf-8'))
BASE = os.path.dirname(os.path.abspath(A.config))
IDS = json.load(open(os.path.join(BASE, CFG['ids']['accounts']), encoding='utf-8'))
S = CFG['sage']
chart = {str(x['code']): x['name'] for x in json.load(open(A.isaflow_chart, encoding='utf-8'))}

sage = set()
if A.gl:
    sage |= {x['Account'].strip() for x in csv.DictReader(open(A.gl, encoding='utf-8-sig')) if x.get('Account')}
for fn in A.tb:
    for x in csv.reader(open(fn, encoding='utf-8-sig')):
        if len(x) >= 5 and x[0] and x[0] != 'Name' and re.search(r'\d', (x[3] or '') + (x[4] or '')):
            sage.add(x[0].strip())
if not sage:
    sys.exit('give --gl and/or --tb')

handled = set(CFG['account_map']) | set(S['bank_accounts']) | set(CFG.get('tb_names', {})) | {
    S['transfer_account'], S['ar_control'], S['ap_control']}
unmapped = sorted(sage - handled)

def norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', s.lower()).split()

def suggest(name):
    best = None
    for code, cname in chart.items():
        score = difflib.SequenceMatcher(None, ' '.join(norm(name)), ' '.join(norm(cname))).ratio()
        if best is None or score > best[2]:
            best = (code, cname, score)
    return best

sug = {}
print(f'Sage accounts: {len(sage)}   mapped or handled: {len(sage) - len(unmapped)}   unmapped: {len(unmapped)}\n')
for n in unmapped:
    code, cname, score = suggest(n)
    sug[n] = {'suggested': code, 'name': cname, 'score': round(score, 2)}
    print(f'  {n[:50]:50} -> {code} {cname[:40]:40} ({score:.2f}){"  weak - decide by hand" if score < 0.6 else ""}')
bad_targets = sorted({c for c in list(CFG['account_map'].values()) + list(S['bank_accounts'].values()) if c not in chart and c != 'RE'})
missing_ids = sorted({c for c in list(CFG['account_map'].values()) + list(S['bank_accounts'].values())
                      + list(CFG['isaflow_codes'].values()) if c and c != 'RE' and c not in IDS})
if bad_targets:
    print('\naccount_map codes not in the IsaFlow chart (create them with create_gl_account):', ', '.join(bad_targets))
if missing_ids:
    print('codes missing from account_ids.json (refresh it from list_gl_accounts):', ', '.join(missing_ids))
if A.out:
    json.dump(sug, open(A.out, 'w', encoding='utf-8'), indent=1)
sys.exit(1 if unmapped or bad_targets or missing_ids else 0)
