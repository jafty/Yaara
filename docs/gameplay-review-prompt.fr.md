# Yaara — Contexte vérifié et demande de réflexion sur le rythme du jeu

Document de travail en français, utilisable comme prompt autonome. Aucun changement de règles n'est décidé par ce document.

## Périmètre et fiabilité

Lecture du 19 octobre 2026, sur la branche de déploiement récupérée depuis le dépôt, au commit `2b0d424bd3cb328c408e69e3870d342005df3d14`. Cela identifie le code analysé, sans attester quelle révision tourne effectivement en production ni les paramètres d'une sauvegarde particulière.

Les sections « Fonctionnement vérifié » décrivent les nouvelles parties par défaut. Les sauvegardes peuvent conserver des règles antérieures. Les observations du joueur et les propositions sont séparées des faits implémentés.

Sources principales : [moteur](../simulation/engine.py), [paramètres et formules](../simulation/rules.py), [calendrier](../simulation/calendar.py), [services applicatifs](../simulation/services.py), [décisions](decisions.md). Le [dossier historique](design-source.fr.md) contient des propositions et des valeurs dépassées : notamment, sa progression agricole 100/200/300 ne décrit pas la nouvelle économie 100/130/200.

## Fonctionnement vérifié : cadre et calendrier

- Le joueur dirige une maison possédant initialement trois cités, face à deux maisons de trois cités chacune. Le code applicatif propose actuellement du solo contre des adversaires automatiques actifs ou passifs ; le multijoueur humain n'est pas encore livré.
- Le monde avance par tours communs à toutes les maisons d'une même partie, appelés lunes ou mois. Une année comprend douze tours. Les horloges de parties distinctes ne constituent pas un monde commun.
- La cadence automatique est actuellement de dix minutes par tour par défaut ; cinq minutes sont également proposées. Un mode manuel existe.
- À dix minutes par tour, une année représente nominalement deux heures ; onze tours représentent 1 h 50. Le premier tour automatique peut être plus court : son échéance est alignée sur la prochaine borne UTC. Les pauses et retards du planificateur affectent le temps réel observé.
- Une nouvelle partie automatique attend un démarrage explicite. Lire les pages d'introduction ne la démarre pas.
- La première lune ouverte est la lune 1. Sa clôture comptabilise son économie et exécute ses ordres, puis ouvre la lune 2. La première récolte est versée à la clôture de la lune 12, puis aux lunes 24, 36, etc.
- La durée par défaut est de 120 tours, soit dix années et environ vingt heures sans pause à la cadence actuelle. Des durées de 24, 60 et 240 tours sont également acceptées.
- Posséder toutes les cités donne immédiatement la victoire. Sinon, le classement final compare le nombre de cités, puis la population de rattachement ; une égalité reste possible. Perdre toutes ses cités entraîne l'élimination en fin de tour.

## Fonctionnement vérifié : habitants, mesures et liquidités

Chaque cité commence avec :

| Élément | Valeur initiale |
| --- | ---: |
| Population de rattachement | 1 000 habitants |
| Fidèles mobilisables, inclus dans cette population | 100 |
| Réserves dépensables | 600 000 mesures |
| Prélèvement accumulé, non dépensable | 0 |
| Capacité du grenier | 2 400 000 mesures |

Une maison commence donc avec 3 000 habitants, 300 Fidèles et 1 800 000 mesures réparties entre trois greniers. **Ce total n'est pas une caisse mutualisée.**

Le rendement est de **100 mesures par habitant présent et par tour**, puis **130 avec les premiers canaux**, puis **200 avec le réseau de canaux**. Le premier ouvrage agricole apporte donc **+30 par habitant et par tour**, et le second **+70 supplémentaires**, pas +100 à chaque étape.

À population constante de 1 000 habitants présents :

| État agricole | Comptabilisation par tour | Production sur douze tours |
| --- | ---: | ---: |
| Sans canaux | 100 000 | 1 200 000 |
| Premiers canaux | 130 000 | 1 560 000 |
| Réseau de canaux | 200 000 | 2 400 000 |

**Cette production n'entre pas dans le grenier chaque tour.** Elle s'accumule dans un compte de prélèvement indisponible, puis est versée annuellement dans la limite de la capacité locale. Le surplus est perdu.

Les hommes en expédition ne produisent pas pendant les tours où le moteur les compte absents. La comptabilisation économique précède les départs et les retours : le tour du départ compte encore leur présence ; le tour du retour compte encore leur absence.

