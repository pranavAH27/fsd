from datetime import datetime, timezone
from secrets import randbelow
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import Base, engine, get_db
from .models import User, Donation, Claim, ChatMessage, AuditLog
from .schemas import UserCreate, UserOut, Login, Token, DonationCreate, DonationOut, ClaimOut, AssignVolunteer, PickupVerification, AssistantRequest
from .security import hash_password, verify_password, create_access_token, current_user, require_roles
from .services import distance_km, geocode, ask_grok

app = FastAPI(title="SurplusReach API", version="1.0.0", description="Surplus food redistribution and NGO coordination API")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",") if x.strip()], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


def audit(db: Session, actor: User | None, action: str, entity: str | None = None, entity_id: int | None = None):
    db.add(AuditLog(actor_id=actor.id if actor else None, action=action, entity_type=entity, entity_id=entity_id))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "surplusreach"}


@app.post("/api/auth/register", response_model=Token, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if payload.role not in {"donor", "ngo", "volunteer"}:
        raise HTTPException(422, "Role must be donor, ngo, or volunteer")
    email = payload.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "Email already registered")
    user = User(name=payload.name, email=email, password_hash=hash_password(payload.password), role=payload.role, organization_name=payload.organization_name, phone=payload.phone, address=payload.address, lat=payload.lat, lng=payload.lng, is_verified=payload.role != "ngo")
    db.add(user); db.commit(); db.refresh(user)
    return Token(access_token=create_access_token(user), user=user)


@app.post("/api/auth/login", response_model=Token)
def login(payload: Login, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if payload.role and user.role != payload.role:
        raise HTTPException(401, "This account is registered as a different user type")
    return Token(access_token=create_access_token(user), user=user)


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/donations", response_model=list[DonationOut])
def list_donations(status: str | None = None, dietary: str | None = None, urgency_hours: int | None = Query(None, ge=1, le=168), lat: float | None = None, lng: float | None = None, radius_km: float = Query(30, gt=0, le=500), db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = db.query(Donation)
    if user.role == "donor": query = query.filter(Donation.donor_id == user.id)
    elif user.role in {"ngo", "volunteer"}: query = query.filter(Donation.status == "available")
    if status and user.role in {"donor", "admin"}: query = query.filter(Donation.status == status)
    if dietary: query = query.filter(Donation.dietary_info == dietary)
    if urgency_hours: query = query.filter(Donation.expiry_time <= datetime.now(timezone.utc).replace(tzinfo=None) + __import__("datetime").timedelta(hours=urgency_hours))
    rows = query.order_by(Donation.expiry_time.asc()).all()
    if lat is not None and lng is not None:
        rows = [row for row in rows if row.lat is not None and row.lng is not None and distance_km(lat, lng, float(row.lat), float(row.lng)) <= radius_km]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        if row.status == "available" and row.expiry_time <= now: row.status = "expired"
    db.commit()
    return rows


@app.post("/api/donations", response_model=DonationOut, status_code=201)
def create_donation(payload: DonationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("donor"))):
    if payload.expiry_time.replace(tzinfo=None) <= datetime.utcnow(): raise HTTPException(422, "Expiry must be in the future")
    if payload.food_type not in {"cooked meal", "raw produce", "bakery", "packaged"} or payload.dietary_info not in {"veg", "non-veg", "vegan"}: raise HTTPException(422, "Invalid food type or dietary value")
    item = Donation(**payload.model_dump(), donor_id=user.id, status="available")
    db.add(item); db.flush(); audit(db, user, "donation.created", "donation", item.id); db.commit(); db.refresh(item)
    return item


@app.get("/api/donations/{donation_id}", response_model=DonationOut)
def get_donation(donation_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    item = db.get(Donation, donation_id)
    if not item: raise HTTPException(404, "Donation not found")
    if user.role == "donor" and item.donor_id != user.id: raise HTTPException(403, "Not your donation")
    return item


@app.put("/api/donations/{donation_id}", response_model=DonationOut)
def update_donation(donation_id: int, payload: DonationCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("donor"))):
    item = db.get(Donation, donation_id)
    if not item or item.donor_id != user.id: raise HTTPException(404, "Donation not found")
    if item.status != "available": raise HTTPException(409, "Only available donations can be edited")
    if payload.expiry_time.replace(tzinfo=None) <= datetime.utcnow(): raise HTTPException(422, "Expiry must be in the future")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    audit(db, user, "donation.updated", "donation", item.id); db.commit(); db.refresh(item)
    return item


@app.delete("/api/donations/{donation_id}", status_code=204)
def delete_donation(donation_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("donor"))):
    item = db.get(Donation, donation_id)
    if not item or item.donor_id != user.id: raise HTTPException(404, "Donation not found")
    if item.status != "available": raise HTTPException(409, "Only available donations can be removed")
    audit(db, user, "donation.deleted", "donation", item.id); db.delete(item); db.commit()


