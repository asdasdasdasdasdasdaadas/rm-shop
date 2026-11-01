"""Empirical repeat-payment survival, conditional on time since the last RUB payment."""
from collections import defaultdict
from datetime import timedelta


def survival_curve(intervals):
    from collections import Counter
    durations=sorted(duration for duration,event in intervals)
    counts=Counter(durations)
    deaths=Counter(duration for duration,event in intervals if event)
    times=[];values=[];risk=len(durations);survival=1.0
    for duration in sorted(counts):
        survival*=1-deaths[duration]/risk
        times.append(duration);values.append(survival)
        risk-=counts[duration]
    return durations,times,values


def repeat_probability(intervals, age, horizon, curve=None):
    from bisect import bisect_right
    # Kaplan–Meier: incomplete follow-up is censored, not classified as churn.
    durations,times,values=curve if curve is not None else survival_curve(intervals)
    if len(durations)-bisect_right(durations,age)<10:
        return None
    if not durations or durations[-1]<age+horizon:
        return None
    def survival(t):
        i=bisect_right(times,t)-1
        return values[i] if i>=0 else 1.0
    initial=survival(age)
    return max(0.0,min(1.0,1-survival(age+horizon)/initial)) if initial>0 else None


def forecast(payments, candidates, now, price):
    users=defaultdict(list)
    for row in payments:
        if row['currency']=='RUB':
            users[row['telegram_id']].append(dict(row))
    intervals=[];amounts=[];last={}
    for uid,rows in users.items():
        rows.sort(key=lambda r:(r['at'],r['id']))
        last[uid]=rows[-1]['at']
        for i,row in enumerate(rows):
            following=rows[i+1] if i+1<len(rows) else None
            duration=((following['at'] if following else now)-row['at']).total_seconds()/86400
            if duration>0:
                intervals.append((duration,following is not None))
            if row['payment_number']>1 and row['amount'] is not None:
                amounts.append(int(row['amount']))
    average=sum(amounts)/len(amounts) if len(amounts)>=3 else None
    curve=survival_curve(intervals)
    result=[]
    for horizon in (7,30):
        eligible=[]
        for row in candidates:
            due=[]
            if row['balance_low'] and row['device_count']:
                due.append(max(0,int(row['balance_rub']))/(price*row['device_count']))
            if row['router_due'] and row['router_expire_at']:
                due.append(max(0,(row['router_expire_at']-now).total_seconds()/86400))
            if due and min(due)<=horizon:
                eligible.append(row)
        expected=0;covered=0
        for row in eligible:
            previous=last.get(row['telegram_id'])
            if previous is None or average is None:
                continue
            p=repeat_probability(intervals,(now-previous).total_seconds()/86400,horizon,curve)
            if p is not None:
                expected+=p;covered+=1
        complete=covered==len(eligible)
        result.append(dict(days=horizon,clients=len(eligible),covered=covered,
            expected_payments=round(expected,1) if complete else None,
            rub=round(expected*(average or 0)) if complete else None))
    return dict(periods=result,sample_intervals=len(intervals),repeat_amounts=len(amounts),
                average_repeat_rub=round(average,2) if average is not None else None)


async def report():
    from app import db
    from app.config import get_settings
    from app.finance import PAYMENTS_SQL,DUE_SQL
    now=db._utc_now();pool=db._pool_req();price=max(1,int(get_settings().vpn_day_price_rub))
    payments=await pool.fetch(PAYMENTS_SQL,now-timedelta(days=365),now)
    candidates=await pool.fetch(DUE_SQL,price,30)
    return forecast(payments,candidates,now,price)
