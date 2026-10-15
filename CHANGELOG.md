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
- Aucun changement spécifique recensé pour cette version.

### Corrigé
- Aucun correctif spécifique recensé pour cette version.