@app.post("/api/donations/{donation_id}/pickup-code")
def get_pickup_code(donation_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("donor"))):
    item = db.get(Donation, donation_id)
    if not item or item.donor_id != user.id: raise HTTPException(404, "Donation not found")
    claim = db.query(Claim).filter(Claim.donation_id == donation_id, Claim.status.in_(["claimed", "assigned", "in_transit"])).first()
    if not claim: raise HTTPException(409, "Donation has no active claim")
    if not item.pickup_code:
        item.pickup_code = f"{randbelow(1_000_000):06d}"; db.commit()
    return {"pickup_code": item.pickup_code}


@app.post("/api/claims", response_model=ClaimOut, status_code=201)
def claim_donation(donation_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("ngo"))):
    if not user.is_verified: raise HTTPException(403, "NGO account is awaiting verification")
    item = db.query(Donation).filter(Donation.id == donation_id).with_for_update().first()
    if not item or item.status != "available": raise HTTPException(409, "Donation is no longer available")
    if item.expiry_time <= datetime.utcnow(): item.status = "expired"; db.commit(); raise HTTPException(409, "Donation has expired")
    item.status = "claimed"; claim = Claim(donation_id=item.id, ngo_id=user.id, status="claimed")
    db.add(claim); db.flush(); audit(db, user, "claim.created", "claim", claim.id); db.commit()
    return db.query(Claim).options(joinedload(Claim.donation)).get(claim.id)


@app.get("/api/claims", response_model=list[ClaimOut])
def list_claims(db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = db.query(Claim).options(joinedload(Claim.donation))
    if user.role == "ngo": query = query.filter(Claim.ngo_id == user.id)
    elif user.role == "volunteer": query = query.filter(Claim.volunteer_id == user.id)
    elif user.role == "donor": query = query.join(Donation).filter(Donation.donor_id == user.id)
    return query.order_by(Claim.claimed_at.desc()).all()


@app.get("/api/volunteers", response_model=list[UserOut])
def list_volunteers(db: Session = Depends(get_db), user: User = Depends(require_roles("ngo"))):
    return db.query(User).filter(User.role == "volunteer", User.is_verified.is_(True)).order_by(User.name.asc()).all()


@app.delete("/api/claims/{claim_id}", status_code=204)
def cancel_claim(claim_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("ngo"))):
    claim = db.query(Claim).options(joinedload(Claim.donation)).filter(Claim.id == claim_id, Claim.ngo_id == user.id).first()
    if not claim: raise HTTPException(404, "Claim not found")
    if claim.status in {"in_transit", "completed"}: raise HTTPException(409, "A pickup already in progress cannot be cancelled")
    claim.status = "cancelled"
    claim.donation.status = "available" if claim.donation.expiry_time > datetime.utcnow() else "expired"
    audit(db, user, "claim.cancelled", "claim", claim.id); db.commit()


@app.patch("/api/claims/{claim_id}/assign", response_model=ClaimOut)
def assign_volunteer(claim_id: int, payload: AssignVolunteer, db: Session = Depends(get_db), user: User = Depends(require_roles("ngo"))):
    claim = db.query(Claim).options(joinedload(Claim.donation)).filter(Claim.id == claim_id, Claim.ngo_id == user.id).first()
    volunteer = db.get(User, payload.volunteer_id)
    if not claim: raise HTTPException(404, "Claim not found")
    if not volunteer or volunteer.role != "volunteer": raise HTTPException(422, "Select a registered volunteer")
    claim.volunteer_id = volunteer.id; claim.status = "assigned"; audit(db, user, "claim.volunteer_assigned", "claim", claim.id); db.commit(); db.refresh(claim)
    return claim


