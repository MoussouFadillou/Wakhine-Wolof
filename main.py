from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import os
import csv
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 🚀 Initialisation de l'application FastAPI (c'est ce 'app' que Gunicorn/Uvicorn cherche)
app = FastAPI(title="Wakhin Wolof - API de Collecte")

# 🌍 Configuration CORS essentielle pour communiquer avec ton site Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FICHIER_SAUVEGARDE = "collecte_wolof.json"

# 🟢 Ton identifiant de dossier Google Drive
ID_DOSSIER_DRIVE = "1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ"

def obtenir_service_drive():
    # Récupération sécurisée des variables d'environnement configurées sur Render
    client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    private_key = os.getenv("GOOGLE_PRIVATE_KEY")
    
    if not client_email or not private_key:
        raise HTTPException(
            status_code=500, 
            detail="Les variables d'environnement Google (EMAIL ou KEY) sont manquantes sur Render."
        )
    
    # Nettoyage magique de la clé privée pour éviter le bug de signature JWT
    p_key = private_key.replace("\\n", "\n")
    
    info_credentials = {
        "type": "service_account",
        "project_id": project_id,
        "private_key": p_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(info_credentials, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def sauvegarder_donnees(donnees):
    with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)

# 1. ROUTE DE VÉRIFICATION
@app.get("/")
def home():
    return {"statut": "Le serveur de thèse fonctionne et est connecté avec succès ! 🇸🇳"}

# 2. ROUTE POUR RÉCUPÉRER L'APERÇU SUR TON SITE
@app.get("/api/contributions")
def obtenir_contributions():
    return charger_donnees()

# 3. ROUTE EXPORT EXCEL (CSV) : AVEC COLONNE TRANSCRIPTION
@app.get("/api/contributions/csv")
def exporter_csv():
    donnees = charger_donnees()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # En-têtes complets pour tes analyses statistiques de thèse
    writer.writerow([
        "ID", "Age", "Sexe", "Region", "Departement", 
        "Accent_Regional", "Niveau_Alphabetisation", 
        "Type_Parole", "Transcription", "Lien_Audio_Google_Drive"
    ])
    
    for row in donnees:
        writer.writerow([
            row.get("id"), row.get("age"), row.get("sexe"), row.get("region"),
            row.get("departement"), row.get("accent"), row.get("alphabetisation"),
            row.get("type_parole"), row.get("transcription", ""), row.get("audioUrl")
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=corpus_wakhin_wolof.csv"}
    )

# 4. ROUTE ENREGISTREMENT (METADONNÉES + AUDIO MICRO + TRANSCRIPTION)
@app.post("/api/contribuer", status_code=201)
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
        
        # Écriture temporaire de l'audio reçu sur le serveur
        contenu_audio = await audioFile.read()
        with open(chemin_temporaire, "wb") as f_temp:
            f_temp.write(contenu_audio)
            
        # Métadonnées et nommage du fichier audio pour ton Drive
        nom_fichier_propre = f"{region}_{departement}_{type_parole.replace(' ', '_')}_{audioFile.filename}"
        file_metadata = {
            'name': nom_fichier_propre,
            'parents': [ID_DOSSIER_DRIVE]
        }
        
        # Envoi sécurisé via un fichier physique stable
        media = MediaFileUpload(chemin_temporaire, mimetype=audioFile.content_type, resumable=True)
        fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        id_fichier = fichier_drive.get('id')
        
        # Attribution des droits de lecture pour pouvoir écouter l'audio depuis ton tableau Excel
        service.permissions().create(fileId=id_fichier, body={'type': 'anyone', 'role': 'reader'}).execute()
        lien_audio_direct = f"https://docs.google.com/uc?export=download&id={id_fichier}"

        # Sauvegarde synchrone dans la base locale JSON
        liste_contributions = charger_donnees()
        nouvelle_entree = {
            "id": len(liste_contributions) + 1,
            "age": age,
            "sexe": sexe,
            "region": region,
            "departement": departement,
            "accent": accent,
            "alphabetisation": alphabetisation,
            "type_parole": type_parole,
            "transcription": transcription,
            "audioUrl": lien_audio_direct
        }
        
        liste_contributions.append(nouvelle_entree)
        sauvegarder_donnees(liste_contributions)
        
        return nouvelle_entree

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur d'envoi : {str(e)}")
        
    finally:
        # Nettoyage automatique du fichier temporaire sur Render
        if os.path.exists(chemin_temporaire):
            os.remove(chemin_temporaire)
