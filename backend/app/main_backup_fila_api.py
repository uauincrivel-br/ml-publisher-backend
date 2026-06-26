import os, time, json, hashlib, re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import jwt, pandas as pd, requests
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, Session

APP_ENV=os.getenv('APP_ENV','local')
JWT_SECRET=os.getenv('JWT_SECRET','troque-este-segredo')
DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./data/mlp_enterprise.db')
MLB_REDIRECT_URI=os.getenv('MLB_REDIRECT_URI','http://localhost:8090/api/ml/callback')

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
) if DATABASE_URL.startswith('sqlite') else {})
SessionLocal=sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base=declarative_base()

class User(Base):
    __tablename__='users'
    id=Column(Integer, primary_key=True)
    email=Column(String, unique=True, index=True)
    password_hash=Column(String)
    name=Column(String, default='Operador')
    plan=Column(String, default='starter')
    created_at=Column(DateTime, default=datetime.utcnow)

class MLAccount(Base):
    __tablename__='ml_accounts'
    id=Column(Integer, primary_key=True)
    user_id=Column(Integer, index=True)
    seller_id=Column(String, index=True)
    nickname=Column(String)
    client_id=Column(String)
    client_secret=Column(String)
    access_token=Column(Text)
    refresh_token=Column(Text)
    token_user_id=Column(String)
    connected=Column(Boolean, default=False)
    updated_at=Column(DateTime, default=datetime.utcnow)

class Product(Base):
    __tablename__='products'
    id=Column(Integer, primary_key=True)
    user_id=Column(Integer, index=True)
    import_id=Column(String, index=True)
    offset=Column(Integer, index=True)
    sku=Column(String, index=True)
    title=Column(String)
    category_id=Column(String)
    price=Column(Float)
    stock=Column(Integer)
    raw_json=Column(Text)
    validation_status=Column(String, default='pending')
    validation_reason=Column(Text)
    item_id=Column(String, index=True)
    publication_status=Column(String, default='not_published')
    created_at=Column(DateTime, default=datetime.utcnow)

class PublishedItem(Base):
    __tablename__='published_items'
    id=Column(Integer, primary_key=True)
    seller_id=Column(String, index=True)
    sku=Column(String, unique=True, index=True)
    offset=Column(Integer, unique=True, index=True)
    item_id=Column(String, index=True)
    status=Column(String)
    created_at=Column(DateTime, default=datetime.utcnow)

class PublishQueue(Base):
    __tablename__='publish_queue'
    id=Column(Integer, primary_key=True)
    seller_id=Column(String, index=True)
    sku=Column(String, index=True)
    offset=Column(Integer, index=True)
    status=Column(String, default='queued')
    attempts=Column(Integer, default=0)
    last_error=Column(Text)
    created_at=Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__='audit_logs'
    id=Column(Integer, primary_key=True)
    user_id=Column(Integer, index=True)
    action=Column(String)
    sku=Column(String)
    offset=Column(Integer)
    item_id=Column(String)
    status=Column(String)
    detail=Column(Text)
    created_at=Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)
