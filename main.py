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

app = FastAPI(title="Wakhin Wolof - API de Collecte")

# 🌍 Configuration CORS essentielle pour communiquer avec Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FICHIER_CREDENTIALS = "credentials.json"
FICHIER_SAUVEGARDE = "collecte_wolof.json"

# 🟢 Identifiant de ton dossier Google Drive
ID_DOSSIER_DRIVE = "1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ"

def obtenir_service_drive():
    if not os.path.exists(FICHIER_CREDENTIALS):
        raise HTTPException(
            status_code=500, 
            detail="Le fichier credentials.json est introuvable sur le serveur Render. Vérifiez l'onglet Secret Files."
        )
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(FICHIER_CREDENTIALS, scopes=scopes)
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

@app.get("/")
def home():
    return {"statut": "Serveur de thèse connecté à Google Drive avec succès ! 🇸🇳"}

@app.get("/api/contributions")
def obtenir_contributions():
    return charger_donnees()

@app.get("/api/contributions/csv")
def exporter_csv():
    donnees = charger_donnees()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
    writer.writerow(["ID", "Age", "Sexe", "Region", "Departement", "Accent_Regional", "Niveau_Alphabetisation", "Type_Parole", "Transcription", "Lien_Audio_Google_Drive"])
    
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

# 📥 ROUTE DE TÉLÉVERSEMENT ROBUSTE ET CORRIGÉE
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
        
        # 1. Écriture physique sécurisée du fichier audio sur le disque temporaire de Render
        contenu_audio = await audioFile.read()
        with open(chemin_temporaire, "wb") as f_temp:
            f_temp.write(contenu_audio)
            
        # 2. Préparation du nommage et des métadonnées pour Google Drive
        nom_fichier_propre = f"{region}_{departement}_{type_parole.replace(' ', '_')}_{audioFile.filename}"
        file_metadata = {
            'name': nom_fichier_propre,
            'parents': [ID_DOSSIER_DRIVE]
        }
        
        # 3. Utilisation de MediaFileUpload (beaucoup plus stable pour les fichiers physiques)
        media = MediaFileUpload(chemin_temporaire, mimetype=audioFile.content_type, resumable=True)
        
        # Envoi effectif vers Google Drive
        fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        id_fichier = fichier_drive.get('id')
        
        # 4. Rendre le fichier lisible pour l'écoute sur le site
        service.permissions().create(fileId=id_fichier, body={'type': 'anyone', 'role': 'reader'}).execute()
        lien_audio_direct = f"https://docs.google.com/uc?export=download&id={id_fichier}"

        # 5. Structure finale et sauvegarde dans le fichier local
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
        # Nettoyage impératif du fichier temporaire sur le serveur Render après l'opération
        if os.path.exists(chemin_temporaire):
            os.remove(chemin_temporaire)
