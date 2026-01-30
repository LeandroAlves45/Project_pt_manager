from pathlib import Path
from sqlalchemy import text
from app.db.session import engine

def run_migrations() -> None:
    """
    Migrações simples via SQL (manual)
    -Executa scripts em ordem
    -Sem controlo de tabela Schema_migrations ainda
    """

    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        return

    scripts =sorted(migrations_dir.glob("*.sql"))
    if not scripts:
        return
    
    with engine.begin() as conn:
        raw = conn.connection #DB-API connection

        for script_path in scripts:
            sql = script_path.read_text(encoding="utf-8").strip()
            if not sql:
                continue

            #se for SQLite, executescript está disponível
            #em postgres futuro, mudamos para alambic
            if hasattr(raw, "executescript"):
                raw.executescript(sql)
            else:
                raw.execute(text(sql))