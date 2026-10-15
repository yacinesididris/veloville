# VéloVille — Plateforme de valorisation des données

## Présentation

Ceci est la V1 du projet Veloville, une application de gestion des données et des indicateurs qui doit répondre aux objectifs suivants :

1. Disposer d'une base de données unique, fiable et documentée des
   stations, des trajets et des incidents.
2. Automatiser l'import et la fiabilisation des exports, avec un journal des
   données écartées.
3. Exposer les données et trois indicateurs par une API sécurisée, afin que
   d'autres outils puissent les consommer.
4. Offrir aux équipes une restitution simple, consultable depuis un poste de
   travail ou une tablette, sans compétence technique.
5. Distinguer ce que peut faire un exploitant (suivre et traiter les
   incidents) de ce que peut faire la direction (consulter).

## Prérequis

- Python 3.12 ou supérieur.
- PostgreSQL 14 ou supérieur et un client d'administration (pgAdmin est
  facultatif).
- Git.

## Installation

### Création de la base de donnée

Dans pgAdmin, se connecter au serveur avec un compte administrateur et créer
le rôle applicatif avec un mot de passe choisi pour l'environnement :

```sql
CREATE ROLE veloville LOGIN PASSWORD 'choisir-un-mot-de-passe';
CREATE DATABASE veloville OWNER veloville;
```

Se connecter ensuite à la base `veloville` avec pgAdmin et exécuter les scripts
du dépôt dans cet ordre :

1. `sql/schema.sql`
2. `sql/comptes.sql`


### Importation du dépôt

Depuis VSCode, le terminal pointant sur le dossier dans lequel vous souhaitez installer la solution :

1. Cloner le dépôt :
   ```python
   git clone https://github.com/yacinesididris/veloville.git
   cd veloville
   ```

2. Créer et activer l'environnement virtuel :
    ```python
    python -m venv .venv
    ```
    puis, sous Windows PowerShell :
    ```python
    .\.venv\Scripts\Activate.ps1
    ```

3. Installer les dépendances :
    ```python
    pip install -r requirements.txt
    ```

4. Copier `.env.example` en `.env` (`Copy-Item .env.example .env` sous
   PowerShell), puis remplacer les valeurs d'exemple. Les variables utilisées
   sont :

   | Variable | Usage |
   |---|---|
   | `DATABASE_URL` | Connexion SQLAlchemy à la base `veloville` |
   | `TEST_DATABASE_URL` | Connexion aux tests sur `veloville_bdd_test` |
   | `JWT_SECRET` | Clé aléatoire de signature des jetons ; ne pas la versionner |
   | `JWT_ALGORITHM` | Algorithme JWT, par défaut `HS256` |
   | `JWT_EXPIRE_MINUTES` | Durée de validité du jeton, par défaut 10 minutes |
   | `API_URL` | Adresse de l'API utilisée par le front, par défaut `http://localhost:8000` |
   | `API_TIMEOUT_SECONDES` | Délai maximal d'appel du front, par défaut 5 secondes |

   Les URL de base suivent le format
   `postgresql+psycopg://veloville:<mot_de_passe>@localhost:5432/<nom_base>`.
   Générer la clé JWT avec :

    ```python
    python -c "import secrets; print(secrets.token_urlsafe(32))"
    ```

### Importation des données

Les trois fichiers source sont `data/stations.csv`, `data/trajets.csv` et
`data/incidents.csv`.

Lancer le script suivant depuis la racine du dépôt pour peupler les tables :

```powershell
python scripts/importer.py
```

Un rapport de nettoyage et d'import apparaît dans `docs/rapports/`. L'import
est idempotent pour les identifiants déjà présents : les conflits de clé
primaire ne réécrivent pas les lignes en base. Les fichiers manquants sont
signalés dans le rapport.

### Audit des données importées

Pour le jeu fourni, les CSV contiennent 120 stations, 2 030 trajets et
180 incidents. La recette a relevé 120 stations, 2 004 trajets et
177 incidents insérés. Pour les trajets, 15 lignes sont rejetées et
11 doublons écartés ; pour les incidents, 3 lignes sont rejetées. Le rapport
d'import détaille ses décisions et motifs, mais ne récapitule pas tous les
volumes demandés : les comptages par fichier sont donc faits manuellement
dans [les résultats de recette](docs/recette/resultats-recette.md).

### Création d'une base de données de test

Les tests de base de données doivent utiliser `veloville_bdd_test`, jamais la
base de production. Après avoir créé et chargé `veloville`, créer la base de
test à partir de celle-ci :

1. Donner temporairement les droits `SUPERUSER` au rôle `veloville` depuis
   pgAdmin.
2. Lancer `python -m scripts.creer_bdd_test`.
3. Retirer immédiatement le droit `SUPERUSER`.

Le script clone la base `veloville` et crée `veloville_bdd_test`. Il nécessite
donc un rôle PostgreSQL autorisé à créer une base et à copier le modèle. Les
tests annulent leurs transactions à la fin de chaque test.

## Lancement des tests

Avec `.env` configuré et `TEST_DATABASE_URL` pointant vers la base de test,
lancer depuis la racine :

```python
pytest --cov=api/services --cov-report=term-missing
```

Dernière exécution documentée : **29 tests réussis** ; couverture de
`api/services/fiabilisation.py` et `api/services/indicateurs.py` : **100 %**
(236 instructions couvertes). Cette mesure ne représente pas la couverture de
toute l'application : le module de tests d'intégration API est encore un
squelette.

## Lancement du programme

Dans le terminal, lancer l'API :


```python
uvicorn api.main:app --reload
```

Puis dans un autre terminal, toujours à la racine, lancer le front

```python
streamlit run front/app.py
```

L'API est disponible sur `http://localhost:8000` et sa documentation
interactive sur `http://localhost:8000/docs`. Contrôler son état avec
`http://localhost:8000/sante`.

## Choix écoresponsables

- Les listes sont paginées côté API afin de ne charger que les lignes
  nécessaires à l'écran.
- Les indicateurs sont calculés par agrégation dans PostgreSQL plutôt qu'en
  transférant toutes les lignes vers le front.
- Le front reste tabulaire, sans graphiques ni dépendance de visualisation
  supplémentaire.
- Les imports sont lancés à la demande ; aucune tâche permanente inutile ne
  tourne en arrière-plan.

## Limites connues

- Le jeu livré est un extrait (environ 2 000 trajets), pas la volumétrie cible
  de 3 millions de trajets ; une validation de charge reste à faire.
- Les tests unitaires couvrent les services, mais les tests d'intégration
  complets de l'API restent à écrire.
- Le jeton de connexion Streamlit est perdu après un rechargement complet du
  navigateur ; il faut se reconnecter.
- Le récapitulatif des volumes d'import doit être établi manuellement à partir
  des rapports et des comptages en base.

## Documentation et version

- [Schéma de données](docs/schema-donnees.md)
- [Procédure de déploiement](docs/procedure-deploiement.md)
- [Matrice des rôles et droits](docs/matrice-roles-droits.md)
- [Plan et résultats de recette](docs/recette/resultats-recette.md)
- [Journal des versions](CHANGELOG.md)

## Historique Git

Les versions livrées sont repérées par les tags `v0.1.0` (avant recette) et
`v1.0.0` (après recette et corrections). Consulter les versions avec
`git tag --list` et l'historique des branches avec
`git log --oneline --graph --decorate --all`.

## Notes de fin


| Auteur | Version |
|---|---|
| Sid Idris Yacine | 1.0.0 |