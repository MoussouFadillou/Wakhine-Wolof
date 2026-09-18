from supabase_client import supabase

TABLE = "contributions"


def create_contribution(
    age,
    sexe,
    region,
    departement,
    accent,
    alphabetisation,
    type_parole,
    transcription,
    audio_path,
    audio_filename,
    audio_content_type,
):
    data = {
        "age": age,
        "sexe": sexe,
        "region": region,
        "departement": departement,
        "accent": accent,
        "alphabetisation": alphabetisation,
        "type_parole": type_parole,
        "transcription": transcription or None,
        "audio_path": audio_path,
        "audio_filename": audio_filename,
        "audio_content_type": audio_content_type,
    }

    response = supabase.table(TABLE).insert(data).execute()

    if not response.data:
        raise RuntimeError(
            "La contribution n'a pas été enregistrée."
        )

    return response.data[0]


def list_all_contributions():
    response = (
        supabase
        .table(TABLE)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []
