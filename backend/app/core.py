"""ProofPay's rule-bound purchasing engine. No money movement is delegated to the LLM."""
from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
import httpx
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DB_PATH = os.getenv('DATABASE_PATH', str(Path(__file__).resolve().parents[2] / 'proofpay.sqlite3'))
DEFAULT_REQUIREMENT = {'type':'motor','horsepower':3,'voltage':230,'rpm':1750,'shaft_inches':0.875,'max_total_usd':500}
OFFERS = [
 {'id':'ofs-01','vendor':'BudgetDrive Parts','title':'3 HP Industrial Motor · 460V','part':'BD-300-460','type':'motor','horsepower':3,'voltage':460,'rpm':1750,'shaft_inches':0.875,'price_usd':299,'shipping_usd':0,'lead_days':1,'approved_vendor':True,'reliability':93},
 {'id':'ofs-02','vendor':'Northline Industrial','title':'3 HP Industrial Motor · 230V','part':'NL-300-230','type':'motor','horsepower':3,'voltage':230,'rpm':1750,'shaft_inches':0.875,'price_usd':405,'shipping_usd':20,'lead_days':2,'approved_vendor':True,'reliability':98},
 {'id':'ofs-03','vendor':'Precision Motion Supply','title':'3 HP Industrial Motor · 230V','part':'PM-330-230','type':'motor','horsepower':3,'voltage':230,'rpm':1750,'shaft_inches':0.875,'price_usd':459,'shipping_usd':30,'lead_days':5,'approved_vendor':True,'reliability':96},
 {'id':'ofs-04','vendor':'Unverified Warehouse','title':'3 HP Industrial Motor · 230V','part':'UW-330-230','type':'motor','horsepower':3,'voltage':230,'rpm':1750,'shaft_inches':0.875,'price_usd':340,'shipping_usd':25,'lead_days':1,'approved_vendor':False,'reliability':75}
]

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def new_id(prefix): return f'{prefix}-{uuid.uuid4().hex[:12]}'
@contextmanager
def connect():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn=sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory=sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally: conn.close()

