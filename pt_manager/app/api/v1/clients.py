from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import db_session
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.db.models.client import Client

router = APIRouter(prefix="/clients", tags=["clients"])

@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, session: Session = Depends(db_session)) -> Client:
    """
    Cria um novo cliente.
    Não permite criar clientes já arquivados.
    Unicidade do email é verificada em services
    Nesta fase, validamos também a nível de app para devolver erro amigável.
    """

    #Verifica opcional. a constraint UNIQUE será a garantia final
    existing_client = session.exec(select(Client).where(Client.phone == payload.phone)).first()
    if existing_client:
        raise HTTPException(status_code=409, detail= "Telefone já existe.")
    
    if payload.email:
        existing_client = session.exec(select(Client).where(Client.email == payload.email)).first()
        if existing_client:
            raise HTTPException(status_code=409, detail= "Email já existe.")    
        
    client = Client(
        full_name= payload.full_name,
        phone= payload.phone,
        email=str(payload.email) if payload.email else None,
        birth_date= payload.birth_date,
        sex= payload.sex,
        height_cm= payload.height_cm,
        weight_kg= payload.weight_kg,   
        objetive= payload.objetive,
        notes= payload.notes,
        emergency_contact_name= payload.emergency_contact_name,
        emergency_contact_phone= payload.emergency_contact_phone
    )

    session.add(client)
    session.commit()
    session.refresh(client)
    return client

@router.get("", response_model=list[ClientRead])
def list_clients(include_archived: bool = False, session: Session = Depends(db_session)) -> list[Client]:
    """
    Lista todos os clientes.
    Por padrão, não inclui clientes arquivados.
    """

    query = select(Client)
    if not include_archived:
        query = query.where(Client.archived_at.is_(None))
    
    query = query.order_by(Client.full_name)
    return list(session.exec(query).all())

@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: str, session: Session = Depends(db_session)) -> Client:
    """
    Obtem um cliente específico pelo ID.
    """
    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return client

@router.patch("/{client_id}", response_model=ClientRead)
def update_client(client_id: str, payload: ClientUpdate, session: Session = Depends(db_session)) -> Client:
    """
    Update parcial do cliente
    Atualiza os dados de um cliente específico.
    Não permite atualizar clientes arquivados.
    """

    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    
    data = payload.model_dump(exclude_unset=True)

    #Normaliza email -> str
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"])

    #verificações de unicidade 
    if "phone" in data and data["phone"] != client.phone:
        existing = session.exec(
            select(Client).where(Client.phone == data["phone"])).first()
        if existing:
            raise HTTPException(status_code=409, detail="Telefone já existe.")

    if "email" in data and data["email"] != client.email and data["email"] is not None:
        existing_email = session.exec(
            select(Client).where(Client.email == data["email"])).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email já existe.")
    
   # if client.archived_at:
        #raise HTTPException(status_code=400, detail="Não é possível atualizar um cliente arquivado.")
    
    for key, value in data.items():
        setattr(client, key, value)
    
    session.add(client)
    session.commit()
    session.refresh(client)
    return client

@router.post("/{client_id}/archive", response_model=ClientRead)
def archive_client(client_id: str, session: Session = Depends(db_session)) -> Client:
    """
    Arquiva (soft delete) um cliente.
    """

    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    
    if client.archived_at is None:
       from datetime import datetime, timezone
    
    client.archived_at = datetime.now(timezone.utc)
    session.add(client)
    session.commit()
    session.refresh(client)
       
    return client

@router.post("/{client_id}/unarchive", response_model=ClientRead)
def unarchive_client(client_id: str, session: Session = Depends(db_session)) -> Client:
    """
    Reativa um cliente.
    """

    client = session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    
    if client.archived_at is not None:
        client.archived_at = None
        session.add(client)
        session.commit()
        session.refresh(client)

    return client