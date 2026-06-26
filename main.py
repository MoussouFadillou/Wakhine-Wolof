# 1. Les imports (tout en haut du fichier)
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import os
import csv
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 2. L'initialisation de l'application
app = FastAPI(title="Wakhin Wolof - API de Collecte")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FICHIER_SAUVEGARDE = "collecte_wolof.json"

# 3. Ton ID de dossier Google Drive
ID_DOSSIER_DRIVE = "1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ"

# 4. C'EST ICI QUE TU METS LA FONCTION ! 
def obtenir_service_drive():
    chemin_credentials = "credentials.json"
    
    if not os.path.exists(chemin_credentials):
        raise HTTPException(
            status_code=500, 
            detail="Le fichier credentials.json est introuvable."
        )
    
    scopes = ['https://www.googleapis.com/auth/drive']
    
    try:
        with open(chemin_credentials, "r", encoding="utf-8") as f:
            info_credentials = json.load(f)
        
        p_key = info_credentials["private_key"].strip().strip('"').strip("'")
        p_key = p_key.replace("\\n", "\n")
        
        info_credentials["private_key"] = p_key
        
        creds = service_account.Credentials.from_service_account_info(info_credentials, scopes=scopes)
        return build('drive', 'v3', credentials=creds)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de traitement des credentials : {str(e)}"
        )

# 5. Les routes commencent juste après (ex: @app.get("/"))
@app.get("/")
def home():
    return {"statut": "Le serveur de thèse fonctionne !"}
