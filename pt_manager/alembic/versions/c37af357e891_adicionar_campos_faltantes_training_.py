"""adicionar campos faltantes training models 

Revision ID: XXXXXXXXXX
Revises: 302a9cd06c05
Create Date: 2026-02-10 XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = 'XXXXXXXXXX'
down_revision: Union[str, Sequence[str], None] = '302a9cd06c05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - VERSÃO CORRIGIDA"""
    
    # ========================================
    # 1. TRAINING_PLANS - adicionar client_id (FALTAVA!)
    # ========================================
    op.add_column(
        'training_plans',
        sa.Column('client_id', sa.String(), nullable=True)
    )
    op.create_index(
        op.f('ix_training_plans_client_id'),
        'training_plans',
        ['client_id'],
        unique=False
    )
    op.create_foreign_key(
        'fk_training_plans_client_id_clients',
        'training_plans',
        'clients',
        ['client_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Adicionar archived_at
    op.add_column(
        'training_plans',
        sa.Column('archived_at', sa.Date(), nullable=True)
    )
    op.create_index(
        op.f('ix_training_plans_archived_at'),
        'training_plans',
        ['archived_at'],
        unique=False
    )
    
    # ========================================
    # 2. TRAINING_PLAN_DAYS - adicionar notes
    # ========================================
    op.add_column(
        'training_plan_days',
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True)
    )
    
    # ========================================
    # 3. PLAN_DAY_EXERCISES - CORREÇÕES CRÍTICAS
    # ========================================
    
    # 3.1. Adicionar order_index COM server_default (permite NOT NULL mesmo com dados)
    op.add_column(
        'plan_day_exercises',
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0')
    )
    op.create_index(
        op.f('ix_plan_day_exercises_order_index'),
        'plan_day_exercises',
        ['order_index'],
        unique=False
    )
    
    # 3.2. RENOMEAR is_superset para is_superset_group (preserva dados!)
    op.alter_column(
        'plan_day_exercises',
        'is_superset',
        new_column_name='is_superset_group',
        existing_type=sa.VARCHAR(length=20),
        existing_nullable=True
    )
    
    # ========================================
    # 4. PLAN_EXERCISE_SET_LOADS - constraint única
    # ========================================
    op.create_unique_constraint(
        'uix_exercise_set',
        'plan_exercise_set_loads',
        ['plan_day_exercise_id', 'set_number']
    )


def downgrade() -> None:
    """Downgrade schema - VERSÃO CORRIGIDA"""
    
    # Reverte na ordem inversa
    
    # 4. Remove constraint
    op.drop_constraint(
        'uix_exercise_set',
        'plan_exercise_set_loads',
        type_='unique'
    )
    
    # 3. Reverte plan_day_exercises
    op.alter_column(
        'plan_day_exercises',
        'is_superset_group',
        new_column_name='is_superset',
        existing_type=sa.VARCHAR(length=20),
        existing_nullable=True
    )
    
    op.drop_index(
        op.f('ix_plan_day_exercises_order_index'),
        table_name='plan_day_exercises'
    )
    op.drop_column('plan_day_exercises', 'order_index')
    
    # 2. Reverte training_plan_days
    op.drop_column('training_plan_days', 'notes')
    
    # 1. Reverte training_plans
    op.drop_index(
        op.f('ix_training_plans_archived_at'),
        table_name='training_plans'
    )
    op.drop_column('training_plans', 'archived_at')
    
    op.drop_constraint(
        'fk_training_plans_client_id_clients',
        'training_plans',
        type_='foreignkey'
    )
    op.drop_index(
        op.f('ix_training_plans_client_id'),
        table_name='training_plans'
    )
    op.drop_column('training_plans', 'client_id')