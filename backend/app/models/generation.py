# backend/app/models/generation.py
"""Generation request/response models."""
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Enum as SQLEnum, ForeignKey, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Provider(str, enum.Enum):
    TERRAFORM = "terraform"
    CLOUDFORMATION = "cloudformation"
    ARM = "arm"


class Target(str, enum.Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


class GenerationStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (
        Index("ix_generations_user_created", "user_id", "created_at"),
        Index("ix_generations_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[Provider] = mapped_column(SQLEnum(Provider), nullable=False)
    target: Mapped[Target] = mapped_column(SQLEnum(Target), nullable=False)

    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_estimate_usd: Mapped[float | None] = mapped_column(nullable=True)
    components: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array

    status: Mapped[GenerationStatus] = mapped_column(SQLEnum(GenerationStatus), default=GenerationStatus.PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="generations")

    def __repr__(self) -> str:
        return f"<Generation(id={self.id}, provider={self.provider.value}, target={self.target.value}, status={self.status.value})>"