
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

app = FastAPI(title="Wakhin Wolof Backend - Production Railway")

# 🇸🇳 Configuration du CORS pour autoriser ton frontend Vercel à communiquer librement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📂 ID du dossier Google Drive partagé pour ta thèse
DRIVE_FOLDER_ID = "17oylBfSgSCfuo4xGEyBFOIICtsyjT90h"

def obtenir_service_drive():
    """Initialise la connexion avec Google Drive en utilisant le fichier JSON local."""
    chemin_credentials = "credentials.json"
    
    if not os.path.exists(chemin_credentials):
        raise HTTPException(
            status_code=500, 
            detail="Le fichier credentials.json est introuvable à la racine du projet backend."
        )

    try:
        scopes = ["https://www.googleapis.com/auth/drive"]
        # Utilisation de la méthode officielle pour lire un fichier physique local
        creds = service_account.Credentials.from_service_account_file(
            chemin_credentials, 
            scopes=scopes
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de lecture ou de signature du fichier credentials.json : {str(e)}"
        )

@app.get("/")
def home():
    """Route de vérification pour s'assurer que le serveur est bien en ligne."""
    return {
        "status": "OK", 
        "message": "Backend Wakhin Wolof opérationnel sur Railway avec authentification par fichier."
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
    transcription: str = Form(None),
    audioFile: UploadFile = File(...)
):
    """Reçoit l'audio et les métadonnées du frontend, et les envoie sur Google Drive."""
    try:
        service = obtenir_service_drive()
    except HTTPException as he:
        raise he

    # 1. Lecture du fichier audio en mémoire
    audio_content = await audioFile.read()
    nom_fichier_audio = audioFile.filename

    # 2. Préparation de la description texte (les métadonnées stockées dans la description du fichier sur Drive)
    texte_metadonnees = (
        f"Age: {age}\n"
        f"Sexe: {sexe}\n"
        f"Region: {region}\n"
        f"Departement: {departement}\n"
        f"Accent: {accent}\n"
        f"Alphabetisation: {alphabetisation}\n"
        f"Type de parole: {type_parole}\n"
        f"Transcription: {transcription or ''}"
    )

    # 3. Envoi du fichier audio sur Google Drive
    metadata_audio = {
        "name": nom_fichier_audio,
        "description": texte_metadonnees,
        "parents": [DRIVE_FOLDER_ID]
    }
    
    media_audio = MediaIoBaseUpload(
        io.BytesIO(audio_content), 
        mimetype="audio/wav", 
        chunksize=1024*1024, 
        resumable=True
    )

    try:
        fichier_cree = service.files().create(
            body=metadata_audio, 
            media_body=media_audio, 
            fields="id"
        ).execute()
        
        return {
            "status": "Succès",
            "message": "Données et fichier audio enregistrés avec succès sur Google Drive !",
            "file_id": fichier_cree.get("id")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du transfert vers Google Drive : {str(e)}"
        )

@app.get("/api/contributions/csv")
async def telecharger_csv():
    """Génère dynamiquement un fichier CSV de toutes les contributions présentes dans le dossier Drive."""
    try:
        service = obtenir_service_drive()
        
        # Récupération de la liste des fichiers dans le dossier Drive
        requete = f"'{DRIVE_FOLDER_ID}' in parents and trashed = false"
        resultats = service.files().list(
            q=requete, 
            fields="files(id, name, description, createdTime)",
            pageSize=1000
        ).execute()
        
        fichiers = resultats.get("files", [])
        
        # Création du contenu CSV en mémoire
        output = io.StringIO()
        output.write("Fichier_Audio;Date_Creation;Age;Sexe;Region;Departement;Accent;Alphabetisation;Type_Parole;Transcription\n")
        
        for f in fichiers:
            nom = f.get("name", "")
            date_c = f.get("createdTime", "")
            desc = f.get("description", "")
            
            # Extraction basique des lignes de la description
            meta = {}
            if desc:
                for ligne in desc.split("\n"):
                    if ":" in ligne:
                        cle, val = ligne.split(":", 1)
                        meta[cle.strip()] = val.strip()
            
            age_val = meta.get("Age", "")
            sexe_val = meta.get("Sexe", "")
            reg_val = meta.get("Region", "")
            dep_val = meta.get("Departement", "")
            acc_val = meta.get("Accent", "")
            alpha_val = meta.get("Alphabetisation", "")
            type_p = meta.get("Type de parole", "")
            trans = meta.get("Transcription", "").replace("\n", " ").replace(";", ",")
            
            output.write(f"{nom};{date_c};{age_val};{sexe_val};{reg_val};{dep_val};{acc_val};{alpha_val};{type_p};{trans}\n")
            
        csv_content = output.getvalue()
        output.close()
        
        return StreamingResponse(
            io.BytesIO(csv_content.encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=contributions_wolof.csv"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du fichier CSV : {str(e)}"
        )
