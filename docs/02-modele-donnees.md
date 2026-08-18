# EpicQuiz — Modèle de données

Django 6.0 — `BigAutoField` par défaut sur tous les modèles (comportement natif 6.0, pas besoin de le déclarer).

## 1. Vue d'ensemble des entités

```
Question ──< Proposition                      User (AUTH_USER_MODEL, tous rôles ;
   │                                            is_staff=True pour Manager/Admin)
   │ (figée dans, sans position)                    │
   ▼                                                 │ (via Participant, sauf Manager/Admin)
Challenge ──── Episode ──< Participant ─────────────┘
                  │        (user + episode + role :
                  │         joueur/animateur/écran/opérateur)
                  ▼
                Grid (FSM : configured → positions_drawn → attributes_drawn)
                  │
                  ▼
                Cell ──── Prize (si spéciale "prize")
                  │
                  ▼
            GameEvent (log append-only) ──► GameStateSnapshot (projection)
```

Changement clé par rapport à la v1 de ce document : `Challenge` n'est plus positionné à sa création — il est rattaché à l'`Episode` mais sans coordonnée sur la grille. L'affectation `Challenge → Cell` (positions) et l'ajout des attributs spéciaux (vol/lot) sont deux tirages aléatoires **filmés en direct**, modélisés comme deux `GameEvent` distincts et deux transitions de la machine à états `Grid` (voir §3 et §4). Par ailleurs, les comptes sont désormais unifiés sous un seul modèle Django (`User`) ; `Participant` n'est plus un compte mais l'entité qui relie un `User` à sa participation à un `Episode` précis, avec un rôle (voir §6).

## 2. Banque de questions (persistant, réutilisable entre épisodes)

```python
class Question(TimeStampedModel):
    class Difficulty(models.IntegerChoices):
        ONE_POINT = 1, "1 point"
        TWO_POINTS = 2, "2 points"
        THREE_POINTS = 3, "3 points"
        FOUR_POINTS = 4, "4 points"
        FIVE_POINTS = 5, "5 points"

    qid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    label = models.CharField(max_length=300)
    difficulty = models.PositiveSmallIntegerField(choices=Difficulty.choices)
    theme = models.CharField(max_length=100, blank=True)
    tags = ArrayField(models.CharField(max_length=50), blank=True, null=True)
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)  # évite les répétitions entre épisodes


class Proposition(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="propositions")
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            # une seule proposition correcte par question, vérifié en validation applicative
        ]


class Prize(TimeStampedModel):
    name = models.CharField(max_length=150)
    sponsor = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    estimated_value_fcfa = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
```

**Note sur l'import** : l'upload de fichier (CSV/XLSX) crée des `Question` + `Proposition` en une transaction. Validation attendue à l'import : exactement une proposition correcte, 2 à 4 propositions, `difficulty` dans 1-5, `label` non vide. Voir `07-app-manager.md` pour le détail du flux d'upload.

## 3. Partie et grille (créés à la configuration, tirage en direct)