La croissance annuelle est de 0,5 %, arrondie à l'entier inférieur par cité, après calcul du prélèvement. La reconstitution des Fidèles transforme des habitants existants en hommes mobilisables, sans ressusciter les morts ; elle est plafonnée à 1 % de la population et à l'écart avec un contingent cible de 10 %.

Les mesures représentent, dans l'intention du concepteur, des ressources et un équivalent de temps de travail. **Toute nouvelle activité doit avoir un coût d'opportunité.** Ne pas inventer une réserve parallèle de travail gratuit.

Distinction importante avec le code : les constructions actuelles facturent un coût en mesures et occupent l'équipe locale, mais ne retirent pas explicitement un nombre de travailleurs de la population productive. Ajouter cette mobilisation serait une nouvelle règle ; il faudrait éviter de facturer deux fois le même travail.

## Fonctionnement vérifié : constructions et réparations

| Ouvrage | Premier niveau : coût / durée | Second niveau : coût / durée | Effet |
| --- | --- | --- | --- |
| Canaux | 2 400 000 / 6 tours | 4 800 000 / 12 tours | Rendement 100 → 130 → 200 |
| Grenier | 500 000 / 4 tours | 1 200 000 / 8 tours | Capacité 2,4 → 3,6 → 6 millions |
| Enceinte | 1 200 000 / 8 tours | 9 600 000 / 20 tours | Multiplicateur de la défense locale contre capture : 1 → 1,6 → 3 |
| Forge locale | Au moins 600 000 / 8 tours | Au moins 1 400 000 / 14 tours | Équipement militaire amélioré |
| Réparation d'enceinte | 240 000 / 3 tours au niveau 1 | 1 920 000 / 6 tours au niveau 2 | Restaure une enceinte endommagée |

Pour la forge, le coût exact est `max(600 000, 600 × population)` au premier niveau et `max(1 400 000, 1 400 × population)` au second.

Les valeurs internes d'équipement sont 100, 120 et 145 : elles remplacent le niveau précédent, sans cumul. Une forge équipe les gens de sa cité, pas tout le royaume. Les équipements des contingents sont figés au départ. Les valeurs numériques de combativité ne sont pas montrées aux joueurs.

Chaque cité finance seule ses travaux et ne dispose que d'une équipe de chantier : ordres scellés et chantiers actifs bloquent cette équipe. Un ordre peut sélectionner plusieurs cités, mais chaque cité doit pouvoir financer sa propre tâche ; sinon, tout l'ordre est refusé sans réservation.

Une construction commencée à la clôture de la lune 1 et durant six tours se termine à la clôture de la lune 7. Elle ne termine pas à la lune 6. Le moteur comptabilisant l'économie avant les achèvements, de nouveaux canaux achevés en lune 7 augmentent la production à partir de la lune 8.

Les réparations de murailles existent déjà. Un assaut de capture victorieux peut endommager l'enceinte ; son bonus est alors réduit de moitié, sans supprimer la défense de base. Un raid ordinaire ne déclenche pas cet état et ne désactive pas la production des villages. Les réparations agricoles ou généralisées seraient de nouvelles fonctionnalités.

Les enceintes n'augmentent pas la défense utilisée dans la formule des raids. Les forges, en revanche, interviennent dans la force militaire. Ne pas confondre ces usages.

## Fonctionnement vérifié : ordres et expéditions

- Préparer et vérifier un ordre ne réserve rien. Le sceller réserve les mesures, les effectifs ou l'équipe nécessaires. Le paiement intervient à la clôture, après la comptabilisation économique et le versement annuel éventuel.
- L'annulation avant clôture existe dans les règles complètes actuelles ; elle libère les réservations, sans remboursement puisque la dépense n'a pas encore eu lieu.
- La confirmation exige néanmoins des fonds disponibles à cet instant : une récolte attendue à la clôture ne permet pas de sceller un ordre encore inabordable.
- Chaque origine paie la part variable correspondant à ses hommes et une part du forfait proportionnelle à son contingent. Les autres cités ne contribuent pas.
- Raid : minimum 20 Fidèles ; coût = 20 000 + 2 500 × effectif.
- Capture : minimum 80 Fidèles ; coût = 900 000 + 18 000 × effectif. Au minimum, cela représente 2 340 000 mesures, davantage que toutes les réserves initiales d'une maison.
- Départ à la clôture N, combat à N+1, retour à N+2. Le butin n'est dépensable qu'après son dépôt effectif, sous réserve de capacité et de propriété des cités de retour.
- Une cible est réservée exclusivement dès la confirmation. La géographie et les composantes de cités amies déterminent les origines admissibles. Chaque maison a initialement une cité ennemie accessible dans chacun des deux domaines rivaux.