app=FastAPI(title='ML Publisher Enterprise V5 API', version='5.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

class LoginBody(BaseModel):
    email:str
    password:str
class AccountBody(BaseModel):
    seller_id:str
    client_id:str
    client_secret:str
    access_token:Optional[str]=None
    refresh_token:Optional[str]=None
class PublishBody(BaseModel):
    seller_id:str
    quantidade:int=1
    delay_seconds:int=240
    dry_run:bool=True

COLUMN_ALIASES={
    'sku':['sku','código sku','codigo sku','código','codigo','cod produto','referencia','referência'],
    'title':['título mercado livre','titulo mercado livre','titulo ml','título ml','título','titulo','produto base','produto','nome do produto','descrição curta'],
    'category_id':['categoria id mercado livre','categoria id ml','categoria id','category_id','mlb categoria','id categoria','categoria mercado livre id'],
    'category_name':['categoria mercado livre','categoria','category'],
    'price':['preço sugerido ml','preco sugerido ml','preço ml','preco ml','preço','preco','price','valor','valor venda'],
    'stock':['estoque','stock','quantidade','available_quantity','qtd'],
    'brand':['marca','brand'],
    'model':['modelo','model'],
    'ean':['ean/gtin','gtin/ean','ean','gtin','código de barras','codigo de barras'],
    'description':['descrição mercado livre limpa','descricao mercado livre limpa','descrição','descricao','description'],
}

def db_dep():
    db=SessionLocal()
    try: yield db
    finally: db.close()

def hash_pw(p): return hashlib.sha256(('mlp-v5:'+p).encode()).hexdigest()
def token_for(user:User):
    return jwt.encode({'sub':user.email,'uid':user.id,'exp':datetime.now(timezone.utc)+timedelta(days=7)}, JWT_SECRET, algorithm='HS256')
def current_user(authorization: Optional[str]=Header(None), db:Session=Depends(db_dep)):
    if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'login_required')
    try: data=jwt.decode(authorization.split(' ',1)[1], JWT_SECRET, algorithms=['HS256'])
    except Exception: raise HTTPException(401,'invalid_token')
    u=db.query(User).filter(User.id==data['uid']).first()
    if not u: raise HTTPException(401,'user_not_found')
    return u

def log(db,u,action,status,detail='', sku=None, offset=None, item_id=None):
    db.add(AuditLog(user_id=u.id, action=action, status=status, detail=detail, sku=sku, offset=offset, item_id=item_id)); db.commit()

def normalize_name(s:str)->str:
    s=str(s or '').strip().lower()
    repl=str.maketrans('áàãâäéèêëíìîïóòõôöúùûüçñ','aaaaaeeeeiiiiooooouuuucn')
    s=s.translate(repl)
    s=re.sub(r'[^a-z0-9]+',' ',s).strip()
    return s

def find_col(cols, options):
    normalized={normalize_name(c):c for c in cols}
    for opt in options:
        optn=normalize_name(opt)
        for key, original in normalized.items():
            if optn==key or optn in key:
                return original
    return None

def smart_mapping(cols):
    return {key: find_col(cols, aliases) for key, aliases in COLUMN_ALIASES.items()}

def safe_float(v):
    if v is None: return 0.0
    s=str(v).strip().replace('R$','').replace(' ','')
    if not s or s.lower() in ('nan','none'): return 0.0
    if ',' in s and '.' in s: s=s.replace('.','').replace(',','.')
    elif ',' in s: s=s.replace(',','.')
    try: return float(s)
    except Exception: return 0.0

def safe_int(v):
    try: return int(float(str(v).strip().replace(',','.')))
    except Exception: return 0

def published_skus(db:Session):
    return set([str(r.sku) for r in db.query(PublishedItem).all() if r.sku])

def published_offsets(db:Session):
    return set([int(r.offset) for r in db.query(PublishedItem).filter(PublishedItem.offset!=None).all()])

@app.get('/api/health')
def health():
    return {'status':'ok','service':'ml-publisher-enterprise-v5','environment':APP_ENV,'safe_mode':True,'publish_paused_required':True,'worker_concurrency':1}

@app.post('/api/auth/register')
def register(body:LoginBody, db:Session=Depends(db_dep)):
    exists=db.query(User).filter(User.email==body.email).first()
    if exists: raise HTTPException(400,'email_already_registered')
    u=User(email=body.email, password_hash=hash_pw(body.password), name=body.email.split('@')[0]); db.add(u); db.commit(); db.refresh(u)
    return {'token':token_for(u),'user':{'email':u.email,'plan':u.plan}}

