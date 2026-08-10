from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from database import Base


class Contribution(Base):

    __tablename__ = "contributions"


    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    age = Column(
        Integer,
        nullable=False
    )


    sexe = Column(
        String(50),
        nullable=False
    )


    region = Column(
        String(100),
        nullable=False
    )


    departement = Column(
        String(100),
        nullable=False
    )


    accent = Column(
        String(150),
        nullable=False
    )


    alphabetisation = Column(
        String(200),
        nullable=False
    )


    type_parole = Column(
        String(200),
        nullable=False
    )


    transcription = Column(
        Text,
        nullable=True
    )


    audio_url = Column(
        Text,
        nullable=False
    )


    google_drive_file_id = Column(
        String(255),
        nullable=False
    )


    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