## Pourquoi un raid victorieux peut être déficitaire

Un raid rencontre aléatoirement 20 %, 30 % ou 40 % des Fidèles disponibles de sa cible. La victoire exige une force strictement supérieure à celle des défenseurs rencontrés.

Le stock accessible représente un quart du grenier. En cas de succès, le butin est le minimum entre 60 % de ce quart et 5 000 mesures par survivant. Le raid peut aussi détruire des réserves : cette destruction n'est pas un revenu pour l'attaquant. Un succès protège la cible contre le pillage pour une durée de douze tours selon les contrôles du calendrier.

Exemple contrôlé : cible à 600 000 mesures et 100 Fidèles disponibles, équipements ordinaires des deux côtés, sans autre événement.

| Attaquants | Dépense | Défense rencontrée | Résultat | Butin | Solde brut |
| --- | ---: | ---: | --- | ---: | ---: |
| 20 | 70 000 | 20 | Défaite, car égalité de force | 0 | −70 000 |
| 30 | 95 000 | 20 | Victoire | 90 000 | −5 000 |
| 40 | 120 000 | 30 | Victoire | 90 000 | −30 000 |
| 41 | 122 500 | 40 | Victoire | 90 000 | −32 500 |

Ces soldes excluent les décès, les prélèvements perdus pendant l'absence et les pertes éventuelles au dépôt. Une cible ayant déjà dépensé ses réserves rapporte encore moins. Un raid n'est donc pas nécessairement une activité de financement, même en cas de victoire.

## Diagnostic chiffré du début de partie

Les points suivants sont des déductions des règles, pas de nouvelles propositions :

1. Une forge initiale absorbe les 600 000 mesures d'une cité ; un grenier en absorbe 500 000 et laisse 100 000. Les canaux et l'enceinte ne sont pas finançables avec ses seules réserves initiales.
2. Sans dépense, expédition ou attaque, une cité atteint 1 800 000 mesures après la première récolte. Les premiers canaux restent donc inabordables. À la seconde récolte, elle atteint sa capacité de 2 400 000 ; 606 000 mesures débordent, compte tenu de la croissance à 1 005 habitants durant la deuxième année.
3. L'agriculture productive est ainsi inaccessible pendant la première année dans ce scénario, et accessible après la deuxième récolte. Agrandir le grenier ne suffit pas à rendre les canaux abordables après la première récolte : 600 000 − 500 000 + 1 200 000 = 1 300 000 mesures.
4. À population constante de 1 000 habitants, les premiers canaux procurent 360 000 mesures supplémentaires par année complète pour un coût de 2 400 000 : environ 6,67 années de production améliorée pour amortir ce coût brut, soit 13 h 20 à la cadence actuelle, hors construction et attente des versements. La croissance, le stockage et l'horizon de victoire modifient la valeur réelle.
5. Il existe deux blocages distincts : les réserves dépensables et la disponibilité des équipes. Ajouter de petits ouvrages au même emplacement de chantier pourrait rendre l'ouverture plus conflictuelle sans créer d'actions pendant un grand chantier.

## Observations du joueur

Le jeu est fonctionnel, clair et sans anomalie flagrante d'affichage ou de fonctionnalité pendant les essais.

En revanche, les réserves sont rapidement immobilisées dans quelques bâtiments coûteux. Dépenser immédiatement paraît tentant, mais même une gestion prudente laisse peu de possibilités avant la récolte suivante. Le raid devient presque la seule activité divertissante, alors qu'il est rarement rentable au début.

Le joueur accepte un jeu de temps long, avec des connexions espacées. Il souhaite néanmoins davantage de décisions abordables : petits aménagements agricoles, étapes de construction, améliorations militaires spécialisées, travaux contextuels et éventuellement illustrations dans un style de papyrus.

Il confie les arbitrages de conception à son interlocuteur : ces suggestions peuvent être rejetées ou transformées.

## Réflexions déjà échangées et statut des idées

