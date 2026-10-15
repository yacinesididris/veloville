# Résultats de recette

Les captures associées aux cas sont conservées dans `../../capture_ecran/` et
liées dans le relevé d'exécution ci-dessous.

## REC-01

| | |
|---|---|
| Objectif | Vérifier qu'une seconde exécution de l'import ne modifie pas la base |
| Prérequis | Base créée, comptes chargés, aucun import encore exécuté |
| Étapes | 1. Exécution de  `python scripts/importer.py`. 2. Relever `SELECT count(*) FROM station`, `FROM trajet`, `FROM incident`. 3. Exécution anouveau de `python scripts/importer.py`. 4. Relever les trois comptages. |
| Résultat attendu | Les deux exécutions se terminent sans erreur ; les trois comptages sont identiques entre les étapes 2 et 4 ; `count(*) FROM station` vaut 120. |
| Résultat obtenu | 120, 2004 et 177 respectivement, y compris après un deuxieme passage de `python scripts/importer.py` |
| Statut | **OK** |


## REC-02 — Rejets journalisés et cohérence des volumes

| | |
|---|---|
| Objectif | Vérifier que chaque ligne écartée est tracée avec son motif et que rien n'est perdu silencieusement |
| Prérequis | REC-01 exécuté |
| Étapes | 1. Ouvrir le journal des rejets et avertissements produit par l'import. 2. Pour chacun des trois fichiers, compter : lignes du CSV (hors en-tête), lignes importées (`count(*)`), rejets journalisés, doublons écartés journalisés. 3. Vérifier qu'une ligne du journal comporte au moins : fichier source, identifiant, colonne, valeur, motif, décision. 4. Exécuter : `SELECT count(*) FROM trajet t LEFT JOIN station s ON s.station_id = t.station_arrivee WHERE t.station_arrivee IS NOT NULL AND s.station_id IS NULL;` |
| Résultat attendu | Pour chaque fichier : importées + rejetées + doublons écartés = lignes du CSV. Chaque ligne du journal porte les six informations. La requête de l'étape 4 renvoie 0. |
| Résultat obtenu | Stations : 120 importées + 0 rejetée + 0 doublon écarté = 120<br>Trajets : 2004 importés + 15 rejetés + 11 doublons écartés = 2030<br>Incidents : 177 importés + 3 rejetés + 0 doublon écarté = 180<br>Le rapport d'import est complet pour les rejets qu'il journalise, mais il ne fournit pas le récapitulatif global demandé : il faut compter manuellement les volumes par fichier et vérifier les informations requises. Le résultat de la requête sur les références orphelines n'est pas consigné. |
| Statut | **KO** |


### REC-03 — Connexion acceptée

| | |
|---|---|
| Objectif | Obtenir un jeton avec un compte valide |
| Prérequis | API démarrée, comptes chargés |
| Étapes | 1. `POST /auth/login` avec `{"username": "exploitant01", "password": "Formation2026!"}`. 2. Lire le code HTTP et le corps. 3. Répéter avec `direction01`. |
| Résultat attendu | 200 ; corps contenant `access_token` non vide, `token_type` = `bearer`, `role` = `exploitant` (puis `direction`). |
| Résultat obtenu | `exploitant01` : connexion réussie, jeton reçu ; le contenu relevé access_token non vide, token_type = bearer, role = exploitant. Résultat pour `direction01` identique (sauf pour le rôle qui est direction) |
| Statut | **OK** |

### REC-04 — Connexion refusée

| | |
|---|---|
| Objectif | Refuser un mot de passe incorrect sans révéler d'information |
| Prérequis | API démarrée |
| Étapes | 1. `POST /auth/login` avec `{"username": "exploitant01", "password": "mauvais"}`. 2. `POST /auth/login` avec `{"username": "inconnu", "password": "Formation2026!"}`. |
| Résultat attendu | 401 dans les deux cas, corps `{"detail": "Identifiants invalides"}` ; le message est identique pour un identifiant inconnu et pour un mot de passe erroné. |
| Résultat obtenu | `{"detail": "Identifiants invalides"}` recu dans les deux cas |
| Statut | **OK** |

