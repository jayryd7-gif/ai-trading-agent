"""
key_level_test.py - Which key levels give more (and better) trades?

Compares six ways to pick the breakout levels on the last 60 days of
5-minute candles, for both markets, with the same 3-target trade management
(gold uses the 1, 2, 2 sell plan) and $1 per contract in fees. It also splits
the sessions into a first and second half: only trust a variation that does
well in both.

Run from the project folder:
    python experiments/key_level_test.py

This is a replay on past data. Results going forward can be worse.
"""
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import main as R
from data import SYMBOLS, load_from_yahoo
from key_levels import check_breakout, find_key_levels
from risk import manage_trade, new_trade

data = {k: load_from_yahoo(SYMBOLS[k], "5m", "60d") for k in R.SESSIONS}

def play(inst, sess, hi, lo, scan_from, window, confirm):
    for i,(m,c) in enumerate(sess):
        if m < scan_from: continue
        if m >= window: break
        d = check_breakout(c, hi, lo)
        if not d: continue
        entry = c.close; stop = c.low if d=="long" else c.high; j=i
        if confirm:
            if i+1>=len(sess): break
            m2,c2 = sess[i+1]
            if check_breakout(c2,hi,lo)!=d: continue
            entry=c2.close; stop=min(c.low,c2.low) if d=="long" else max(c.high,c2.high); j=i+1
        if entry==stop: continue
        t = new_trade(inst,d,round(entry,2),round(stop,2),[1,2,2] if inst=="gold" else None)
        n=t["contracts"]
        for _,l in sess[j+1:]:
            _,t = manage_trade(t,l.high,l.low)
            if t["contracts"]==0: break
        if t["contracts"]>0:
            last=sess[-1][1].close
            pts=(last-t["entry"]) if d=="long" else (t["entry"]-last)
            t["banked"]+=pts*t["point_value"]*t["contracts"]
        return t["banked"]-n
    return None

def halves(variants):
    for k,v in variants.items():
        h=len(v)//2
        a=[x for x in v[:h] if x is not None]; b=[x for x in v[h:] if x is not None]
        print(f"   {k[:40]:40s} 1st half {len(a):2d} trades ${sum(a):7.0f} | 2nd half {len(b):2d} trades ${sum(b):7.0f}")
    print()
for inst in R.SESSIONS:
    cfg=R.SESSIONS[inst]; S=R.group_into_sessions(data[inst],cfg); st=list(S)
    allc=[(R.parse_time(c.time),c) for c in data[inst]]
    variants={}
    for i in range(1,len(st)):
        s=st[i]; sess=S[s]; prev=R.previous_full_session(S,st,i,cfg)
        if prev is None: continue
        ph,pl=find_key_levels([c for _,c in S[prev]])
        def add(name,r): variants.setdefault(name,[]).append(r)
        add("A old rule: prev session H/L, confirm, 30m", play(inst,sess,ph,pl,s,s+timedelta(minutes=30),True))
        add("B prev session H/L, no confirm, 30m", play(inst,sess,ph,pl,s,s+timedelta(minutes=30),False))
        add("C prev session H/L, confirm, 120m", play(inst,sess,ph,pl,s,s+timedelta(minutes=120),True))
        orc=[c for m,c in sess if m< s+timedelta(minutes=15)]
        if len(orc)==3:
            oh,ol=find_key_levels(orc)
            add("D 15m opening range, confirm, to 90m", play(inst,sess,oh,ol,s+timedelta(minutes=15),s+timedelta(minutes=90),True))
            add("E 15m opening range, no confirm, to 90m", play(inst,sess,oh,ol,s+timedelta(minutes=15),s+timedelta(minutes=90),False))
        pre=[c for m,c in allc if s-timedelta(hours=2)<=m<s]
        if len(pre)>=12:
            qh,ql=find_key_levels(pre)
            add("F 2h pre-open range, confirm, 60m (rule now)", play(inst,sess,qh,ql,s,s+timedelta(minutes=60),True))
    halves(variants)
    print(f"\n== {inst} ({len(st)-1} sessions)")
    for k,v in variants.items():
        tr=[x for x in v if x is not None]; w=[x for x in tr if x>0]
        print(f"{k:45s} sessions {len(v):3d} trades {len(tr):3d} wins {len(w):3d} net ${sum(tr):8.0f}")
