def obtenir_service_drive():
    # 1. Récupération sécurisée des variables d'environnement de Render
    client_email = os.getenv("GOOGLE_CLIENT_EMAIL")
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    private_key = os.getenv("GOOGLE_PRIVATE_KEY")
    
    # Sécurité : On vérifie que Render a bien accès à ces informations
    if not client_email or not private_key:
        raise HTTPException(
            status_code=500, 
            detail="Les variables d'environnement Google sont manquantes ou mal configurées sur Render."
        )
    
    # 2. Nettoyage magique de la clé privée pour éviter l'erreur JWT Signature
    p_key = private_key.replace("\\n", "\n")
    
    # 3. Reconstruction du dictionnaire d'authentification pour Google
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
