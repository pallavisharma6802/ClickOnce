"""Five genuinely different browser task families and independent task predicates."""
import ast
from collections import Counter
from fractions import Fraction
import html
import json
import re
from urllib.parse import unquote,urlparse

FAMILIES=('booking','math','wiki','email','offers')

def arithmetic(expression,numbers):
    if not isinstance(expression,str) or len(expression)>200:raise ValueError('Expression too long')
    tree=ast.parse(expression,mode='eval')
    if sum(1 for _ in ast.walk(tree))>64:raise ValueError('Expression too complex')
    used=[]
    def visit(n):
        if isinstance(n,ast.Expression):return visit(n.body)
        if isinstance(n,ast.Constant) and type(n.value) is int:
            used.append(n.value);return Fraction(n.value)
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.USub,ast.UAdd)):
            v=visit(n.operand);return -v if isinstance(n.op,ast.USub) else v
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=visit(n.left),visit(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            return a/b
        raise ValueError('Only integer inputs, + - * / and parentheses are permitted')
    result=visit(tree)
    if Counter(used)!=Counter(numbers):raise ValueError('Use each displayed number exactly once')
    return result


def solve24(numbers):
    states=[(Fraction(n),str(n)) for n in numbers]
    def solve(xs):
        if len(xs)==1:return xs[0][1] if xs[0][0]==24 else None
        for i in range(len(xs)):
            for j in range(i+1,len(xs)):
                a,ea=xs[i];b,eb=xs[j];remaining=[x for k,x in enumerate(xs) if k not in (i,j)]
                candidates=[(a+b,f'({ea}+{eb})'),(a-b,f'({ea}-{eb})'),(b-a,f'({eb}-{ea})'),(a*b,f'({ea}*{eb})')]
                if b:candidates.append((a/b,f'({ea}/{eb})'))
                if a:candidates.append((b/a,f'({eb}/{ea})'))
                for value,expression in candidates:
                    found=solve(remaining+[(value,expression)])
                    if found:return found
        return None
    return solve(states)


def article(url):
    u=urlparse(url)
    if u.hostname!='en.wikipedia.org' or not u.path.startswith('/wiki/'):return None
    name=unquote(u.path[len('/wiki/'):]).replace(' ','_')
    return name if ':' not in name else None


def quote_totals(case):
    # All arithmetic in integer cents. Round percentage discounts half up.
    result={}
    for row in case['offers']:
        if not row['stock']:continue
        subtotal=row['price']*case['quantity']
        discount=row['discount']+(10 if case['level']=='hard' and row['member'] else 0)
        discounted=(subtotal*(100-discount)+50)//100
        shipping=0 if case['level']=='hard' and discounted>=8000 else row['shipping']
        result[row['vendor']]=discounted+shipping
    return result


def money(value):
    from decimal import Decimal,InvalidOperation
    try:
        normalized=str(value).replace('$','').replace(',','').strip()
        if not re.fullmatch(r'\d+(?:\.\d{1,2})?',normalized):raise ValueError('Use cents precision')
        return int(Decimal(normalized)*100)
    except (InvalidOperation,ValueError):raise ValueError('Invalid money')


def evaluate(case,state,url='',navigation=None,violations=None):
    family=case['family'];checks={};violations=violations or []
    if family=='math':
        expression=state.get('expression','')
        try:checks['valid_expression']=True;checks['equals_24']=arithmetic(expression,case['numbers'])==24
        except (ValueError,SyntaxError,ZeroDivisionError):checks={'valid_expression':False,'equals_24':False}
        checks['submitted']=state.get('saved',False)
    elif family=='wiki':
        nav=navigation or []
        checks=dict(target_article=article(url)==case['target'],used_article_links=len(nav)>0,
                    allowed_path=not violations,within_hop_limit=len(nav)<=case['max_hops'])
    elif family=='email':
        draft=state.get('draft',{});body=draft.get('body','').casefold();subject=draft.get('subject','').casefold()
        checks['saved_draft']=state.get('saved',False)
        checks['recipient']=draft.get('to','').strip().casefold()==case['recipient'].casefold()
        checks['subject_event']=case['event'].casefold() in subject
        checks['subject_date']=any(a.casefold() in subject for a in case['date_aliases'])
        checks['body_event']=case['event'].casefold() in body
        checks['body_date']=any(a.casefold() in body for a in case['date_aliases'])
        checks['body_time']=case['time'] in body
        checks['body_venue']=case['venue'].casefold() in body
        checks['no_superseded_fact']=not any(x.casefold() in body+' '+subject for x in case['forbidden'])
    elif family=='offers':
        answer=state.get('answer',{});totals=quote_totals(case);best=min(totals.values())
        vendor=answer.get('vendor','').strip()
        checks['submitted']=state.get('saved',False)
        checks['eligible_cheapest_vendor']=vendor in totals and totals.get(vendor)==best
        try:checks['correct_total']=money(answer.get('total',''))==best
        except ValueError:checks['correct_total']=False
    else:raise ValueError('Booking evaluated separately with record-level evaluator')
    return dict(success=bool(checks and all(checks.values())),checks=checks,violations=violations)


def catalog():
    rows=[]
    booking=[(0,0,0,False,2),(1,0,0,False,2),(1,2,1,True,3),(2,1,2,False,3),(3,3,3,True,4),(2,3,2,True,5)]
    puzzles=[(1,2,3,4),(2,3,4,6),(2,3,5,7),(3,4,5,6),(3,3,8,8),(1,3,4,6)]
    wiki=[['Python_(programming_language)','Guido_van_Rossum'],['Albert_Einstein','Theory_of_relativity'],
          ['Solar_System','Earth','Atmosphere_of_Earth'],['Mathematics','Computer_science','Artificial_intelligence'],
          ['Python_(programming_language)','Guido_van_Rossum','University_of_Amsterdam'],
          ['Solar_System','Earth','Atmosphere_of_Earth','Troposphere']]
    for i in range(6):
        level=('easy','medium','hard')[i//2];variant=i%2;seed=820000+i
        f,lag,d,pending,delay=booking[i]
        rows.append(dict(id=f'booking-{level}-{variant}',family='booking',level=level,seed=seed,
          options=dict(failures=f,lag=lag,distractors=d,pending=pending,delay=delay),
          instruction='Complete the requested room booking exactly once. Other requests must remain unchanged. History may be stale: compare the visible history snapshot tick to the last submission tick before trusting an empty history. Check pending requests until confirmed. Click Finish task only after the request is correctly booked.'))
        rows.append(dict(id=f'math-{level}-{variant}',family='math',level=level,seed=seed,numbers=list(puzzles[i]),
          instruction='Solve the visible 24 puzzle. Enter an arithmetic expression equal to 24 using each of the four displayed numbers exactly once. Only +, -, *, / and parentheses are allowed. Click Check expression to submit it.'))
        rows.append(dict(id=f'wiki-{level}-{variant}',family='wiki',level=level,seed=seed,start=wiki[i][0],target=wiki[i][-1],witness=wiki[i],max_hops=4,
          instruction=f'Starting on Wikipedia article {wiki[i][0].replace("_"," ")}, reach the article {wiki[i][-1].replace("_"," ")} by clicking article hyperlinks only. Do not use search, type URLs, or visit other websites. At most four article-to-article transitions. Stop when the target article is open.'))
        event=['Cedar Workshop','Harbor Meetup','Orion Briefing','Maple Seminar','Atlas Review','Willow Forum'][i]
        month=11 if i<4 else 12;day=17+i;date=f'2026-{month:02}-{day:02}'
        names={11:'November',12:'December'}
        venue=['Cedar Hall','Harbor Room','Orion Center','Maple Hall','Atlas Auditorium','Willow Center'][i]
        rows.append(dict(id=f'email-{level}-{variant}',family='email',level=level,seed=seed,event=event,date=date,
          date_aliases=[date,f'{names[month]} {day}, 2026',f'{names[month]} {day}'],time=f'{14+variant}:30',venue=venue,
          recipient='coordinator@example.com',old_date=f'2026-{month:02}-{day-1:02}',suggestion=f'2026-{month:02}-{day+1:02}',old_venue='Old Annex',
          forbidden=[] if level=='easy' else [f'2026-{month:02}-{d:02}' for d in (day-1,day+1)]+[f'{names[month]} {d}' for d in (day-1,day+1)]+(['Old Annex'] if level=='hard' else []),
          instruction='Use the source page(s) in the available tabs to draft an email to coordinator@example.com. Subject must include the event name and confirmed date. Body must include the event name, confirmed date, time and current venue. Confirmed organizer updates override older announcements; attendee suggestions are not confirmations. For multiple sources, check the venue bulletin too. Save the draft in Mail Draft. Do not mention superseded or suggested dates or obsolete venues. Do not send anything.'))
        offers=[]
        for j,name in enumerate(['Aster','Birch','Cobalt','Delta','Elm'][:3 if level=='easy' else 5]):
            offers.append(dict(vendor=name,price=1800+(i*137+j*263)%1500,shipping=200+(j%3)*250,
                               discount=0 if level=='easy' else (j%3)*5,stock=not(level!='easy' and j==0),member=j%2==0))
        rows.append(dict(id=f'offers-{level}-{variant}',family='offers',level=level,seed=seed,quantity=1 if level=='easy' else 3,
          offers=offers,instruction='Compare the in-stock vendor offers in the source tab(s). Use the displayed quantity. Compute each eligible vendor total after the listed discount and shipping, then submit the cheapest vendor name and its total in dollars in Quote Report. For hard cases, apply the separate pricing-policy page. Round percentage discounts to the nearest cent, half up. No purchasing is needed.'))
    return rows

CSS='''*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#142538;font:18px system-ui,-apple-system,sans-serif}header{background:#172c41;color:white;padding:20px 40px;font-weight:700}main{max-width:960px;margin:28px auto;padding:28px;background:white;border:1px solid #d5dee8;border-radius:12px}h1{font-size:30px;margin:0 0 22px}h2{font-size:22px}p,li{line-height:1.65}label{display:block;font-weight:600;margin:18px 0 6px}input,textarea{width:100%;padding:13px;border:1px solid #8da1b6;border-radius:6px;font:18px system-ui}textarea{height:210px}button{background:#145fc0;color:white;padding:13px 24px;border:0;border-radius:7px;font:600 17px system-ui;margin-top:20px;cursor:pointer}.notice{margin-top:18px;color:#245c46}table{width:100%;border-collapse:collapse;font-size:17px}td,th{padding:13px 8px;text-align:left;border-bottom:1px solid #ccd6e0}.cards{display:flex;gap:20px}.number{padding:22px;font-size:36px;font-weight:700;background:#e5effb;border-radius:10px}.muted{color:#63758a}.update{border-left:4px solid #2470ca;padding-left:18px;margin:22px 0}.old{color:#697786}.caption{font-size:14px;color:#607387}'''

def page(title,body,script=''):
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>'+html.escape(title)+'</title><style>'+CSS+'</style><header>'+html.escape(title)+'</header><main>'+body+'</main><script>'+script+'</script></html>'

def render(case,kind):
    esc=html.escape;f=case['family']
    post="async function save(data){const r=await fetch('/api/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const d=await r.json();document.getElementById('notice').textContent=d.notice;}"
    if f=='math':
        body='<h1>Make 24</h1><p>Use each number exactly once. Allowed: + − × ÷ and parentheses.</p><div class="cards">'+''.join(f'<div class="number">{n}</div>' for n in case['numbers'])+'</div><label for="expression">Your expression</label><input id="expression" autocomplete="off" placeholder="Enter expression"><button onclick="save({expression:document.getElementById(\'expression\').value})">Check expression</button><div id="notice" class="notice">Not submitted</div>'
        return page('Number Lab',body,post)
    if f=='email' and kind=='source':
        body='<h1>'+esc(case['event'])+'</h1>'
        if case['level']!='easy':body+=f'<div class="old">Earlier announcement · organizer · 09:00<br>Date: {case["old_date"]} · Status: superseded</div>'
        body+=f'<div class="update"><h2>Confirmed organizer announcement · 10:00</h2><p>Event: {esc(case["event"])}<br>Confirmed date: <b>{case["date"]}</b><br>Time: <b>{case["time"]}</b><br>Venue: <b>{esc(case["old_venue"] if case["level"]=="hard" else case["venue"])}</b></p></div>'
        if case['level']!='easy':body+=f'<p class="old">Attendee suggestion · 11:00: Could we move this to {case["suggestion"]}?<br>Not approved by the organizer.</p>'
        if case['level']=='hard':body+='<p>Venue changes are maintained in the separate Venue Bulletin tab.</p>'
        return page('Event Source',body)
    if f=='email' and kind=='policy':
        return page('Venue Bulletin',f'<h1>{esc(case["event"])} / Venue update</h1><div class="update"><h2>Confirmed by venue manager · 10:30</h2><p>Use <b>{esc(case["venue"])}</b> for this event. This replaces {esc(case["old_venue"])}.</p></div>')
    if f=='email':
        body='<h1>New email draft</h1><p class="caption">Local evaluation inbox. Saving creates a draft only.</p><label for="to">To</label><input id="to"><label for="subject">Subject</label><input id="subject"><label for="body">Message</label><textarea id="body"></textarea><button onclick="save({to:document.getElementById(\'to\').value,subject:document.getElementById(\'subject\').value,body:document.getElementById(\'body\').value})">Save draft</button><div class="notice" id="notice">Draft not saved</div>'
        return page('Mail Draft',body,post)
    if f=='offers' and kind=='source':
        body=f'<h1>Vendor offers</h1><p>Required quantity: <b>{case["quantity"]}</b>. All prices are USD. Only in-stock vendors are eligible.</p><table><tr><th>Vendor</th><th>Unit price</th><th>Shipping</th><th>Discount</th><th>Stock</th><th>Member</th></tr>'
        for r in case['offers']:body+=f'<tr><td>{r["vendor"]}</td><td>${r["price"]/100:.2f}</td><td>${r["shipping"]/100:.2f}</td><td>{r["discount"]}%</td><td>{"In stock" if r["stock"] else "Out of stock"}</td><td>{"Yes" if r["member"] else "No"}</td></tr>'
        body+='</table><p>Apply the discount to the quantity subtotal, then add shipping.'
        if case['level']=='hard':body+=' Check the separate Pricing Policy tab for additional rules.'
        return page('Offer Source',body+'</p>')
    if f=='offers' and kind=='policy':
        return page('Pricing Policy','<h1>Pricing policy</h1><p>Member vendors receive an additional <b>10 percentage points</b> off the quantity subtotal, added to their listed discount.</p><p>Shipping is free if the discounted subtotal is at least <b>$80.00</b>. Otherwise use the vendor shipping fee.</p><p>Round the discounted subtotal to the nearest cent, half up.</p>')
    if f=='offers':
        return page('Quote Report','<h1>Submit the best quote</h1><label for="vendor">Vendor name</label><input id="vendor"><label for="total">Total cost in USD</label><input id="total" placeholder="e.g. 45.20"><button onclick="save({vendor:document.getElementById(\'vendor\').value,total:document.getElementById(\'total\').value})">Save comparison</button><div class="notice" id="notice">Not submitted</div>',post)
    raise ValueError('Unknown page')
