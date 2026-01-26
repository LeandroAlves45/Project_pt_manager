from __future__ import annotations
from typing import Optional
from sqlmodel import Session, select

from app.db.models.pack import PackType, ClientPack
from app.db.models.client import Client


class PackService:
    """
    Serviços de negócio relacionados a pacotes.

    Aqui é onde fica:
    -compra do pack (com snapchot sessions_total do pack_type)
    - querys "pack ativo"
    """

    @staticmethod
    def purchase_pack(
        session: Session,
        client_id: int,
        pack_type_id: int,
        purchase_date: Optional[str] = None,
    ) -> ClientPack:
        """
        Compra um pack:
        Valida se o pack_type existe e o cliente existe.
        -Copia sessions_total do pack type para o client_pack (snapshot)
        """

        client = session.get(Client, client_id)
        if not client:
            raise ValueError("Cliente não encontrado.")
        
        if client.archived_at is not None:
            raise ValueError("Não é possível comprar um pack para um cliente arquivado.")
        
        pack_type = session.get(PackType, pack_type_id)
        if not pack_type:
            raise ValueError("Tipo de pack não encontrado.")
        
        client_pack = ClientPack(
            client_id=client_id,
            pack_type_id=pack_type_id,
            purchase_date=purchase_date,
            sessions_total=pack_type.session_total,
            sessions_used=0,
        )

        session.add(client_pack)
        session.commit()
        session.refresh(client_pack)
        return client_pack  
    
    @staticmethod
    def get_active_packs(session: Session, client_id: str) -> Optional[ClientPack]:
        """
        Retorna os packs ativos de um cliente.
        Pack ativo é aquele que não está cancelado e tem sessões restantes.
        """

        statement = (select(ClientPack)
        .where(ClientPack.client_id == client_id)
        .where(ClientPack.archived_at.is_(None))
        .where(ClientPack.canceled_at.is_(None))
        .where(ClientPack.sessions_used < ClientPack.sessions_total)
        )
        
        from datetime import datetime, timezone

        now_iso = datetime.now(timezone.utc).replace (microsecond=0).isoformat()
        statement = (
            select(ClientPack)
            .where(ClientPack.client_id == client_id)   
            .where(ClientPack.archived_at.is_(None))    
            .where(ClientPack.canceled_at.is_(None))
            .where(ClientPack.sessions_used < ClientPack.sessions_total)
            .where(ClientPack.purchase_date <= now_iso)
            .order_by(ClientPack.purchase_date())
            .limit(1)
        ) 
        
        return session.exec(statement).first()
        


