import io
import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


# ============================================================
# GOOGLE DRIVE
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


def get_drive_service():
    """
    Crée une connexion Google Drive
    à partir de GOOGLE_CREDENTIALS dans Railway.
    """

    credentials_json = os.getenv(
        "GOOGLE_CREDENTIALS"
    )

    if not credentials_json:
        raise RuntimeError(
            "GOOGLE_CREDENTIALS n'est pas configurée dans Railway."
        )

    # --------------------------------------------------------
    # Lecture du JSON
    # --------------------------------------------------------

    try:
        credentials_data = json.loads(
            credentials_json
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "GOOGLE_CREDENTIALS n'est pas un JSON valide : "
            f"{error}"
        )

    # --------------------------------------------------------
    # Vérification minimale
    # --------------------------------------------------------

    if "client_email" not in credentials_data:

        raise RuntimeError(
            "client_email est absent de GOOGLE_CREDENTIALS."
        )

    if "private_key" not in credentials_data:

        raise RuntimeError(
            "private_key est absent de GOOGLE_CREDENTIALS."
        )

    # --------------------------------------------------------
    # Création des credentials
    # --------------------------------------------------------

    try:

        credentials = (
            service_account.Credentials
            .from_service_account_info(
                credentials_data,
                scopes=SCOPES
            )
        )

    except Exception as error:

        raise RuntimeError(
            "Impossible de créer les credentials Google : "
            f"{error}"
        )

    # --------------------------------------------------------
    # Connexion Google Drive
    # --------------------------------------------------------

    try:

        service = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False
        )

        return service

    except Exception as error:

        raise RuntimeError(
            "Impossible de se connecter à Google Drive : "
            f"{error}"
        )


# ============================================================
# UPLOAD AUDIO
# ============================================================

def uploader_audio(
    contenu,
    nom_fichier,
    content_type
):

    # --------------------------------------------------------
    # ID DU DOSSIER DRIVE
    # --------------------------------------------------------

    folder_id = os.getenv(
        "GOOGLE_DRIVE_FOLDER_ID"
    )

    if not folder_id:

        raise RuntimeError(
            "GOOGLE_DRIVE_FOLDER_ID n'est pas configuré dans Railway."
        )

    # --------------------------------------------------------
    # Connexion Drive
    # --------------------------------------------------------

    service = get_drive_service()

    # --------------------------------------------------------
    # Métadonnées du fichier
    # --------------------------------------------------------

    file_metadata = {
        "name": nom_fichier,
        "parents": [
            folder_id
        ]
    }

    # --------------------------------------------------------
    # Préparation du fichier audio
    # --------------------------------------------------------

    media = MediaIoBaseUpload(
        io.BytesIO(contenu),
        mimetype=content_type,
        resumable=True
    )

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    try:

        fichier = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id,webViewLink"
            )
            .execute()
        )

    except Exception as error:

        raise RuntimeError(
            "Erreur lors de l'upload Google Drive : "
            f"{error}"
        )

    # --------------------------------------------------------
    # ID Google Drive
    # --------------------------------------------------------

    file_id = fichier.get("id")

    if not file_id:

        raise RuntimeError(
            "Google Drive n'a pas retourné de file_id."
        )

    # --------------------------------------------------------
    # URL du fichier
    # --------------------------------------------------------

    audio_url = (
        "https://drive.google.com/file/d/"
        f"{file_id}/view"
    )

    return file_id, audio_url