@app.post("/api/claims/{claim_id}/pickup", response_model=ClaimOut)
def verify_pickup(claim_id: int, payload: PickupVerification, db: Session = Depends(get_db), user: User = Depends(require_roles("volunteer"))):
    claim = db.query(Claim).options(joinedload(Claim.donation)).filter(Claim.id == claim_id, Claim.volunteer_id == user.id).first()
    if not claim or claim.status not in {"assigned", "claimed"}: raise HTTPException(409, "No assigned pickup is ready")
    if not claim.donation.pickup_code or payload.code != claim.donation.pickup_code: raise HTTPException(422, "Pickup code does not match")
    claim.status = "in_transit"; claim.donation.status = "in_transit"; audit(db, user, "claim.pickup_verified", "claim", claim.id); db.commit(); db.refresh(claim)
    return claim


@app.post("/api/claims/{claim_id}/deliver", response_model=ClaimOut)
def confirm_delivery(claim_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("volunteer"))):
    claim = db.query(Claim).options(joinedload(Claim.donation)).filter(Claim.id == claim_id, Claim.volunteer_id == user.id).first()
    if not claim or claim.status != "in_transit": raise HTTPException(409, "Pickup must be verified before delivery")
    claim.status = "completed"; claim.delivered_at = datetime.utcnow(); claim.donation.status = "completed"; claim.donation.pickup_code = None
    audit(db, user, "claim.delivered", "claim", claim.id); db.commit(); db.refresh(claim)
    return claim


@app.get("/api/admin/overview")
def admin_overview(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    counts = {status: db.query(func.count(Donation.id)).filter(Donation.status == status).scalar() or 0 for status in ["available", "claimed", "in_transit", "completed", "expired"]}
    completed_food = db.query(Donation.quantity, Donation.unit).filter(Donation.status == "completed").all()
    kg_factors = {"kg": 1, "g": 0.001, "meal": 0.35, "meals": 0.35, "portion": 0.35, "portions": 0.35, "item": 0.15, "items": 0.15, "box": 4, "boxes": 4}
    saved = sum(float(quantity) * kg_factors.get(unit.lower(), 0) for quantity, unit in completed_food)
    meals = sum(float(quantity) for quantity, unit in completed_food if unit.lower() in {"meal", "meals", "portion", "portions"})
    claim_counts = {status: db.query(func.count(Claim.id)).filter(Claim.status == status).scalar() or 0 for status in ["claimed", "assigned", "in_transit", "completed", "cancelled"]}
    return {"donations": counts, "claims": claim_counts, "food_saved_kg_estimate": round(saved, 1), "meals_distributed_estimate": int(meals + max(saved - meals * 0.35, 0) * 2.5), "users": db.query(func.count(User.id)).scalar(), "pending_ngos": db.query(func.count(User.id)).filter(User.role == "ngo", User.is_verified.is_(False)).scalar()}


@app.get("/api/admin/users", response_model=list[UserOut])
def admin_users(role: str | None = None, pending: bool = False, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    query = db.query(User)
    if role: query = query.filter(User.role == role)
    if pending: query = query.filter(User.role == "ngo", User.is_verified.is_(False))
    return query.order_by(User.created_at.desc()).all()


@app.patch("/api/admin/users/{user_id}/verify", response_model=UserOut)
def verify_ngo(user_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    target = db.get(User, user_id)
    if not target or target.role != "ngo": raise HTTPException(404, "NGO not found")
    target.is_verified = True; audit(db, user, "ngo.verified", "user", target.id); db.commit(); db.refresh(target)
    return target


@app.get("/api/admin/audit")
def audit_logs(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    return [{"id": x.id, "actor_id": x.actor_id, "action": x.action, "entity_type": x.entity_type, "entity_id": x.entity_id, "created_at": x.created_at} for x in db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()]


@app.post("/api/maps/geocode")
async def geocode_address(address: str = Query(min_length=4, max_length=500), user: User = Depends(current_user)):
    return await geocode(address)


@app.post("/api/assistant/chat")
async def assistant(payload: AssistantRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    history = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).order_by(ChatMessage.created_at.desc()).limit(12).all()
    history.reverse()
    answer = await ask_grok(payload.message, [{"role": m.role, "content": m.content} for m in history])
    db.add(ChatMessage(user_id=user.id, role="user", content=payload.message)); db.add(ChatMessage(user_id=user.id, role="assistant", content=answer)); db.commit()
    return {"reply": answer}