```python
class Episode(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        READY = "ready", "Prêt"
        REVEAL = "reveal", "Révélation initiale"
        IN_PROGRESS = "in_progress", "En cours"
        AD_BREAK = "ad_break", "Pause publicitaire"
        FINISHED = "finished", "Terminé"

    eid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=150)
    recording_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey("User", on_delete=models.PROTECT)


class Challenge(TimeStampedModel):
    """Instantané figé d'une Question, rattaché à l'épisode mais SANS position sur la grille.
    Créé en amont (configuration), positionné en direct (voir Grid.draw_positions)."""
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="challenges")
    source_question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="challenges")
    text = models.CharField(max_length=300)
    propositions = ArrayField(models.CharField(max_length=200))
    correct_answer_index = models.PositiveSmallIntegerField()
    point_value = models.PositiveSmallIntegerField()
    time_limit_sec = models.PositiveSmallIntegerField(default=20)


class GridState(models.TextChoices):
    CONFIGURED = "configured", "Configurée"                 # distribution définie, challenges créés, positions non tirées
    POSITIONS_DRAWN = "positions_drawn", "Positions tirées"  # chaque Challenge a désormais une Cell
    ATTRIBUTES_DRAWN = "attributes_drawn", "Attributs tirés" # grille complète, prête pour la révélation


class Grid(TimeStampedModel):
    episode = models.OneToOneField(Episode, on_delete=models.CASCADE, related_name="grid")
    row_count = models.PositiveSmallIntegerField(default=6)
    column_count = models.PositiveSmallIntegerField(default=8)
    empty_cell_count = models.PositiveSmallIntegerField(default=8)
    point_distribution = models.JSONField(default=dict)        # {"1":12,"2":10,"3":8,"4":6,"5":4}
    attribute_distribution = models.JSONField(default=dict)    # {"steal":3,"prize":2}
    state = FSMField(default=GridState.CONFIGURED, choices=GridState.choices, protected=True)

    def validate_distribution(self):
        """Appelé à la configuration amont, avant toute création de Challenge.
        Vérifie : somme(valeur * nb_cases) == 100, somme(nb_cases par valeur) == 40,
        40 + empty_cell_count == row_count * column_count,
        somme(attribute_distribution.values()) <= 40."""
        ...

    @transition(field=state, source=GridState.CONFIGURED, target=GridState.POSITIONS_DRAWN)
    def draw_positions(self):
        """Appelé par le serveur juste après l'écriture réussie du GameEvent
        GRID_POSITIONS_DRAWN, dans la même transaction : répartit aléatoirement
        les Challenge de l'épisode sur les Cell, laisse empty_cell_count positions
        sans Challenge (type=empty)."""
        pass

    @transition(field=state, source=GridState.POSITIONS_DRAWN, target=GridState.ATTRIBUTES_DRAWN)
    def draw_attributes(self):
        """Appelé après l'écriture du GameEvent GRID_ATTRIBUTES_DRAWN. django-fsm
        refuse l'appel si state != POSITIONS_DRAWN — impossible de tirer les attributs
        sur une grille dont les cellules n'ont pas encore de Challenge assigné."""
        pass


class Cell(TimeStampedModel):
    class Type(models.TextChoices):
        EMPTY = "empty", "Vide (skip)"
        NORMAL = "normal", "Normale"
        SPECIAL_STEAL = "steal", "Spéciale — vol de points"
        SPECIAL_PRIZE = "prize", "Spéciale — lot à gagner"

    grid = models.ForeignKey(Grid, on_delete=models.CASCADE, related_name="cells")
    position = models.PositiveSmallIntegerField()  # 0 à 47, existe dès la configuration amont
    type = models.CharField(max_length=16, choices=Type.choices, null=True, blank=True)
    # null tant que draw_positions() n'a pas eu lieu (sauf pour les positions déjà connues comme vides)
    challenge = models.ForeignKey(Challenge, null=True, blank=True, on_delete=models.SET_NULL, related_name="cell")
    prize = models.ForeignKey(Prize, null=True, blank=True, on_delete=models.SET_NULL)
    state = models.CharField(max_length=16, choices=[("not_played", "Non jouée"), ("played", "Jouée")], default="not_played")
    played_by = models.ForeignKey("Participant", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        unique_together = ("grid", "position")
```

**Ordre réel des opérations :**

1. **Configuration amont** (Manager, HTTP) : `Grid.validate_distribution()` puis création des 48 `Cell` (positions seules, `type=None`) et des 40 `Challenge` de l'épisode (questions sélectionnées depuis la banque, sans position).
2. **Tirage des positions** (en direct, filmé) : `draw_positions_command` → le serveur exécute la répartition aléatoire, écrit `GameEvent(type=GRID_POSITIONS_DRAWN)`, appelle `grid.draw_positions()`.
3. **Tirage des attributs** (en direct, filmé, juste après) : `draw_attributes_command` → sélection aléatoire des cellules spéciales parmi les cellules à valeur désormais positionnées, écrit `GameEvent(type=GRID_ATTRIBUTES_DRAWN)`, appelle `grid.draw_attributes()`.
4. **Révélation** puis déroulé de partie, inchangés par rapport à la version précédente de ce document.

## 4. Event log (source de vérité pendant le direct)

