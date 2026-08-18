# EpicQuiz — App Manager

Seul rôle avec un pied dans la configuration amont (interface web classique, HTTP) et un pied dans la supervision live (connexion au canal Jeu avec des privilèges d'intervention). C'est aussi le seul rôle disposant d'un vrai compte `User` avec identité nominative et mot de passe — nécessaire puisque toute intervention en direct est journalisée avec cette identité.

## Partie A — Configuration amont (avant l'émission)

### A.1 Import de la banque de questions

- Écran d'upload de fichier (CSV ou XLSX, à trancher selon l'outil de saisie utilisé en amont — les deux formats doivent être supportés côté parsing).
- Colonnes attendues : `label`, `difficulty` (1-5), `theme`, `proposition_1..4`, `correct_answer_index`.
- Validation à l'import, ligne par ligne, avec rapport d'erreurs explicite (numéro de ligne + raison) plutôt qu'un rejet global du fichier :
  - `label` non vide
  - `difficulty` entre 1 et 5
  - au moins 2 propositions non vides, une seule marquée correcte
- Import **partiel accepté** : les lignes valides sont créées, les lignes en erreur sont listées pour correction et re-import ciblé.
- Vue de la banque existante avec filtres (thème, difficulté, nombre d'utilisations) pour piloter la sélection des questions par épisode et éviter les répétitions.

### A.2 Gestion des lots

- CRUD simple sur `Prize` (nom, sponsor, description, valeur estimée, actif/inactif).

### A.3 Création d'un épisode

1. Créer l'`Episode` (titre, date prévue). *(Point à trancher plus tard : faut-il que le Manager pré-saisisse les noms réels des participants avant le direct, ou est-ce uniquement connu à la connexion — cf. `04-app-joueur.md` §1 — comme actuellement modélisé ?)*
2. Configurer la `Grid` : distribution des points (40 questions selon la répartition pyramidale 12/10/8/6/4 imposée par les règles v1.3), nombre de cases vides (8), répartition des attributs spéciaux (vol/lot, ex. 3/2) — `Grid.validate_distribution()` (cf. `02-modele-donnees.md` §3).
3. L'app doit **empêcher la validation** si la distribution ne respecte pas les règles (ex. bloque si plus de 4 cases à 5 points sont sélectionnées).
4. Sélection des 40 `Challenge` de l'épisode (questions choisies depuis la banque, sans position — le tirage des positions et des attributs a lieu **en direct, filmé**, cf. `02-modele-donnees.md` §3).
5. Une fois la configuration validée, l'épisode passe en statut `ready` — ce passage déclenche automatiquement la tâche Celery `provision_episode_participants` (cf. `02-modele-donnees.md` §7), qui crée les `User` (username généré, sans token) et leurs `Participant` associés pour les 4 rôles de plateau (Joueur ×2, Animateur, Écran TV ×N, Opérateur).
6. Écran de distribution des identifiants : liste des comptes générés (rôle, tags, username) avec, pour chacun, un QR code encodant le seul `username` — aucun token à ce stade, il est émis à la première connexion de chaque appareil (cf. `03-protocole-websocket.md` §2).

## Partie B — Supervision live (pendant l'émission)

Le Manager se connecte au canal Jeu **en écoute** comme les autres acteurs (identifié via `user.is_staff`, sans `Participant`, cf. `03-protocole-websocket.md` §2). Ses interventions passent par l'endpoint HTTP dédié `POST /episodes/<eid>/manager-intervention/`, réservé exclusivement à ce rôle (`03-protocole-websocket.md` §7).

### B.1 Vue de supervision

Reprend les informations du tableau de bord animateur (grille, scores, phase) en lecture, en ajoutant :
- Historique en direct du log d'événements (défilement des derniers `GameEvent`), pour repérer rapidement une anomalie.
- Indicateurs de connexion de chaque appareil de plateau (dernier ping reçu par rôle).

### B.2 Interventions disponibles

Chaque intervention exige une **raison textuelle obligatoire** (`reason`), saisie avant validation, et une confirmation explicite (pas d'action à un seul tap pour ce type de commande) :

| Action | Usage typique |
| --- | --- |
| `force_cell_resolution` — Forcer la résolution d'une case | Une tablette joueur plante en plein QCM |
| `reopen_cell` — Rouvrir une case déjà résolue | Erreur technique détectée après coup, avant que la case suivante ne soit jouée |
| `adjust_score` — Ajuster un score manuellement | Correction d'une anomalie de calcul constatée en direct |
| `skip_ad_break` — Sauter la pause publicitaire | Décision de production en direct |
| `pause_game` — Mettre la partie en pause (hors pause pub) | Incident technique plateau nécessitant un arrêt |

Ces actions restent volontairement limitées et explicites plutôt qu'un accès libre en base — l'objectif est de couvrir les incidents réalistes de plateau sans donner un pouvoir de réécriture arbitraire de l'historique.

## Partie C — Après l'émission

### C.1 Export du rapport d'audit

Rapport détaillé dans `10-rapport-audit.md` : algorithme de génération à partir du `GameEvent` log, récit chronologique lisible, section incidents séparée, et trois formats de sortie (PDF, JSON, CSV) exposant toujours les événements bruts en plus de la version narrative.