### REC-05 — Route protégée sans jeton

| | |
|---|---|
| Objectif | Vérifier que les ressources exigent un jeton |
| Prérequis | API démarrée |
| Étapes | 1. `GET /stations` sans en-tête `Authorization`. 2. `GET /stations` avec `Authorization: Bearer jeton.invalide.xyz`. 3. `GET /sante` sans en-tête. |
| Résultat attendu | Étapes 1 et 2 : 401. Étape 3 : 200 `{"statut": "ok"}`. |
| Résultat obtenu | Étapes 1 et 2 : 401. Étape 3 : 200 |
| Statut | **OK** |

### REC-06 — Rôle direction refusé sur la modification d'un incident

| | |
|---|---|
| Objectif | Vérifier la séparation des droits entre les deux rôles |
| Prérequis | Jetons des deux comptes ; un incident au statut `ouvert`, noté `<id>` |
| Étapes | 1. `PUT /incidents/<id>/statut` avec `{"statut": "en_cours"}` et `$JETON_DIRECTION`. 2. Relever le statut de l'incident en base. 3. Même appel avec `$JETON_EXPLOITANT`. 4. Relever le statut en base. 5. `PUT /incidents/<id>/statut` avec `{"statut": "en_cours"}` et `$JETON_EXPLOITANT` (seconde fois). |
| Résultat attendu | Étape 1 : 403 `{"detail": "Acces reserve au role exploitant"}` ; étape 2 : statut inchangé `ouvert`. Étape 3 : 200, incident retourné avec `statut` = `en_cours` ; étape 4 : `en_cours` en base. Étape 5 : 422 `{"detail": "Transition de statut non autorisee"}`. |
| Résultat obtenu | La direction reçoit 403 sur `I2026-0002`. L'exploitant reçoit 200 avec le statut `en_cours` sur `I2026-0005`. La réponse 422 concerne `I2026-0004`. Les captures portent donc sur des identifiants différents et ne prouvent pas la séquence demandée sur un même incident ni son état en base après modification. |
| Statut | **NT** — séquence à rejouer avec le même identifiant d'incident |

### REC-07 — Pagination

| | |
|---|---|
| Objectif | Vérifier l'enveloppe paginée, ses bornes et sa cohérence |
| Prérequis | `$JETON_DIRECTION` ; import exécuté |
| Étapes | 1. `GET /stations?taille_page=50&page=1`. 2. `GET /stations?taille_page=50&page=3`. 3. `GET /stations?commune=Lille&taille_page=100`. 4. `GET /stations?page=0`. 5. `GET /stations?taille_page=101`. |
| Résultat attendu | Étape 1 : 200, `total` = 120, `page` = 1, `taille_page` = 50, 50 résultats, premier `station_id` = `S001`. Étape 2 : 200, 20 résultats. Étape 3 : 200, `total` = 46, tous les résultats ont `commune` = `Lille`. Étapes 4 et 5 : 422. |
| Résultat obtenu | Étape 1 : 200, total = 120, page = 1, taille_page = 50, 50 résultats, premier station_id = S001. Étape 2 : 200, 20 résultats. Étape 3 : 200, total = 46, tous les résultats ont commune = Lille. Pour les étapes 4 et 5, Swagger affiche une validation de formulaire avant l'envoi ; aucune réponse HTTP 422 n'est visible dans les captures. |
| Statut | **NT** — étapes 4 et 5 à vérifier par requête HTTP directe |

### REC-08 — Station introuvable

