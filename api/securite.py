"""Authentification et autorisation.

À compléter : vérification d'un mot de passe contre son hachage bcrypt, création et
décodage du JWT (secret et algorithme lus dans l'environnement),
dépendances utilisateur_courant() et exiger_role("exploitant").
"""

import secrets



def main():
    jwt_secret = secrets.token_urlsafe(32)
    print(jwt_secret)


if __name__ == "__main__":
    main()


    