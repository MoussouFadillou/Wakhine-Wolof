import csv
import io
import os

from fastapi import (
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from database import (
    create_contribution,
    list_all_contributions
)

from storage import upload_audio


app = FastAPI(
    title="Wakhin Wolof API",
    version="5.0.0"
)


FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://wakhine-wolof-frontend-qfq4.vercel.app"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Wakhin Wolof API",
        "version": "5.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "wakhin-wolof-api"
    }


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
    audioFile: UploadFile = File(...)
):

    if age < 1 or age > 120:
        raise HTTPException(
            status_code=400,
            detail="L'âge doit être compris entre 1 et 120."
        )

    values = {
        "sexe": sexe,
        "region": region,
        "departement": departement,
        "accent": accent,
        "alphabetisation": alphabetisation,
        "type_parole": type_parole
    }

    for field, value in values.items():

        if not value or not value.strip():

            raise HTTPException(
                status_code=400,
                detail=f"Le champ {field} est obligatoire."
            )

    content = await audioFile.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide."
        )

    try:

        audio_path = upload_audio(
            content=content,
            original_name=audioFile.filename or "audio.wav",
            content_type=audioFile.content_type or "audio/wav"
        )

        row = create_contribution(
            age=age,
            sexe=sexe,
            region=region,
            departement=departement,
            accent=accent,
            alphabetisation=alphabetisation,
            type_parole=type_parole,
            transcription=transcription,
            audio_path=audio_path,
            audio_filename=audioFile.filename or "audio.wav",
            audio_content_type=audioFile.content_type or "audio/wav"
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

    return {
        "success": True,
        "message": "Contribution enregistrée avec succès.",
        "contribution": row,
        "audio_path": audio_path
    }


@app.get("/api/contributions/csv")
def contributions_csv():

    try:

        rows = list_all_contributions()

        output = io.StringIO()

        fields = [
            "id",
            "age",
            "sexe",
            "region",
            "departement",
            "accent",
            "alphabetisation",
            "type_parole",
            "transcription",
            "audio_path",
            "audio_filename",
            "audio_content_type",
            "created_at"
        ]

        writer = csv.DictWriter(
            output,
            fieldnames=fields,
            delimiter=";"
        )

        writer.writeheader()

        for row in rows:

            writer.writerow({
                field: row.get(field, "")
                for field in fields
            })

        return Response(
            content=output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition":
                    'attachment; filename="corpus_wakhin_wolof.csv"'
            }
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Erreur CSV : {exc}"
        )
