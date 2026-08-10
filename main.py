
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


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "Wakhin Wolof API"

APP_VERSION = "3.0.0"

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://wakhine-wolof-frontend-qfq4.vercel.app",
)


# ============================================================
# DATABASE
# ============================================================

try:
    Base.metadata.create_all(bind=engine)
    print("✅ PostgreSQL : connexion initialisée")
except Exception as error:
    print(
        "❌ Erreur lors de l'initialisation PostgreSQL :",
        error,
    )


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title=APP_NAME,
    description=(
        "API de collecte de données "
        "audio et sociolinguistiques Wolof"
    ),
    version=APP_VERSION,
)


# ============================================================
# CORS
# ============================================================

origins = []

if FRONTEND_URL:
    origins = [
        url.strip().rstrip("/")
        for url in FRONTEND_URL.split(",")
        if url.strip()
    ]

# Autoriser également le frontend Vercel connu
default_frontend = (
    "https://wakhine-wolof-frontend-qfq4.vercel.app"
)

if default_frontend not in origins:
    origins.append(default_frontend)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def nettoyer_nom(nom: str) -> str:
    """
    Nettoie une chaîne pour créer un nom de fichier propre.
    """

    nom = nom.strip()

    nom = re.sub(
        r"[^a-zA-Z0-9À-ÿ_ -]",
        "",
        nom,
    )

    nom = re.sub(
        r"\s+",
        "_",
        nom,
    )

    return nom


def obtenir_extension_audio(
    content_type: str,
    filename: str | None,
) -> str:

    if content_type:
        if "webm" in content_type:
            return ".webm"

        if "ogg" in content_type:
            return ".ogg"

        if "wav" in content_type:
            return ".wav"

        if "mpeg" in content_type:
            return ".mp3"

        if "mp4" in content_type:
            return ".m4a"

    if filename:
        extension = os.path.splitext(
            filename
        )[1].lower()

        if extension:
            return extension

    return ".webm"


# ============================================================
# ROUTE RACINE
# ============================================================

@app.get("/")
def root():

    return {
        "status": "OK",
        "service": "wakhin-wolof-api",
        "version": APP_VERSION,
        "message": (
            "Backend Wakhin Wolof "
            "opérationnel."
        ),
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "wakhin-wolof-api",
        "database": "PostgreSQL",
        "storage": "Google Drive",
    }


# ============================================================
# AJOUTER UNE CONTRIBUTION
# ============================================================

