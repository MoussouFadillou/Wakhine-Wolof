import csv
import io
import os

from fastapi import (
    FastAPI,
    Depends,
    File,
    Form,
    UploadFile,
    HTTPException
)

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
# APPLICATION
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
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# INITIALISATION POSTGRESQL
# ============================================================

try:

    Base.metadata.create_all(
        bind=engine
    )

    print(
        "PostgreSQL initialisé avec succès."
    )

except Exception as error:

    print(
        f"Erreur PostgreSQL : {error}"
    )


# ============================================================
# ROUTE PRINCIPALE
# ============================================================

@app.get("/")
def root():

    return {
        "message": "Wakhin Wolof API",
        "version": APP_VERSION,
        "status": "online"
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
# CONTRIBUER
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

    print(
        "=========================================="
    )

    print(
        "Nouvelle contribution reçue."
    )

    # ========================================================
    # VALIDATION AGE
    # ========================================================

    if age < 1 or age > 120:

        raise HTTPException(
            status_code=400,
            detail="L'âge doit être compris entre 1 et 120 ans."
        )

    # ========================================================
    # VALIDATION DES CHAMPS
    # ========================================================

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

    # ========================================================
    # VALIDATION AUDIO
    # ========================================================

    if audioFile is None:

        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est obligatoire."
        )

    if not audioFile.filename:

        raise HTTPException(
            status_code=400,
            detail="Le nom du fichier audio est invalide."
        )

    print(
        f"Fichier reçu : {audioFile.filename}"
    )

    print(
        f"Type audio : {audioFile.content_type}"
    )

    # ========================================================
    # LECTURE DU FICHIER AUDIO
    # ========================================================

    try:

        contenu_audio = await audioFile.read()

    except Exception as error:

        print(
            f"Erreur lecture audio : {error}"
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "Impossible de lire le fichier audio : "
                f"{error}"
            )
        )

    if not contenu_audio:

        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide."
        )

    print(
        f"Taille audio : {len(contenu_audio)} octets"
    )

    # ========================================================
    # GOOGLE DRIVE
    # ========================================================

    try:

        print(
            "Envoi vers Google Drive..."
        )

        file_id, audio_url = uploader_audio(
            contenu_audio,
            audioFile.filename,
            audioFile.content_type or "audio/webm"
        )

        print(
            f"Google Drive OK : {file_id}"
        )

    except Exception as error:

        print(
            f"Erreur Google Drive : {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de l'envoi vers Google Drive : "
                f"{error}"
            )
        )

    # ========================================================
    # POSTGRESQL
    # ========================================================

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
            f"PostgreSQL OK : contribution {contribution.id}"
        )

    except Exception as error:

        db.rollback()

        print(
            f"Erreur PostgreSQL : {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "L'audio a été envoyé vers Google Drive, "
                "mais l'enregistrement PostgreSQL a échoué : "
                f"{error}"
            )
        )

    # ========================================================
    # RÉPONSE
    # ========================================================

    print(
        "Contribution terminée avec succès."
    )

    print(
        "=========================================="
    )

    return {
        "success": True,
        "message": "Contribution enregistrée avec succès.",
        "id": contribution.id,
        "audio_url": audio_url,
        "google_drive_file_id": file_id
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
            .order_by(
                Contribution.created_at.desc()
            )
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
            iter([
                output.getvalue()
            ]),
            media_type="text/csv",
            headers={
                "Content-Disposition":
                    "attachment; "
                    "filename=corpus_wakhin_wolof.csv"
            }
        )

    except Exception as error:

        print(
            f"Erreur export CSV : {error}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de l'export CSV : "
                f"{error}"
            )
        )
