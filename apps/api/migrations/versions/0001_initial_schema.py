"""initial schema

Revision ID: fe48110e926c
Revises: 
Create Date: 2026-11-20 22:22:20.949235
"""
from collections.abc import Sequence

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # pg_trgm (typo-tolerant food search) ships with standard Postgres, Supabase and
    # Neon. Some minimal local builds lack it, so the app works without it too.
    op.execute("""
        DO $$ BEGIN
            CREATE EXTENSION IF NOT EXISTS pg_trgm;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pg_trgm not available; food search will skip trigram matching';
        END $$;
    """)
    op.create_table('documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('source_key', sa.String(length=300), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=False),
    sa.Column('version', sa.String(length=50), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source', 'source_key')
    )
    op.create_table('exercises',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=120), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('category', sa.String(length=40), nullable=False),
    sa.Column('level', sa.String(length=20), nullable=False),
    sa.Column('equipment', sa.String(length=60), nullable=False),
    sa.Column('primary_muscles', sa.ARRAY(sa.String()), nullable=False),
    sa.Column('secondary_muscles', sa.ARRAY(sa.String()), nullable=False),
    sa.Column('instructions', sa.ARRAY(sa.Text()), nullable=False),
    sa.Column('images', sa.ARRAY(sa.String()), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('foods',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=30), nullable=False),
    sa.Column('source_id', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=300), nullable=False),
    sa.Column('category', sa.String(length=200), nullable=False),
    sa.Column('barcode', sa.String(length=32), nullable=True),
    sa.Column('kcal', sa.Float(), nullable=True),
    sa.Column('protein_g', sa.Float(), nullable=True),
    sa.Column('fat_g', sa.Float(), nullable=True),
    sa.Column('carbs_g', sa.Float(), nullable=True),
    sa.Column('fiber_g', sa.Float(), nullable=True),
    sa.Column('sugar_g', sa.Float(), nullable=True),
    sa.Column('sat_fat_g', sa.Float(), nullable=True),
    sa.Column('sodium_mg', sa.Float(), nullable=True),
    sa.Column('potassium_mg', sa.Float(), nullable=True),
    sa.Column('calcium_mg', sa.Float(), nullable=True),
    sa.Column('iron_mg', sa.Float(), nullable=True),
    sa.Column('vitamin_c_mg', sa.Float(), nullable=True),
    sa.Column('vitamin_d_ug', sa.Float(), nullable=True),
    sa.Column('search_tsv', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', coalesce(name, '') || ' ' || coalesce(category, ''))", persisted=True), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source', 'source_id')
    )
    op.create_index(op.f('ix_foods_barcode'), 'foods', ['barcode'], unique=False)
    op.create_index('ix_foods_embedding', 'foods', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_foods_search', 'foods', ['search_tsv'], unique=False, postgresql_using='gin')
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('chat_messages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('video_id', sa.String(length=20), nullable=True),
    sa.Column('rating', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_user_created', 'chat_messages', ['user_id', 'created_at'], unique=False)
    op.create_table('chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('heading', sa.String(length=300), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('search_tsv', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', coalesce(heading, '') || ' ' || content)", persisted=True), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chunks_document_id'), 'chunks', ['document_id'], unique=False)
    op.create_index('ix_chunks_embedding', 'chunks', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_chunks_search', 'chunks', ['search_tsv'], unique=False, postgresql_using='gin')
    op.create_table('favorite_foods',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('food_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['food_id'], ['foods.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'food_id')
    )
    op.create_index(op.f('ix_favorite_foods_user_id'), 'favorite_foods', ['user_id'], unique=False)
    op.create_table('food_portions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('food_id', sa.Integer(), nullable=False),
    sa.Column('description', sa.String(length=200), nullable=False),
    sa.Column('grams', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['food_id'], ['foods.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_food_portions_food_id'), 'food_portions', ['food_id'], unique=False)
    op.create_table('meal_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('eaten_on', sa.Date(), nullable=False),
    sa.Column('meal', sa.String(length=20), nullable=False),
    sa.Column('food_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=300), nullable=False),
    sa.Column('grams', sa.Float(), nullable=False),
    sa.Column('kcal', sa.Float(), nullable=False),
    sa.Column('protein_g', sa.Float(), nullable=False),
    sa.Column('carbs_g', sa.Float(), nullable=False),
    sa.Column('fat_g', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['food_id'], ['foods.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_meal_entries_user_day', 'meal_entries', ['user_id', 'eaten_on'], unique=False)
    op.create_table('profiles',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('age', sa.Integer(), nullable=False),
    sa.Column('sex', sa.String(length=10), nullable=False),
    sa.Column('height_cm', sa.Float(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.Column('activity', sa.String(length=20), nullable=False),
    sa.Column('goal', sa.String(length=20), nullable=False),
    sa.Column('units', sa.String(length=10), nullable=False),
    sa.Column('diet', sa.String(length=30), nullable=False),
    sa.Column('allergies', sa.ARRAY(sa.String()), nullable=False),
    sa.Column('equipment', sa.ARRAY(sa.String()), nullable=False),
    sa.Column('training_days', sa.Integer(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('weight_entries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('measured_on', sa.Date(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'measured_on')
    )
    op.create_index(op.f('ix_weight_entries_user_id'), 'weight_entries', ['user_id'], unique=False)
    op.create_table('workout_plans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('plan', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workout_plans_user_id'), 'workout_plans', ['user_id'], unique=False)
    op.create_table('workout_sets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=True),
    sa.Column('exercise_id', sa.Integer(), nullable=True),
    sa.Column('exercise_name', sa.String(length=200), nullable=False),
    sa.Column('performed_on', sa.Date(), nullable=False),
    sa.Column('set_number', sa.Integer(), nullable=False),
    sa.Column('reps', sa.Integer(), nullable=False),
    sa.Column('weight_kg', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['exercise_id'], ['exercises.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['plan_id'], ['workout_plans.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workout_sets_user_exercise', 'workout_sets', ['user_id', 'exercise_id'], unique=False)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
                CREATE INDEX IF NOT EXISTS ix_foods_name_trgm ON foods USING gin (name gin_trgm_ops);
            END IF;
        END $$;
    """)
    # ### end Alembic commands ###


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_foods_name_trgm")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_workout_sets_user_exercise', table_name='workout_sets')
    op.drop_table('workout_sets')
    op.drop_index(op.f('ix_workout_plans_user_id'), table_name='workout_plans')
    op.drop_table('workout_plans')
    op.drop_index(op.f('ix_weight_entries_user_id'), table_name='weight_entries')
    op.drop_table('weight_entries')
    op.drop_table('profiles')
    op.drop_index('ix_meal_entries_user_day', table_name='meal_entries')
    op.drop_table('meal_entries')
    op.drop_index(op.f('ix_food_portions_food_id'), table_name='food_portions')
    op.drop_table('food_portions')
    op.drop_index(op.f('ix_favorite_foods_user_id'), table_name='favorite_foods')
    op.drop_table('favorite_foods')
    op.drop_index('ix_chunks_search', table_name='chunks', postgresql_using='gin')
    op.drop_index('ix_chunks_embedding', table_name='chunks', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_index(op.f('ix_chunks_document_id'), table_name='chunks')
    op.drop_table('chunks')
    op.drop_index('ix_chat_messages_user_created', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index('ix_foods_search', table_name='foods', postgresql_using='gin')
    op.drop_index('ix_foods_embedding', table_name='foods', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_index(op.f('ix_foods_barcode'), table_name='foods')
    op.drop_table('foods')
    op.drop_table('exercises')
    op.drop_table('documents')
    # ### end Alembic commands ###
