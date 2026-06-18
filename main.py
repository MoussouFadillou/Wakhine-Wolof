from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

app = FastAPI(title="Wakhin Wolof API - Soutenance Thèse")

# Configuration CORS pour autoriser ton site Vercel à communiquer avec Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📂 CONFIGURATION GOOGLE DRIVE
FICHIER_CREDENTIALS = "credentials.json"  # Créé secrètement par Render via "Secret Files"
ID_DOSSIER_DRIVE = "TON_ID_DE_DOSSIER_GOOGLE_DRIVE"  # ⚠️ REMPLACE PAR L'ID DE TON DOSSIER DRIVE
CODE_SECRET_ATTENDU = "SENEGAL2026"
FICHIER_SAUVEGARDE = "regions_wolof.json"

def obtenir_service_drive():
    if not os.path.exists(FICHIER_CREDENTIALS):
        raise HTTPException(
            status_code=500, 
            detail="Le fichier secret credentials.json est introuvable sur le serveur Render."
        )
    
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

@app.get("/api/mots")
def obtenir_toutes_les_regions():
    return charger_donnees()

@app.post("/api/mots", status_code=201)
async def ajouter_une_region(
    wolof: str = Form(...),
    codeSecurite: str = Form(...),
    audioFile: Optional[UploadFile] = File(None)
):
    # 1. Vérification de sécurité pour le rôle d'Enregistreur
    if codeSecurite != CODE_SECRET_ATTENDU:
        raise HTTPException(status_code=403, detail="Code de sécurité incorrect.")

    lien_audio_direct = ""

    # 2. Envoi automatique du fichier audio vers Google Drive
    if audioFile:
        try:
            service = obtenir_service_drive()
            
            file_metadata = {
                'name': f"{wolof.strip()}_{audioFile.filename}",
                'parents': [ID_DOSSIER_DRIVE]
            }
            
            contenu = await audioFile.read()
            fh = io.BytesIO(contenu)
            media = MediaIoBaseUpload(fh, mimetype=audioFile.content_type, resumable=True)
            
            # Upload sur Drive
            fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            id_fichier = fichier_drive.get('id')
            
            # Rendre le fichier lisible par n'importe qui (indispensable pour l'écoute dans l'app)
            permission_publique = {'type': 'anyone', 'role': 'reader'}
            service.permissions().create(fileId=id_fichier, body=permission_publique).execute()
            
            # Génération du lien de lecture directe pour la balise Audio de React
            lien_audio_direct = f"https://docs.google.com/uc?export=download&id={id_fichier}"

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur Google Drive : {str(e)}")

    # 3. Enregistrement des données dans le fichier de stockage JSON
    try:
        liste_actuelle = charger_donnees()
        prochain_id = max([r["id"] for r in liste_actuelle], default=0) + 1

        nouvelle_region = {
            "id": prochain_id,
            "wolof": wolof.strip(),
            "audioUrl": lien_audio_direct
        }

        liste_actuelle.append(nouvelle_region)
        sauvegarder_donnees(liste_actuelle)
        return nouvelle_region

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'écriture de la base de données : {str(e)}")

@app.get("/")
def racine():
    return {"statut": "Serveur de thèse connecté à Google Drive avec succès ! 🇸🇳"}