def init_db():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, title TEXT NOT NULL, requirement TEXT NOT NULL, status TEXT NOT NULL, selected_offer TEXT, ai_mode TEXT, ai_explanation TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE, offer_id TEXT NOT NULL, amount TEXT NOT NULL, paypal_order_id TEXT UNIQUE, capture_id TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, request_id TEXT NOT NULL, event TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL);
        ''')
        if db.execute('SELECT COUNT(*) FROM requests').fetchone()[0] == 0:
            add_request(db,'Emergency conveyor motor replacement', DEFAULT_REQUIREMENT)

def audit(db, request_id, event, details):
    db.execute('INSERT INTO audit VALUES (?,?,?,?,?)',(new_id('evt'),request_id,event,json.dumps(details,sort_keys=True),now()))

def add_request(db,title,requirement):
    rid=new_id('req'); stamp=now()
    db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?,?,?)',(rid,title,json.dumps(requirement),'NEW',None,None,None,stamp,stamp))
    audit(db,rid,'REQUEST_CREATED',{'title':title,'requirements':requirement})
    return rid

def get_request(db,rid):
    row=db.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
    if row is None: raise ValueError('Purchasing request not found')
    x=dict(row);x['requirement']=json.loads(x['requirement']);return x

def list_requests():
    with connect() as db:
        return [dict(dict(r), requirement=json.loads(r['requirement'])) for r in db.execute('SELECT * FROM requests ORDER BY created_at DESC')]

def evaluate(offer, requirement):
    issues=[]
    for field in ('type','horsepower','voltage','shaft_inches'):
        if offer[field] != requirement[field]: issues.append(f'{field.replace("_", " ")} mismatch: {offer[field]} vs {requirement[field]}')
    if abs(offer['rpm']-requirement['rpm'])>25: issues.append('RPM exceeds ±25 tolerance')
    if not offer['approved_vendor']: issues.append('supplier not on approved list')
    total=round(offer['price_usd']+offer['shipping_usd'],2)
    if total>requirement['max_total_usd']: issues.append('exceeds approved spending limit')
    # Explanatory score, only eligible offers are selectable.
    score=round(100-min(total/requirement['max_total_usd'],1)*45-min(offer['lead_days'],30)*5+offer['reliability']*.1,1)
    return dict(offer,total_usd=total,eligible=not issues,reasons=issues,score=score)

def ranked_offers(requirement):
    return sorted([evaluate(o, requirement) for o in OFFERS],key=lambda x:(not x['eligible'],-x['score']))

def offer_by_id(oid):
    x=next((o for o in OFFERS if o['id']==oid),None)
    if x is None: raise ValueError('Supplier offer not found')
    return x

async def ai_explain(req, offers):
    """Optional genuine model inference; never allowed to change eligibility or payment amount."""
    base=os.getenv('AI_BASE_URL','').rstrip('/')
    model=os.getenv('AI_MODEL','')
    key=os.getenv('AI_API_KEY','')
    eligible=[o for o in offers if o['eligible']]
    if not base or not model:
        return 'rules-only', 'Deterministic evaluation: ' + (f"{eligible[0]['vendor']} is the highest-ranked eligible offer; voltage, mechanical fit, budget and vendor approval checks passed." if eligible else 'No supplier satisfies all mandatory requirements.')
    instruction='You are an industrial procurement analyst. Explain the supplied validation results in 1-2 sentences. Do not invent facts, change eligibility, pick an ineligible offer, or authorize payments. Return plain text.'
    payload={'model':model,'temperature':0.1,'max_tokens':190,'messages':[{'role':'system','content':instruction},{'role':'user','content':json.dumps({'requirements':req,'offers':offers})}]}
    headers={'Content-Type':'application/json'}
    if key: headers['Authorization']=f'Bearer {key}'
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.post(f'{base}/chat/completions',json=payload,headers=headers)
            response.raise_for_status()
            result=response.json()['choices'][0]['message']['content'].strip()
            if not result: raise ValueError('Empty model result')
            return 'model',result[:1000]
    except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
        return 'rules-only',f'AI inference unavailable ({type(exc).__name__}); deterministic checks remain active. '

async def analyze(rid):
    with connect() as db:
        record=get_request(db,rid)
        if record['status'] not in ('NEW','ANALYZED'): raise ValueError('Request cannot be reanalyzed after approval')
        offers=ranked_offers(record['requirement'])
    ai_mode,explanation=await ai_explain(record['requirement'],offers)
    with connect() as db:
        record=get_request(db,rid)
        if record['status'] not in ('NEW','ANALYZED'): raise ValueError('Request status changed; refresh and retry')
        db.execute('UPDATE requests SET status=?, ai_mode=?, ai_explanation=?, updated_at=? WHERE id=?',('ANALYZED',ai_mode,explanation,now(),rid))
        audit(db,rid,'AGENT_ANALYZED',{'mode':ai_mode,'eligible':sum(o['eligible'] for o in offers),'total_offers':len(offers)})
    return {'request':record,'offers':offers,'ai_mode':ai_mode,'explanation':explanation}

def approve(rid,oid):
    with connect() as db:
        rec=get_request(db,rid)
        if rec['status']!='ANALYZED':raise ValueError('Request must first be analyzed and not already approved')
        offer=evaluate(offer_by_id(oid),rec['requirement'])
        if not offer['eligible']:raise ValueError('Cannot approve ineligible offer: '+', '.join(offer['reasons']))
        db.execute('UPDATE requests SET selected_offer=?, status=?, updated_at=? WHERE id=?',(oid,'APPROVED',now(),rid))
        audit(db,rid,'HUMAN_APPROVED',{'offer_id':oid,'vendor':offer['vendor'],'total_usd':offer['total_usd']})
    return {'request_id':rid,'status':'APPROVED','offer':offer}

def get_history(rid):
    with connect() as db:
        get_request(db,rid)
        return [dict(dict(r),details=json.loads(r['details'])) for r in db.execute('SELECT * FROM audit WHERE request_id=? ORDER BY rowid DESC',(rid,))]

def get_orders():
    with connect() as db:return [dict(r) for r in db.execute('SELECT * FROM orders ORDER BY rowid DESC')]

class PayPalClient:
    def __init__(self):
        self.client_id=os.getenv('PAYPAL_CLIENT_ID','')
        self.client_secret=os.getenv('PAYPAL_CLIENT_SECRET','')
        self.base='https://api-m.sandbox.paypal.com' # strictly sandbox, never live funds
    @property
    def configured(self):return bool(self.client_id and self.client_secret)
    async def token(self):
        if not self.configured:raise ValueError('PayPal sandbox credentials are not configured')
        async with httpx.AsyncClient(timeout=25) as client:
            res=await client.post(self.base+'/v1/oauth2/token',data={'grant_type':'client_credentials'},auth=(self.client_id,self.client_secret))
            res.raise_for_status();return res.json()['access_token']
    async def call(self,method,path,*,body=None,request_id=None):
        token=await self.token()
        headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','Prefer':'return=representation'}
        if request_id:headers['PayPal-Request-Id']=request_id
        async with httpx.AsyncClient(timeout=30) as client:
            res=await client.request(method,self.base+path,headers=headers,json=body)
            res.raise_for_status()
            return res.json()

async def create_paypal_order(rid, paypal=None):
    paypal=paypal or PayPalClient()
    with connect() as db:
        rec=get_request(db,rid)
        if rec['status'] not in ('APPROVED','ORDER_CREATED'):raise ValueError('Human approval required before creating a PayPal order')
        existing=db.execute('SELECT * FROM orders WHERE request_id=?',(rid,)).fetchone()
        if existing and existing['paypal_order_id']:
            return {'id':existing['paypal_order_id'],'reused':True}
        offer=evaluate(offer_by_id(rec['selected_offer']),rec['requirement'])
        if not offer['eligible']:raise ValueError('Previously approved offer no longer eligible')
        order_id=existing['id'] if existing else new_id('ord')
        if not existing:
            db.execute('INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)',(order_id,rid,offer['id'],f"{offer['total_usd']:.2f}",None,None,'PENDING',now(),now()))
        audit(db,rid,'PAYPAL_ORDER_REQUESTED',{'offer_id':offer['id'],'amount':f"{offer['total_usd']:.2f}"})
    body={'intent':'CAPTURE','purchase_units':[{'reference_id':rid,'custom_id':order_id,'description':offer['title'][:127], 'amount':{'currency_code':'USD','value':f"{offer['total_usd']:.2f}"}}]}
    result=await paypal.call('POST','/v2/checkout/orders',body=body,request_id=order_id)
    pid=result.get('id')
    if not pid:raise ValueError('PayPal did not return an order ID')
    with connect() as db:
        db.execute('UPDATE orders SET paypal_order_id=?,status=?,updated_at=? WHERE id=? AND paypal_order_id IS NULL',(pid,'CREATED',now(),order_id))
        db.execute('UPDATE requests SET status=?,updated_at=? WHERE id=?',('ORDER_CREATED',now(),rid))
        audit(db,rid,'PAYPAL_ORDER_CREATED',{'paypal_order_id':pid,'provider_status':result.get('status')})
    return {'id':pid,'status':result.get('status')}

async def capture_paypal_order(rid,pid,paypal=None):
    paypal=paypal or PayPalClient()
    with connect() as db:
        rec=get_request(db,rid)
        order=db.execute('SELECT * FROM orders WHERE request_id=?',(rid,)).fetchone()
        if not order or order['paypal_order_id']!=pid:raise ValueError('PayPal order does not match this approved purchase')
        if order['status']=='COMPLETED':return {'status':'COMPLETED','capture_id':order['capture_id'],'reused':True}
        if rec['status']!='ORDER_CREATED':raise ValueError('Purchase is not awaiting capture')
        expected=order['amount']
        idem=order['id']+'-capture'
    result=await paypal.call('POST',f'/v2/checkout/orders/{pid}/capture',body={},request_id=idem)
    captures=[c for unit in result.get('purchase_units',[]) for c in unit.get('payments',{}).get('captures',[])]
    capture=next((c for c in captures if c.get('status')=='COMPLETED' and c.get('amount',{}).get('value')==expected and c.get('amount',{}).get('currency_code')=='USD'),None)
    if result.get('status')!='COMPLETED' or capture is None or not capture.get('id'):
        with connect() as db:audit(db,rid,'PAYPAL_CAPTURE_UNVERIFIED',{'provider_status':result.get('status'),'paypal_order_id':pid})
        raise ValueError('PayPal did not confirm a completed capture with matching currency and total; payment not marked completed')
    with connect() as db:
        db.execute('UPDATE orders SET status=?,capture_id=?,updated_at=? WHERE request_id=?',('COMPLETED',capture['id'],now(),rid))
        db.execute('UPDATE requests SET status=?,updated_at=? WHERE id=?',('PAID',now(),rid))
        audit(db,rid,'PAYPAL_CAPTURE_VERIFIED',{'paypal_order_id':pid,'capture_id':capture['id'],'amount_usd':expected})
    return {'status':'COMPLETED','capture_id':capture['id'],'paypal_order_id':pid,'amount_usd':expected}


async def parse_purchase_text(text: str):
    """AI-assisted natural-language requirements intake; no defaults or automatic purchasing."""
    if not os.getenv('AI_BASE_URL') or not os.getenv('AI_MODEL'):
        raise ValueError('Configure AI_BASE_URL and AI_MODEL for genuine AI requirements extraction')
    base=os.environ['AI_BASE_URL'].rstrip('/')
    headers={'Content-Type':'application/json'}
    if os.getenv('AI_API_KEY'):headers['Authorization']='Bearer '+os.environ['AI_API_KEY']
    instructions=(
        'Convert the procurement request into exactly one JSON object with these keys: '
        'title (string), horsepower (number), voltage (integer), rpm (integer), '
        'shaft_inches (number), max_total_usd (number). Extract ONLY numbers explicitly supplied by the user. '
        'If any required numeric value is missing, set it to null. Do not guess, authorize spending, or add markdown. '
        'Output valid JSON only.'
    )
    body={'model':os.environ['AI_MODEL'],'temperature':0,'max_tokens':300,'messages':[{'role':'system','content':instructions},{'role':'user','content':text[:1500]}]}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res=await client.post(base+'/chat/completions',json=body,headers=headers)
            res.raise_for_status()
            raw=res.json()['choices'][0]['message']['content'].strip()
        if raw.startswith('```'):
            raw=raw.split('\n',1)[1].rsplit('```',1)[0].strip()
        fields=json.loads(raw)
        required=('title','horsepower','voltage','rpm','shaft_inches','max_total_usd')
        if not isinstance(fields,dict) or any(fields.get(k) is None for k in required):
            raise ValueError('AI could not extract all required fields. Include HP, voltage, RPM, shaft diameter and maximum total USD.')
        return {k:fields[k] for k in required}
    except (httpx.HTTPError,KeyError,TypeError,json.JSONDecodeError) as exc:
        raise ValueError(f'AI extraction failed ({type(exc).__name__}). Check the model endpoint and retry.') from exc
