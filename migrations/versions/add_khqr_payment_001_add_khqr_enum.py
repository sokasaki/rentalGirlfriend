"""Add KHQR payment method to enum

Revision ID: add_khqr_payment_001
Revises: 3c901e9e9f75
Create Date: 2026-02-14 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_khqr_payment_001"
down_revision = "3c901e9e9f75"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("payments") as batch_op:
        batch_op.alter_column(
            "method",
            existing_type=sa.Enum("ABA", "CARD", "WING", name="paymentmethodenum"),
            type_=sa.Enum("ABA", "CARD", "KHQR", "WING", name="paymentmethodenum"),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("payments") as batch_op:
        batch_op.alter_column(
            "method",
            existing_type=sa.Enum("ABA", "CARD", "KHQR", "WING", name="paymentmethodenum"),
            type_=sa.Enum("ABA", "CARD", "WING", name="paymentmethodenum"),
            existing_nullable=False,
        )
