import csv
import io
import os

from fastapi import Depends
from fastapi import FastAPI
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import UploadFile

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import StreamingResponse

from sqlalchemy.orm import Session

from database import Base
from database import engine
from database import get_db

from google_drive import uploader_audio

from models import Contribution


# --------------------------------------------------
# Création de la base de données
# --------------------------------------------------

Base.metadata.create_all(
    bind=engine
)


# --------------------------------------------------
# Application FastAPI
# --------------------------------------------------

app = FastAPI(

    title="Wakhin Wolof API",

    description=(
        "API de collecte de données "
        "audio et sociolinguistiques Wolof"
    ),

    version="2.0.0"

)


# --------------------------------------------------
# CORS
# --------------------------------------------------

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "*"
)


origins = [

    FRONTEND_URL

]


# Pendant le développement, plusieurs URLs
# peuvent être séparées par des virgules
if "," in FRONTEND_URL:

    origins = [

        url.strip()

        for url in FRONTEND_URL.split(",")

    ]


app.add_middleware(

    CORSMiddleware,

    allow_origins=origins,

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]

)


# --------------------------------------------------
# Route principale
# --------------------------------------------------

@app.get("/")
def root():

    return {

        "status": "OK",

        "message": (
            "Backend Wakhin Wolof "
            "opérationnel."
        )

    }


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
def health():

    return {

        "status": "healthy",

        "service": "wakhin-wolof-api"

    }


# --------------------------------------------------
# Ajouter une contribution
# --------------------------------------------------

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

    db: Session = Depends(get_db)

):

    try:

        # ------------------------------------------
        # Validation de l'âge
        # ------------------------------------------

        if age < 1 or age > 120:

            raise HTTPException(

                status_code=400,

                detail=(
                    "L'âge doit être compris "
                    "entre 1 et 120 ans."
                )

            )


        # ------------------------------------------
        # Lecture de l'audio
        # ------------------------------------------

        contenu = await audioFile.read()


        if not contenu:

            raise HTTPException(

                status_code=400,

                detail="Le fichier audio est vide."

            )


        # ------------------------------------------
        # Type MIME
        # ------------------------------------------

        content_type = (

            audioFile.content_type

            or "audio/webm"

        )


        # ------------------------------------------
        # Nettoyage du nom
        # ------------------------------------------

        region_propre = (

            region

            .strip()

            .replace(" ", "_")

        )


        departement_propre = (

            departement

            .strip()

            .replace(" ", "_")

        )


        type_propre = (

            type_parole

            .split("(")[0]

            .strip()

            .replace(" ", "_")

        )


        nom_fichier = (

            f"{region_propre}_"

            f"{departement_propre}_"

            f"{type_propre}_"

            f"{audioFile.filename}"

        )


        # ------------------------------------------
        # Upload Google Drive
        # ------------------------------------------

        file_id, audio_url = uploader_audio(

            contenu=contenu,

            nom_fichier=nom_fichier,

            content_type=content_type

        )


        # ------------------------------------------
        # Sauvegarde PostgreSQL
        # ------------------------------------------

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


        return {

            "success": True,

            "message": (

                "Contribution enregistrée "
                "avec succès."

            ),

            "data": {

                "id": contribution.id,

                "age": contribution.age,

                "region": contribution.region,

                "audioUrl": contribution.audio_url

            }

        }


    except HTTPException:

        raise


    except Exception as error:

        db.rollback()


        raise HTTPException(

            status_code=500,

            detail=str(error)

        )


# --------------------------------------------------
# Export CSV
# --------------------------------------------------

@app.get("/api/contributions/csv")
def exporter_csv(

    db: Session = Depends(get_db)

):

    contributions = (

        db.query(Contribution)

        .order_by(

            Contribution.id.asc()

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

        "Lien_Drive",

        "Date"

    ])


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

            contribution.created_at

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

            "attachment; "

            "filename=corpus_wakhin_wolof.csv"

        }

    )
