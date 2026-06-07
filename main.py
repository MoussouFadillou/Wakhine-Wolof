import io
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import uvicorn

app = FastAPI(title="Kalama Wolof API - Google Drive Version")

# 1. CONFIGURATION SÉCURITÉ (CORS)
# Permet à ton frontend (Vercel ou local) de communiquer avec ce backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, tu pourras remplacer par ton lien Vercel unique
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. CONFIGURATION GOOGLE DRIVE
# Remplace 'ID_DE_TON_DOSSIER_DRIVE' par l'identifiant réel de ton dossier de thèse sur Drive
GOOGLE_DRIVE_FOLDER_ID = "ID_DE_TON_DOSSIER_DRIVE"
SERVICE_ACCOUNT_FILE = "credentials.json"  # Ton fichier de clé secrète Google Cloud
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_drive_service():
    """Connexion sécurisée à l'API Google Drive via le compte de service."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        print(f"Erreur de connexion Google API : {e}")
        return None


# 3. ROUTE UNIQUE DE COLLECTE AUDIO
@app.post("/api/collecte")
async def collect_voice(
    audio: UploadFile = File(...),
    transcript: str = Form(...),
    region: str = Form(...),
    accent: str = Form(...),
    gender: str = Form(...),
    age: int = Form(...),
    speech_type: str = Form(...),
    secret_key: str = Form(...),
):
    # Sécurité : Garde-fou pour éviter le spam anonyme
    if secret_key != "WOLOF2026":
        raise HTTPException(
            status_code=403, detail="Clé de sécurité Kalama non valide."
        )

    # Initialisation du service Google Drive
    drive_service = get_drive_service()
    if not drive_service:
        raise HTTPException(
            status_code=500,
            detail="Impossible de se connecter au stockage Google Drive.",
        )

    try:
        # Lire le contenu binaire de l'audio envoyé par le smartphone
        audio_content = await audio.read()

        # Configurer le nom du fichier sur Google Drive (Nom d'origine envoyé par le front)
        file_metadata = {
            "name": audio.filename,
            "parents": [GOOGLE_DRIVE_FOLDER_ID],  # Destination dans ton Drive
        }

        # Préparer le flux binaire pour l'upload direct (sans écriture sur le disque Render)
        media = MediaIoBaseUpload(
            io.BytesIO(audio_content), mimetype="audio/wav", resumable=True
        )

        # Exécuter l'envoi vers Google Drive
        drive_file = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        drive_file_id = drive_file.get("id")

        # --- GESTION DES MÉTADONNÉES (CSV ou LOG) ---
        # Note pour ta thèse : Puisque le disque Render s'efface, nous affichons les données
        # dans les logs du serveur. Pour l'avenir, ces lignes alimenteront directement
        # un fichier Google Sheets en ligne ou une base Supabase.
        print(f"--- NOUVEL ENREGISTREMENT SYNC DRIVE ({drive_file_id}) ---")
        print(
            f"Fichier : {audio.filename} | Texte : {transcript} | Région : {region} ({accent})"
        )
        print(f"Profil : {gender} | Âge : {age} ans | Type : {speech_type}")

        return {
            "status": "success",
            "message": "Audio sauvegardé avec succès sur Google Drive !",
            "drive_file_id": drive_file_id,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la transmission vers Google Drive : {str(e)}",
        )


# Lancement du serveur (Utile pour tes tests locaux)
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