- Attendre les résultats d'une décision peut être satisfaisant ; attendre de pouvoir prendre une décision peut être frustrant.
- Investir tôt peut être rationnel. Le système ne doit pas compter sur l'autodiscipline du joueur pour préserver son intérêt.
- Multiplier les achats bon marché ne résout pas à lui seul l'absence de liquidités entre récoltes.
- Une capacité de travail gratuite parallèle aux mesures a été explicitement rejetée par le joueur.
- Les exemples précédemment proposés avec 100 mesures initiales, 120 mesures annuelles ou des actions à 2–16 mesures étaient fictifs et hors échelle. **Ils ne doivent servir ni de référence ni de base d'équilibrage.**
- Des progressions courtes d'aménagements, des préparatifs payants et de la reconnaissance restent des pistes, sans tarifs validés. Leur intérêt doit être comparé aux dépenses, rendements, équipes et durées actuels.
- Distribuer progressivement une fraction de la production annuelle reste une hypothèse structurelle, pas une décision. Le moteur accumule déjà la production tour par tour : modifier sa disponibilité changerait la liquidité, l'exposition au pillage et les possibilités de réinvestissement, même à production nominale inchangée. Un versement anticipé peut aussi éviter des débordements : les recettes effectivement encaissées ne resteraient donc pas forcément identiques.
- De nouveaux dégâts et travaux de réparation ne doivent pas enfermer le vaincu dans une spirale sans ressources. Les réparations d'enceinte existantes doivent être prises en compte avant de proposer un système supplémentaire.
- Les illustrations restent une proposition. L'interface actuelle privilégie le manuscrit sobre et comporte déjà une carte schématique ; ajouter des illustrations de papyrus serait un choix de présentation à discuter.
- Le code conserve des familles de règles et des marqueurs de compatibilité pour les anciennes sauvegardes. Le souhait de ne plus parler de versions dans la conception ne justifie pas de les supprimer ni de modifier silencieusement les parties existantes.

## Demande à adresser au game designer

Tu es un game designer expérimenté en jeux de stratégie et de gestion asynchrones. Utilise les faits vérifiés ci-dessus pour proposer une évolution concrète de Yaara. Réponds entièrement en français. **Ne code rien et ne considère aucune proposition antérieure comme approuvée.**

1. Analyse séparément le rythme des décisions, la disponibilité des réserves locales, l'occupation des équipes, la rentabilité agricole et l'intérêt militaire des raids.
2. Prends position : faut-il préserver les versements entièrement annuels, revoir les investissements initiaux, ajouter des actions intermédiaires, ou combiner certains de ces leviers ? Explique les compromis.
3. Propose un ensemble limité de mécanismes cohérents. Pour chaque nouveauté, précise coût en mesures, durée en tours, effet, éventuel usage de l'équipe locale, conditions, répétabilité et coût d'opportunité. Identifie clairement les chiffres proposés et leur justification relativement à l'économie actuelle.
4. Évite le travail gratuit, les clics systématiquement rentables, les améliorations universelles et les tâches qui obligent à se reconnecter toutes les dix minutes.
5. Compare une première année actuelle à une première année proposée, sur douze clôtures, avec soldes locaux, réservations, dates d'achèvement et prélèvements réellement dépensables. Toute simulation simplifiée doit expliciter population, adversaires et événements exclus.
6. Évalue les investissements par rapport à une partie par défaut de 120 tours, soit vingt heures nominales. Distingue production acquise, argent versé, amortissement et valeur stratégique.
7. Préserve une reprise possible après défaite. Distingue raids, captures, sièges, dégâts existants et nouveaux dégâts proposés.
8. Explique comment le jeu reste intéressant avec des connexions espacées. Distingue une activité facultative d'un avantage décisif accordé à la présence permanente.
9. Tu peux t'inspirer de Travian, OGame, Clash of Clans ou Age of Empires, sans importer des mécanismes incompatibles avec notre cadence, notre économie et nos tours communs.
10. Termine par les décisions recommandées, les ajustements simples, les changements structurels et les mesures à collecter lors des essais. Signale toute information manquante au lieu d'inventer une règle actuelle.

## Vérifications réalisées pour ce document

Lecture des paramètres et des chemins d'exécution cités, puis exécution directe du moteur natif sans base de données et sans modifier le jeu : progression passive jusqu'aux clôtures 1, 11, 12 et 24 ; devis initiaux forge/grenier/canaux/enceinte ; calculs de raids à 20, 30, 40 et 41 attaquants face à 20, 30 et 40 défenseurs. Les résultats reproduisent les exemples ci-dessus. Aucun équilibrage, code applicatif ou état de partie n'a été modifié.
