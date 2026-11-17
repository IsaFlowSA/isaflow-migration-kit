"""Create (or complete) a company's migration folder. Never overwrites existing files.

Usage: python -I scaffold.py --root "D:/Clients" --name "Example Trading (Pty) Ltd" --short example
Creates <root>/<name>/ with the standard layout and copies the templates into it.
"""
import argparse, os

ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True, help='folder that holds one folder per company')
ap.add_argument('--name', required=True, help="company's folder name, usually its registered name")
ap.add_argument('--short', required=True, help='short lowercase name, used in keys and the MCP server name')
A = ap.parse_args()

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(KIT, 'templates')
co = os.path.join(A.root, A.name)
work = os.path.join(co, '04_Finance', 'Agentic_Accounting')
DIRS = ['01_Corporate/CIPC', '01_Corporate/Shareholding', '01_Corporate/Compliance', '02_Tax/SARS', '03_Directors_ID',
        '04_Finance/AFS', '05_Legal', '08_To_Review'] + [
       f'04_Finance/Agentic_Accounting/{d}' for d in ('Bank Statements', 'Source Documents/Sage exports', 'Suppliers',
                                                      'Customers', 'Payroll', 'Financials', 'outputs', 'data')]
made = []
for d in DIRS:
    p = os.path.join(co, d)
    if not os.path.isdir(p):
        os.makedirs(p); made.append(d)

def place(src, dst):
    if os.path.exists(dst):
        return f'kept   {os.path.relpath(dst, co)}'
    text = open(src, encoding='utf-8').read().replace('<COMPANY NAME>', A.name).replace('<short>', A.short)
    open(dst, 'w', encoding='utf-8').write(text)
    return f'added  {os.path.relpath(dst, co)}'

log = [place(os.path.join(TPL, 'document-register.md'), os.path.join(co, '00_Document_Register.md')),
       place(os.path.join(TPL, 'company-AGENTS.md'), os.path.join(work, 'AGENTS.md')),
       place(os.path.join(TPL, 'company-CLAUDE.md'), os.path.join(work, 'CLAUDE.md')),
       place(os.path.join(TPL, 'company.json'), os.path.join(work, 'data', 'company.json')),
       place(os.path.join(TPL, 'state.json'), os.path.join(work, 'data', 'state.json'))]
for f in ('account_ids.json', 'customer_ids.json', 'supplier_ids.json'):
    p = os.path.join(work, 'data', f)
    if not os.path.exists(p):
        open(p, 'w').write('{}\n'); log.append(f'added  {os.path.relpath(p, co)}')

print('company folder:', co)
print('folders created:', len(made))
print('\n'.join(log))
print('\nNext: open your agent in', work, 'and connect IsaFlow (see templates/mcp/README.md in the kit).')
