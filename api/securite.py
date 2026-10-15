"""Authentification JWT et contrôle des rôles."""

from datetime import datetime, timedelta, timezone
from typing import Callable

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from api.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET
from api.database import get_db
from api.models import Utilisateur

bearer_scheme = HTTPBearer(auto_error=False)


def verifier_mot_de_passe(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    return bcrypt.checkpw(
        mot_de_passe.encode("utf-8"),
        mot_de_passe_hash.encode("utf-8"),
    )


def creer_jeton(utilisateur: Utilisateur) -> str:
    maintenant = datetime.now(timezone.utc)
    charge_utile = {
        "sub": str(utilisateur.id_utilisateur),
        "role": utilisateur.role,
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(charge_utile, JWT_SECRET, algorithm=JWT_ALGORITHM)


def utilisateur_courant(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    erreur_auth = HTTPException(
        status_code=401,
        detail="Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise erreur_auth

    try:
        charge_utile = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
        identifiant = int(charge_utile["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise erreur_auth from exc

    utilisateur = db.get(Utilisateur, identifiant)
    if utilisateur is None:
        raise erreur_auth
    return utilisateur


def exiger_role(role_requis: str) -> Callable:
    def verifier_role(
        utilisateur: Utilisateur = Depends(utilisateur_courant),
    ) -> Utilisateur:
        if utilisateur.role != role_requis:
            raise HTTPException(
                status_code=403,
                detail="Acces reserve au role exploitant",
            )
        return utilisateur

    return verifier_role
