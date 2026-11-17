import csv,sys,datetime as dt,collections,json
fn=sys.argv[1]
rows=list(csv.reader(open(fn,encoding='utf-8-sig')))[2:]
acct=None; out=[]; opening={}
f=lambda s: float(s.replace(',','')) if s and s.strip() else 0.0
for r in rows:
    if not r or not r[0]: continue
    if all(not c for c in r[1:]) : acct=r[0].strip(); continue
    if r[0].startswith('Opening Balance'): opening[acct]=f(r[6])-f(r[7]); continue
    if r[0].startswith('Closing') or r[0].startswith('Total'): continue
    try: d=dt.datetime.strptime(r[0].strip(),'%d/%m/%Y').date()
    except: continue
    out.append(dict(acct=acct,date=d.isoformat(),payee=r[1],desc=r[2],ref=r[3],type=r[4],alloc=r[5],amt=round(f(r[6])-f(r[7]),2),bal=f(r[8])))
json.dump(dict(opening=opening,rows=out),open(sys.argv[2],'w'))
c=collections.defaultdict(lambda:[0,0.0,None,None])
for x in out:
    k=c[x['acct']]; k[0]+=1; k[1]+=x['amt']; k[2]=k[2] or x['date']; k[3]=x['date']
for a,(n,s,d0,d1) in c.items(): print(f'{a[:45]:45} n={n:5} open={opening.get(a,0):>12,.2f} net={s:>15,.2f} close={opening.get(a,0)+s:>14,.2f} {d0}..{d1}')