```python
class GameEvent(TimeStampedModel):
    class Type(models.TextChoices):
        GAME_STARTED = "game_started"
        GRID_POSITIONS_DRAWN = "grid_positions_drawn"
        GRID_ATTRIBUTES_DRAWN = "grid_attributes_drawn"
        GRID_REVEAL_STARTED = "grid_reveal_started"
        GRID_REVEAL_ENDED = "grid_reveal_ended"
        CELL_SELECTED = "cell_selected"
        QUESTION_REVEALED = "question_revealed"
        ANSWER_SUBMITTED = "answer_submitted"
        CELL_RESOLVED = "cell_resolved"
        EMPTY_CELL_PLAYED = "empty_cell_played"
        AD_BREAK_STARTED = "ad_break_started"
        AD_BREAK_ENDED = "ad_break_ended"
        GAME_FINISHED = "game_finished"
        MANAGER_INTERVENTION = "manager_intervention"  # override manuel, toujours distingué
        PLAYER_LOCKED = "player_locked"      # verrouillage d'un ou tous les joueurs par l'animateur
        PLAYER_UNLOCKED = "player_unlocked"

    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="events")
    sequence = models.PositiveIntegerField()
    type = models.CharField(max_length=32, choices=Type.choices)
    payload = models.JSONField()
    emitted_by = models.CharField(max_length=32)  # "participant:<username>", "manager:<username>", "system"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["episode", "sequence"], name="uniq_episode_sequence")]
        ordering = ["sequence"]
```

**Exemples de `payload` par type :**

| Type | Payload |
| --- | --- |
| `GRID_POSITIONS_DRAWN` | `{"assignments": [{"cell_id": 12, "challenge_id": 88}, ...], "empty_positions": [3, 17, ...]}` |
| `GRID_ATTRIBUTES_DRAWN` | `{"steal_cells": [12, 27, 40], "prize_cells": [{"cell_id": 5, "prize_id": 2}, {"cell_id": 33, "prize_id": 4}]}` |
| `CELL_SELECTED` | `{"cell_id": 12, "position": 12, "participant_id": 4}` |
| `QUESTION_REVEALED` | `{"cell_id": 12, "challenge_id": 88, "text": "...", "propositions": [...], "point_value": 3}` |
| `ANSWER_SUBMITTED` | `{"participant_id": 4, "chosen_index": 2, "time_elapsed_sec": 7.4, "result": "success"}` |
| `CELL_RESOLVED` | `{"cell_id": 12, "cell_type": "steal", "points_earned": 6, "points_removed_from_opponent": 3, "prize_awarded": null}` |
| `MANAGER_INTERVENTION` | `{"action": "force_cell_resolution", "cell_id": 12, "reason": "erreur technique tablette joueur", "user": "manager_oscar"}` |
| `PLAYER_LOCKED` / `PLAYER_UNLOCKED` | `{"target": "all"}` ou `{"target": "participant_id", "participant_id": 4}` |

## 5. Projection (lecture rapide, reconnexion)

```python
class GameStateSnapshot(models.Model):
    """Mise à jour à chaque GameEvent traité. Sert uniquement à la reconnexion rapide
    d'un client — jamais consultée pour l'audit, qui relit GameEvent en séquence."""
    episode = models.OneToOneField(Episode, on_delete=models.CASCADE, related_name="snapshot")
    last_sequence = models.PositiveIntegerField(default=0)
    phase = models.CharField(max_length=20)
    current_turn_participant_id = models.IntegerField(null=True)
    active_cell_id = models.IntegerField(null=True)
    scores = models.JSONField(default=dict)  # {"participant_1_id": 12, "participant_2_id": 8}
    cells_played = models.PositiveSmallIntegerField(default=0)
    locked_participant_ids = ArrayField(models.IntegerField(), default=list, blank=True)
    # participants actuellement verrouillés par l'animateur (interaction désactivée côté app joueur)
    updated_at = models.DateTimeField(auto_now=True)
```

Règle d'implémentation : `GameStateSnapshot` n'est **jamais** modifié directement par une vue ou un consumer sur une intention client. Il est recalculé uniquement par la fonction de projection `apply_event(snapshot, event) -> snapshot`, appelée immédiatement après l'écriture réussie d'un `GameEvent`. Ce découplage garantit qu'il n'y a qu'un seul chemin de calcul de l'état, utilisé aussi bien en direct qu'en rejouant le log pour audit.

## 6. Comptes — `User` unique, `Participant` comme entité de participation

