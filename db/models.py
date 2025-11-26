from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cvs: Mapped[list["CV"]] = relationship(back_populates="user")
    preferences: Mapped[Optional["Preference"]] = relationship(back_populates="user", uselist=False)
    states: Mapped[Optional["UserState"]] = relationship(back_populates="user", uselist=False)


class CV(Base):
    __tablename__ = "cvs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    analysis: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="cvs")


class Preference(Base):
    __tablename__ = "preferences"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    contract_types: Mapped[list] = mapped_column(JSON, default=list)
    min_match_score: Mapped[int] = mapped_column(Integer, default=70)
    notify_via_email: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship(back_populates="preferences")


class JobOffer(Base):
    __tablename__ = "job_offers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(4000))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    source: Mapped[Optional[str]] = mapped_column(String(120))
    created: Mapped[Optional[str]] = mapped_column(String(64))
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    extracted_skills: Mapped[list] = mapped_column(JSON, default=list)

    __table_args__ = (
        UniqueConstraint('title', 'company', 'url', name='uq_offer_title_company_url'),
    )


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    offer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("job_offers.id"), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(50), default="success")

    user: Mapped["User"] = relationship("User")
    offer: Mapped[Optional["JobOffer"]] = relationship("JobOffer")


class UserState(Base):
    __tablename__ = "user_state"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    favorites: Mapped[list] = mapped_column(JSON, default=list)
    viewed: Mapped[list] = mapped_column(JSON, default=list)
    hidden: Mapped[list] = mapped_column(JSON, default=list)

    user: Mapped[User] = relationship(back_populates="states")
