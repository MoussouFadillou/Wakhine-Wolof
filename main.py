from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import json
import os
import csv
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

app = FastAPI(title="Wakhin Wolof - API de Collecte")

# 🌍 CORS totalement ouvert pour Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FICHIER_SAUVEGARDE = "collecte_wolof.json"
ID_DOSSIER_DRIVE = "1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ"

def obtenir_service_drive():
    chemin_credentials = "credentials.json"
    if not os.path.exists(chemin_credentials):
        raise HTTPException(status_code=500, detail="Fichier credentials.json introuvable.")
    
    scopes = ['https://www.googleapis.com/auth/drive']
    try:
        with open(chemin_credentials, "r", encoding="utf-8") as f:
            info_credentials = json.load(f)
        
        p_key = info_credentials["private_key"].strip().strip('"').strip("'").replace("\\n", "\n")
        info_credentials["private_key"] = p_key
        
        creds = service_account.Credentials.from_service_account_info(info_credentials, scopes=scopes)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de credentials : {str(e)}")

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

# 🟢 ROUTE 1 : Si tu tapes juste l'adresse de base (https://wakhine-wolof-1.onrender.com/)
@app.get("/")
async def root():
    return {"statut": "Le serveur backend Wakhin Wolof fonctionne à 100% ! 🇸🇳"}

# 🟢 ROUTE 2 : Route de secours (au cas où /api/ ne passe pas)
@app.get("/api")
async def api_root():
    return {"statut": "L'API Wakhin Wolof est en ligne ! 🇸🇳"}

# 🟢 ROUTE 3 : L'adresse exacte pour recevoir ton formulaire de Vercel
@app.post("/api/contribuer")
async def ajouter_contribution(
    age: int = Form(...),
    sexe: str = Form(...),
    region: str = Form(...),
    departement: str = Form(...),
    accent: str = Form(...),
    alphabetisation: str = Form(...),
    type_parole: str = Form(...),
    transcription: str = Form(...),
    audioFile: UploadFile = File(...)
):
    chemin_temporaire = f"temp_{audioFile.filename}"
    try:
        service = obtenir_service_drive()
        contenu_audio = await audioFile.read()
        with open(chemin_temporaire, "wb") as f_temp:
            f_temp.write(contenu_audio)
            
        nom_fichier_propre = f"{region}_{departement}_{audioFile.filename}"
        file_metadata = {'name': nom_fichier_propre, 'parents': [ID_DOSSIER_DRIVE]}
        
        media = MediaFileUpload(chemin_temporaire, mimetype=audioFile.content_type, resumable=True)
        fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        id_fichier = fichier_drive.get('id')
        
        service.permissions().create(fileId=id_fichier, body={'type': 'anyone', 'role': 'reader'}).execute()
        lien_audio_direct = f"https://docs.google.com/uc?export=download&id={id_fichier}"

        liste_contributions = charger_donnees()
        nouvelle_entree = {
            "id": len(liste_contributions) + 1, "age": age, "sexe": sexe, "region": region,
            "departement": department, "accent": accent, "alphabetisation": alphabetisation,
            "type_parole": type_parole, "transcription": transcription, "audioUrl": lien_audio_direct
        }
        liste_contributions.append(nouvelle_entree)
        with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
            json.dump(liste_contributions, f, ensure_ascii=False, indent=4)
        
        return nouvelle_entree
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")
    finally:
        if os.path.exists(chemin_temporaire):
            os.remove(chemin_temporaire)