@app.post("/api/contribuer")
async def ajouter_contribution(

    age: int = Form(...),

    sexe: str = Form(...),

    region: str = Form(...),

    departement: str = Form(...),

    accent: str = Form(...),

    alphabetisation: str = Form(...),

    type_parole: str = Form(...),

    transcription: str = Form(""),

    audioFile: UploadFile = File(...),

    db: Session = Depends(get_db),

):

    print("")
    print("=" * 70)
    print("📥 NOUVELLE CONTRIBUTION")
    print("=" * 70)

    # ========================================================
    # VALIDATION DES DONNÉES
    # ========================================================

    if age < 1 or age > 120:

        raise HTTPException(
            status_code=400,
            detail=(
                "L'âge doit être compris "
                "entre 1 et 120 ans."
            ),
        )

    if not sexe.strip():

        raise HTTPException(
            status_code=400,
            detail="Le sexe est obligatoire.",
        )

    if not region.strip():

        raise HTTPException(
            status_code=400,
            detail="La région est obligatoire.",
        )

    if not departement.strip():

        raise HTTPException(
            status_code=400,
            detail="Le département est obligatoire.",
        )

    if not accent.strip():

        raise HTTPException(
            status_code=400,
            detail="L'accent régional est obligatoire.",
        )

    if not alphabetisation.strip():

        raise HTTPException(
            status_code=400,
            detail=(
                "Le niveau d'alphabétisation "
                "est obligatoire."
            ),
        )

    if not type_parole.strip():

        raise HTTPException(
            status_code=400,
            detail="Le type de parole est obligatoire.",
        )

    # ========================================================
    # LECTURE AUDIO
    # ========================================================

    try:

        contenu = await audioFile.read()

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=(
                "Impossible de lire le fichier audio : "
                f"{error}"
            ),
        )

    if not contenu:

        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide.",
        )

    print(
        f"🎙️ Audio reçu : "
        f"{len(contenu) / 1024:.2f} Ko"
    )

    # ========================================================
    # TYPE AUDIO
    # ========================================================

    content_type = (
        audioFile.content_type
        or "audio/webm"
    )

    print(
        f"🎵 Type audio : {content_type}"
    )

    extension = obtenir_extension_audio(
        content_type,
        audioFile.filename,
    )

    # ========================================================
    # NOM DU FICHIER
    # ========================================================

    region_propre = nettoyer_nom(
        region
    )

    departement_propre = nettoyer_nom(
        departement
    )

    type_propre = nettoyer_nom(
        type_parole.split("(")[0]
    )

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d_%H%M%S"
    )

    nom_fichier = (
        f"wolof_"
        f"{region_propre}_"
        f"{departement_propre}_"
        f"{type_propre}_"
        f"{timestamp}_"
        f"{extension}"
    )

    print(
        f"📁 Nom fichier : {nom_fichier}"
    )

    # ========================================================
    # GOOGLE DRIVE
    # ========================================================

    try:

        print(
            "☁️ Upload vers Google Drive..."
        )

        file_id, audio_url = uploader_audio(

            contenu=contenu,

            nom_fichier=nom_fichier,

            content_type=content_type,

        )

        print(
            "✅ Google Drive : upload réussi"
        )

        print(
            f"📌 File ID : {file_id}"
        )

        print(
            f"🔗 URL : {audio_url}"
        )

    except Exception as error:

        print(
            "❌ ERREUR GOOGLE DRIVE"
        )

        print(error)

        db.rollback()

        raise HTTPException(

            status_code=500,

            detail=(
                "L'audio n'a pas pu être "
                "enregistré dans Google Drive. "
                f"Détail : {str(error)}"
            ),
        )

    # ========================================================
    # POSTGRESQL
    # ========================================================

    try:

        print(
            "🗄️ Enregistrement PostgreSQL..."
        )

        contribution = Contribution(

            age=age,

            sexe=sexe.strip(),

            region=region.strip(),

            departement=departement.strip(),

            accent=accent.strip(),

            alphabetisation=(
                alphabetisation.strip()
            ),

            type_parole=(
                type_parole.strip()
            ),

            transcription=(
                transcription.strip()
                if transcription
                else ""
            ),

            audio_url=audio_url,

            google_drive_file_id=file_id,

        )

        db.add(
            contribution
        )

        db.commit()

        db.refresh(
            contribution
        )

        print(
            "✅ PostgreSQL : contribution enregistrée"
        )

        print(
            f"🆔 ID contribution : "
            f"{contribution.id}"
        )

    except Exception as error:

        db.rollback()

        print(
            "❌ ERREUR POSTGRESQL"
        )

        print(error)

        raise HTTPException(

            status_code=500,

            detail=(
                "L'audio a été envoyé vers "
                "Google Drive mais les "
                "métadonnées n'ont pas pu être "
                "enregistrées dans PostgreSQL. "
                f"Détail : {str(error)}"
            ),
        )

    # ========================================================
    # RÉPONSE
    # ========================================================

    return {

        "success": True,

        "message": (
            "Contribution enregistrée "
            "avec succès."
        ),

        "data": {

            "id": contribution.id,

            "age": contribution.age,

            "sexe": contribution.sexe,

            "region": contribution.region,

            "departement": (
                contribution.departement
            ),

            "accent": contribution.accent,

            "alphabetisation": (
                contribution.alphabetisation
            ),

            "type_parole": (
                contribution.type_parole
            ),

            "transcription": (
                contribution.transcription
            ),

            "audioUrl": (
                contribution.audio_url
            ),

            "googleDriveFileId": (
                contribution.google_drive_file_id
            ),

            "created_at": (
                str(contribution.created_at)
                if contribution.created_at
                else None
            ),
        },
    }


# ============================================================
# EXPORT CSV
# ============================================================

@app.get("/api/contributions/csv")
def exporter_csv(

    db: Session = Depends(get_db),

):

    try:

        print(
            "📥 Export CSV demandé"
        )

        contributions = (

            db.query(
                Contribution
            )

            .order_by(
                Contribution.id.asc()
            )

            .all()
        )

        output = io.StringIO()

        writer = csv.writer(
            output,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
        )

        # ====================================================
        # TOUTES LES COLONNES
        # ====================================================

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

            "Date_Creation",

        ])

        # ====================================================
        # DONNÉES
        # ====================================================

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

                contribution.created_at,

            ])

        output.seek(0)

        fichier = io.BytesIO(
            output.getvalue().encode(
                "utf-8-sig"
            )
        )

        print(
            f"✅ CSV généré : "
            f"{len(contributions)} contributions"
        )

        return StreamingResponse(

            fichier,

            media_type="text/csv; charset=utf-8",

            headers={

                "Content-Disposition":
                    "attachment; "
                    "filename="
                    "corpus_wakhin_wolof.csv"

            },
        )

    except Exception as error:

        print(
            "❌ ERREUR EXPORT CSV"
        )

        print(error)

        raise HTTPException(

            status_code=500,

            detail=(
                "Impossible de générer "
                f"le fichier CSV : {str(error)}"
            ),
        )
```