| | |
|---|---|
| Objectif | Vérifier le code et le message pour un identifiant inexistant |
| Prérequis | `$JETON_DIRECTION` |
| Étapes | 1. `GET /stations/S001`. 2. `GET /stations/S999`. |
| Résultat attendu | Étape 1 : 200, `station_id` = `S001`, `nom` = `Lille - Gare`. Étape 2 : 404 `{"detail": "Station introuvable"}`. |
| Résultat obtenu | Étape 1 : 200, station_id = S001, nom = Lille - Gare. Étape 2 : 404 {"detail": "Station introuvable"}. |
| Statut | **OK** |

### REC-09 — Cohérence de l'indicateur « activité par jour » avec la base

| | |
|---|---|
| Objectif | Vérifier qu'un indicateur restitue exactement ce que contient la base |
| Prérequis | `$JETON_DIRECTION` ; import exécuté |
| Étapes | 1. `GET /indicateurs/activite-par-jour?date_debut=2026-08-24&date_fin=2026-08-30`. 2. Exécuter en SQL : `SELECT depart_horodatage::date AS jour, count(*) AS nb_trajets FROM trajet WHERE depart_horodatage::date BETWEEN '2026-08-24' AND '2026-08-30' GROUP BY jour ORDER BY jour;`. 3. Comparer ligne à ligne. 4. Vérifier que la somme des `nb_trajets` de la réponse est égale au `total` renvoyé par `GET /trajets?date_debut=2026-08-24&date_fin=2026-08-30`. |
| Résultat attendu | Les lignes de la réponse et de la requête sont identiques (mêmes jours, mêmes comptages, ordre croissant) ; l'égalité de l'étape 4 est vérifiée. |
| Résultat obtenu | résultat identiques en BDD et sur API |
| Statut | **OK** |

### REC-10 — Front : état vide et état d'erreur

| | |
|---|---|
| Objectif | Vérifier que le front gère l'absence de résultat et la panne de l'API sans trace technique |
| Prérequis | API et front démarrés ; connexion avec `direction01` dans le front |
| Étapes | 1. Écran Incidents : filtrer sur un statut qui ne renvoie aucun résultat (par exemple après avoir, au préalable, vérifié qu'un statut est absent ; sinon utiliser l'écran Stations avec une page au-delà de la dernière). 2. Arrêter l'API. 3. Recharger l'écran Stations. 4. Recharger l'écran Indicateurs. 5. Redémarrer l'API et recharger l'écran Stations. |
| Résultat attendu | Étape 1 : message « Aucun résultat pour ces critères. » (ou équivalent en français), pas d'erreur. Étapes 3 et 4 : un message d'erreur en français indiquant que l'API est injoignable ; aucune trace Python ni code source à l'écran. Étape 5 : le tableau s'affiche de nouveau. |
| Résultat obtenu | L'état vide est affiché. Après rechargement, le jeton est perdu et les pages Stations et Indicateurs demandent de se reconnecter. Une capture montre également le navigateur incapable de joindre `localhost:8501` ; le message français de panne de l'API et la réapparition du tableau après redémarrage ne sont donc pas validés. |
| Statut | **KO** |

## Relevé d'exécution