@app.post('/api/auth/login')
def login(body:LoginBody, db:Session=Depends(db_dep)):
    u=db.query(User).filter(User.email==body.email).first()
    if not u or u.password_hash!=hash_pw(body.password): raise HTTPException(401,'invalid_credentials')
    return {'token':token_for(u),'user':{'email':u.email,'plan':u.plan}}

@app.post('/api/ml/account')
def save_account(body:AccountBody, u:User=Depends(current_user), db:Session=Depends(db_dep)):
    acc=db.query(MLAccount).filter(MLAccount.user_id==u.id, MLAccount.seller_id==body.seller_id).first() or MLAccount(user_id=u.id, seller_id=body.seller_id)
    acc.client_id=body.client_id; acc.client_secret=body.client_secret; acc.access_token=body.access_token; acc.refresh_token=body.refresh_token; acc.updated_at=datetime.utcnow()
    db.add(acc); db.commit(); log(db,u,'save_ml_account','ok',f'seller={body.seller_id}')
    return {'ok':True,'seller_id':body.seller_id,'message':'Credenciais salvas no backend seguro'}

@app.post('/api/ml/validate-token/{seller_id}')
def validate_token(seller_id:str, u:User=Depends(current_user), db:Session=Depends(db_dep)):
    acc=db.query(MLAccount).filter(MLAccount.user_id==u.id, MLAccount.seller_id==seller_id).first()
    if not acc or not acc.access_token: raise HTTPException(400,'access_token_not_configured')
    r=requests.get('https://api.mercadolibre.com/users/me', headers={'Authorization':f'Bearer {acc.access_token}'}, timeout=20)
    ok=r.status_code==200
    data=r.json() if ok else {'error':r.text[:300]}
    acc.token_user_id=str(data.get('id','')) if ok else None; acc.nickname=data.get('nickname') if ok else None; acc.connected= ok and str(data.get('id'))==str(seller_id); db.commit()
    log(db,u,'validate_token','ok' if acc.connected else 'blocked',json.dumps(data)[:1000])
    return {'status_code':r.status_code,'seller_id_informed':seller_id,'token_user_id':acc.token_user_id,'matches_seller_id':acc.connected,'nickname':acc.nickname,'raw':data}

@app.post('/api/import/upload')
def upload(file:UploadFile=File(...), u:User=Depends(current_user), db:Session=Depends(db_dep)):
    os.makedirs('/app/uploads', exist_ok=True)
    path=f'/app/uploads/{int(time.time())}_{file.filename}'
    with open(path,'wb') as f: f.write(file.file.read())
    try:
        df=pd.read_csv(path) if file.filename.lower().endswith('.csv') else pd.read_excel(path)
    except Exception as e:
        raise HTTPException(400, f'erro_lendo_planilha: {e}')
    cols=list(df.columns)
    mapping=smart_mapping(cols)
    import_id=hashlib.md5((file.filename+str(time.time())).encode()).hexdigest()[:12]
    pub_skus=published_skus(db); pub_offsets=published_offsets(db)
    seen_skus=set(); ready=pending=blocked=0; created=[]
    for idx,row in df.iterrows():
        offset=int(idx)
        sku=str(row.get(mapping['sku'],'')).strip() if mapping.get('sku') else ''
        title=str(row.get(mapping['title'],'')).strip() if mapping.get('title') else ''
        cat=str(row.get(mapping['category_id'],'')).strip() if mapping.get('category_id') else ''
        price=safe_float(row.get(mapping['price'],0)) if mapping.get('price') else 0
        stock=safe_int(row.get(mapping['stock'],0)) if mapping.get('stock') else 0
        reasons=[]
        if not sku: reasons.append('SKU ausente')
        if sku and sku in seen_skus: reasons.append('SKU repetido nesta planilha')
        if sku and sku in pub_skus: reasons.append('SKU já publicado no histórico')
        if offset in pub_offsets: reasons.append('Offset já usado no histórico')
        if not title: reasons.append('Título ausente')
        if not cat: reasons.append('Categoria ID Mercado Livre ausente')
        if price<=0: reasons.append('Preço inválido')
        if stock<0: reasons.append('Estoque inválido')
        status='ready' if not reasons else ('blocked' if any('já' in r or 'repetido' in r for r in reasons) else 'pending')
        ready += status=='ready'; pending += status=='pending'; blocked += status=='blocked'
        if sku: seen_skus.add(sku)
        p=Product(user_id=u.id, import_id=import_id, offset=offset, sku=sku, title=title, category_id=cat, price=price, stock=stock, raw_json=json.dumps(row.fillna('').to_dict(), ensure_ascii=False), validation_status=status, validation_reason='; '.join(reasons) or 'Aprovado para fila segura')
        db.add(p)
        if len(created)<10: created.append({'offset':offset,'sku':sku,'title':title,'status':status,'reason':p.validation_reason})
    db.commit(); log(db,u,'import_upload','ok',f'import_id={import_id}, rows={len(df)}, ready={ready}, pending={pending}, blocked={blocked}')
    return {'ok':True,'import_id':import_id,'rows':len(df),'ready':ready,'pending':pending,'blocked':blocked,'mapping':{k:str(v) if v is not None else None for k,v in mapping.items()}, 'preview':created}

