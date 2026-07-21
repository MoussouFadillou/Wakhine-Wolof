import json
import os
import tempfile

from google.oauth2.service_account import Credentials

from googleapiclient.discovery import build

from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


def obtenir_service_drive():

    credentials_json = os.getenv(
        "GOOGLE_CREDENTIALS"
    )

    if not credentials_json:

        raise RuntimeError(
            "La variable GOOGLE_CREDENTIALS est absente."
        )

    try:

        credentials_info = json.loads(
            credentials_json
        )

    except json.JSONDecodeError as error:

        raise RuntimeError(
            f"GOOGLE_CREDENTIALS n'est pas un JSON valide : {error}"
        )


    private_key = credentials_info.get(
        "private_key"
    )


    if not private_key:

        raise RuntimeError(
            "private_key est absente des credentials Google."
        )


    # Important pour les variables d'environnement
    credentials_info["private_key"] = (
        private_key.replace(
            "\\n",
            "\n"
        )
    )


    try:

        credentials = (
            Credentials
            .from_service_account_info(
                credentials_info,
                scopes=SCOPES
            )
        )


        service = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False
        )


        return service


    except Exception as error:

        raise RuntimeError(
            f"Erreur d'authentification Google Drive : {error}"
        )


def uploader_audio(
    contenu: bytes,
    nom_fichier: str,
    content_type: str
):

    service = obtenir_service_drive()


    folder_id = os.getenv(
        "GOOGLE_DRIVE_FOLDER_ID"
    )


    if not folder_id:

        raise RuntimeError(
            "GOOGLE_DRIVE_FOLDER_ID est absente."
        )


    chemin_temporaire = None


    try:

        extension = ".webm"


        if "wav" in content_type:

            extension = ".wav"

        elif "ogg" in content_type:

            extension = ".ogg"

        elif "mp4" in content_type:

            extension = ".mp4"


        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        ) as fichier_temp:

            fichier_temp.write(contenu)

            chemin_temporaire = fichier_temp.name


        metadata = {

            "name": nom_fichier,

            "parents": [
                folder_id
            ]

        }


        media = MediaFileUpload(

            chemin_temporaire,

            mimetype=content_type,

            resumable=True

        )


        fichier = (

            service.files()

            .create(

                body=metadata,

                media_body=media,

                fields="id,name"

            )

            .execute()

        )


        file_id = fichier["id"]


        # Rend le fichier accessible en lecture
        service.permissions().create(

            fileId=file_id,

            body={

                "type": "anyone",

                "role": "reader"

            }

        ).execute()


        audio_url = (
            "https://drive.google.com/"
            f"uc?id={file_id}"
        )


        return file_id, audio_url


    finally:

        if (

            chemin_temporaire

            and os.path.exists(

                chemin_temporaire

            )

        ):

            os.remove(

                chemin_temporaire

            )
