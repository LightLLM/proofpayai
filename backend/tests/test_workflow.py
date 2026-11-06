import pytest
from fastapi.testclient import TestClient
from app import core
from app.main import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(core,'DB_PATH',str(tmp_path/'test.sqlite3'))
    with TestClient(app) as c: yield c

def rid(client):return client.get('/api/requests').json()[0]['id']

def test_health_and_seed(client):
    assert client.get('/api/health').json()['ok']
    assert len(client.get('/api/requests').json())==1

def test_rules_reject_cheaper_incompatible_and_unapproved(client):
    r=rid(client);response=client.post(f'/api/requests/{r}/analyze')
    assert response.status_code==200
    offers=response.json()['offers']
    assert offers[0]['id']=='ofs-02' and offers[0]['total_usd']==425
    assert not next(o for o in offers if o['id']=='ofs-01')['eligible']
    assert not next(o for o in offers if o['id']=='ofs-04')['eligible']
    bad=client.post(f'/api/requests/{r}/approve',json={'offer_id':'ofs-01'})
    assert bad.status_code==400
    assert client.post(f'/api/requests/{r}/approve',json={'offer_id':'ofs-02'}).status_code==200
    assert client.post(f'/api/requests/{r}/approve',json={'offer_id':'ofs-02'}).status_code==400
    assert client.get(f'/api/requests/{r}').json()['status']=='APPROVED'

def test_cannot_order_without_approval(client):
    r=rid(client)
    assert client.post(f'/api/requests/{r}/paypal/create-order').status_code==400

def test_budget_rule(client):
    req=dict(core.DEFAULT_REQUIREMENT,max_total_usd=350)
    assert all(not x['eligible'] for x in core.ranked_offers(req))

class FakePayPal:
    def __init__(self):self.calls=[]
    async def call(self,method,path,*,body=None,request_id=None):
        self.calls.append((method,path,body,request_id))
        if path=='/v2/checkout/orders':
            return {'id':'SANDBOX-ORDER-111','status':'CREATED'}
        return {'id':'SANDBOX-ORDER-111','status':'COMPLETED','purchase_units':[{'payments':{'captures':[{'id':'SANDBOX-CAPTURE-999','status':'COMPLETED','amount':{'currency_code':'USD','value':'425.00'}}]}}]}

@pytest.mark.asyncio
async def test_fake_paypal_order_and_capture(client):
    r=rid(client)
    await core.analyze(r)
    core.approve(r,'ofs-02')
    fake=FakePayPal()
    order=await core.create_paypal_order(r,fake)
    assert order['id']=='SANDBOX-ORDER-111'
    assert fake.calls[0][2]['purchase_units'][0]['amount']['value']=='425.00'
    repeat=await core.create_paypal_order(r,fake)
    assert repeat['reused'] and len(fake.calls)==1
    done=await core.capture_paypal_order(r,order['id'],fake)
    assert done['status']=='COMPLETED'
    assert (await core.capture_paypal_order(r,order['id'],fake))['reused']
    assert len(fake.calls)==2
    assert client.get(f'/api/requests/{r}').json()['status']=='PAID'
    assert any(e['event']=='PAYPAL_CAPTURE_VERIFIED' for e in core.get_history(r))

@pytest.mark.asyncio
async def test_wrong_capture_amount_never_marks_paid(client):
    r=rid(client);await core.analyze(r);core.approve(r,'ofs-02')
    fake=FakePayPal();order=await core.create_paypal_order(r,fake)
    async def forged(method,path,*,body=None,request_id=None):
        return {'status':'COMPLETED','purchase_units':[{'payments':{'captures':[{'id':'bad','status':'COMPLETED','amount':{'currency_code':'USD','value':'1.00'}}]}}]}
    fake.call=forged
    with pytest.raises(ValueError,match='did not confirm'):await core.capture_paypal_order(r,order['id'],fake)
    assert client.get(f'/api/requests/{r}').json()['status']!='PAID'

@pytest.mark.asyncio
async def test_ai_intake_requires_config(client,monkeypatch):
    monkeypatch.delenv('AI_BASE_URL',raising=False)
    monkeypatch.delenv('AI_MODEL',raising=False)
    res=client.post('/api/agent/parse-request',json={'text':'Need a 3 horsepower 230 volt 1750 rpm motor with a 0.875 inch shaft and 500 dollar ceiling.'})
    assert res.status_code==400
    assert 'Configure AI_' in res.json()['detail']

@pytest.mark.asyncio
async def test_ai_intake_extracts_validated_fields(client,monkeypatch):
    monkeypatch.setenv('AI_BASE_URL','http://example.invalid/v1')
    monkeypatch.setenv('AI_MODEL','test-model')
    class MockResponse:
        def raise_for_status(self):pass
        def json(self):return {'choices':[{'message':{'content':'{"title":"Emergency conveyor motor","horsepower":3,"voltage":230,"rpm":1750,"shaft_inches":0.875,"max_total_usd":500}'}}]}
    class FakeClient:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):return MockResponse()
    monkeypatch.setattr(core.httpx,'AsyncClient',FakeClient)
    res=client.post('/api/agent/parse-request',json={'text':'Need a 3 horsepower 230 volt 1750 rpm motor with a 0.875 inch shaft and 500 dollar ceiling.'})
    assert res.status_code==200
    assert res.json()['parsed']['shaft_inches']==0.875