@app.get('/api/products')
def products(import_id:Optional[str]=None, status:Optional[str]=None, limit:int=100, u:User=Depends(current_user), db:Session=Depends(db_dep)):
    q=db.query(Product).filter(Product.user_id==u.id)
    if import_id: q=q.filter(Product.import_id==import_id)
    if status: q=q.filter(Product.validation_status==status)
    rows=q.order_by(Product.offset.asc()).limit(limit).all()
    return [{'id':p.id,'offset':p.offset,'sku':p.sku,'title':p.title,'category_id':p.category_id,'price':p.price,'stock':p.stock,'status':p.validation_status,'reason':p.validation_reason,'item_id':p.item_id,'publication_status':p.publication_status} for p in rows]

@app.get('/api/continuity/next')
def continuity(import_id:Optional[str]=None, u:User=Depends(current_user), db:Session=Depends(db_dep)):
    published_rows=db.query(PublishedItem).order_by(PublishedItem.offset.desc()).all()
    last=published_rows[0] if published_rows else None
    pub_skus=[p.sku for p in published_rows if p.sku]
    q=db.query(Product).filter(Product.user_id==u.id, Product.validation_status=='ready', Product.item_id==None)
    if import_id: q=q.filter(Product.import_id==import_id)
    if pub_skus: q=q.filter(~Product.sku.in_(pub_skus))
    nextp=q.order_by(Product.offset.asc()).first()
    next_offset=(last.offset+1) if last and last.offset is not None else None
    return {'published_skus_count':len(published_rows), 'last_published': {'offset':last.offset,'sku':last.sku,'item_id':last.item_id,'status':last.status} if last else None, 'next_safe': {'offset':nextp.offset,'sku':nextp.sku,'title':nextp.title} if nextp else {'offset':next_offset,'sku':None,'title':None,'requires_product_import':True}}

@app.post('/api/continuity/import-legacy-jobs')
def import_legacy_jobs(source_url:str, u:User=Depends(current_user), db:Session=Depends(db_dep)):
    r=requests.get(source_url, timeout=30)
    if r.status_code>=300: raise HTTPException(400, f'legacy_jobs_http_{r.status_code}: {r.text[:300]}')
    data=r.json(); jobs=data.get('jobs', data if isinstance(data, list) else [])
    imported=0; ignored=0; published=[]
    for j in jobs:
        sku=str(j.get('sku','')).strip(); item_id=str(j.get('item_id','')).strip() if j.get('item_id') else ''; status=str(j.get('status','')).upper()
        if not sku or not item_id or status not in ('PUBLISHED','PUBLISHED_PAUSED','PAUSED'):
            ignored+=1; continue
        if db.query(PublishedItem).filter(PublishedItem.sku==sku).first():
            ignored+=1; continue
        p=PublishedItem(seller_id=str(j.get('seller_id') or ''), sku=sku, offset=None, item_id=item_id, status='paused')
        db.add(p); imported+=1; published.append({'sku':sku,'item_id':item_id,'status':status})
    db.commit(); log(db,u,'import_legacy_jobs','ok',f'imported={imported}, ignored={ignored}, source={source_url}')
    return {'ok':True,'imported':imported,'ignored':ignored,'published':published[:50]}

