# EpicQuiz — Rapport d'audit de fin de partie

Généré à la demande depuis l'app Manager (`07-app-manager.md` §C.1), via une tâche Celery. Source unique : la séquence de `GameEvent` de l'épisode, rejouée dans l'ordre — jamais le `GameStateSnapshot` (qui n'est qu'une projection pour la reconnexion, pas un historique).

## 1. Algorithme de génération

Le rapport regroupe les événements en **tours** (une case sélectionnée jusqu'à sa résolution) et isole séparément les **incidents** (interventions Manager, verrouillages, pauses pub) qui ne font pas partie du déroulé normal du jeu.

```
build_report(episode):
    events = GameEvent.objects.filter(episode=episode).order_by("sequence")
    turns = []
    incidents = []
    current_turn = None

    for event in events:
        match event.type:
            case CELL_SELECTED:
                current_turn = Turn(cell_id=event.payload.cell_id,
                                     participant_id=event.payload.participant_id)
            case QUESTION_REVEALED:
                current_turn.question = event.payload
            case ANSWER_SUBMITTED:
                current_turn.answer = event.payload
            case CELL_RESOLVED:
                current_turn.resolution = event.payload
                turns.append(current_turn)
                current_turn = None
            case EMPTY_CELL_PLAYED:
                turns.append(Turn(cell_id=event.payload.cell_id, empty=True))
                current_turn = None
            case MANAGER_INTERVENTION | PLAYER_LOCKED | PLAYER_UNLOCKED \
                 | AD_BREAK_STARTED | AD_BREAK_ENDED:
                incidents.append(event)
            # GAME_STARTED, GRID_POSITIONS_DRAWN, GRID_ATTRIBUTES_DRAWN,
            # GRID_REVEAL_STARTED/ENDED, GAME_FINISHED : utilisés pour l'en-tête
            # et les horodatages, pas de ligne dédiée dans le récit

    return Report(header=build_header(episode, events), turns=turns, incidents=incidents,
                   raw_events=events)
```

Un `Turn` mal formé (ex. `CELL_SELECTED` sans `CELL_RESOLVED` ni `EMPTY_CELL_PLAYED` correspondant — coupure en plein direct suivie d'une intervention Manager) doit apparaître dans le rapport avec une mention explicite **"tour interrompu"** plutôt que d'être silencieusement ignoré — la donnée est incomplète mais réelle, l'audit doit en garder trace.

## 2. En-tête du rapport

```
EpicQuiz — Rapport d'audit
Épisode : {title}
Date d'enregistrement : {recording_date}
Participants : {participant_1.name} vs {participant_2.name}
Score final : {score_1} — {score_2}
Vainqueur : {winner.name}
Durée totale (GAME_STARTED → GAME_FINISHED) : {duration}
```

## 3. Récit chronologique (corps du rapport)

Un paragraphe par `Turn`, généré par gabarit selon le type de case et l'issue.

**Case normale, bonne réponse :**
> Léon Kali a choisi la case en position 12 (3 points). Question posée : « Quelle est la capitale du Sénégal ? » — propositions : Dakar, Thiès, Saint-Louis, Ziguinchor. Réponse donnée : « Dakar », en 7,4 secondes. Bonne réponse — Léon Kali remporte 3 points.

**Case spéciale « vol de points », bonne réponse :**
> Adama Traoré a choisi la case en position 27 (case spéciale — vol de points, 4 points). Question posée : [...]. Réponse donnée : [...], en 5,1 secondes. Bonne réponse — Adama Traoré remporte 8 points (doublés), Léon Kali perd 4 points.

**Case spéciale « lot à gagner », bonne réponse :**
> Léon Kali a choisi la case en position 5 (case spéciale — lot à gagner : Cafetière Moulinex, 2 points). [...] Bonne réponse — Léon Kali remporte 2 points et le lot mis en jeu.

**Mauvaise réponse :**
> [...] Réponse donnée : « Thiès », en 4,2 secondes. Mauvaise réponse — la bonne réponse était : Dakar. Aucun point marqué, case brûlée.

**Temps écoulé sans réponse :**
> [...] Aucune réponse donnée dans le temps imparti (20 secondes). La bonne réponse était : Dakar. Aucun point marqué, case brûlée.

**Case vide :**
> Adama Traoré a choisi la case en position 33 (case vide). Aucune question posée, tour passé à l'adversaire.

**Tour interrompu (cf. §1) :**
> Léon Kali a choisi la case en position 19. *Tour interrompu — aucune résolution enregistrée avant la fin de la séquence d'événements.* Voir incidents ci-dessous pour le contexte.

## 4. Incidents (section séparée du récit)

Liste chronologique, hors narration principale, pour ne pas alourdir la lecture du déroulé normal tout en gardant une traçabilité complète :

```
[20:14:03] AD_BREAK_STARTED
[20:17:41] AD_BREAK_ENDED
[20:22:10] PLAYER_LOCKED — cible : tous les joueurs
[20:22:45] PLAYER_UNLOCKED — cible : tous les joueurs
[20:31:02] MANAGER_INTERVENTION — action : force_cell_resolution, case 19,
           raison : "tablette joueur 2 déconnectée pendant le temps de réponse",
           utilisateur : manager_oscar
```

## 5. Formats de sortie

| Format | Contenu | Usage |
| --- | --- | --- |
| **PDF** | En-tête + récit chronologique + section incidents, mise en page lisible | Archivage, consultation humaine, preuve en cas de litige sur un résultat |
| **JSON** | `{header, turns: [...], incidents: [...], raw_events: [...]}` — structure complète, y compris `raw_events` (tous les `GameEvent` bruts, sans reconstruction) | Réexploitation programmatique, ré-audit indépendant |
| **CSV** | Une ligne par `GameEvent` brut : `sequence, type, timestamp, emitted_by, payload_json` | Import tableur, vérification ligne à ligne |

Le JSON et le CSV exposent toujours les événements bruts en plus de la version narrative — la reconstruction en `Turn` est une aide à la lecture, jamais la seule source exportée, pour qu'un audit externe puisse toujours revérifier le récit à partir des données primaires.

## 6. Génération asynchrone

Tâche Celery `generate_audit_report(episode_id, format)` : lit les `GameEvent`, exécute `build_report`, rend le format demandé, stocke le fichier résultant (accessible ensuite via un lien de téléchargement dans l'app Manager). Asynchrone par défaut dès que l'épisode dépasse un volume d'événements significatif (le rendu PDF avec mise en page peut prendre quelques secondes) ; peut rester synchrone pour un export CSV/JSON simple si le volume est faible.
