import os
import csv
import io

from fastapi import FastAPI, Depends, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import Contribution
from google_drive import uploader_audio


# ============================================================
# CONFIGURATION
# ============================================================

APP_VERSION = "3.0.0"

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://wakhine-wolof-frontend-qfq4.vercel.app"
)


# ============================================================
# APPLICATION FASTAPI
# ============================================================

app = FastAPI(
    title="Wakhin Wolof API",
    description="API de collecte de données vocales en Wolof",
    version=APP_VERSION
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_URL,
        "https://wakhine-wolof-frontend-qfq4.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INITIALISATION DE LA BASE DE DONNÉES
# ============================================================

try:
    Base.metadata.create_all(bind=engine)
    print("PostgreSQL initialisé avec succès.")
except Exception as e:
    print(f"Erreur initialisation PostgreSQL : {e}")


# ============================================================
# ROUTE RACINE
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Wakhin Wolof API",
        "version": APP_VERSION,
        "status": "online",
        "frontend": FRONTEND_URL
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": "PostgreSQL",
        "storage": "Google Drive"
    }


# ============================================================
# CONTRIBUTION
# ============================================================

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
    """
    Reçoit une contribution depuis le frontend.

    1. Vérifie les données
    2. Envoie l'audio vers Google Drive
    3. Enregistre les métadonnées dans PostgreSQL
    """

    # --------------------------------------------------------
    # VALIDATION ÂGE
    # --------------------------------------------------------

    if age < 1 or age > 120:
        raise HTTPException(
            status_code=400,
            detail="L'âge doit être compris entre 1 et 120 ans."
        )

    # --------------------------------------------------------
    # VALIDATION DES CHAMPS
    # --------------------------------------------------------

    champs = {
        "sexe": sexe,
        "region": region,
        "departement": departement,
        "accent": accent,
        "alphabetisation": alphabetisation,
        "type_parole": type_parole,
    }

    for nom, valeur in champs.items():
        if not valeur or not valeur.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Le champ '{nom}' est obligatoire."
            )

    # --------------------------------------------------------
    # VALIDATION AUDIO
    # --------------------------------------------------------

    if not audioFile:
        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est obligatoire."
        )

    if not audioFile.filename:
        raise HTTPException(
            status_code=400,
            detail="Le nom du fichier audio est invalide."
        )

    # --------------------------------------------------------
    # ENVOI VERS GOOGLE DRIVE
    # --------------------------------------------------------

    try:
        print(
            f"Réception audio : "
            f"{audioFile.filename}"
        )

        print("Envoi de l'audio vers Google Drive...")

        drive_result = await uploader_audio(audioFile)

        print("Audio envoyé vers Google Drive.")

    except Exception as e:
        print(
            f"Erreur Google Drive : {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de l'envoi de l'audio "
                f"vers Google Drive : {str(e)}"
            )
        )

    # --------------------------------------------------------
    # RÉCUPÉRATION DES INFORMATIONS GOOGLE DRIVE
    # --------------------------------------------------------

    audio_url = None
    google_drive_file_id = None

    if isinstance(drive_result, dict):
        audio_url = (
            drive_result.get("audio_url")
            or drive_result.get("webViewLink")
            or drive_result.get("url")
        )

        google_drive_file_id = (
            drive_result.get("google_drive_file_id")
            or drive_result.get("file_id")
            or drive_result.get("id")
        )

    elif isinstance(drive_result, str):
        audio_url = drive_result

    # --------------------------------------------------------
    # ENREGISTREMENT DANS POSTGRESQL
    # --------------------------------------------------------

    try:

        contribution = Contribution(
            age=age,
            sexe=sexe.strip(),
            region=region.strip(),
            departement=departement.strip(),
            accent=accent.strip(),
            alphabetisation=alphabetisation.strip(),
            type_parole=type_parole.strip(),
            transcription=transcription.strip(),
            audio_url=audio_url,
            google_drive_file_id=google_drive_file_id
        )

        db.add(contribution)
        db.commit()
        db.refresh(contribution)

        print(
            f"Contribution enregistrée : "
            f"{contribution.id}"
        )

    except Exception as e:

        db.rollback()

        print(
            f"Erreur PostgreSQL : {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "L'audio a été envoyé vers Google Drive, "
                "mais l'enregistrement PostgreSQL a échoué : "
                f"{str(e)}"
            )
        )

    # --------------------------------------------------------
    # RÉPONSE
    # --------------------------------------------------------

    return {
        "success": True,
        "message": "Contribution enregistrée avec succès.",
        "id": contribution.id,
        "audio_url": audio_url,
        "google_drive_file_id": google_drive_file_id
    }


# ============================================================
# EXPORT CSV
# ============================================================

@app.get("/api/contributions/csv")
def exporter_contributions_csv(
    db: Session = Depends(get_db)
):

    try:

        contributions = (
            db.query(Contribution)
            .order_by(Contribution.created_at.desc())
            .all()
        )

        output = io.StringIO()

        writer = csv.writer(
            output,
            delimiter=";"
        )

        # ----------------------------------------------------
        # EN-TÊTES
        # ----------------------------------------------------

        writer.writerow([
            "id",
            "age",
            "sexe",
            "region",
            "departement",
            "accent",
            "alphabetisation",
            "type_parole",
            "transcription",
            "audio_url",
            "google_drive_file_id",
            "created_at"
        ])

        # ----------------------------------------------------
        # DONNÉES
        # ----------------------------------------------------

        for contribution in contributions:

            writer.writerow([
                contribution.id,
                contribution.age,
                contribution.sexe,
                contribution.region,
                contribution.departement,
                contribution.accent,
                contribution.alphabetisation,
                contribution.type_parole,
                contribution.transcription,
                contribution.audio_url,
                contribution.google_drive_file_id,
                contribution.created_at
            ])

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    "attachment; filename=corpus_wakhin_wolof.csv"
            }
        )

    except Exception as e:

        print(
            f"Erreur export CSV : {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de l'export CSV : "
                f"{str(e)}"
            )
        )
