from datetime import datetime, timezone

def utc_now_dt() -> datetime:
    """
    Devolve datetime timezone-aware em UTC, sem microsegundos.
    Ideal para persistir no DB com consistência.
    """
    return datetime.now(timezone.utc).replace(microsecond=0)
