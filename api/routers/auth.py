"""Route d'authentification."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import Utilisateur
from api.schemas import ConnexionReponse, ConnexionRequete
from api.securite import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=ConnexionReponse)
def login(
    requete: ConnexionRequete,
    db: Session = Depends(get_db),
) -> ConnexionReponse:
    utilisateur = db.scalar(
        select(Utilisateur).where(Utilisateur.username == requete.username)
    )
    if utilisateur is None or not verify_password(
        requete.password, utilisateur.mot_de_passe_hash
    ):
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    return ConnexionReponse(
        access_token=create_access_token(utilisateur),
        token_type="bearer",
        role=utilisateur.role,
    )
