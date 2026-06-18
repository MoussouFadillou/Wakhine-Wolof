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
from googleapiclient.http import MediaIoBaseUpload

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

# ⚠️ REMPLACE CETTE VALEUR PAR TON VRAI ID DE DOSSIER GOOGLE DRIVE
ID_DOSSIER_DRIVE = "1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ"

def obtenir_service_drive():
    if not os.path.exists(FICHIER_CREDENTIALS):
        raise HTTPException(
            status_code=500, 
            detail="Le fichier credentials.json est absent de la Zone Secret Files sur Render."
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

# 🟢 1. ROUTE DE VÉRIFICATION (Racine du serveur)
@app.get("/")
def home():
    return {"statut": "Serveur de thèse connecté à Google Drive avec succès ! 🇸🇳"}

# 🟢 2. ROUTE POUR RÉCUPÉRER L'APERCU DES DONNÉES SUR LE SITE
@app.get("/api/contributions")
def obtenir_contributions():
    return charger_donnees()

# 📊 3. ROUTE EXCLUSIVECSV : EXPORTATION ET TÉLÉCHARGEMENT DIRECT
@app.get("/api/contributions/csv")
def exporter_csv():
    donnees = charger_donnees()
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';') # Le point-virgule est le séparateur parfait pour Excel France/Sénégal
    
    # Écriture de la ligne d'en-tête (Toutes les métadonnées requises)
    writer.writerow([
        "ID", 
        "Age", 
        "Sexe", 
        "Region", 
        "Departement", 
        "Accent_Regional", 
        "Niveau_Alphabetisation", 
        "Type_Parole", 
        "Lien_Audio_Google_Drive"
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
            row.get("audioUrl")
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')), # 'utf-8-sig' force Excel à afficher correctement les caractères accentués
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=corpus_wakhin_wolof.csv"}
    )

# 📥 4. ROUTE D'ENREGISTREMENT SIMULTANÉ (DONNÉES + AUDIO MICRO)
@app.post("/api/contribuer", status_code=201)
async def ajouter_contribution(
    age: int = Form(...),
    sexe: str = Form(...),
    region: str = Form(...),
    departement: str = Form(...),
    accent: str = Form(...),
    alphabetisation: str = Form(...),
    type_parole: str = Form(...),
    audioFile: UploadFile = File(...)
):
    try:
        service = obtenir_service_drive()
        
        # Format de nommage standardisé pour l'organisation de ton Drive : ex "Dakar_Rufisque_Lue_...mp3"
        nom_fichier_propre = f"{region}_{departement}_{type_parole.replace(' ', '_')}_{audioFile.filename}"
        
        file_metadata = {
            'name': nom_fichier_propre,
            'parents': [ID_DOSSIER_DRIVE]
        }
        
        contenu_audio = await audioFile.read()
        fh = io.BytesIO(contenu_audio)
        media = MediaIoBaseUpload(fh, mimetype=audioFile.content_type, resumable=True)
        
        # Envoi de la voix vers Google Drive
        fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        id_fichier = fichier_drive.get('id')
        
        # Rendre le fichier lisible publiquement afin que le site Vercel puisse le lire à distance
        service.permissions().create(fileId=id_fichier, body={'type': 'anyone', 'role': 'reader'}).execute()
        lien_audio_direct = f"https://docs.google.com/uc?export=download&id={id_fichier}"

        # Structure finale de ton entrée de base de données
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
            "audioUrl": lien_audio_direct
        }
        
        liste_contributions.append(nouvelle_entree)
        sauvegarder_donnees(liste_contributions)
        
        return nouvelle_entree

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
