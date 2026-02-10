from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """
        Serviço para envio de emails via SMTP.
    
        Suporta:
        - Gmail (smtp.gmail.com) - requer senha de app
        - Outlook (smtp-mail.outlook.com)
        - Outros servidores SMTP
    """

    @staticmethod
    def load_email_template() -> str:
        """
        Carrega o template HTML do email.
        """
        template_path = Path("app/htmls/email.html")

        if not template_path.exists():
            error_msg = f"Template de email não encontrado em {template_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template = f.read()
            return template
        except Exception as e:
            logger.error(f"Erro ao carregar template de email: {e}")
            raise ValueError(f"Erro ao carregar template de email: {e}")

    @staticmethod
    def get_email_template(
        client_name:str,
        session_date:str,
        session_time:str,
        duration_minutes:int,
        location:str,
    ) -> str:
        """
        Gera email HTML substituindo variáveis no template.
        
        Args:
            client_name: Nome do cliente
            session_date: Data da sessão (formato: "10/02/2026")
            session_time: Hora da sessão (formato: "10:00")
            duration_minutes: Duração em minutos
            location: Local do treino
            
        Returns:
            str: HTML do email com variáveis substituídas
        """
        
        try:

            template_path = EmailService.load_email_template()

             # Substituir variáveis usando .format()
            html = template_path.format(
            client_name=client_name,
            session_date=session_date,
            session_time=session_time,
            duration_minutes=duration_minutes,
            location=location
            )
        
            logger.debug(f"[EMAIL] Template processado para {client_name}")
            return html
        
        except FileNotFoundError as e:
            error_msg = f"Template de email não encontrado: {e}"
            logger.error(f"[EMAIL] ❌ {error_msg}")
            raise ValueError(error_msg)
        
        except KeyError as e:
            error_msg = f"Variável {e} não encontrada no template HTML"
            logger.error(f"[EMAIL] ❌ {error_msg}")
            raise ValueError(error_msg)

        except Exception as e:
            logger.error(f"Erro ao carregar template de email: {e}")
            raise ValueError(f"Erro ao carregar template de email: {e}")
        
    @staticmethod
    def send_email(to_email: str, subject: str, body: str, html_body: str = None, attach_logo: bool = True) -> None:
        """
        Envia email via SMTP configurado no .env
        
        Args:
            to_email: Email do destinatário
            subject: Assunto do email
            body: Corpo do email (texto simples)
            html_body: Corpo do email em HTML (opcional)
            attach_logo: Se deve anexar o logo ao email (opcional)  
        Raises:
            ValueError: Se configuração SMTP estiver incompleta
            smtplib.SMTPException: Se falhar ao enviar
        """
        if not all([settings.smtp_host, settings.smtp_port, settings.smtp_user, settings.smtp_password, settings.smtp_from_email]):
            error_msg = "Email não configurado. Defina SMTP_HOST, SMTP_USER, SMTP_PASSWORD no .env"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        #construir mensagem
        msg = MIMEMultipart('related') 
        msg["From"] = settings.smtp_from_email or settings.smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        
        #criar alternativa 
        msg_alternative = MIMEMultipart('alternative')
        msg.attach(msg_alternative)

        if body:
            msg_alternative.attach(MIMEText(body, 'plain', 'utf-8'))

        #anexar HTML
        if html_body:
            msg_alternative.attach(MIMEText(html_body, 'html', 'utf-8'))
        elif not body:
            raise ValueError("É necessário fornecer body ou html_body para o email")
        
        #anexar logo
        if attach_logo and html_body:
            logo_path = Path("assets/logo.png")
            if logo_path.exists():
                try: 
                    with open(logo_path, "rb") as logo_file:
                        logo_img = MIMEImage(logo_file.read())
                        logo_img.add_header("Content-ID", "<logo>")
                        logo_img.add_header("Content-Disposition", "inline", filename="logo.png")
                        msg.attach(logo_img)
                    logger.info(f"[EMAIL] Logo anexada ao email com sucesso: {logo_path}")
                except Exception as e:
                    logger.error(f"[EMAIL] Erro ao anexar logo: {e}")
            else:
                logger.warning(f"[EMAIL] Logo não encontrada, email será enviado sem logo: {logo_path}")

        try:
            logger.info(f"[EMAIL] Enviando email para {to_email}")

            #conectar e enviar email
            if settings.smtp_use_tls:
                 # Usar STARTTLS (porta 587)
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
                server.starttls()
            else:
                # Usar SSL direto (porta 465)
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20)

            #autenticar
            server.login(settings.smtp_user, settings.smtp_password)

            #enviar email
            server.send_message(msg)
            server.quit()

            logger.info(f"[EMAIL] Email enviado com sucesso para {to_email}")
        except smtplib.SMTPException:
            logger.error("Falha na autenticação SMTP - verifique SMTP_USER e SMTP_PASSWORD")
            raise ValueError("Credenciais SMTP inválidas")
        
        except smtplib.SMTPException as e:
            logger.error(f"[EMAIL] ❌ Erro SMTP: {e}")
            raise ValueError(f"Erro ao enviar email: {e}")
            
        except Exception as e:
            logger.exception("[EMAIL] ❌ Erro inesperado")
            raise ValueError(f"Erro inesperado: {e}")
