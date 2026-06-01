from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import csv

app = FastAPI(
    title="Kalama Wolof API",
    description="Moteur de gestion sécurisé pour la collecte de données ASR Wolof",
    version="1.4.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "kalama_dataset_wav"
CSV_FILE_PATH = "kalama_dataset.csv"

os.makedirs(UPLOAD_DIR, exist_ok=True)


def append_to_kalama_csv(metadata: dict):
    # Uniquement les données sociolinguistiques essentielles pour la thèse
    fieldnames = ["audio_path", "transcript", "region", "accent", "gender", "age", "literacy", "speech_type"]
    file_exists = os.path.isfile(CSV_FILE_PATH)

    with open(CSV_FILE_PATH, mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(metadata)


@app.post("/api/collecte")
async def collect_voice(
        audio: UploadFile = File(...),
        transcript: str = Form(...),
        region: str = Form(...),
        accent: str = Form(...),
        gender: str = Form(...),
        age: int = Form(...),
        literacy: str = Form(...),
        speech_type: str = Form(...),
        secret_key: str = Form(...)
):
    if secret_key != "WOLOF2026":
        raise HTTPException(status_code=403, detail="Accès refusé. Clé invalide.")

    if not audio.filename.lower().endswith(('.wav', '.blob')):
        raise HTTPException(status_code=400, detail="Format audio non valide.")

    audio_content = await audio.read()
    if len(audio_content) == 0:
        raise HTTPException(status_code=400, detail="Échantillon audio vide.")

    if len(audio_content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop lourd (Max 5 Mo).")

    unique_filename = f"{uuid.uuid4()}.wav"
    relative_audio_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(relative_audio_path, "wb") as buffer:
            buffer.write(audio_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'écriture : {str(e)}")

    metadata_row = {
        "audio_path": relative_audio_path,
        "transcript": transcript,
        "region": region,
        "accent": accent,
        "gender": gender,
        "age": age,
        "literacy": literacy,
        "speech_type": speech_type
    }

    try:
        append_to_kalama_csv(metadata_row)
    except Exception as e:
        if os.path.exists(relative_audio_path):
            os.remove(relative_audio_path)
        raise HTTPException(status_code=500, detail=f"Erreur CSV : {str(e)}")

    return {"status": "success", "audio_path": relative_audio_path}


@app.get("/api/download-csv")
async def download_dataset_csv():
    if not os.path.isfile(CSV_FILE_PATH):
        raise HTTPException(status_code=404, detail="Le fichier CSV n'existe pas.")
    return FileResponse(path=CSV_FILE_PATH, filename="kalama_dataset.csv", media_type="text/csv")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)