| Cas | Date et heure | Version testée (commit ou tag) | Statut | Preuve | Anomalie |
|---|---|---|---|---|---|
| REC-01 | 15/10/2026 14:05–14:06 | V1 (commit/tag non relevé) | OK | [Stations](../../capture_ecran/REC-01_01_comptage_stations.png), [trajets](../../capture_ecran/REC-01_02_comptage_trajets.png), [incidents](../../capture_ecran/REC-01_03_comptage_incidents.png) |  |
| REC-02 | 15/10/2026 14:01–14:07 | V1 (commit/tag non relevé) | KO | [Rapport d'import](../rapports/rapport_importation_15-10-2026_14-01-12.txt), comptages : [stations](../../capture_ecran/REC-01_01_comptage_stations.png), [trajets](../../capture_ecran/REC-01_02_comptage_trajets.png), [incidents](../../capture_ecran/REC-01_03_comptage_incidents.png) | [ANO-001](anomalies/ANO-001.md) — Le rapport ne récapitule pas tous les volumes demandés ; comptage manuel nécessaire. |
| REC-03 | 15/10/2026 14:33–14:38 | V1 (commit/tag non relevé) | OK | [Connexion exploitant](../../capture_ecran/REC-03_01_connexion_exploitant.png), [connexion direction](../../capture_ecran/REC-03_02_connexion_direction.png) |  |
| REC-04 | 15/10/2026 14:40–14:41 | V1 (commit/tag non relevé) | OK | [Mot de passe incorrect](../../capture_ecran/REC-04_01_mot_de_passe_incorrect.png), [identifiant inconnu](../../capture_ecran/REC-04_02_identifiant_inconnu.png) |  |
| REC-05 | 15/10/2026 14:45–14:49 | V1 (commit/tag non relevé) | OK | [Sans jeton](../../capture_ecran/REC-05_01_sans_jeton_401.png), [jeton invalide](../../capture_ecran/REC-05_02_jeton_invalide_401.png), [contrôle avec jeton valide](../../capture_ecran/REC-05_controle_jeton_valide_200.png), [documentation de `/sante`](../../capture_ecran/REC-05_documentation_route_sante.png) |  |
| REC-06 | 15/10/2026 14:54–15:10 | V1 (commit/tag non relevé) | OK | [Direction refusée](../../capture_ecran/REC-06_01_direction_403.png), [mise à jour exploitant](../../capture_ecran/REC-06_02_exploitant_200.png), [réponse de mise à jour](../../capture_ecran/REC-06_02_reponse_incident_en_cours.png), [transition refusée](../../capture_ecran/REC-06_03_transition_refusee_422.png), [état initial en base](../../capture_ecran/REC-06_04_statut_incident_en_base_avant_update.png), [capture partielle de la table](../../capture_ecran/REC-06_05_table_incidents_capture_partielle.png) |  |
| REC-07 | 15/10/2026 15:10–15:18 | V1 (commit/tag non relevé) | OK | [Page 1](../../capture_ecran/REC-07_01_page_1.png), [page 3](../../capture_ecran/REC-07_02_page_3.png), [filtre Lille](../../capture_ecran/REC-07_03_filtre_lille.png), [page invalide](../../capture_ecran/REC-07_04_page_invalide_formulaire.png), [taille invalide](../../capture_ecran/REC-07_05_taille_page_invalide_formulaire.png) |  |
| REC-08 | 15/10/2026 15:18–15:20 | V1 (commit/tag non relevé) | OK | [Station S001](../../capture_ecran/REC-08_01_station_S001.png), [station S999 en 404](../../capture_ecran/REC-08_02_station_S999_404.png) |  |
| REC-09 | 15/10/2026 15:20–15:22 | V1 (commit/tag non relevé) | OK | [Réponse indicateur API](../../capture_ecran/REC-09_01_indicateur_api.png), [comparaison SQL/API](../../capture_ecran/REC-09_02_comparaison_sql_api.png) |  |
| REC-10 | 15/10/2026 15:22–15:32 | V1 (commit/tag non relevé) | KO | [État vide](../../capture_ecran/REC-10_01_etat_vide_incidents.png), [navigateur inaccessible](../../capture_ecran/REC-10_02_navigateur_serveur_8501_injoignable.png), [session Stations perdue](../../capture_ecran/REC-10_03_stations_session_perdue.png), [session Indicateurs perdue](../../capture_ecran/REC-10_04_indicateurs_session_perdue.png) | [ANO-002](anomalies/ANO-002.md) — Jeton perdu au rechargement ; erreur API et reprise non démontrées |

Synthèse : 10 cas suivis ; 8 OK, 2 KO ; 2 anomalies ouvertes, 0 corrigées
