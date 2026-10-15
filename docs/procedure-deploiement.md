# Procédure de déploiement

Cette procédure décrit une installation locale reproductible depuis un poste
vierge. Elle utilise PostgreSQL et les scripts du dépôt.

## Prérequis

- Python 3.12 ou supérieur.
- PostgreSQL 14 ou supérieur.
- Git.
- pgAdmin (facultatif, pour créer la base et exécuter les scripts SQL).

## 1. Récupérer le projet et installer les dépendances

Depuis PowerShell :

```powershell
git clone https://github.com/yacinesididris/veloville.git
Set-Location veloville
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Générer une clé JWT :

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Renseigner la valeur générée dans `JWT_SECRET` du fichier `.env`. Adapter
également `DATABASE_URL` et `TEST_DATABASE_URL` aux identifiants PostgreSQL
choisis. Format utilisé par SQLAlchemy :

```text
postgresql+psycopg://veloville:<mot_de_passe>@localhost:5432/veloville
postgresql+psycopg://veloville:<mot_de_passe>@localhost:5432/veloville_bdd_test
```

Si le mot de passe contient des caractères réservés aux URL, les encoder
(percent-encoding) dans les deux chaînes de connexion. Ne pas versionner le
fichier `.env`.

## 2. Créer et initialiser la base

Dans pgAdmin, se connecter au serveur PostgreSQL avec un compte administrateur
et ouvrir le Query Tool sur la base `postgres`. Créer le rôle applicatif et
la base :

```sql
CREATE ROLE veloville LOGIN PASSWORD 'choisir-un-mot-de-passe';
CREATE DATABASE veloville OWNER veloville;
```

Le rôle applicatif n'a pas besoin d'être superutilisateur pour lancer l'API.
Se connecter ensuite à la base `veloville` et exécuter, dans cet ordre :

1. `sql/schema.sql`
2. `sql/comptes.sql`

Les deux comptes de recette (`exploitant01` et `direction01`) sont ajoutés
par le second script.

## 3. Importer les données

Depuis la racine du dépôt, avec l'environnement virtuel activé :

```powershell
python scripts/importer.py
```

Le script lit les fichiers de `data/` et écrit un rapport horodaté dans
`docs/rapports/`. Le rapport signale les lignes rejetées ou normalisées et
les éventuels fichiers absents. L'import n'écrase pas les lignes déjà
présentes avec la même clé primaire.

Contrôler les volumes dans pgAdmin :

```sql
SELECT count(*) FROM station;
SELECT count(*) FROM trajet;
SELECT count(*) FROM incident;
```

Pour le jeu fourni, les volumes après import sont 120 stations, 2 004 trajets
et 177 incidents.

## 4. Configurer et lancer les tests

Les tests de base de données doivent pointer vers une base distincte,
`veloville_bdd_test`. Après avoir initialisé `veloville`, créer une copie
destinée aux tests :

1. Donner temporairement le droit `SUPERUSER` au rôle `veloville` via
   pgAdmin.
2. Exécuter `python -m scripts.creer_bdd_test`.
3. Retirer immédiatement le droit `SUPERUSER`.

Ce script clone `veloville` vers `veloville_bdd_test` et nécessite le droit
PostgreSQL de créer une base. Vérifier que `TEST_DATABASE_URL` dans `.env`
pointe bien vers cette base avant d'exécuter les tests.

```powershell
pytest --cov=api/services --cov-report=term-missing
```

Résultat de la dernière exécution consignée : 29 tests réussis et 100 % de
couverture des modules `api/services/fiabilisation.py` et
`api/services/indicateurs.py`. Les tests ne couvrent pas toute l'application.

## 5. Lancer l'application et vérifier l'API

Dans un premier terminal PowerShell, depuis la racine et avec l'environnement
virtuel activé :

```powershell
uvicorn api.main:app --reload
```

Dans un second terminal :

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run front/app.py
```

Ouvrir l'adresse Streamlit affichée par la commande. Vérifier l'état de l'API
dans un navigateur ou avec `curl.exe` :

```powershell
curl.exe -i http://localhost:8000/sante
```

Le résultat attendu est le code HTTP 200 et le corps
`{"statut":"ok"}`. La documentation interactive est disponible à
`http://localhost:8000/docs`.
