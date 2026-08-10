import csv
import io
import os
import re
from datetime import datetime

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Contribution
from google_drive import uploader_audio


# =====================================================
# CONFIGURATION
# =====================================================

APP_NAME = "Wakhin Wolof API"
APP_VERSION = "3.0.0"

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://wakhine-wolof-frontend-qfq4.vercel.app"
)


# =====================================================
# DATABASE
# =====================================================

try:
    Base.metadata.create_all(bind=engine)
    print("✅ PostgreSQL initialisé")

except Exception as error:
    print(
        "❌ Erreur PostgreSQL :",
        error
    )


# =====================================================
# FASTAPI
# =====================================================

app = FastAPI(
    title=APP_NAME,
    description=(
        "API de collecte de données "
        "audio et sociolinguistiques Wolof"
    ),
    version=APP_VERSION,
)


# =====================================================
# CORS
# =====================================================

origins = [
    url.strip()
    for url in FRONTEND_URL.split(",")
    if url.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# UTILITAIRES
# =====================================================

def nettoyer_nom(nom: str):

    nom = nom.strip()

    nom = re.sub(
        r"[^a-zA-Z0-9À-ÿ_-]",
        "",
        nom
    )

    return nom.replace(
        " ",
        "_"
    )


def extension_audio(
    content_type,
    filename
):

    if content_type:

        if "webm" in content_type:
            return ".webm"

        if "wav" in content_type:
            return ".wav"

        if "ogg" in content_type:
            return ".ogg"


    if filename:

        ext = os.path.splitext(
            filename
        )[1]

        if ext:
            return ext


    return ".webm"



# =====================================================
# ROUTES TEST
# =====================================================

@app.get("/")
def root():

    return {
        "status": "OK",
        "service": "wakhin-wolof-api",
        "version": APP_VERSION
    }



@app.get("/health")
def health():

    return {
        "status": "healthy",
        "database": "PostgreSQL",
        "storage": "Google Drive"
    }



# =====================================================
# AJOUT CONTRIBUTION
# =====================================================

@app.post("/api/contribuer")
async def contribuer(

    age: int = Form(...),

    sexe: str = Form(...),

    region: str = Form(...),

    departement: str = Form(...),

    accent: str = Form(...),

    alphabetisation: str = Form(...),

    type_parole: str = Form(...),

    transcription: str = Form(""),

    audioFile: UploadFile = File(...),

    db: Session = Depends(get_db)

):

    print("📥 Nouvelle contribution")


    if age < 1 or age > 120:

        raise HTTPException(
            400,
            "Age invalide"
        )


    contenu = await audioFile.read()


    if not contenu:

        raise HTTPException(
            400,
            "Audio vide"
        )


    content_type = (
        audioFile.content_type
        or "audio/webm"
    )


    nom_fichier = (

        "wolof_"
        + nettoyer_nom(region)
        + "_"
        + nettoyer_nom(departement)
        + "_"
        + datetime.utcnow().strftime(
            "%Y%m%d_%H%M%S"
        )
        + extension_audio(
            content_type,
            audioFile.filename
        )

    )


    # ==============================
    # GOOGLE DRIVE
    # ==============================

    try:

        file_id, audio_url = uploader_audio(

            contenu=contenu,

            nom_fichier=nom_fichier,

            content_type=content_type

        )

        print(
            "✅ Audio Drive OK"
        )


    except Exception as error:

        print(
            "❌ Drive erreur:",
            error
        )

        raise HTTPException(
            500,
            str(error)
        )


    # ==============================
    # POSTGRESQL
    # ==============================

    try:

        contribution = Contribution(

            age=age,

            sexe=sexe,

            region=region,

            departement=departement,

            accent=accent,

            alphabetisation=alphabetisation,

            type_parole=type_parole,

            transcription=transcription,

            audio_url=audio_url,

            google_drive_file_id=file_id

        )


        db.add(
            contribution
        )

        db.commit()

        db.refresh(
            contribution
        )


        print(
            "✅ PostgreSQL OK"
        )


    except Exception as error:

        db.rollback()

        print(
            "❌ PostgreSQL erreur:",
            error
        )

        raise HTTPException(
            500,
            str(error)
        )



    return {

        "success": True,

        "message":
        "Contribution enregistrée",

        "id":
        contribution.id,

        "audio_url":
        audio_url

    }



# =====================================================
# EXPORT CSV
# =====================================================

@app.get("/api/contributions/csv")
def export_csv(

    db: Session = Depends(get_db)

):

    contributions = (

        db.query(
            Contribution
        )

        .order_by(
            Contribution.id
        )

        .all()

    )


    output = io.StringIO()


    writer = csv.writer(
        output,
        delimiter=";"
    )


    writer.writerow([

        "ID",
        "Age",
        "Sexe",
        "Region",
        "Departement",
        "Accent",
        "Alphabetisation",
        "Type_Parole",
        "Transcription",
        "Audio_URL",
        "Google_Drive_File_ID",
        "Date"

    ])



    for c in contributions:

        writer.writerow([

            c.id,
            c.age,
            c.sexe,
            c.region,
            c.departement,
            c.accent,
            c.alphabetisation,
            c.type_parole,
            c.transcription,
            c.audio_url,
            c.google_drive_file_id,
            c.created_at

        ])



    output.seek(0)


    return StreamingResponse(

        io.BytesIO(
            output.getvalue()
            .encode("utf-8-sig")
        ),

        media_type="text/csv",

        headers={

            "Content-Disposition":
            "attachment; filename=corpus_wolof.csv"

        }

    )
