from __future__ import annotations
from sched import scheduler

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import datetime
from sqlmodel import Session
import logging

from app.core.config import settings
from app.db.session import engine, get_session
from app.db.models.notification import NotificationChannel, NotificationStatus
from app.services.notification_service import NotificationService
from app.services.email_service import EmailService
from app.utils.time import utc_now_datetime

logger = logging.getLogger(__name__)

# Criar scheduler
scheduler = BackgroundScheduler()

def dispatch_job():

    """
    Job que processa e envia notificações de EMAIL pendentes.
    
    Executa a cada 1 minuto (configurado no scheduler).
    
    Fluxo:
    1. Busca notificações pendentes (scheduled_for <= now)
    2. Para cada notificação EMAIL:
       - Se for template HTML (cliente): gera HTML bonito
       - Se for texto simples (PT): envia direto
    3. Marca como SENT ou FAILED
    4. Commit na base de dados
    """
    logger.info(f"[SCHEDULER] 🔄 Iniciando dispatch às {utc_now_datetime()}")

    with next(get_session()) as session:
        # Buscar notificações pendentes
        notifications = NotificationService.list_due_notifications(session, limit=100)
        logger.info(f"[SCHEDULER] 📬 Encontradas {len(notifications)} notificação(ões) para enviar")
        for notification in notifications:
            try:
                recipient =(notification.recipient or "").strip()

                # ================================================
                # PROCESSAR EMAIL
                # ================================================
                if notification.channel == NotificationChannel.EMAIL:
                    logger.info(f"[EMAIL] 📧 Processando para {recipient}")
                
                    #verificar se é template HTML (cliente)
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
                        
                        # Gerar HTML 
                        html_body = EmailService.get_email_template(
                            client_name=data.get("client_name", "Cliente"),
                            session_date=data.get("session_date", ""),
                            session_time=data.get("session_time", ""),
                            duration_minutes=int(data.get("duration_minutes", 60)),
                            location=data.get("location", "")
                        )

                        #texto simples de fallback 
                        fallbaack_body=(
                            f"Olá {data.get('client_name', '')},\n\n"
                            f"Você tem treino agendado para {data.get('session_date', '')} "
                            f"às {data.get('session_time', '')}.\n"
                            f"Duração: {data.get('duration_minutes', '')} minutos\n"
                            f"Local: {data.get('location', '')}\n\n"
                            f"Até lá!"
                        )

                        # Enviar email com html
                        EmailService.send_email(
                            to_email=recipient,
                            subject="Lembrete de Treino - Leandro Alves Personal Trainer",
                            html_body=html_body,
                            body=fallbaack_body,
                            attach_logo=True
                        )

                        logger.info(f"[EMAIL] ✅ Email HTML enviado para {recipient}")

                    else:
                        # ========================================
                        # EMAIL SIMPLES PARA TREINADOR
                        # ========================================
                        
                        EmailService.send_email(
                            to_email=recipient,
                            subject="Lembrete de Treino - Leandro Alves Personal Trainer",
                            body=notification.message,
                            attach_logo=True
                        )

                        logger.info(f"[EMAIL] ✅ Email simples enviado para {recipient}")

                    # Marcar como enviada
                    notification.status = NotificationStatus.SENT
                    notification.sent_at = utc_now_datetime()
                    session.add(notification)
                    
                    logger.info(f"[SUCCESS] ✅ Notificação {notification.id[:8]} processada com sucesso")

                # ================================================
                #CANAL NÃO SUPORTADO
                # ================================================
                else:
                    logger.warning(
                        f"[SCHEDULER] ⚠️  Canal {notification.channel} não suportado. "
                        f"Cancelando notificação {notification.id[:8]}"
                    )
                    notification.status = NotificationStatus.CANCELLED
                    notification.error_message = f"Canal {notification.channel} não está ativo"
                    session.add(notification)
                    
            except Exception as e:
                # Erro ao processar notificação
                logger.error(f"[FAILED] ❌ Erro ao processar notificação {notification.id[:8]}: {e}")
                logger.exception("Stacktrace completo:")
                
                notification.status = NotificationStatus.FAILED
                notification.error_message = str(e)[:500]  # Limitar tamanho
                session.add(notification)

        session.commit()
        logger.info(f"[SCHEDULER] ✅ Dispatch concluído. {len(notifications)} processada(s).")

def start_scheduler():
    """Inicia o scheduler em background"""
    logger.info("[SCHEDULER] Iniciando scheduler de notificações")
    
    scheduler.add_job(
        dispatch_job, 
        IntervalTrigger(seconds=60), 
        id="notification_dispatch", 
        replace_existing=True, 
        max_instances=1
    )
    
    scheduler.start()
    logger.info("[SCHEDULER] Scheduler iniciado com sucesso")

def shutdown_scheduler():

    #Função para desligar o scheduler graciosamente (ex: em shutdown da aplicação).

    logger.info("[SCHEDULER] Desligando scheduler de notificações")
    scheduler.shutdown(wait=False)
    logger.info("[SCHEDULER] Scheduler desligado")