Un seul modèle Django réel (`AUTH_USER_MODEL`), simple, sans logique de rôle embarquée. Le rôle et le contexte (quel épisode, quel ordre de jeu, quels tags d'affichage) vivent sur une entité séparée, `Participant`, qui représente la participation d'un `User` à un `Episode` donné — c'est le même pattern que le `GamePlayer` (`user` FK + `game` FK) de ton ancien code.

```python
class User(AbstractUser):
    """Compte Django unique pour tous les rôles. Manager/Admin ont is_staff=True
    et un mot de passe classique. Les autres rôles (joueur, animateur, écran,
    opérateur) sont provisionnés par épisode : username généré aléatoirement,
    name laissé vide jusqu'à l'authentification (cf. §8)."""
    name = models.CharField(_("Name"), max_length=255, blank=True)


class Participant(TimeStampedModel):
    """La participation d'un User à un Episode donné, avec un rôle. Un même User
    peut avoir plusieurs Participant (ex. un opérateur ou un animateur récurrent
    qui intervient sur plusieurs épisodes) — pas de scoping en dur au niveau User.
    Le Manager n'a PAS besoin d'un Participant : son statut se lit directement
    sur User.is_staff, pas de ligne par épisode nécessaire pour lui."""

    class Role(models.TextChoices):
        PLAYER = "player", "Joueur"
        PRESENTER = "presenter", "Animateur"
        SCREEN = "screen", "Écran TV"
        OPERATOR = "operator", "Opérateur"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="participations")
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name="participants")
    role = models.CharField(max_length=20, choices=Role.choices)
    tags = ArrayField(models.CharField(max_length=50), blank=True, null=True)
    # métadonnées libres clé:valeur — ex. ["color:red"] pour un joueur, ["screen:1"] pour distinguer plusieurs écrans
    order = models.PositiveSmallIntegerField(null=True, blank=True)
    # pertinent seulement pour role=PLAYER (1 ou 2, détermine qui commence)

    class Meta:
        unique_together = ("user", "episode")
```

L'authentification utilise le `Token` DRF standard (`rest_framework.authtoken.models.Token`), qui pointe vers `AUTH_USER_MODEL` — donc identique pour tous les rôles, Manager compris, sans modèle de token custom.

## 7. Provisionnement des comptes d'épisode (tâche Celery)

À la validation de la grille d'un épisode (passage en statut `ready`, cf. `07-app-manager.md` §A.3), une tâche Celery `provision_episode_participants(episode_id)` :

1. Crée un `User` par acteur de plateau attendu (2 `PLAYER`, 1 `HOST`, N `SCREEN`, 1 `OPERATOR`) : `username` généré aléatoirement (8 caractères, vérifié unique), `name` laissé vide.
2. Crée le `Participant` correspondant pour chacun (`episode`, `role`, `tags`, `order` si joueur).
3. Renvoie la liste des `username` générés au Manager, pour distribution physique aux appareils avant le direct (affichage à l'écran de config, éventuellement un QR code encodant le `username`).

Le Manager n'a rien à provisionner pour lui-même : son `User` existe déjà (compte permanent, créé manuellement), il choisit simplement l'épisode à superviser depuis son interface — aucun `Participant` créé pour cette supervision, la vérification d'autorisation se fait sur `user.is_staff`.

## 8. Authentification d'un Participant (flux détaillé)

Un `User` de plateau (joueur/animateur/écran/opérateur) n'a pas de token dès sa création — il est émis à la première connexion, quand la personne physique s'installe devant l'appareil :

```
POST /api/auth/join/
{ "username": "XYBNN", "name": "Léon Kali" }
```

Traitement serveur :
1. Résout le `User` par `username` (rejette si inconnu).
2. Renseigne ou met à jour `User.name` avec la valeur `name` reçue.
3. Supprime le `Token` existant pour ce `User` s'il y en a un (empêche toute double connexion simultanée sur le même compte, cf. `01-architecture-backend.md` §5).
4. Crée un nouveau `Token`, renvoie sa `key`.

L'app utilise ensuite cette `key` pour ouvrir la connexion WebSocket (`?token=<key>`). Le middleware d'authentification résout le `User` via le `Token` standard DRF (`TokenAuthentication`), puis le Consumer résout le `Participant` correspondant (`Participant.objects.get(user=user, episode=<eid de l'URL>)`) pour connaître le rôle, les tags et l'ordre applicables à cette connexion précise. Manager/Admin suivent le même schéma de résolution `Token → User`, mais sans lookup `Participant` — leur rôle s'obtient directement via `user.is_staff`. Détail complet du flux WebSocket dans `03-protocole-websocket.md`.
