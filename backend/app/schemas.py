from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: str
    organization_name: str | None = None
    phone: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None


class UserOut(BaseModel):
    id: int; name: str; email: str; role: str; organization_name: str | None
    phone: str | None; address: str | None; lat: float | None; lng: float | None
    is_verified: bool
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class Login(BaseModel):
    email: EmailStr
    password: str
    role: str | None = None


class DonationCreate(BaseModel):
    food_name: str = Field(min_length=2, max_length=180)
    food_type: str
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=32)
    dietary_info: str
    preparation_time: datetime | None = None
    expiry_time: datetime
    pickup_address: str = Field(min_length=5, max_length=500)
    lat: float | None = None
    lng: float | None = None
    storage_notes: str | None = None


class DonationOut(BaseModel):
    id: int; donor_id: int; food_name: str; food_type: str; quantity: float; unit: str
    dietary_info: str; preparation_time: datetime | None; expiry_time: datetime
    pickup_address: str; lat: float | None; lng: float | None; storage_notes: str | None
    status: str; created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ClaimOut(BaseModel):
    id: int; donation_id: int; ngo_id: int; volunteer_id: int | None; status: str
    notes: str | None; claimed_at: datetime; delivered_at: datetime | None
    donation: DonationOut
    model_config = ConfigDict(from_attributes=True)


class AssignVolunteer(BaseModel):
    volunteer_id: int


class PickupVerification(BaseModel):
    code: str


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
