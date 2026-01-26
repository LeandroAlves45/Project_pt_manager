from datetime import date
from typing import Optional

from pydantic import EmailStr, Field
from sqlmodel import SQLModel

class ClientCreate(SQLModel):
    """
    Payload para criação de um novo cliente.
    aqui validamos formato; regras de negócio mais avançadas ficam em services
    """

    full_name: str = Field(min_length = 1, max_length=200)
    phone: str = Field(min_length = 8, max_length=20)
    email: Optional[EmailStr] = None

    birth_date: date
    sex: Optional[str] = Field(defult = None)

    height_cm: Optional[int] = Field(default=None, ge= 80, le= 260)
    weight_kg: Optional[float] = Field(default=None, ge= 20, le= 500)
    objetive: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

class ClientUpdate(SQLModel):
    """
    Payload para atualização de um cliente.
    todos os campos são opcionais
    """

    full_name: Optional[str] = Field(default=None, min_length = 1, max_length=200)
    phone: Optional[str] = Field(default=None, min_length = 8, max_length=20)
    email: Optional[EmailStr] = None

    birth_date: Optional[date] = None
    sex: Optional[str] = None

    height_cm: Optional[int] = Field(default=None, ge= 80, le= 260)
    weight_kg: Optional[float] = Field(default=None, ge= 20, le= 500)
    objetive: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = None

    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

class ClientRead(SQLModel):
    """
    Schema para leitura de dados do cliente.
    usado em respostas de API
    """

    id: int
    full_name: str
    phone: str
    email: Optional[EmailStr] = None

    birth_date: date
    sex: Optional[str] 
    height_cm: Optional[int]
    weight_kg: Optional[float]
    objetive: Optional[str]
    notes: Optional[str]
    emergency_contact_name: Optional[str]
    emergency_contact_phone: Optional[str]
    created_at: str
    updated_at: str
    