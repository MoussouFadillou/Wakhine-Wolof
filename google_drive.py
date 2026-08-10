import json
import os
import io

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload


SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


def get_drive_service():

    credentials_json = os.getenv(
        "GOOGLE_CREDENTIALS"
    )

    if not credentials_json:
        raise RuntimeError(
            "GOOGLE_CREDENTIALS n'est pas configurée."
        )

    try:
        credentials_data = json.loads(
            credentials_json
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"GOOGLE_CREDENTIALS n'est pas un JSON valide : {error}"
        )

    credentials = (
        service_account.Credentials
        .from_service_account_info(
            credentials_data,
            scopes=SCOPES
        )
    )

    return build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False
    )


def uploader_audio(
    contenu,
    nom_fichier,
    content_type
):

    folder_id = os.getenv(
        "GOOGLE_DRIVE_FOLDER_ID"
    )

    if not folder_id:
        raise RuntimeError(
            "GOOGLE_DRIVE_FOLDER_ID n'est pas configuré."
        )

    service = get_drive_service()

    file_metadata = {
        "name": nom_fichier,
        "parents": [folder_id]
    }

    media = MediaIoBaseUpload(
        io.BytesIO(contenu),
        mimetype=content_type,
        resumable=True
    )

    fichier = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id,webViewLink"
        )
        .execute()
    )

    file_id = fichier["id"]

    audio_url = (
        f"https://drive.google.com/file/d/"
        f"{file_id}/view"
    )

    return file_id, audio_url
