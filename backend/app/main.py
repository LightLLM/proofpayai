from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import hmac
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from . import core
import os

@asynccontextmanager
async def lifespan(app:FastAPI):
    core.init_db()
    yield

app=FastAPI(title='ProofPay AI Sandbox API',version='0.1.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:3000').split(',')],allow_methods=['GET','POST'],allow_headers=['Content-Type','Authorization'])

@app.middleware('http')
async def demo_write_guard(request: Request, call_next):
    """Require explicit operator access before changing requests or payments.

    In local sandbox-only mode without credentials, seeded sample workflows
    may be edited freely. Once external credentials exist, a demo token is
    mandatory and all mutating endpoints are protected.
    """
    if request.method in ('POST','PUT','PATCH','DELETE') and request.url.path.startswith('/api/'):
        token = os.getenv('DEMO_ACCESS_TOKEN', '')
        external_credentials = bool(
            os.getenv('PAYPAL_CLIENT_ID') or os.getenv('PAYPAL_CLIENT_SECRET')
            or os.getenv('AI_API_KEY')
        )
        if token:
            supplied = request.headers.get('authorization', '')
            expected = 'Bearer ' + token
            if not hmac.compare_digest(supplied, expected):
                return JSONResponse({'detail':'Demo operator access required'}, status_code=401)
        elif external_credentials:
            return JSONResponse(
                {'detail':'Set DEMO_ACCESS_TOKEN before enabling credential-backed writes'},
                status_code=503
            )
    return await call_next(request)


class RequestIn(BaseModel):
    title:str=Field(min_length=4,max_length=140)
    horsepower:float=Field(gt=0,le=100)
    voltage:int=Field(gt=0,le=1000)
    rpm:int=Field(gt=0,le=20000)
    shaft_inches:float=Field(gt=0,le=10)
    max_total_usd:float=Field(gt=0,le=100000)
class TextIn(BaseModel):
    text:str=Field(min_length=20,max_length=1500)

class ApprovalIn(BaseModel):
    offer_id:str
class CaptureIn(BaseModel):
    paypal_order_id:str

def safe(call):
    try:return call()
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@app.get('/api/health')
def health():return {'ok':True,'service':'ProofPay AI','mode':'sandbox-only'}

@app.get('/api/config')
def config():
    paypal=core.PayPalClient()
    return {'paypal_configured':paypal.configured,'paypal_client_id':paypal.client_id,'ai_configured':bool(os.getenv('AI_BASE_URL') and os.getenv('AI_MODEL')),'sandbox_only':True}

@app.get('/api/requests')
def requests():return core.list_requests()

@app.post('/api/requests')
def create_request(payload:RequestIn):
    req={'type':'motor','horsepower':payload.horsepower,'voltage':payload.voltage,'rpm':payload.rpm,'shaft_inches':payload.shaft_inches,'max_total_usd':payload.max_total_usd}
    with core.connect() as db:rid=core.add_request(db,payload.title,req)
    return {'id':rid,'status':'NEW'}

@app.get('/api/requests/{rid}')
def request(rid:str):
    with core.connect() as db:rec=safe(lambda:core.get_request(db,rid))
    return {**rec,'offers':core.ranked_offers(rec['requirement']) if rec['status']!='NEW' else [],'audit':core.get_history(rid),'order':next((o for o in core.get_orders() if o['request_id']==rid),None)}

@app.post('/api/requests/{rid}/analyze')
async def analyze(rid:str):
    try:return await core.analyze(rid)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@app.post('/api/requests/{rid}/approve')
def approve(rid:str,payload:ApprovalIn):return safe(lambda:core.approve(rid,payload.offer_id))

@app.post('/api/requests/{rid}/paypal/create-order')
async def paypal_create(rid:str):
    try:return await core.create_paypal_order(rid)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    except Exception as exc:
        import httpx
        if isinstance(exc,httpx.HTTPError):raise HTTPException(502,'PayPal sandbox API request failed; check credentials and seller account') from exc
        raise

@app.post('/api/requests/{rid}/paypal/capture')
async def paypal_capture(rid:str,payload:CaptureIn):
    try:return await core.capture_paypal_order(rid,payload.paypal_order_id)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    except Exception as exc:
        import httpx
        if isinstance(exc,httpx.HTTPError):raise HTTPException(502,'PayPal sandbox capture request failed; review order status') from exc
        raise

@app.get('/api/overview')
def overview():
    reqs=core.list_requests();orders=core.get_orders()
    return {'requests':len(reqs),'approved':sum(x['status'] in ('APPROVED','ORDER_CREATED','PAID') for x in reqs),'completed':sum(x['status']=='COMPLETED' for x in orders),'total_spend_usd':round(sum(float(x['amount']) for x in orders if x['status']=='COMPLETED'),2),'orders':orders}


@app.post('/api/agent/parse-request')
async def parse_request(payload:TextIn):
    try:
        fields=await core.parse_purchase_text(payload.text)
        validated=RequestIn.model_validate(fields)
        return {'parsed':validated.model_dump(),'source':'AI model — review all fields before creating purchase'}
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc
    except Exception as exc:
        from pydantic import ValidationError
        if isinstance(exc,ValidationError):raise HTTPException(422,'AI extracted invalid specification; provide explicit technical values') from exc
        raise
