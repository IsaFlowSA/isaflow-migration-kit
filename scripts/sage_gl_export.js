// Run on Sage One's Account Transactions report (Reports > Account Transactions, all accounts, date range set,
// report rendered as HTML: /Reports/HTMLAccountTransactionListing.aspx). Downloads the GL as CSV:
// Account,Date,Party,Reference,Type,Description,Debit,Credit,Balance  (Date dd/mm/yyyy, opening rows Date=OPENING).
// Set FILE before running.
const FILE = 'Sage_GL_life_to_date_YYYY-MM-DD.csv';
const big = [...document.querySelectorAll('table')].sort((a, b) => b.rows.length - a.rows.length)[0];
const q = s => '"' + String(s).replace(/"/g, '""') + '"';
let acct = '';
const lines = ['Account,Date,Party,Reference,Type,Description,Debit,Credit,Balance'];
for (const r of big.rows) {
  const c = [...r.cells].map(x => x.innerText.trim());
  if (c.length === 1) { acct = c[0]; continue; }
  if (c.length >= 8 && /^\d{2}\/\d{2}\/\d{4}$/.test(c[1])) {
    lines.push([acct, ...c.slice(1, 9)].map(q).join(','));
  } else if (c.length >= 4 && /^Opening Balance/.test(c[1] || '')) {
    lines.push([acct, 'OPENING', '', '', '', '', c[3] || '', c[4] || '', ''].map(q).join(','));
  }
}
const blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv' });
const a = document.createElement('a');
a.href = URL.createObjectURL(blob); a.download = FILE; document.body.appendChild(a); a.click();
'rows ' + lines.length;
