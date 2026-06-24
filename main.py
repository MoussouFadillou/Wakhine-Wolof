from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
import os
import csv
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 🚀 Initialisation de l'application FastAPI
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

# 🟢 METS TON PROPRE ID DE DOSSIER GOOGLE DRIVE ICI
ID_DOSSIER_DRIVE = "1i4Nmu25ja6TQpW0usdxdFXep2bP-NCcJ"

def obtenir_service_drive():
    chemin_credentials = "credentials.json"
    
    if not os.path.exists(chemin_credentials):
        raise HTTPException(
            status_code=500, 
            detail="Le fichier credentials.json est introuvable."
        )
    
    scopes = ['https://www.googleapis.com/auth/drive']
    
    try:
        # 1. On charge le fichier JSON manuellement
        with open(chemin_credentials, "r", encoding="utf-8") as f:
            info_credentials = json.load(f)
        
        # 2. NETTOYAGE DE LA CLÉ PRIVÉE POUR ÉVITER LES BUGS RENDER
        p_key = info_credentials["private_key"].strip().strip('"').strip("'")
        p_key = p_key.replace("\\n", "\n")
        info_credentials["private_key"] = p_key
        
        # 3. On donne le dictionnaire nettoyé à Google
        creds = service_account.Credentials.from_service_account_info(info_credentials, scopes=scopes)
        return build('drive', 'v3', credentials=creds)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de traitement des credentials : {str(e)}"
        )

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

# 1. ROUTE DE VÉRIFICATION SUR NAVIGATEUR (TEST D'ACCUEIL)
@app.get("/")
def home():
    return {"statut": "Le serveur de thèse fonctionne et est connecté avec succès ! 🇸🇳"}

# 2. ROUTE POUR RÉCUPÉRER L'APERÇU SUR TON SITE
@app.get("/api/contributions")
def obtenir_contributions():
    return charger_donnees()

# 3. ROUTE EXPORT EXCEL (CSV)
@app.get("/api/contributions/csv")
def exporter_csv():
    donnees = charger_donnees()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    
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

# 4. ROUTE PRINCIPALE : RÉCEPTION AUDIO + ENVOI DRIVE
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
        
        contenu_audio = await audioFile.read()
        with open(chemin_temporaire, "wb") as f_temp:
            f_temp.write(contenu_audio)
            
        nom_fichier_propre = f"{region}_{departement}_{type_parole.replace(' ', '_')}_{audioFile.filename}"
        file_metadata = {
            'name': nom_fichier_propre,
            'parents': [ID_DOSSIER_DRIVE]
        }
        
        media = MediaFileUpload(chemin_temporaire, mimetype=audioFile.content_type, resumable=True)
        fichier_drive = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        id_fichier = fichier_drive.get('id')
        
        service.permissions().create(fileId=id_fichier, body={'type': 'anyone', 'role': 'reader'}).execute()
        lien_audio_direct = f"https://docs.google.com/uc?export=download&id={id_fichier}"

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
        if os.path.exists(chemin_temporaire):
            os.remove(chemin_temporaire)
