# Journal des versions

Les changements sont regroupés selon leur nature. Les tags Git associés aux
versions sont `v0.1.0` et `v1.0.0`.

## [1.0.0] - 2026-10-15

Version après recette et corrections.

### Ajouté
- Documentation du schéma relationnel et du portage des règles RG1 à RG8.
- Procédure reproductible de déploiement.
- Fiches d'anomalie et résultats de la campagne de recette.

### Modifié
- README complété avec l'installation, les variables d'environnement, les
  tests, l'audit des données, les choix écoresponsables et les limites connues.

### Corrigé
- Création de la base de test depuis la base d'administration PostgreSQL, et
  non depuis la base modèle qui doit être copiée.

## [0.1.0] - 2026-10-15

Version de l'application avant la campagne de recette.

### Ajouté
- Import et fiabilisation des fichiers stations, trajets et incidents.
- API FastAPI avec authentification JWT, gestion des rôles et indicateurs.
- Front Streamlit tabulaire et premiers tests unitaires des services.

### Modifié
- Les doublons déjà présents en base sont gérés au moment de l'insertion dans
  `importer.py` ; les fonctions de fiabilisation restent indépendantes de la
  base et ne réalisent pas de nettoyage ni de test nécessitant une connexion
  à celle-ci.

### Corrigé
- Correction d'une fonction de fiabilisation qui utilisait `station_id` au lieu
  de la colonne passée en paramètre, notamment pour `station_depart` et
  `station_arrivee`.
- Ajout de la colonne `type_incident` oubliée dans le script SQL.
- Correction du type de `capacite` dans le modèle de station : `Integer` au
  lieu de `Decimal`, conformément au schéma SQL déjà défini.
- Correction de l'indentation de la classe `Incident` dans les modèles, qui
  empêchait le lancement ; FastAPI démarrait correctement après correction.