@app.post('/api/publish/start')
def publish(body:PublishBody, u:User=Depends(current_user), db:Session=Depends(db_dep)):
    acc=db.query(MLAccount).filter(MLAccount.user_id==u.id, MLAccount.seller_id==body.seller_id).first()
    if not acc or not acc.access_token: raise HTTPException(400,'token_not_configured')
    if body.quantidade<1 or body.quantidade>10: raise HTTPException(400,'quantidade_deve_ser_1_a_10')
    pub_skus=published_skus(db)
    items=db.query(Product).filter(Product.user_id==u.id, Product.validation_status=='ready', Product.item_id==None).order_by(Product.offset.asc()).limit(body.quantidade).all()
    results=[]
    for p in items:
        if p.sku in pub_skus:
            p.validation_status='blocked'; p.validation_reason='SKU já publicado no histórico PublishedItem'; db.commit(); continue
        if body.dry_run:
            p.publication_status='dry_run_ready'; db.commit(); log(db,u,'publish_dry_run','ok','Simulação segura',p.sku,p.offset)
            results.append({'sku':p.sku,'offset':p.offset,'status':'DRY_RUN','item_id':None}); continue
        payload={'title':p.title[:60], 'category_id':p.category_id, 'price':p.price, 'currency_id':'BRL', 'available_quantity':p.stock, 'buying_mode':'buy_it_now', 'condition':'new', 'listing_type_id':'gold_special', 'status':'paused'}
        r=requests.post('https://api.mercadolibre.com/items', headers={'Authorization':f'Bearer {acc.access_token}'}, json=payload, timeout=30)
        data=r.json() if r.text else {}
        if r.status_code in (401,403,429):
            log(db,u,'publish','blocked',f'HTTP {r.status_code}: {r.text[:1000]}',p.sku,p.offset); raise HTTPException(400, f'Parada obrigatória HTTP {r.status_code}')
        if r.status_code>=300 or not data.get('id'):
            p.publication_status='failed'; p.validation_status='pending'; p.validation_reason=f'Erro ML: {r.text[:500]}'; db.commit(); log(db,u,'publish','failed',r.text[:1000],p.sku,p.offset); break
        p.item_id=data.get('id'); p.publication_status='published_paused'
        db.add(PublishedItem(seller_id=body.seller_id, sku=p.sku, offset=p.offset, item_id=p.item_id, status='paused'))
        db.commit(); log(db,u,'publish','published_paused',json.dumps(data)[:1000],p.sku,p.offset,p.item_id)
        results.append({'sku':p.sku,'offset':p.offset,'status':'PUBLISHED_PAUSED','item_id':p.item_id})
        time.sleep(max(1, body.delay_seconds))
    return {'ok':True,'dry_run':body.dry_run,'results':results}

@app.get('/api/audit/logs')
def audit(limit:int=100, u:User=Depends(current_user), db:Session=Depends(db_dep)):
    rows=db.query(AuditLog).filter(AuditLog.user_id==u.id).order_by(AuditLog.id.desc()).limit(limit).all()
    return [{'created_at':str(r.created_at),'action':r.action,'status':r.status,'sku':r.sku,'offset':r.offset,'item_id':r.item_id,'detail':r.detail} for r in rows]
