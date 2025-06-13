#!/usr/bin/env python3

from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

load_dotenv()

def run_migrations():
    try:
        print("🔄 Ejecutando migraciones de base de datos...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("✅ Migraciones ejecutadas exitosamente")
    except Exception as e:
        print(f"❌ Error ejecutando migraciones: {e}")
        raise

if __name__ == "__main__":
    run_migrations() 