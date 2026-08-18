# EpicQuiz — App Opérateur (régie technique)

Poste de régie plateau. Contrôle exclusivement la couche présentation — bascule d'écrans, effets, tally. Aucune action de cette app ne touche jamais l'état du jeu ni ne produit de `GameEvent` (cf. `03-protocole-websocket.md` §8).

## 1. Écrans / zones fonctionnelles

1. **Connexion** — même flux simplifié que les autres rôles de plateau : `username` (distribué par le Manager) + nom de la personne → token (cf. `04-app-joueur.md` §1). Identité nominative utile en cas d'investigation d'un problème technique de diffusion, même si la traçabilité est moins critique que pour le Manager puisqu'aucune règle de jeu n'est en jeu.
2. **Multivision des écrans TV** — aperçu miniature de ce qu'affiche chaque écran physique du plateau, avec un sélecteur de vue par écran (`grid`, `active_question`, `scores`, `cell_replay`, `idle`) → `POST /episodes/<eid>/change-tv-view/` avec l'identifiant de l'écran ciblé.
3. **Pupitre d'effets** — boutons pour déclencher manuellement des effets sonores/visuels (stinger de début de segment, ambiance, jingle de fin) → `POST /episodes/<eid>/trigger-effect/`.
4. **Journal des effets automatiques** — affichage des effets déclenchés automatiquement par le serveur en réaction à un événement de jeu (ex. son de case vide), pour que l'opérateur sache ce qui vient de se produire sans avoir eu à agir, et puisse enchaîner une action manuelle en conséquence si besoin (ex. couper l'ambiance après le jingle automatique).
5. **Tally / retour caméra** — hors périmètre du jeu, à spécifier avec l'équipe technique plateau si le système doit piloter ça ou si c'est un système broadcast dédié déjà existant (auquel cas cette app ne fait qu'informer, pas piloter).

## 2. Ce que cette app ne fait jamais

- Aucun appel aux endpoints `select-cell`, `launch-question`, etc. — ces endpoints refusent l'accès au rôle Opérateur au niveau des permissions DRF, pas seulement masqués dans l'interface (défense en profondeur : même une app modifiée ou un client alternatif ne peut pas les appeler avec succès).
- Aucune lecture des propositions/bonnes réponses avant qu'elles ne soient officiellement révélées à l'antenne — l'app ne doit afficher que ce qui est déjà `question_revealed`, jamais anticiper le contenu d'une case non encore jouée, pour éviter toute fuite d'information côté régie qui pourrait influencer indirectement le déroulé (ex. réaction visible d'un technicien).

## 3. Latence et fiabilité

Contrairement aux apps joueurs/animateur où une latence de quelques centaines de ms est tolérable, la bascule d'écran TV doit être perçue comme quasi instantanée à l'antenne. Prévoir :
- Connexion WebSocket dédiée et prioritaire (canal Broadcast séparé du canal Jeu, cf. architecture) pour recevoir la confirmation de bascule sans contention avec le trafic de jeu.
- Retour visuel immédiat côté app Opérateur dès l'envoi de la requête HTTP (état "en cours d'application"), confirmé ensuite par l'événement de diffusion reçu sur WebSocket.
