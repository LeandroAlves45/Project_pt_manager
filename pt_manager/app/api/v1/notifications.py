from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, logger
from sqlmodel import Session, select

from app.db import session
from app.db.session import get_session as db_session
from app.db.models.notification import Notification, NotificationChannel, NotificationStatus
from app.services.email_service import EmailService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("/dispatch")
def dispach_due_notifications(session: Session = Depends(db_session)) -> dict:
    #Endpoint para o worker process chamar periodicamente (ex: a cada 5 minutos) e disparar notificações pendentes.

    logger.info("[API DISPATCH] Iniciando processamento manual de notificações")

    now = datetime.now(timezone.utc)

    #busca notificações pendentes (scheduled_for <= now)
    stmt = select(Notification).where(
        Notification.status == NotificationStatus.PENDING,
        Notification.scheduled_for <= now,
    )
    notifications_to_send = session.exec(stmt).all()
    
    logger.info(f"[API DISPATCH] Encontradas {len(notifications_to_send)} notificações pendentes")

    sent= 0
    failed = 0

    for notification in notifications_to_send:
            
        try:
            recipient = (notification.recipient or "").strip()

            # ================================================
            # PROCESSAR EMAIL
            # ================================================

            if notification.channel == NotificationChannel.EMAIL:
                logger.info(f"[API DISPATCH] Processando email para {recipient}")
                
                # Verificar se é template HTML (cliente)
                if notification.message.startswith("TEMPLATE_HTML|"):
                    # ========================================
                    # EMAIL HTML PARA CLIENTE
                    # ========================================
                    
                    # Parsear dados do template
                    parts = notification.message.replace("TEMPLATE_HTML|", "").split("|")
                    data = {}
                    for part in parts:
                        if "=" in part:
                            key, value = part.split("=", 1)
                            data[key.strip()] = value.strip()
                    
                    # Gerar HTML do template
                    html_body = EmailService.get_email_template(
                        client_name=data.get("client_name", "Cliente"),
                        session_date=data.get("session_date", ""),
                        session_time=data.get("session_time", ""),
                        duration_minutes=int(data.get("duration_minutes", 60)),
                        location=data.get("location", "Online")
                    )
                    
                    # Texto simples como fallback
                    fallback_text = (
                        f"Olá {data.get('client_name', '')},\n\n"
                        f"Você tem treino agendado para {data.get('session_date', '')} "
                        f"às {data.get('session_time', '')}.\n"
                        f"Duração: {data.get('duration_minutes', '')} minutos\n"
                        f"Local: {data.get('location', '')}\n\n"
                        f"Até lá!"
                    )
                    
                    # Enviar email com HTML
                    EmailService.send_email(
                        to_email=recipient,
                        subject="🏋️ Lembrete de Treino - Leandro Alves Online Coaching",
                        html_body=html_body,
                        body=fallback_text,
                        attach_logo=True
                    )
                    
                    logger.info(f"[API DISPATCH] ✅ Email HTML enviado para {recipient}")
                
                else:
                    # ========================================
                    # EMAIL SIMPLES PARA PT
                    # ========================================
                    
                    EmailService.send_email(
                        to_email=recipient,
                        subject="🏋️ Lembrete de Treino - PT Manager",
                        body=notification.message,
                        attach_logo=False
                    )
                    
                    logger.info(f"[API DISPATCH] ✅ Email simples enviado para {recipient}")
                
                # Marcar como enviada
                notification.status = NotificationStatus.SENT
                notification.sent_at = now
                notification.error_message = None
                sent += 1
            
            # ================================================
            # CANAL NÃO SUPORTADO
            # ================================================
            else:
                logger.warning(
                    f"[API DISPATCH] ⚠️  Canal {notification.channel} não suportado. "
                    f"Cancelando notificação {notification.id[:8]}"
                )
                notification.status = NotificationStatus.CANCELLED
                notification.error_message = f"Canal {notification.channel} não está ativo"
                failed += 1

        except Exception as e:
            # Erro ao processar notificação
            logger.error(f"[API DISPATCH] ❌ Erro ao processar notificação {notification.id[:8]}: {e}")
            logger.exception("Stacktrace:")
            
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)[:500]  # Limitar tamanho
            failed += 1
    
    # Commit de todas as alterações
    session.commit()
    
    result = {
        "due_found": len(notifications_to_send),
        "sent": sent,
        "failed": failed,
        "timestamp": now.isoformat()
    }
    
    logger.info(
        f"[API DISPATCH] Concluído - "
        f"Encontradas: {result['due_found']}, "
        f"Enviadas: {result['sent']}, "
        f"Falhadas: {result['failed']}"
    )
    
    return result

@router.get("/pending")
def list_pending_notifications(limit: int = 100, session: Session = Depends(db_session)) -> dict:
    #lista de notificações pendentes (para debug)

    stmt =(
        select(Notification)
        .where(Notification.status == NotificationStatus.PENDING)
        .order_by(Notification.scheduled_for.asc())
        .limit(limit)
    )
    notifications = session.exec(stmt).all()

    now = datetime.now(timezone.utc)

    result = []
    for n in notifications:
        #calcular tempo restante para envio
        is_due = n.scheduled_for <= now
        time_diff = (n.scheduled_for - now).total_seconds() / 60

        result.append({
            "id": n.id,
            "channel": n.channel,
            "recipient": n.recipient,
            "recipient_type": n.recipient_type,
            "scheduled_for": n.scheduled_for.isoformat(),
            "is_due": is_due,
            "minutes_until_send": round(time_diff, 1) if time_diff > 0 else 0,
            "created_at": n.created_at.isoformat() if n.created_at else None
        })

    return result

@router.get("/stats")
def get_notification_stats(session: Session = Depends(db_session)) -> dict:
    #Estatísticas básicas de notificações (total, pendentes, enviadas, falhadas)

    # Contar por status
    all_notifications = session.exec(select(Notification)).all()
    
    stats = {
        "total": len(all_notifications),
        "pending": 0,
        "sent": 0,
        "failed": 0,
        "cancelled": 0,
        "by_channel": {
            "email": 0,
            "whatsapp": 0  # Mantido para compatibilidade com dados antigos
        }
    }
    
    for n in all_notifications:
        # Contar por status
        if n.status == NotificationStatus.PENDING:
            stats["pending"] += 1
        elif n.status == NotificationStatus.SENT:
            stats["sent"] += 1
        elif n.status == NotificationStatus.FAILED:
            stats["failed"] += 1
        elif n.status == NotificationStatus.CANCELLED:
            stats["cancelled"] += 1
        
        # Contar por canal
        if n.channel == NotificationChannel.EMAIL:
            stats["by_channel"]["email"] += 1
        elif n.channel == NotificationChannel.WHATSAPP:
            stats["by_channel"]["whatsapp"] += 1
    
    return stats

@router.delete("/{notification_id}")
def delete_notification(notification_id: str, session: Session = Depends(db_session)) -> dict:

    notification = session.get(Notification, notification_id)

    if not notification:
        return {"error": "Notificação não encontrada"}
    
    if notification.status == NotificationStatus.PENDING:
        return {
            "error": f"Notificação já está com status '{notification.status}'",
            "status": 400
        }
    
    notification.status = NotificationStatus.CANCELLED
    session.add(notification)
    session.commit()

    logger.info(f"[API] Notificação {notification_id[:8]} cancelada manualmente")

    return {
        "message": "Notificação cancelada com sucesso",
        "notification_id": notification_id
    }