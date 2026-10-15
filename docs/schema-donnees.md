# Schéma de données

La base PostgreSQL est composée de quatre tables : `station`, `trajet`,
`incident` et `utilisateur`.

## MLD

```text
station (station_id PK)
  1 ─── 0..N trajet.station_depart
  0..1 ─ 0..N trajet.station_arrivee
  0..N ─ 0..1 incident.station_id

trajet (trajet_id PK)
incident (incident_id PK)
utilisateur (id_utilisateur PK, username UNIQUE)
```

Une station peut être référencée par plusieurs trajets comme départ ou arrivée
et par plusieurs incidents. L'arrivée d'un trajet et la station d'un incident
sont facultatives selon leur cible.

## Tables et contraintes

### `station`

| Colonne | Type | Règle |
|---|---|---|
| `station_id` | `VARCHAR(10)` | Clé primaire, obligatoire |
| `nom` | `VARCHAR(100)` | Obligatoire |
| `commune` | `VARCHAR(100)` | Obligatoire |
| `capacite` | `INTEGER` | Obligatoire, strictement positif |
| `latitude` | `NUMERIC(8,5)` | Obligatoire, comprise entre -90 et 90 |
| `longitude` | `NUMERIC(8,5)` | Obligatoire, comprise entre -180 et 180 |
| `date_mise_en_service` | `DATE` | Obligatoire |

### `trajet`

| Colonne | Type | Règle |
|---|---|---|
| `trajet_id` | `VARCHAR(12)` | Clé primaire, obligatoire |
| `velo_id` | `VARCHAR(8)` | Obligatoire |
| `depart_horodatage` | `TIMESTAMP` | Obligatoire |
| `station_depart` | `VARCHAR(10)` | Obligatoire, clé étrangère vers `station.station_id` |
| `station_arrivee` | `VARCHAR(10)` | Facultative, clé étrangère vers `station.station_id` |
| `duree_secondes` | `INTEGER` | Obligatoire, strictement positive |
| `type_usager` | `VARCHAR(50)` | Obligatoire, `abonne` ou `occasionnel` |
| `usager_ref` | `VARCHAR(9)` | Facultative ; dépend du type d'usager |

La contrainte `chk_usager_ref` impose un pseudonyme pour un abonné et l'absence
de pseudonyme pour un usager occasionnel.

### `incident`

| Colonne | Type | Règle |
|---|---|---|
| `incident_id` | `VARCHAR(12)` | Clé primaire, obligatoire |
| `date_signalement` | `TIMESTAMP` | Obligatoire |
| `cible` | `VARCHAR(50)` | Obligatoire, `velo` ou `station` |
| `velo_id` | `VARCHAR(8)` | Facultative selon la cible |
| `station_id` | `VARCHAR(10)` | Facultative, clé étrangère vers `station.station_id` |
| `type_incident` | `VARCHAR(30)` | Obligatoire, valeur dans la liste autorisée du schéma |
| `statut` | `VARCHAR(10)` | Obligatoire, `ouvert`, `en_cours` ou `resolu` |
| `date_resolution` | `TIMESTAMP` | Facultative selon le statut |
| `technicien` | `VARCHAR(100)` | Facultatif |

Les contraintes `chk_velo_id` et `chk_station_id` imposent une seule référence
cohérente avec `cible`. La contrainte `chk_date_resolution` impose une date de
résolution pour un incident résolu, postérieure ou égale au signalement, et
l'absence de cette date pour les autres statuts.

### `utilisateur`

| Colonne | Type | Règle |
|---|---|---|
| `id_utilisateur` | `SERIAL` | Clé primaire |
| `username` | `VARCHAR(50)` | Obligatoire et unique |
| `mot_de_passe_hash` | `VARCHAR(100)` | Obligatoire ; hash bcrypt, jamais le mot de passe en clair |
| `role` | `VARCHAR(20)` | Obligatoire, `exploitant` ou `direction` |

## Index

En plus des clés primaires et de l'unicité de `utilisateur.username`, le schéma
crée des index sur `station.nom`, `trajet.station_depart`,
`trajet.station_arrivee`, `incident.date_signalement`,
`incident.date_resolution` et `utilisateur.username`. L'index sur
`utilisateur.username` est redondant avec la contrainte `UNIQUE`.

## Règles de gestion RG1 à RG8

| Règle | Application |
|---|---|
| RG1 — identifiant de station unique et capacité positive | Clé primaire et `CHECK (capacite > 0)` en base ; format de `station_id` et validation de la capacité contrôlés à l'import. |
| RG2 — départ obligatoire et stations référencées existantes | `NOT NULL` et clé étrangère sur `trajet.station_depart` ; l'import normalise le format des identifiants et rejette les départs inconnus. Une arrivée non nulle est contrôlée de la même manière par sa clé étrangère. |
| RG3 — arrivée inconnue conservée sans compter comme arrivée | `trajet.station_arrivee` accepte `NULL`. L'import remplace par `NULL` une référence d'arrivée inconnue et la journalise ; l'indicateur des arrivées ignore les valeurs nulles. |
| RG4 — durée entière strictement positive | Colonne `INTEGER` et `CHECK (duree_secondes > 0)` ; l'import rejette les valeurs nulles, non entières, non positives ou hors capacité du type. |
| RG5 — pseudonyme cohérent avec le type d'usager | `chk_usager_ref` en base et vérification à l'import ; aucune donnée directement identifiante n'est attendue. |
| RG6 — cible d'incident et référence cohérentes | Les contraintes `chk_velo_id` et `chk_station_id` vérifient la référence selon `cible` ; la clé étrangère vérifie la station. L'import contrôle aussi les valeurs et formats. |
| RG7 — statuts et transitions d'incident | Le `CHECK` de `statut` limite les valeurs en base. L'import normalise les formes reconnues et rejette les statuts invalides. Les transitions autorisées (`ouvert` vers `en_cours` ou `resolu`, `en_cours` vers `resolu`) sont contrôlées par la route de mise à jour ; elles ne sont pas imposées par le schéma. |
| RG8 — cohérence des dates et technicien | `chk_date_resolution` impose la présence et l'ordre chronologique de la date de résolution. L'import contrôle les dates et signale un technicien absent sans rejeter l'incident ; `technicien` reste nullable en base. |

Le détail des valeurs admises et le traitement des lignes non conformes sont
définis dans `sql/schema.sql` et `api/services/fiabilisation.py`.
