from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

app = FastAPI(title="Wakhin Wolof - Collecte Publique")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FICHIER_CREDENTIALS = "credentials.json"  # À mettre dans "Secret Files" sur Render
ID_DOSSIER_DRIVE = "TON_ID_DE_DOSSIER_GOOGLE_DRIVE"  # ⚠️ Mets l'ID de ton dossier Drive
FICHIER_SAUVEGARDE = "collecte_wolof.json"

def obtenir_service_drive():
    if not os.path.exists(FICHIER_CREDENTIALS):
        raise HTTPException(status_code=500, detail="Erreur d'authentification Cloud.")
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(FICHIER_CREDENTIALS, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def sauvegarder_donnees(donnees):
    with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)

@app.get("/api/contributions")
def obtenir_contributions():
    return charger_donnees()

@app.post("/api/contribuer", status_code=201)
async def ajouter_contribution(
    region: str = Form(...),
    saitLire: str = Form(...),  # "Oui" ou "Non"
    audioFile: UploadFile = File(...)  # L'audio est obligatoire ici !
):
    try:
        service = obtenir_service_drive()
        
        # Nom du fichier personnalisé pour ton Drive : ex "Dakar_NonLecteur_audio.mp3"
        nom_fichier = f"{region}_{saitLire}_{audioFile.filename}"
        
        file_metadata = {
            'name': nom_fichier,
            'parents': [ID_DOSSIER_DRIVE]
        }
        
        contenu = await audioFile.read()
        fh = io.BytesIO(contenu)
        media = MediaIoBaseUpload(fh, mimetype=audioFile.content_type, resumable=True)
        
        # Envoi Drive
        fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        id_fichier = fichier_drive.get('id')
        
        # Rendre public le lien
        service.permissions().create(fileId=id_fichier, body={'type': 'anyone', 'role': 'reader'}).execute()
        lien_audio = f"https://docs.google.com/uc?export=download&id={id_fichier}"

        # Sauvegarde de la contribution
        liste_contributions = charger_donnees()
        nouvelle_entree = {
            "id": len(liste_contributions) + 1,
            "region": region,
            "sait_lire": saitLire,
            "audioUrl": lien_audio
        }
        liste_contributions.append(nouvelle_entree)
        sauvegarder_donnees(liste_contributions)
        
        return nouvelle_entree

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
