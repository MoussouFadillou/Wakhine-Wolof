from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import os
import csv
import io

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = FastAPI(title="Wakhin Wolof - API Officielle de Thèse")

# -----------------------------
# Configuration
# -----------------------------

FICHIER_SAUVEGARDE = "collecte_wolof.json"
ID_DOSSIER_DRIVE = "17oylBfSgSCfuo4xGEyBFOIICtsyjT90h"

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]

# -----------------------------
# CORS (Autorise ton Frontend Vercel)
# -----------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Google Drive (Adapté pour Railway)
# -----------------------------

def obtenir_service_drive():
    # Railway va lire ces variables directement depuis son panneau de configuration
    private_key = os.environ.get("GOOGLE_PRIVATE_KEY")
    client_email = os.environ.get("GOOGLE_CLIENT_EMAIL")

    if not private_key or not client_email:
        raise HTTPException(
            status_code=500,
            detail="Configuration manquante sur Railway : GOOGLE_PRIVATE_KEY ou GOOGLE_CLIENT_EMAIL est introuvable."
        )

    try:
        # Nettoyage automatique des retours à la ligne de la clé privée pour Google
        clean_key = private_key.strip().strip('"').strip("'").replace("\\n", "\n")

        info_credentials = {
            "type": "service_account",
            "private_key": clean_key,
            "client_email": client_email,
            "token_uri": "https://oauth2.googleapis.com/token"
        }

        credentials = Credentials.from_service_account_info(
            info_credentials,
            scopes=SCOPES
        )

        service = build(
            "drive",
            "v3",
            credentials=credentials
        )

        return service

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur d'authentification Google Drive : {str(e)}"
        )

# -----------------------------
# Chargement JSON
# -----------------------------

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

# -----------------------------
# Sauvegarde JSON
# -----------------------------

def sauvegarder_donnees(data):
    with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )

# -----------------------------
# Test API
# -----------------------------

@app.get("/")
async def root():
    return {
        "status": "OK",
        "message": "Backend Wakhin Wolof opérationnel sur Railway."
    }

# -----------------------------
# Export CSV
# -----------------------------

@app.get("/api/contributions/csv")
async def exporter_csv():
    donnees = charger_donnees()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "ID", "Age", "Sexe", "Region", "Departement",
        "Accent", "Alphabetisation", "Type_Parole",
        "Transcription", "Lien_Drive"
    ])

    for row in donnees:
        writer.writerow([
            row.get("id"),
            row.get("age"),
            row.get("sexe"),
            row.get("region"),
            row.get("departement"),
            row.get("accent"),
            row.get("alphabetisation"),
            row.get("type_parole"),
            row.get("transcription"),
            row.get("audioUrl")
        ])

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=corpus_wakhin_wolof.csv"
        }
    )

# -----------------------------
# Contribution
# -----------------------------

@app.post("/api/contribuer")
async def ajouter_contribution(
    age: int = Form(...),
    sexe: str = Form(...),
    region: str = Form(...),
    departement: str = Form(...),
    accent: str = Form(...),
    alphabetisation: str = Form(...),
    type_parole: str = Form(...),
    transcription: Optional[str] = Form(""),
    audioFile: UploadFile = File(...)
):
    chemin_temporaire = f"temp_{audioFile.filename}"

    try:
        service = obtenir_service_drive()
        contenu = await audioFile.read()

        with open(chemin_temporaire, "wb") as f:
            f.write(contenu)

        type_propre = (
            type_parole
            .split("(")[0]
            .strip()
            .replace(" ", "_")
        )

        nom_drive = (
            f"{region}_{departement}_{type_propre}_{audioFile.filename}"
        )

        metadata = {
            "name": nom_drive,
            "parents": [ID_DOSSIER_DRIVE]
        }

        media = MediaFileUpload(
            chemin_temporaire,
            mimetype=audioFile.content_type,
            resumable=True
        )

        fichier = service.files().create(
            body=metadata,
            media_body=media,
            fields="id"
        ).execute()

        file_id = fichier["id"]

        service.permissions().create(
            fileId=file_id,
            body={
                "type": "anyone",
                "role": "reader"
            }
        ).execute()

        # Lien optimisé pour le streaming audio direct
        lien = f"https://docs.google.com/uc?export=download&id={file_id}"

        donnees = charger_donnees()

        nouvelle = {
            "id": len(donnees) + 1,
            "age": age,
            "sexe": sexe,
            "region": region,
            "departement": department if 'department' in locals() else departement,
            "accent": accent,
            "alphabetisation": alphabetisation,
            "type_parole": type_parole,
            "transcription": transcription if transcription else "",
            "audioUrl": lien
        }

        donnees.append(nouvelle)
        sauvegarder_donnees(donnees)

        return {
            "success": True,
            "message": "Contribution enregistrée.",
            "data": nouvelle
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if os.path.exists(chemin_temporaire):
            os.remove(chemin_temporaire)
