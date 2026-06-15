from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


def _optional_int(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.isdigit():
            return int(value)
        return None
    return value


class InternetApplicationCreate(BaseModel):
    branches: Optional[str] = None
    departments: Optional[str] = None
    navi_user: Optional[str] = None
    rt_lc_states: str = Field("active", min_length=1, max_length=50)
    msisdn: Optional[str] = None
    rate_plan_first_connection: Optional[str] = None
    selected_tariff_id: Optional[int] = None
    selected_tariff_code: Optional[str] = None

    @field_validator("selected_tariff_id", mode="before")
    @classmethod
    def normalize_selected_tariff_id(cls, value):
        return _optional_int(value)


class InternetApplicationResponse(BaseModel):
    id: int
    city: str
    first_name: str
    last_name: str
    father_name: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    done_at: Optional[datetime] = None
    phone: Optional[str] = None
    selected_tariff_id: Optional[int] = None
    selected_tariff_code: Optional[str] = None
    address: Optional[str] = None
    branches: Optional[str] = None
    departments: Optional[str] = None
    navi_user: Optional[str] = None
    rt_lc_states: Optional[str] = None
    msisdn: Optional[str] = None
    rate_plan_first_connection: Optional[str] = None

    class Config:
        from_attributes = True


class MobileApplicationCreate(BaseModel):
    msisdn: str = Field(..., min_length=1, max_length=100)
    dealer: Optional[str] = None
    navi_user: Optional[str] = None
    rate_plan_first_connection: Optional[str] = None
    branches: Optional[str] = None
    selected_tariff_id: Optional[int] = None
    selected_tariff_code: Optional[str] = None

    @field_validator("selected_tariff_id", mode="before")
    @classmethod
    def normalize_selected_tariff_id(cls, value):
        return _optional_int(value)


class MobileApplicationResponse(BaseModel):
    id: int
    phone: str
    operator_code: str
    first_name: str
    last_name: str
    father_name: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    done_at: Optional[datetime] = None
    selected_tariff_id: Optional[int] = None
    selected_tariff_code: Optional[str] = None
    address: Optional[str] = None
    dealer: Optional[str] = None
    navi_user: Optional[str] = None
    msisdn: Optional[str] = None
    rate_plan_first_connection: Optional[str] = None
    branches: Optional[str] = None

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    client_name: str
    phone: Optional[str] = None
    application_type: str
    application_id: int
    session_id: Optional[str] = None


class OperatorMessage(BaseModel):
    session_id: str
    message: str
    media_url: Optional[str] = None
    skip_telegram: bool = False
