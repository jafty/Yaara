# Yaara — Règles du jeu, équilibrage et conception technique

Révision du 15 octobre 2026, après les arbitrages complémentaires du concepteur (cibles exclusives, stocks locaux et périmètre V0/V1). Ce document remplace la présentation précédente. Il sépare désormais les règles compréhensibles par un joueur, les formules de référence et les choix de développement.

## Comment lire ce dossier

- **Partie I : comprendre et jouer à Yaara.** Aucun prérequis informatique. Les règles sont expliquées avec des exemples, et les actions sont présentées comme des fiches.
- **Partie II : paramètres et calculs.** Destinée au concepteur et au maître du jeu. Les noms de variables sont en anglais, avec des mots entiers.
- **Partie III : construire et exploiter le jeu.** Architecture, tests, concurrence, déploiement, parties multiples et méthode avec l’IA.
- **Annexes : arbitrages et sources.** Ce qui est confirmé, proposé ou reporté reste identifiable.

### Statut des décisions de cette révision

| Statut | Décisions |
|---|---|
| Confirmé par le concepteur | Rendement de référence de 100 Mesures par habitant et par mois ; consommation théorique de 1 000 ; irrigation augmentant le rendement de 100 par niveau ; combativité interne commençant à 100 et décrite qualitativement aux joueurs ; secours plafonnés ; règne de dix ans paramétrable ; tests manuels/solo et premières parties à dix minutes par mois, sans objectif inférieur à cinq minutes ; environnement actuel capable d’exécuter tests et migrations ; stocks locaux ; cible militaire exclusive au premier ordre confirmé ; issues de siège conservées ; annulation avant clôture en V1 ; forge équipant les nouvelles populations ; projection par destinataire ; capture au premier tour impossible ou suicidaire |
| Propositions de cette révision, non présentées comme déjà approuvées | Financement mutualisé automatique des stocks locaux ; stock initial de 600 000 par cité pour rendre la capture initiale impossible ; minimum de 20 hommes pour un raid et 80 pour une capture ; classement départagé par population ; prise en compte des habitants présents par comptabilisation mensuelle et versement annuel |
| Conservé du socle | Cités et villages, Fidèles inclus dans la population, une ressource, missions courtes, défense automatique, deux actions militaires, chantiers longs, monde en réseau, retour par origine, victoire territoriale |
| Reporté | Interventions correctives du MJ en cours de partie, occupation temporairement coûteuse, autonomie locale et révoltes, logistique de convois, classement global compétitif, monde permanent, nombreuses spécialités militaires |

**Les propositions forment une configuration de travail cohérente à discuter.** Elles peuvent être remplacées sans considérer que le concepteur les a implicitement validées. Le changement d’unité est acquis ; le stockage local et l’annulation V1 sont acquis ; le financement mutualisé, le montant initial et la fiscalité restent des recommandations explicites.

# Partie I — Comprendre le jeu

## 1. Le rôle du joueur et la victoire

Vous incarnez un Prétendant qui cherche à étendre son autorité sur les cités-oasis de Yaara. Le monde est fictif : terre crue, sable, terre rouge, agriculture autour des oasis, scribes et rivalités politiques. Les références historiques servent à rendre ce pouvoir vraisemblable ; le jeu ne reproduit pas toutes les institutions d’une civilisation précise.

Vous commencez avec trois cités. Chacune représente son centre et les villages rattachés. Vous donnez des ordres, aménagez votre territoire, faites piller vos voisins ou tentez de prendre leurs cités. Vous ne déplacez pas des unités case par case et ne dirigez pas les combats en temps réel.

La partie dure initialement **dix ans**, soit 120 mois. Le maître du jeu fixe cette durée avant le lancement. Celui qui possède toutes les cités gagne immédiatement. Sinon, celui qui en possède le plus à la fin du règne gagne. Un joueur qui n’a plus aucune cité à la fin d’un mois est éliminé.

**Départage proposé :** à nombre de cités égal, comparer la population totale qui leur est rattachée, puis conserver une égalité si elle subsiste. Les hommes en campagne sont inclus une seule fois, dans leur cité d’origine. Ce critère donne un avantage à la préservation des sujets sans créer une nouvelle ressource de prestige.

Il peut inciter un joueur actuellement derrière à attaquer, mais ne garantit pas la disparition de l’attentisme. Le joueur devant peut continuer à se défendre. Pour préserver les informations cachées, un classement peut indiquer qui est devant sans publier les populations exactes ; ce rang est lui-même une information partielle volontairement rendue publique. Le départage et cette visibilité sont à valider ensemble.

## 2. Un mois de jeu et les formats de partie

Le monde avance par mois. Le passage au mois suivant est appelé un **tick** : le jeu exécute ensemble les événements qui arrivent à échéance.

| Format initial | Déclenchement | Une année | Dix ans |
|---|---|---:|---:|
| Test ou solo manuel | Bouton « Passer au mois suivant » | Selon le joueur/testeur | Selon le joueur/testeur |
| Premier multijoueur | Un mois toutes les dix minutes | Deux heures | Vingt heures actives |
| Variante plus rapide | Un mois toutes les cinq minutes | Une heure | Dix heures actives |

Une partie de vingt heures ne signifie pas vingt heures de clics continus. Elle demande néanmoins un accord sur les plages de jeu. Le premier format conseillé est une partie interrompue entre des sessions communes, plutôt qu’un monde avançant pendant le travail ou le sommeil de chacun. Une pause commune ou une trêve suspend tout le monde ; personne ne peut arrêter seulement ses propres ennemis.

Vous n’êtes pas obligé de donner un ordre à chaque mois. Un chantier continue seul. Une armée partie continue sa mission. Une cité se défend sans confirmation.

### Le déroulement d’un mois

1. Les nouveaux ordres sont clos : on ne peut plus en ajouter pour ce mois.
2. Le jeu comptabilise le mois économique écoulé. Lors du bilan annuel, il renouvelle une partie des Fidèles et verse la récolte fiscale.
3. Les ordres confirmés démarrent : les dépenses sont payées et les troupes quittent leurs cités.
4. Les anciens chantiers et projets arrivés à échéance s’achèvent.
5. Les secours sont répartis, puis les combats du mois sont résolus dans un ordre tiré au sort.
6. Les secours et armées dont le retour est prévu reviennent ; leur butin est déposé.
7. Le jeu constate les éliminations et la victoire éventuelle, puis présente les nouvelles.

Les combats du même mois ne sont pas décrits comme se produisant exactement à la même seconde. Leur ordre reste nécessaire pour les interactions entre des cités différentes, notamment lorsqu’une origine de secours est conquise. Cet ordre est tiré après clôture. En revanche, confirmer en premier donne désormais la priorité de réservation sur une cible : c’est un choix de règle assumé.

## 3. Les habitants et les Fidèles

Une cité initiale possède 1 000 habitants, dont 100 Fidèles mobilisables. Les Fidèles font partie des 1 000 ; ils ne s’y ajoutent pas. Les autres habitants sont les civils.

Quand 40 Fidèles partent, la cité conserve 1 000 habitants de rattachement, mais seulement 960 habitants présents et 60 Fidèles disponibles sur place. Les 40 absents ne défendent pas leur cité.

Si trois meurent, sa population de rattachement descend à 997 et son contingent total à 97. Au retour, les 37 survivants rejoignent les présents ; ils ne sont pas ajoutés une deuxième fois à la population.

Chaque année, une fraction limitée des habitants peut rejoindre ou reprendre le contingent. Cette reconstitution ne ressuscite personne : elle transforme des habitants déjà comptés en hommes mobilisables. Les hommes encore en expédition comptent dans le contingent existant, afin que leur absence ne crée pas gratuitement une nouvelle armée.

En V1 seulement, la population connaît aussi une croissance annuelle lente. Une cité peut donc conserver une population stable tout en ayant subi des morts ; le bilan distingue population actuelle et décès cumulés.

## 4. Les Mesures, les revenus et les réserves

### 4.1 Ce que représente une Mesure

Les Mesures représentent les ressources exceptionnelles à la disposition du pouvoir : prélèvements agricoles et équivalent de fournitures, transports et services. Elles ne sont pas une monnaie historique précisément convertible en kilogrammes ou en euros.

La nouvelle échelle est :

- Un habitant rapporte théoriquement **100 Mesures par mois** au niveau initial.
- Un habitant consomme théoriquement **1 000 Mesures par mois** pour vivre.
- Cette consommation ordinaire appartient à l’économie domestique : elle n’est pas retirée chaque mois des réserves du Prétendant.
- L’irrigation fait passer le rendement fiscal de **100 à 200, puis à 300**.

Une cité stable de mille habitants présents rapporte donc **1 200 000 Mesures par an** au départ. Trois cités rapportent 3 600 000. Il s’agit bien du prélèvement disponible pour le pouvoir, pas de toute la production nécessaire à la survie.

Passer le prélèvement de 100 à 200 double le revenu du pouvoir. Cela ne signifie pas nécessairement que toute la production agricole double : dans l’abstraction où la subsistance reste à 1 000, la production minimale correspondante passerait de 1 100 à 1 200 par habitant. Cette image explique le levier économique ; elle ne crée pas une seconde comptabilité alimentaire.

### 4.2 « Habitants sur place » : précision proposée

Le document antérieur calculait toute la récolte sur la population constatée au seul jour du bilan. Cela aurait donné une année entière d’impôt au propriétaire d’une cité prise juste avant la récolte, et aurait pu retirer une année entière de rendement pour une absence très courte.

Pour appliquer littéralement la nouvelle référence aux **habitants présents**, cette révision propose de comptabiliser le rendement de chaque mois puis de verser le total une fois par an. Le scribe peut annoncer le prélèvement attendu, mais ce montant n’est pas encore dépensable.

Ainsi, 50 Fidèles absents deux mois au rendement initial diminuent le prochain prélèvement de 10 000 Mesures, et non de 60 000. Le coût d’expédition ne doit alors pas facturer une seconde fois la même production perdue.

Cette comptabilisation est une modification proposée, pas une simple correction d’unité. Si l’on préfère une règle encore plus courte, on peut conserver la récolte annuelle instantanée sur la population de rattachement, mais il faut alors abandonner l’exclusion littérale des absents. On ne doit pas mélanger les deux modèles.

### 4.3 Des réserves réellement locales — décision retenue

Dans l’ancien modèle, « ressources locales abstraites » désignait une estimation des ressources exposées dans une cité à partir d’un trésor global. Ce n’était pas un stock indépendant suivi au fil des dépenses. La proposition ci-dessous remplace cette approximation par une quantité réellement enregistrée pour chaque cité.

Chaque cité possède désormais :

- son rendement par habitant ;
- ses réserves effectives ;
- sa capacité de stockage ;
- son prélèvement annuel en préparation, encore indisponible.

La vue du domaine affiche la somme des réserves des cités, mais ce total n’est pas un deuxième trésor. Un raid vise les réserves de sa cible. Un siège consomme celles de la place assiégée. Une capture transfère ce qui reste effectivement sur place. Agrandir le grenier d’une cité ne déplace plus magiquement une part des réserves des autres.

**Pour éviter d’ajouter des convois**, le paiement des ordres reste organisé automatiquement à l’échelle de vos possessions : toutes vos cités peuvent contribuer financièrement, proportionnellement à leurs réserves libres. Il n’y a ni formulaire de transport ni délai de transfert. Les stocks sont donc locaux pour leur exposition et leur plafond, mais les dépenses publiques sont mutualisées. Cette convention doit rester visible ; elle ne simule pas un blocus économique total.

Par défaut, la contribution automatique peut venir de toutes les cités possédées, même si le domaine est coupé. La circulation militaire reste plus restrictive. Restreindre aussi le financement aux zones reliées serait une règle supplémentaire à discuter.

La récolte entre dans chaque cité, selon sa propre capacité. Un grenier plein peut déborder même si un autre est vide. Le butin revient aux cités d’origine des survivants et peut lui aussi y déborder. Aucun transfert manuel de réserve n’est ajouté dans la première proposition.

Si cette conséquence est trop contraignante, on réexamine la mutualisation au retour ou les transferts. Le stockage local est simple à représenter ; ce sont ces choix de financement et de circulation qui déterminent sa complexité réelle.

## 5. Préparer et confirmer un ordre

### V0 : confirmation définitive ; V1 : annulation avant clôture

Le joueur prépare un formulaire, puis consulte un récapitulatif du coût, des effectifs, de la cible et du départ. Avant confirmation, aucun ordre n’existe et rien n’est réservé. Il n’y a pas de brouillon persistant.

En V0, confirmer engage définitivement l’ordre : aucun bouton d’annulation n’est prévu. Le serveur peut toujours invalider un ordre devenu impossible selon les règles, en libérant ses réservations et en donnant le motif.

En V1, le joueur peut annuler avant clôture. Cela libère hommes, fonds, emplacement et cible militaire. Il ne revient pas à un brouillon. Une nouvelle confirmation perd l’ancienne priorité sur la cible.

Après départ, aucune annulation ou restitution des frais n’est prévue.

### Ce qui peut empêcher une confirmation

| Condition | Ce que le scribe explique |
|---|---|
| Cible déjà engagée | « Une autre expédition est déjà engagée vers cette cité. Aucun moyen n’a été réservé. » |
| Réserves libres insuffisantes | « Cette dépense dépasserait les moyens non engagés. » |
| Trop de Fidèles demandés | « Certains de ces hommes sont déjà promis à une autre expédition. » |
| Cité non reliée à la cible | « Cette communauté ne peut rejoindre cette frontière par nos possessions. » |
| Chantier déjà prévu ou en cours | « Les équipes de cette cité sont déjà engagées. » |
| Niveau précédent non achevé | « Il faut achever les premiers canaux avant d’étendre le réseau. » |
| Protection contre les raids encore active | « Les villages ne constituent pas une cible de pillage disponible. » |
| Clôture passée | « Le mois est clos. Vérifiez le départ et le devis du mois suivant. » |

« Réserver un emplacement de chantier » ne désigne pas une case sur la carte. Cela veut seulement dire que la cité ne peut avoir qu’un chantier local prévu ou en cours. Si les canaux sont déjà confirmés pour le prochain mois, on ne peut pas confirmer aussi des murs pour le même emplacement.

Les chantiers de cités différentes se déroulent en parallèle. Un seul projet global d’armement peut être prévu ou actif à l’échelle du Prétendant.

### Grouper les actions sans les confondre

Pour aménager les canaux dans trois cités, une seule proposition présente les trois destinations. Le joueur choisit celles qu’il veut. La confirmation réserve l’ensemble du lot ou ne réserve rien si le budget manque. Chaque cité garde son chantier distinct.

Pour attaquer la même cible avec des hommes de plusieurs cités, on forme **une armée** : 30 de A et 20 de B donnent une expédition de 50. Le prix est calculé sur 50, avec un seul coût fixe. Les origines sont conservées pour les pertes et le retour.

Un joueur ne confirme pas plusieurs petites expéditions du même type sur la même cible pour le même mois. Il prépare une seule expédition réunissant ses contributions. En V1, il peut l’annuler puis le refaire avant clôture, sans garantie de retrouver la cible disponible. En V0, la confirmation est définitive.

### Une seule attaque engagée contre une cité

Dès la confirmation réussie d’une attaque, sa cible devient indisponible pour toute autre attaque, quel que soit le joueur et qu’il s’agisse d’un raid ou d’une capture. Cette règle s’applique aussi aux ordres du même joueur. Un simple formulaire ouvert ne réserve rien.

Le premier ordre **accepté et enregistré par le serveur** obtient la cible. Les suivants sont refusés sans dépense ni réservation partielle, même depuis un onglet non rafraîchi. La cible reste engagée jusqu’à la résolution ou l’invalidation de l’opération ; en V1, une annulation avant clôture la libère également. Le retour ultérieur de l’armée n’empêche plus une nouvelle attaque. Une protection anti-raid reste toutefois applicable après un pillage.

Cette fenêtre couvre toute l’approche : on ne programme pas une seconde attaque pour un mois ultérieur tant que la première est engagée. Il n’y a ni file d’attente ni lancement automatique après libération. Une cible attaquée peut toujours envoyer sa propre expédition et contribuer aux secours.

Le scribe justifie ce refus par le danger d’engager une autre armée dans une opération déjà en cours, où les commandements risqueraient de se confondre. Le message révèle l’indisponibilité de la cible, mais pas l’identité, le type de mission ni les effectifs de l’autre armée. Cette fuite minimale d’information est assumée.

**Événements et alertes :** confirmation et réservation réussies ; refus « cible déjà engagée » ; invalidation avec libération ; annulation V1 avec libération ; résolution avec fin d’engagement. Le refus est montré au demandeur, la confirmation et l’annulation à l’auteur, et les rapports de combat aux destinataires autorisés. Aucun avertissement anticipé au défenseur n’est ajouté automatiquement. Les pages affichent la disponibilité courante lors de leur chargement, mais le serveur décide à chaque confirmation ; aucune actualisation en direct obligatoire pour V0.

Le premier arrivé obtient une priorité réelle. Un raid peut donc empêcher temporairement une capture concurrente. Ses frais et son engagement irréversible en V0 limitent l’usage gratuit de cette tactique ; elle reste à observer en jeu, surtout avec l’annulation V1.

## 6. Les actions accessibles

### Fiche : aménager ou renforcer une cité

**But :** augmenter son revenu, son stockage ou sa résistance.

**Choisir :** famille de travaux et une ou plusieurs cités éligibles.

**Coût :** payé au commencement, automatiquement réparti entre les réserves libres du domaine.

**Durée :** propre au chantier ; un ouvrage commencé au mois 3 et durant huit mois s’achève au mois 11, pas au mois 10.

**Conséquence :** l’ancien niveau reste actif jusqu’à l’achèvement. Si la cité est prise, le chantier et son avancement suivent la cité. Il n’est pas payé une deuxième fois.

| Famille | Première amélioration | Seconde amélioration V1 |
|---|---|---|
| Irrigation | Aménager les canaux | Étendre le réseau |
| Stockage, V1 | Agrandir le grenier | Ériger des silos |
| Fortification | Ériger une enceinte | Élever une grande enceinte |
| Réparation, V1 | Réparer l’enceinte existante | Même action, prix selon l’ouvrage |

### Fiche : organiser l’armement

**But :** améliorer durablement les moyens militaires du Prétendant.

**Choisir :** le prochain projet disponible.

**Limite :** un projet global à la fois. Cela n’occupe pas les chantiers locaux.

**Lore retenu :** le projet crée ou améliore une forge et son organisation de distribution. Elle équipe aussi les populations nouvellement rattachées, sans inventaire, transport, entretien ou délai individuel supplémentaire en V0. La forge est l’habillage du projet global, pas un bâtiment local supplémentaire à capturer.

**Conséquence :** les Fidèles du Prétendant bénéficient de son organisation ; aucune liste d’armes individuelles à gérer. La valeur interne de combativité n’est pas affichée aux joueurs. Le scribe parle d’équipement ordinaire, renforcé ou supérieur, sans montrer un score caché sous une infobulle.

### Fiche : piller

**But :** emporter une partie des réserves accessibles autour d’une cité et éventuellement en détruire une autre partie.

**Choisir :** une cité ennemie accessible et les hommes de chaque origine.

**Minimum proposé :** 20 Fidèles pour toute l’expédition, pas 20 par cité contributrice.

**Durée initiale :** départ au prochain mois, combat un mois après, retour un mois plus tard. À dix minutes par mois, cela représente vingt minutes de mission après le départ.

**Défense :** seule une fraction des hommes présents intervient. Les murs du centre et les secours de domaine ne protègent pas directement ce raid sur les alentours.

**Résultat :** succès ou échec, pertes militaires, butin plafonné par les réserves exposées et le transport. Le butin ne finance rien avant le retour. Une réussite protège la cible contre les raids suivants pendant douze mois de jeu ; cette protection n’empêche pas une capture.

Un raid peut être rentable, médiocre ou déficitaire. Une victoire n’assure pas le remboursement des frais si les réserves sont faibles.

### Fiche : capturer

**But :** prendre le contrôle de la cité, de ses habitants présents, de ses infrastructures et de ses réserves restantes.

**Choisir :** une cible et les contributions militaires accessibles.

**Minimum proposé :** 80 Fidèles au total. Ce seuil évite certaines attaques sans consistance, mais ne remplace pas le plafonnement des secours et n’assure pas la victoire.

**Coût :** beaucoup plus élevé qu’un raid de même taille. Il couvre l’opération, les approvisionnements et les moyens de campagne ; une victoire rapide ne rembourse pas automatiquement la préparation.

**Durée :** les mêmes deux mois de mission. Le siège est résumé au moment du combat, pas simulé par un blocus de nombreux tours.

**Défense :** hommes locaux, murs et secours de la zone reliée. Les murs protègent les locaux, pas les secours extérieurs.

**Après succès :** la cité change de propriétaire ; les assaillants survivants repartent vers leurs origines. Les survivants de la garnison locale passent au vainqueur. Les secours survivants repartent chez eux.

## 7. Qui peut rejoindre une attaque ?

Vos cités forment parfois plusieurs ensembles séparés. Une cible est accessible si elle touche au moins une de vos cités.

Tous les hommes d’un ensemble de cités amies reliées à cette frontière peuvent contribuer. Un ensemble isolé qui ne touche pas cette cible ne peut pas envoyer arbitrairement ses hommes à travers les ennemis.

Exemple : A — B — C sont alignées. Vous possédez A et C, l’ennemi possède B. Vous pouvez réunir A et C pour attaquer B, parce que chacune de ces deux parties touche la cible. Elles ne doivent pas être reliées l’une à l’autre en dehors de B pour cette attaque.

Une armée partie légalement poursuit sa mission si les frontières changent ensuite. Le retour est réglé par ses cités d’origine.

## 8. Les secours automatiques, pas à pas

### 8.1 Le principe

Lorsqu’une cité est menacée de capture, les autres cités reliées du même propriétaire peuvent lui envoyer automatiquement une partie de leurs Fidèles présents. Le joueur n’a pas à donner un ordre de secours ni à payer une mission supplémentaire.

Les hommes envoyés ne défendent plus leur origine pendant ce mois de combats. Ils ne peuvent être affectés qu’à une seule bataille. Chaque cité garde au moins la fraction non mobilisable en secours ; dans l’essai initial, elle peut en exporter au plus 20 %.

« Autre cité » signifie simplement : **les hommes de A qui restent à A forment sa garnison ; ils ne sont pas aussi des secours de A vers A.** Cela n’empêche pas A, même attaquée, de soutenir B.

### 8.2 Une seule attaque

A, B et C sont reliées et possèdent chacune 100 hommes présents. L’ennemi attaque B avec 220 hommes.

| Cité | Hommes conservés sur place | Secours envoyés à B |
|---|---:|---:|
| A | 80 | 20 |
| B | 100 | 0 |
| C | 80 | 20 |

B affronte l’attaque avec ses 100 hommes locaux et 40 secours. Si elle possède une enceinte, son bonus s’applique aux 100 locaux, pas aux 40 secours.

### 8.3 Deux captures au même mois

Deux armées attaquent A et C, chacune avec 220 hommes. B peut envoyer au plus 20 hommes et doit les partager. Les attaques étant comparables, B en envoie dix à chacune.

A peut aussi soutenir C avec vingt hommes, et C soutenir A avec vingt. A et C conservent donc chacune 80 hommes locaux et reçoivent chacune 30 secours. B conserve 80 hommes.

Si l’attaque contre A est deux fois plus forte que celle contre C, la contribution de B est approximativement répartie deux tiers / un tiers. On ne peut pas envoyer deux fois ses vingt mêmes hommes.

### 8.4 Deux ennemis demandent la même cible

Un seul ordre est accepté : celui confirmé en premier par le serveur. L’autre est refusé sans engagement de moyens. Il n’existe donc plus deux combats contre la même cité dans la même phase, ni partage de ses secours entre deux assaillants.

### 8.5 Pourquoi fixer les affectations pour tout le mois ?

Plusieurs **cités différentes** peuvent être attaquées. Une cité de soutien doit donc encore partager ses secours entre ces fronts. Chaque homme envoyé ne participe qu’à une bataille et ne défend plus son origine pendant cette phase.

Les affectations sont calculées une fois avant les combats. La garnison locale combat uniquement chez elle ; la règle de réutilisation de ses survivants contre une seconde attaque au même mois est supprimée, car ce cas n’est plus autorisé.

### 8.6 Le plafond que le concepteur valide

Une très petite attaque ne doit pas faire sortir tous les secours possibles. On limite donc l’aide totale attribuée à une attaque à une force comparable à celle de cette attaque, selon un coefficient administrable.

À équipement égal et avec le coefficient initial : une attaque de 80 hommes peut attirer au plus 80 secours. Le budget de 20 % par cité peut donner un total inférieur. Si un scénario de test permet exceptionnellement un attaquant unique, il attire au plus un secours, pas quarante.

Le minimum de 80 hommes pour une capture évite les missions minuscules dans la configuration proposée ; le plafond reste utile contre une attaque minimale visant un très grand domaine.

### 8.7 Ce que signifie « commandement fixé »

Un groupe envoyé par A pour défendre B reste au service du propriétaire qui l’a envoyé pendant sa bataille prévue. Si A change de maître entre-temps, on ne retourne pas instantanément ce groupe contre ses compagnons au milieu de la résolution.

À son retour, en fin de phase, il rejoint le propriétaire actuel d’A. Cette règle conserve une origine et une échéance claires, sans créer une statistique de fidélité politique.

## 9. Comprendre une tentative de capture

La **défense de campagne** représente les défenseurs locaux sans avantage des murs, auxquels s’ajoutent les secours. La **défense fortifiée** représente les mêmes locaux avec l’avantage des murs, plus les secours.

Il est donc possible d’être plus fort que l’armée en terrain ouvert sans réussir à prendre sa place forte.

### Version V0 : la règle courte

L’assaillant doit dépasser la défense fortifiée. Sinon il échoue, même s’il aurait gagné en terrain ouvert. Une armée très inférieure subit des pertes plus lourdes qu’une armée proche du seuil. Il n’existe pas encore de test de réserves.

L’expression précédente « échec ordinaire » décrivait la gravité de la défaite, pas une supériorité obligatoire sur la défense de campagne. La nouvelle table sépare clairement victoire et mortalité.

### Version V1 : les réserves peuvent faire céder les murs

| Situation | Ce qui se passe |
|---|---|
| Aucune défense | Prise sans massacre automatique des civils |
| Supériorité très nette sur la défense fortifiée | Reddition rapide ; faibles pertes |
| Supériorité simple sur la défense fortifiée | Assaut victorieux ; pertes plus importantes |
| Supériorité sur la campagne, mais pas sur les fortifications | Les réserves de la cité déterminent si elle tient |
| Pas de supériorité sur la campagne | Échec militaire ; pas de siège imposé |

Dans le cas où les réserves décident, elles doivent nourrir temporairement la population abritée. Si elles suffisent, la cité tient et l’armée repart. Sinon, elle capitule. Les vivres consommés sont retirés uniquement de son stock local. Les autres cités ne lui fournissent pas automatiquement du ravitaillement pendant ce test.

Il n’y a pas de famine générale parce que le joueur a dépensé son trésor. Les gens se nourrissent ordinairement hors de cette comptabilité publique.

Si l’assaillant est inférieur à la moitié de la défense de campagne, il subit l’échec très défavorable. Avec des murs dont le coefficient est au moins un, être inférieur à la moitié de la campagne implique déjà d’être inférieur à la défense fortifiée : il n’existe pas de trou entre les branches.

## 10. Capturer, rentrer et perdre une cité

Une cité conquise transfère ses réserves présentes, son chantier, ses infrastructures et sa population de rattachement. Dans la proposition fiscale de cette révision, le prélèvement annuel en préparation reste attaché à la cité et suit également sa souveraineté. Il ne s’agit pas encore de Mesures disponibles.

Les hommes qui étaient absents continuent sous leur ancien commandement jusqu’à leur retour. À cette date, ils rejoignent le propriétaire actuel de leur cité d’origine. Le butin est réparti entre les groupes au prorata de leurs survivants et déposé dans leurs origines.

Reprendre une cité avant le retour de ses hommes permet donc de les récupérer. Mais avec des expéditions de deux mois, cette fenêtre est courte et parfois inexistante. Ce n’est pas une garantie de reconquête.

Une enceinte endommagée perd une partie de son avantage sans disparaître. La réparation demande argent et temps. Un assaut victorieux peut l’endommager ; une reddition rapide la conserve normalement intacte.

Le joueur est éliminé seulement à la fin du mois complet. Ses opérations restantes ne poursuivent pas des conquêtes posthumes : elles rentrent. Si la partie entière est terminée, le classement est figé ; les opérations encore en route sont mentionnées dans l’épilogue, sans modifier ensuite le résultat.

## 11. Information, correspondance et interface

Vous connaissez exactement vos moyens : population, présents, absents, réserves par cité, prélèvement attendu, engagements et échéances. Les propriétaires, liaisons et fortifications achevées sont publics.

Vous ne consultez pas directement les contingents, réserves, ordres ou projets secrets des autres. La combativité n’est jamais affichée comme un nombre dans l’interface joueur, même pour soi ; l’administration et les tests peuvent naturellement la connaître.

Le scribe décrit les observations : « leurs hommes paraissaient lourdement équipés », « nous avons rencontré quelques dizaines de défenseurs ». Il ne déduit pas tout le contingent d’une cité à partir d’un raid sur ses villages. Les observations portent une date ; un ancien rapport ne se transforme pas en renseignement actualisé.

| Dossier du bureau | Ce qu’on y trouve |
|---|---|
| Correspondance | Alertes, résultats, retours, bilan annuel |
| Domaine | Cités, réserves locales, carte de voisinage, hommes, travaux |
| Décrets | Actions disponibles, formulaire, ordres confirmés, annulation avant clôture en V1 |

Le bureau garde un résumé bref accessible : mois, prochaine clôture, réserves libres/engagées, hommes disponibles, prochaine récolte. La fiction donne la forme ; les informations essentielles ne sont pas cachées dans plusieurs lettres.

Un mois sans événement n’exige pas de courrier. Les batailles, retours, refus, pertes de cité et chantiers terminés sont regroupés. Les bilans annuels récapitulent population, impôts et évolution du règne. Les illustrations peuvent être réutilisées ; aucun LLM ni image unique n’est nécessaire pour calculer un mois.

## 12. Expansion, risque et équilibre

### Empêcher une capture au premier tour

Le concepteur souhaite qu’une capture au premier tour soit impossible ou suicidaire. Pour V0, retenir l’impossibilité économique est plus robuste qu’espérer qu’une attaque soit toujours militairement désastreuse.

**Réglage proposé :** 600 000 Mesures par cité, soit 1 800 000 pour trois cités. Avec le minimum proposé de 80 hommes et le tarif actuel, une capture coûte au moins 2 340 000 : elle est impossible au départ. La récolte annuelle théorique reste de 3 600 000 pour le domaine initial.

Stock initial, prix fixe, prix par homme et minimum d’hommes restent paramétrables avant partie. Le scénario standard vérifie que le total initial est strictement inférieur au prix minimal de capture. Un scénario expérimental peut choisir d’autres valeurs, mais ne peut alors promettre cette protection.

Cette solution empêche toute tentative de capture, pas seulement la branche de siège V1. Elle laisse possibles raids et dépenses moins coûteuses ; les premiers canaux à 2 400 000 attendent cependant la récolte ou d’autres recettes. Sans ces recettes, la première possibilité de confirmer une capture arrive après le bilan du mois 12. À dix minutes par mois, cela représente environ deux heures : ce rythme de départ doit être testé.

L’« exposition des origines » désigne les cités dont les hommes sont partis : leurs garnisons diminuent et leurs réserves sont entamées par la campagne. Elles peuvent donc devenir plus faciles à prendre. Cela ne signifie pas que leur position est révélée : leurs propriétaires et leurs liens sont déjà publics.

### Effet boule de neige

Le vainqueur reçoit des ressources qui l’aident à gagner encore. Le coût de campagne, les pertes, la dispersion des forces, les murs à réparer et la contre-attaque limitent ce mouvement ; ils ne l’annulent pas.

Dans la réalité, une conquête peut exiger administration, garnisons, ravitaillement et négociations, et rencontrer des résistances. Les contraintes logistiques sont illustrées par le cas romain [S27] ; la résistance aux annexions apparaît aussi dans l’extrait assyrien consulté [S28]. Elles ne sont pas un équilibrage garanti : des empires ont effectivement accumulé des avantages. Yaara abstrait actuellement beaucoup de ces coûts.

**Piste V2 sobre :** une cité conquise traverse une période d’installation, avec prélèvement réduit et participation limitée aux nouvelles expéditions ou secours. Une seule date de fin et un coefficient peuvent suffire pour un premier essai. Une indemnité d’installation ponctuelle peut compléter ce système. Si on ajoute une charge mensuelle, il faut définir ce qui arrive lorsque le joueur ne peut plus la payer ; cela accroît davantage la complexité.

Le coût du siège repousse le remboursement financier, mais ne retarde pas à lui seul le transfert des soldats survivants ou du point territorial. Il faut donc mesurer plusieurs avantages, pas seulement un ratio prix/impôt.

### Le raid « toujours rentable »

La formule « toujours rentable » du précédent dossier était trop catégorique. La question utile est de savoir si une politique de raids devient dominante dans certaines conditions, et non de présumer que chaque raid réussit. Le nouveau coût, le hasard et le butin limité vont dans le bon sens.

Cependant, si une troupe dépasse toute la défense possible dans une situation donnée, elle peut y gagner avec certitude. Si son butin couvre ses frais, ce cas reste rentable. Les nombres doivent démontrer la présence de choix et de mauvaises cibles ; le vocabulaire « risque » ne suffit pas à la garantir.

# Partie II — Paramètres et formules de référence

## 13. Une convention de calcul lisible

Les noms anglais décrivent les quantités. Les lettres isolées de l’ancienne version sont abandonnées. Les effectifs et Mesures sont entiers ; les calculs de ratios utilisent des fractions exactes ou des décimaux contrôlés.

| Nom | Signification | Unité |
|---|---|---|
| `total_population` | Habitants rattachés à une cité, y compris les absents | Personnes |
| `present_fideles` | Fidèles physiquement à leur origine hors affectations temporaires | Personnes |
| `absent_fideles` | Survivants de cette origine encore en expédition | Personnes |
| `present_population` | Habitants rattachés moins les absents | Personnes |
| `monthly_tax_per_resident` | Rendement fiscal effectif par habitant présent | Mesures/personne/mois |
| `pending_annual_tax` | Prélèvement comptabilisé depuis la dernière récolte, non dépensable | Mesures attendues |
| `city_stock` | Réserves publiques effectives de cette cité | Mesures |
| `city_capacity` | Capacité de stockage de la cité | Mesures |
| `reserved_city_stock` | Part déjà promise à des ordres confirmés | Mesures |
| `combativity` | Valeur interne par Fidèle, jamais affichée au joueur | Points de force/personne |
| `attacker_strength` | Force de l’expédition | Points de force |
| `field_defense_strength` | Force locale sans murs plus secours | Points de force |
| `fortified_defense_strength` | Force locale avec murs plus secours | Points de force |

```text
present_population = total_population - absent_fideles
existing_fideles = present_fideles + absent_fideles
available_fideles = present_fideles - reserved_fideles
available_city_stock = city_stock - reserved_city_stock
realm_available_stock = sum(available_city_stock for each owned city)
```

Ne pas soustraire les réservations d’hommes de la population présente : un homme réservé n’est pas encore parti.

## 14. Rendement, calendrier fiscal et renouvellement

### 14.1 Le 100 est désormais une valeur, pas un pourcentage

```text
monthly_tax = present_population * monthly_tax_per_resident
```

Il n’y a **pas de division par 100** dans cette formule. Mille habitants à 100 rapportent 100 000 par mois. À population/rendement constants, le prélèvement annuel vaut douze fois cette somme.

La division par 100 reste légitime si un autre paramètre est exprimé en pourcentage, par exemple un taux de morts saisi comme « 8 ». On peut aussi saisir directement `0.08`. Le problème n’est pas d’interdire `/100` partout ; il faut distinguer montant, indice et pourcentage.

Les rendements deviennent `100, 200, 300`, contre l’ancienne convention d’indice `100, 125, 160`. Le changement d’échelle multiplie par cent les montants ; les nouvelles améliorations augmentent **en plus** le gain relatif. Les coûts d’irrigation sont donc recalibrés, pas seulement convertis.

### 14.2 Comptabiliser le mois écoulé

Au tick 1, comptabiliser le mois entre 0 et 1 à partir des habitants restés présents pendant cet intervalle. Le départ d’une mission au tick 1 affecte les périodes comptabilisées aux ticks 2 et 3 ; son retour à la fin du tick 3 lui permet de produire de nouveau pour la période suivante.

```text
pending_annual_tax += present_population * monthly_tax_per_resident
```

Cette opération intervient avant les nouveaux départs, nouveaux achèvements et combats du tick. Elle utilise l’état résultant du tick précédent. Un canal achevé au tick 7 agit sur le mois économique comptabilisé au tick 8, pas rétroactivement sur les six premiers mois.

Au tick annuel, après la comptabilisation de la dernière période :

```text
harvest_added = min(pending_annual_tax, city_capacity - city_stock)
harvest_overflow = pending_annual_tax - harvest_added
city_stock += harvest_added
pending_annual_tax = 0
```

Les crédits attendus suivent la cité lors d’une capture et sont perçus par son propriétaire au versement. Le concepteur accepte le principe qu’une conquête transfère la prochaine récolte ; ce calendrier n’est pas considéré comme un défaut à corriger par défaut. La différence est surtout la liquidité : capturer juste avant le versement permet de dépenser plus tôt. Cela peut financer une nouvelle opération ou précéder une reconquête ; à territoire conservé, production égale et sans débordement, le décalage ne crée pas une récolte supplémentaire. Cette règle conserve donc un enjeu de conquête avant récolte. La comptabilité mensuelle corrige l’effet d’une absence ou d’un chantier sur toute l’année ; elle ne partage pas automatiquement les impôts entre anciens propriétaires.

Ensuite, au bilan annuel, appliquer croissance V1 et renouvellement pour les périodes suivantes. Cette croissance ne revalorise pas les prélèvements déjà comptabilisés.

```text
population_growth = floor(total_population * annual_growth_rate)
total_population += population_growth
fidele_ceiling = floor(total_population * mobilizable_population_fraction)
new_fideles = max(0, min(
    fidele_ceiling - existing_fideles,
    floor(total_population * annual_renewal_fraction)
))
present_fideles += new_fideles
```

Les nouveaux mobilisables sont des habitants déjà comptés. Ne pas détruire un contingent existant si son plafond devient inférieur à lui : arrêter seulement son renouvellement.

### 14.3 Financer depuis les stocks locaux

La confirmation répartit le coût au prorata des réserves libres de chaque cité possédée. Exemple : A a 600 000 libres, B 300 000 et C 100 000. Un ordre de 200 000 réserve respectivement 120 000, 60 000 et 20 000.

Avant toute réservation, vérifier que la somme libre couvre le prix entier. Avec 50 en A, 40 en B et 0 en C, un projet de 100 est refusé : total 90, manque 10. Aucun acompte, crédit ou réservation partielle. Avec 50, 40 et 10, le même projet utilise exactement ces montants.

Ce plan de financement est conservé avec l’ordre. À son départ, les montants réservés sont débités des mêmes cités. À son annulation, ils sont simplement libérés, sans déplacer ni créer de stock.

Les arrondis utilisent les plus forts restes : attribuer les parties entières, puis les Mesures restantes aux plus grandes fractions. Ne dépasser ni le coût total ni le libre local. Un lot de chantiers est traité comme un ensemble atomique avec plans distincts dans un ordre déterministe.

Tous les ordres confirmés pour le tick partent avant ses combats. Un pillage ne peut donc pas voler un stock encore réservé à un départ qui serait prévu plus tard dans le même tick. Aucun ordre ne réserve plusieurs mois à l’avance dans ce socle.

## 15. Les secours en formules et exemples

Au début des combats, figer les cités du même propriétaire reliées entre elles, leurs présents après départs et leurs combativités internes. Ne considérer que les captures qui doivent réellement se résoudre et sont hostiles à cet instant.

Pour chaque cité :

```text
relief_budget = floor(present_fideles * relief_fraction)
```

Répartir ce budget entre les captures visant une autre cité de sa zone. Le poids d’une attaque est sa force interne. Puis limiter le total reçu par chaque expédition :

```text
relief_limit = floor(
    attacker_strength * relief_threat_multiplier / defender_combativity
)
```

Si les contributions proposées dépassent ce plafond, les réduire proportionnellement. Les hommes non retenus restent à domicile ; pas de nouvelle redistribution en boucle.

### Comprendre les plus forts restes

Une cité partage vingt hommes entre des attaques visant deux cités différentes, l’une deux fois plus forte que l’autre : les parts théoriques sont 13,333 et 6,667. On donne d’abord treize et six, soit dix-neuf. Il reste un homme ; la plus grande fraction est 0,667, donc la seconde attaque reçoit le dernier. Résultat : treize et sept, total vingt.

Pour départager des fractions égales, utiliser un ordre tiré pour ce tick et conservé. La priorité ne dépend pas de la vitesse du clic et ne crée pas de préférence éternelle pour la première cité créée.

### Une allocation est une affectation unique

Elle conserve la cité d’origine, le propriétaire soutenu, l’expédition défendue et le nombre d’hommes. Les pertes sont imputées à l’origine. Si la cible a changé de propriétaire, l’allocation ne devient pas une aide au nouveau maître. Les survivants reviennent après **tous** les combats du tick.

La garnison locale exclut toutes les exportations de secours. Chaque cible ne reçoit qu’une expédition hostile engagée ; les affectations se partagent uniquement entre des cibles différentes. Les survivants locaux restent dans leur cité après son unique combat.

Le plafond empêche une petite attaque d’attirer trop d’aide ; il ne supprime pas les diversions payantes et militairement consistantes. La configuration doit être testée sur plusieurs fronts et sur des confirmations concurrentes demandant une même cité.

## 16. Forces, pertes et branches de capture

```text
attacker_strength = attacking_fideles * attacker_combativity
field_defense_strength = local_defenders * defender_combativity + relief_strength
fortified_defense_strength = (
    local_defenders * defender_combativity * effective_wall_multiplier
    + relief_strength
)
```

Aucune division par 100 n’est nécessaire pour que des Fidèles de combativité 100 produisent des points de force. Tous les camps utilisent la même unité. On pourrait normaliser toutes les forces par un même facteur sans changer le résultat ; ce serait uniquement une convention interne.

### V0 : succès d’abord, pertes ensuite

| Condition, examinée dans cet ordre | Issue | Morts attaquants / défenseurs engagés |
|---|---|---:|
| Défense nulle et attaque non nulle | Prise sans défense | 0 % / 0 % |
| Force attaquante > 1,5 × défense fortifiée | Reddition rapide | 1 % / 2 % |
| Force attaquante > défense fortifiée | Assaut victorieux | 8 % / 12 % |
| Force attaquante < moitié de la défense de campagne | Échec très défavorable | 25 % / 2 % |
| Tous les autres cas | Échec ordinaire | 12 % / 3 % |

Ainsi, une attaque inférieure à la moitié de la défense de campagne est bien traitée, qu’on répète ou non la condition « inférieure à la défense fortifiée ». Une égalité à la moitié reste dans la défaite ordinaire. Une égalité à la défense fortifiée échoue.

### V1 : insertion du siège

Conserver les trois premières lignes. Si l’assaillant dépasse la campagne sans dépasser les murs, appliquer le test de réserves. Sinon, appliquer les deux lignes d’échec militaire.

```text
siege_food_needed = ceil(
    present_population * monthly_consumption_per_person
    * sheltered_population_fraction * siege_duration_months
)
siege_food_used = min(city_stock, siege_food_needed)
```

Comparer le stock **avant** consommation au besoin. Au moins le besoin : la cité tient, pertes 10 % / 2 %. Stock inférieur : capitulation par pénurie, pertes 4 % / 8 %, et éventuellement 0,2 % de morts parmi les civils de la cible. Débiter uniquement son stock. Transférer ensuite le reliquat local si la cité est prise. Il n’y a plus de recalcul d’une part de trésor global après le siège.

À égalité avec la défense de campagne, l’assaillant n’impose pas le siège. À égalité avec la défense fortifiée, il peut réussir par pénurie en V1, mais pas gagner l’assaut directement. Une attaque nulle est refusée au départ.

### Pertes et murs

Les taux de morts sont des hypothèses de test. Arrondir au plus proche, moitié vers le haut, et borner aux effectifs engagés. Répartir un total entre origines avec les plus forts restes. Le multiplicateur des murs ne crée pas d’hommes : il n’entre pas dans l’effectif sur lequel on compte les morts.

Une mort retire un homme à sa cohorte ou à sa garnison et un habitant à sa véritable origine. Les morts civiles sont limitées aux civils présents de la cible, jamais aux secours ni aux Fidèles déjà comptés parmi les morts militaires.

Les murs deviennent endommagés après un assaut victorieux en V1 ; pas automatiquement après une reddition ou un échec. Coefficient endommagé :

```text
effective_wall_multiplier = 1 + (intact_wall_multiplier - 1) / 2
```

Un renforcement nécessite des murs intacts à son départ. S’ils sont endommagés ensuite, le chantier continue et monte leur niveau à échéance, mais ne répare pas gratuitement l’état endommagé. Une réparation distincte est nécessaire. Aucun niveau ne se construit deux fois simultanément.

## 17. Pillage, butin et observations

Tirer une fraction de rencontre parmi 20 %, 30 % et 40 %, équiprobables. Multiplier les défenseurs locaux disponibles par cette fraction ; arrondir vers le bas, avec au moins un rencontré si la garnison n’est pas vide. Les secours exportés sont absents de ce calcul, les murs n’y interviennent pas.

```text
raid_succeeds = attacker_strength > encountered_defense_strength
accessible_stock = floor(target_city_stock * raid_accessible_fraction)
```

| Issue | Morts attaquants | Morts défenseurs rencontrés |
|---|---:|---:|
| Succès | 2 % | 4 % |
| Échec, attaque au moins moitié de la défense rencontrée | 8 % | 2 % |
| Échec, attaque inférieure à cette moitié | 20 % | 1 % |

Avec zéro défense rencontrée, aucune perte de combat. Un raid réussi sans survivant éventuel ne transporte rien.

```text
# Succès
stolen_stock = min(floor(accessible_stock * 0.60), surviving_raiders * 5000)
destroyed_stock = min(floor(accessible_stock * 0.20), accessible_stock - stolen_stock)

# Échec ordinaire
stolen_stock = 0
destroyed_stock = floor(accessible_stock * 0.05)

# Échec très défavorable
stolen_stock = 0
destroyed_stock = 0
```

Débiter vol et destruction de la cité cible immédiatement ; conserver le butin dans l’expédition jusqu’au retour. Chaque opération recalcule son plafond sur le stock laissé par les précédentes. Protection active si `current_month < raid_protected_until`, avec expiration fixée à `combat_month + 12` après succès. Elle s’applique immédiatement aux autres arrivées du même mois et survit à une capture.

La discrétion par taille reste désactivée en première V0/V1. Si elle est ajoutée, une seule modification de la fraction rencontrée suffit ; pas de second bonus de force comptant la surprise deux fois. L’ancienne suggestion dépendant de la taille devra faire l’objet d’un contrôle de monotonie avant activation.

Les rapports donnent ses propres résultats exacts, mais seulement des fourchettes datées d’effectifs adverses rencontrés et un vocabulaire qualitatif d’équipement. Seuil proposé pour les observations détaillées : dix survivants de la force propre engagée. En dessous, observation vague ; à zéro survivant, aucun inventaire ennemi. Les bandes de nombre sont de vingt hommes. Les seuils de qualificatifs sont internes et ne doivent pas apparaître comme ratios dans le texte joueur.

## 18. Configuration initiale corrigée

**Tous les nombres d’équilibrage sont des hypothèses de jeu**, sauf les unités explicitement choisies par le concepteur. Ils ne sont pas des statistiques historiques. Dans les tables, les nombres de combativité et les multiplicateurs servent au concepteur/MJ, pas aux joueurs.

### Monde et économie

| Paramètre | Valeur |
|---|---:|
| Prétendants / cités | 3 / 9 |
| Carte d’essai | Cycle de neuf cités ; trois possessions consécutives par joueur |
| Habitants / Fidèles initiaux par cité | 1 000 / 100 |
| Stock initial par cité, proposé | 600 000 Mesures |
| Total initial par joueur, simple somme | 1 800 000 |
| Capacité initiale par cité | 2 400 000 |
| Rendement fiscal initial | 100 / habitant présent / mois |
| Consommation théorique | 1 000 / habitant / mois |
| Prochain versement | Mois 12 ; crédit fiscal initial nul |
| Renouvellement annuel | Au plus 1 % de la population, vers un contingent de 10 % |
| Croissance annuelle | V0 : nulle ; V1 : 0,5 % |
| Secours | Au plus 20 % des présents de chaque origine ; plafond de menace ×1 |
| Minimum raid / capture | 20 / 80 hommes, proposition administrable |
| Expédition | Combat au départ+1 ; retour au départ+2 |
| Règne / cadence de départ | 120 mois / dix minutes, ou manuel |
| Réserves exposées au raid | 25 % du stock de la cible |
| Transport du butin | 5 000 Mesures par survivant |
| Protection après raid réussi | 12 mois |
| Siege : durée / fraction abritée | Un mois / 50 % des habitants présents |
| Réduction de rendement d’occupation | Aucune en V0/V1 ; piste V2 |

### Travaux et projets

| Action | Coût supplémentaire | Durée | Effet |
|---|---:|---:|---|
| Aménager les canaux | 2 400 000 | 6 mois | Rendement 100 → 200 |
| Étendre les canaux, V1 | 4 800 000 | 12 mois | Rendement 200 → 300 |
| Agrandir le grenier, V1 | 500 000 | 4 mois | Capacité 2 400 000 → 3 600 000 |
| Ériger des silos, V1 | 1 200 000 | 8 mois | Capacité 3 600 000 → 6 000 000 |
| Enceinte de terre crue | 1 200 000 | 8 mois | Protection interne 1 → 1,6 |
| Grande enceinte, V1 | 9 600 000 | 20 mois | Protection interne 1,6 → 3 |
| Réparer l’enceinte | 240 000 | 3 mois | Restaure l’ouvrage ordinaire |
| Réparer la grande enceinte | 1 920 000 | 6 mois | Restaure le grand ouvrage |
| Organiser l’armement, V1 | `max(1 800 000, 600 × realm_population)` | 8 mois | Combativité interne 100 → 120 |
| Renforcer l’équipement, V1 | `max(4 200 000, 1400 × realm_population)` | 14 mois | Combativité interne 120 → 145 |

Les prix locaux sont fixes pour le scénario de cités de même gabarit. Ceux des projets globaux utilisent la population au devis accepté ; ils sont figés à confirmation. La croissance au bilan ne renchérit pas une commande déjà acceptée. Les corrections de données par le MJ en cours de partie sont hors périmètre ; les paramètres se choisissent avant lancement.

L’avantage « armement bon marché avant expansion » signifie ceci : un projet acheté pour trois cités continue de bénéficier à la quatrième conquise ensuite. Ce n’est pas une erreur technique. Le coût lié à la population et un plancher évitent les achats dérisoires depuis un minuscule domaine, mais un avantage d’anticipation subsiste. Le conserver initialement ; pas d’entretien ou d’achat d’armes individuelles ajouté sans essai.

### Expéditions : nouveau prix d’essai

```text
raid_cost = 20000 + 2500 * attacking_fideles
capture_cost = 900000 + 18000 * attacking_fideles
```

| Effectif | Prix du raid | Prix de la capture |
|---|---:|---:|
| 20 | 70 000 | Sous le minimum de capture |
| 45 | 132 500 | Sous le minimum de capture |
| 80 | 220 000 | 2 340 000 |
| 150 | 395 000 | 3 600 000 |
| 220 | 570 000 | 4 860 000 |

Le raid comprend 2 000 de subsistance exceptionnelle sur deux mois par homme et 500 de logistique/consommables, plus 20 000 de préparation. La capture comprend un forfait beaucoup plus élevé : 2 000 de subsistance, et 16 000 regroupant les autres charges de campagne et d’installation de l’opération. Cette part peut englober transport, entretien, remplacement de matériel, camp, personnels de soutien, animaux de bât et moyens de siège. **Le rapport de 18 à 1 avec une consommation mensuelle est un choix de gameplay, pas un ratio historique démontré.**

La mobilisation ne rachète pas à neuf tout l’armement que le projet global vient de financer. Les frais récurrents représentent les consommables, l’usure et la mise en campagne ; les capacités durables restent dans les projets. La perte de production des absents est déjà comptée dans le revenu fiscal mensuel proposé : elle n’est pas encore facturée sous un second nom.

Des chars et chevaux peuvent appartenir à l’uchronie, mais ils ne sont pas nécessaires pour expliquer que la guerre coûte davantage que les repas des combattants. En Égypte, les attestations discutées par l’UCL et le Met les placent bien après −3000, à la Deuxième Période intermédiaire et au Nouvel Empire [S25–S26]. L’exemple romain fournit des catégories logistiques comparatives, pas un tarif exportable dans Yaara [S27].

## 19. Calculs vérifiables et arbitrages économiques

### 19.1 Revenu et canaux

Mille habitants présents au rendement 100 donnent 100 000 par mois, 1 200 000 par an. Au rendement 200 : 2 400 000 par an. Au rendement 300 : 3 600 000 par an.

Le premier chantier coûte 2 400 000 et ajoute 1 200 000 de revenu annuel à population constante : deux années pleines de revenu supplémentaire après effet. Le second coûte 4 800 000 pour le même supplément : quatre années pleines. Le délai de construction et la date des versements s’ajoutent ; le remboursement en liquidités n’est pas instantané à la date de production théorique.

Canaux démarrés au mois 1, achevés au mois 7 : la première année compte sept mois à 100 et cinq à 200, soit 1 700 000 pour cette cité. Au mois 12, le domaine de trois cités reçoit 4 100 000 avant plafonds locaux, s’il n’a subi ni absence ni pertes. Cet exemple remplace les anciens calculs fondés sur un bonus de 25 %.

### 19.2 Raid de 45 hommes

Cible : cent Fidèles locaux ordinaires, sans secours exportés ; stock local 1 200 000. Les rencontres possibles sont vingt, trente ou quarante. Quarante-cinq attaquants du même niveau gagnent donc dans les trois cas de cette situation précise.

Coût : 132 500. Un mort attaquant après arrondi ; 44 survivants. Stock accessible : 300 000. Vol possible : 180 000, inférieur au transport de 220 000. Destruction : 60 000. **Marge monétaire au retour : 47 500**, avant pertes d’impôt, valeur de l’homme perdu, risque de perdre l’origine et saturation au retour.

Les 45 hommes partis enlèvent au maximum 9 000 de fiscalité sur deux mois au rendement initial si l’effectif restait constant ; après la mort au combat, la perte supplémentaire doit être imputée à la population réelle. La marge est donc plus faible que le seul butin net de coût, sans être nécessairement négative.

Sur une cité qui ne stocke que 300 000, le butin est 45 000 : marge **−87 500**, même en gagnant. Le raid n’est pas rentable partout.

Un raid de trente hommes coûte 95 000. Il ne gagne que contre vingt rencontrés : probabilité d’un tiers dans ce cas. Après succès, 29 survivants peuvent transporter 145 000. Son espérance de butin est environ 48 333 ; sa marge monétaire attendue est donc environ **−46 667**, avant les autres coûts. Il reste possible de rechercher information ou nuisance, mais ce n’est pas une bonne récolte de ressources.

### 19.3 Capture précoce et exposition

Cible sans murs : cent locaux et quarante secours ordinaires. Une attaque de 150 hommes pourrait dépasser cette défense de 140 hommes équivalents, mais coûte 3 600 000. Elle est impossible avec le stock initial proposé de 1 800 000.

Même la capture minimale de 80 hommes coûte 900 000 + 18 000 × 80 = 2 340 000, au-dessus du budget initial. Le refus intervient dès confirmation, sans réservation de cible ni d’hommes.

Après des récoltes ou des gains, une capture devient finançable. Son bénéfice demeure significatif : cité, défenseurs survivants, réserves présentes et prochains impôts. L’impossibilité initiale ne démontre pas l’équilibre des conquêtes ultérieures.

### 19.4 Capture de 220 hommes contre murs

Cent locaux derrière des murs ordinaires et quarante secours donnent une défense de campagne de 140 hommes équivalents et une défense fortifiée de 200. Une attaque de 220 remporte l’assaut ; elle coûte 4 860 000, donc n’est pas finançable avec les seules réserves initiales de 1 800 000.

Pertes d’essai : dix-huit attaquants et dix-sept défenseurs engagés. Les dix-sept défenseurs peuvent se répartir en douze locaux et cinq secours ; les secours morts sont soustraits à leurs origines. Les 88 locaux restants passent au vainqueur, les 202 attaquants reviennent plus tard.

Face à une grande enceinte, la défense fortifiée serait de 340 hommes équivalents, mais celle de campagne resterait 140. En V1, les réserves décident. Pour mille habitants présents, le besoin vaut 500 000. Si la place dispose de 1 200 000, elle consomme 500 000, tient, et conserve 700 000. L’assaillant perd vingt-deux hommes dans cette branche et ses 4 860 000 restent dépensés.

### 19.5 Grande enceinte et stockage local

Le prix de 9 600 000 représente huit années de l’impôt initial d’une cité ou 2,67 années de celui d’un domaine de trois cités. Le total de stockage initial de ce domaine n’est que de 7 200 000 : il faut agrandir au moins un stockage ou posséder davantage de cités pour réunir le prix, même si le financement est mutualisé.

Une seule cité avec silos porte le total à 10 800 000. Cela ne garantit pas que ces places seront remplies assez vite : sans transferts entre greniers, deux cités peuvent être pleines tandis que la troisième accumule encore. Le stock local rend cette distinction réelle.

Scénario local vérifiable, population et rendement constants, sans guerre :

1. Mois 1 : payer l’enceinte ordinaire, 1 200 000, à parts égales. Il reste 200 000 par cité.
2. Mois 10 : commencer un grenier pour 500 000, financement proportionnel ; il s’achève au mois 14.
3. Mois 12 : chaque cité reçoit 1 200 000.
4. Mois 15 : financer les silos pour 1 200 000 ; fin au mois 23. Cette cité peut désormais stocker 6 000 000.
5. Après les récoltes des mois 24 et 36, deux cités plafonnent à 2 400 000, la troisième continue à épargner.
6. Au mois 48, le total disponible est approximativement 9 233 333, encore insuffisant. Au mois 60, il atteint 10 433 333 ; la grande enceinte peut partir au mois 61 et finir au mois 81, en laissant environ 833 333 de réserves.

Les arrondis peuvent déplacer une Mesure selon le départage, sans changer le mois possible. Cet exemple montre un effet important du stockage local : l’ancien calendrier de trésor global ne doit pas être conservé tel quel.

**Charge d’ouvrage illustrative, non historique :** centre de 100×100 mètres, périmètre 400 m ; enceinte initiale 2,5 m de haut et 1 m d’épaisseur ≈1 000 m³ ; grande enceinte 5 m ×2,5 m ≈5 000 m³, ajout ≈4 000 m³. À vingt jours-personnes par m³ ajouté pour la chaîne complète et 16 000 jours supplémentaires, on obtient 96 000 jours-personnes, soit 4 800 mois-personnes de vingt jours. À 2 000 Mesures de coût complet par mois-personne, cela donne 9 600 000 et un équivalent de 240 travailleurs pendant vingt mois.

Cette productivité est une hypothèse haute, pas une mesure archéologique. À huit jours-personnes/m³, avec le même supplément, le coût serait 4 800 000. Le poids exceptionnel de la grande enceinte est donc un choix assumé. L’exemple monumental de Hiérakonpolis [S13] éclaire l’échelle des constructions en terre crue mais ne valide ni une fonction militaire ni cette productivité.

### 19.6 Vivier et décès cumulés

En imposant huit morts militaires par an dans une cité initiale de mille habitants, sans capture :

| Année | Population V0 | Fidèles après renouvellement V0 | Population V1 | Fidèles V1 | Morts cumulées |
|---|---:|---:|---:|---:|---:|
| 0 | 1 000 | 100 | 1 000 | 100 | 0 |
| 1 | 992 | 99 | 996 | 99 | 8 |
| 5 | 960 | 96 | 980 | 98 | 40 |
| 10 | 920 | 92 | 960 | 96 | 80 |

Les valeurs V1 utilisent 0,5 % de croissance après pertes et avant renouvellement. C’est une récurrence de vérification, pas une partie jouée : le nombre de morts y est imposé pour tester les formules. Un contingent presque reconstitué peut cacher des décès cumulés importants.

# Partie III — Construire et exploiter le jeu

## 20. L’architecture expliquée simplement

### 20.1 Domaine Python et application

Le **domaine** calcule les règles du jeu. Par exemple, à partir d’armées, de murs et d’un tirage fourni, il détermine le résultat d’un combat. Il n’a pas besoin de savoir si la demande vient d’une page web ou d’un test, ni comment les données sont enregistrées.

L’**application** organise une opération complète : identifier le joueur, charger la partie, vérifier ses droits, réserver les ressources, appeler les règles, enregistrer et produire la réponse. Ici, « application » désigne une responsabilité dans le code, pas une seconde application à installer.

L’**infrastructure** fournit les moyens concrets : base PostgreSQL, modèles Django, horloge, ordonnanceur. La **présentation** fournit les pages, formulaires et rapports adaptés au destinataire.

| Demande | Domaine | Application et infrastructure |
|---|---|---|
| Confirmer une expédition | Calculer le prix et vérifier les conditions de jeu | Identifier le participant, verrouiller, charger, réserver, enregistrer |
| Résoudre un combat | Calculer défense, issue, pertes, transferts | Charger le mois, fournir les tirages, appliquer et sauvegarder le résultat |
| Consulter le domaine | Définir les informations autorisées | Lire les données, construire la vue, afficher |

Un module de calcul Python ordinaire suffit. Ne pas créer une interface abstraite pour chaque fonction. Un point de substitution est utile quand il permet un test ou isole une dépendance réelle.

### 20.2 « Un contexte principal Simulation »

Les cités, habitants, expéditions, secours et réserves utilisent le même vocabulaire et participent aux mêmes règles : les regrouper dans un ensemble cohérent nommé `simulation`. Les comptes et mots de passe relèvent des fonctions d’authentification de Django ; les pages et rapports relèvent de la présentation.

Ces responsabilités restent dans **un même projet déployé**, avec une base de données. Aucun microservice, appel réseau interne ou système de messages distribué n’est nécessaire. « Contexte » signifie ici une frontière de compréhension et de responsabilité.

### 20.3 Une partie comme frontière de cohérence

Confirmer un ordre touche éventuellement plusieurs cités. Un combat touche une cible, des origines et plusieurs propriétaires. Il faut empêcher deux opérations de modifier ces éléments à partir d’informations contradictoires.

La première règle technique est donc : **toute modification d’une partie prend le même verrou de partie**. Les opérations sur une autre partie restent indépendantes. Cela ne signifie pas charger toutes les données de la partie pour le moindre bouton : charger seulement les éléments nécessaires, sous cette coordination commune.

Un « repository universel par table » serait une couche répétant `create`, `update`, `delete` pour chaque modèle sans protéger une opération de jeu complète. Préférer quelques accès correspondant aux besoins : charger les éléments nécessaires à la confirmation, charger l’état d’un mois, enregistrer une résolution. Les consultations simples peuvent utiliser directement l’ORM Django.

### 20.4 Commandes et consultations

Une **commande** demande un changement : « confirmer cette expédition », « annuler cet ordre », « avancer ce mois ». Elle vérifie droits et conditions et s’exécute dans une transaction.

Une **consultation** demande une vue : « quelles sont mes réserves ? », « que rapporte mon éclaireur ? ». Elle ne doit ni démarrer un combat ni renouveler des Fidèles parce qu’une page est ouverte.

Cette séparation peut tenir dans deux modules. Elle ne demande ni deux bases ni un framework particulier. Les vues comportant plusieurs lectures doivent représenter un même état : instantané de lecture cohérent ou contrôle de version avant/après avec nouvelle lecture si la partie a changé.

### 20.5 Choisir les règles V0 ou V1 au même endroit

Éviter de disséminer des dizaines de `if version == ...` dans les vues et les modèles. À la création de partie, enregistrer une version de règles. Le moteur sélectionne une fois le résolveur correspondant ; les variantes de siège et de démographie sont regroupées dans cette famille.

Commencer par une V0 complète, puis ajouter V1. Garder les anciennes règles tant que des parties les utilisent ; il n’est pas obligatoire de maintenir éternellement toutes les expériences abandonnées. Une modification d’équilibrage ne change pas discrètement les parties déjà ouvertes.

## 21. Données et anticipation du multijoueur à plusieurs parties

### 21.1 Les objets utiles

| Objet | Données et responsabilité |
|---|---|
| `User` | Compte humain ; peut participer à plusieurs parties |
| `Game` | État, mois, date limite, cadence, graine privée, configuration, version des règles et version de l’état |
| `Participant` | Lien compte–partie, domaine politique, statut, équipement interne |
| `City` | Partie, propriétaire, population rattachée, Fidèles présents, stock, capacité, rendement, prélèvement en préparation, murs |
| `CityLink` | Deux cités de la même partie, lien non orienté unique |
| `Order` | Auteur, mois visé, contenu confirmé, prix figé, statut ; pas de brouillon persistant |
| `Reservation` | Hommes, contribution de stock local et emplacement promis à un ordre |
| `TargetEngagement` | Une seule opération militaire active par cible, de la confirmation à la résolution ou libération |
| `Work` | Chantier de cité ou projet de domaine, niveau visé, début, échéance et statut |
| `Expedition` | Mission, cible, commandement, dates et cohortes par origine |
| `ReliefAllocation` | Origine, expédition hostile, commandement figé, engagés et pertes pour ce mois |
| `TickExecution` | Mois résolu une seule fois, version, tirages et trace utile |
| `Report` | Informations explicitement autorisées pour un destinataire |
| `GameResult` | Résultat final immuable, participants, rangs et version des règles |

Le stock du domaine est une somme calculée, pas une seconde quantité à maintenir. Les hommes partis ne restent pas disponibles dans la garnison. L’appartenance politique actuelle de leur origine et le commandement de la mission sont deux informations distinctes.

### 21.2 Que signifiaient `low` et `high` ?

Il s’agissait seulement de ranger les identifiants d’un lien non orienté. Le lien entre les cités 3 et 8 est toujours enregistré comme `(3, 8)`, jamais aussi comme `(8, 3)`. Cela évite les doublons. Aucune altitude ni force militaire n’est indiquée.

Utiliser des noms explicites `first_city_id` et `second_city_id`, avec `first_city_id < second_city_id`, une contrainte d’unicité et une vérification qu’elles appartiennent à la même partie. Les identifiants sont techniques et ne donnent aucune priorité en combat.

### 21.3 Ce qu’il vaut la peine d’anticiper maintenant

Toutes les commandes et consultations sont limitées à une partie et à son participant autorisé. Un joueur de la partie A ne peut jamais accéder à une cité de B en devinant son identifiant. Les contraintes couvrent notamment l’unicité compte–partie, l’unicité mois–partie résolu et les liens internes à une partie.

Conserver la version des règles et les résultats finaux suffit à préparer un classement global. Ne pas inventer dès maintenant un système Elo : un jeu multijoueur avec alliances et tailles de parties variables demande un choix spécifique de classement et des protections contre les parties arrangées. Les parties solo, administrées librement et de test doivent pouvoir être exclues du classement. Prévoir ce statut dès la création ; définir l’algorithme compétitif en V2.

## 22. Verrous, réservations et confirmations simultanées

### 22.1 Trois notions différentes

- **Réservation de jeu :** des ressources sont promises à un ordre pendant plusieurs minutes, jusqu’au départ ou à l’annulation.
- **Emplacement réservé :** un chantier ou projet à venir occupe déjà la place autorisée, même si ses travaux n’ont pas commencé.
- **Verrou de base de données :** une opération qui écrit attend quelques instants qu’une autre opération ait terminé. Le verrou disparaît à la fin de la transaction ; on ne le garde pas pendant les mois d’un chantier.

Exemple : deux confirmations veulent dépenser chacune 700 sur les mêmes 1 000 Mesures libres. Sans coordination, chacune pourrait lire 1 000 et accepter. Avec le verrou, la première réserve 700 ; la seconde attend, relit 300, puis refuse. Une réservation est donc une règle persistante ; le verrou rend sa création fiable.

### 22.2 Niveaux concurrents et places

Deux onglets peuvent demander le même premier canal avant que le premier ordre ait démarré. Réserver seulement le prix ne suffit pas : il faut aussi réserver la place et le niveau visé. Un second ordre contradictoire est refusé immédiatement.

Le socle conserve un chantier de cité à la fois et un projet de domaine à la fois. Un projet d’armement n’occupe pas le chantier d’une cité. Le niveau suivant ne peut pas être confirmé en supposant qu’un ordre encore annulable ou un ouvrage inachevé a déjà produit son effet.

Les contributions à une même expédition sont normalisées avant calcul : si deux entrées donnent 30 et 20 hommes de la même origine pour la même mission, elles deviennent une cohorte de 50. Le prix fixe se paie une fois pour cette expédition. Deux expéditions réellement distinctes conservent deux prix fixes.

### 22.3 Transaction et date limite

Une transaction enregistre l’opération complète ou aucune de ses modifications. Avec Django/PostgreSQL, le service prend la ligne `Game` avec `select_for_update` dans une transaction atomique [S4–S6], puis relit l’état et la date limite.

Contrôler la date **après** avoir obtenu le verrou. Un clic envoyé avant la limite mais traité après n’est pas promis au mois clos. Afficher clairement le mois d’exécution accepté ; ne pas déplacer silencieusement un ordre vers un autre mois.

Le même protocole vaut pour confirmation, annulation V1 et tick. Les interventions correctives du MJ ne font pas partie du socle.

La confirmation réserve la cible, les fonds et les hommes dans une même transaction, après vérification de toutes les conditions. Une contrainte d’unicité garantit un seul engagement actif par partie et cité cible, tous types militaires confondus. Le verrou de partie sérialise les demandes ; la seconde relit la réservation créée par la première. Un ancien onglet n’est jamais une autorisation. Un identifiant de requête évite qu’un double clic crée deux ordres et permet de renvoyer le résultat du premier. Une demande refusée ne conserve aucune réservation. L’engagement actif est libéré atomiquement à l’annulation V1, à l’invalidation ou à la résolution ; aucun minuteur séparé ne le supprime prématurément.

### 22.4 Confirmation et annulation selon la version

Aucun brouillon persistant dans le socle. V0 : récapitulatif puis confirmation définitive. V1 : ajout de l’annulation avant clôture, qui libère toutes les réservations, y compris la cible. Modifier un ordre implique l’annuler et le recréer, avec une nouvelle priorité de confirmation. Après départ, ni rappel ni remboursement.

## 23. Résoudre un mois, reprendre après une panne

### 23.1 Une seule opération mensuelle

Sous verrou de partie :

1. Vérifier que ce mois est dû, que la partie est active et que le couple partie–mois n’a pas déjà été exécuté.
2. Clore ses commandes et figer leurs entrées.
3. Comptabiliser le mois économique écoulé ; s’il est annuel, verser le prélèvement local, traiter le surplus, puis croissance et renouvellement selon la version.
4. Revalider les ordres dans leur ordre stable ; invalider et libérer ceux dont une condition n’est plus satisfaite. Débiter les contributions réservées et faire partir les hommes pour les ordres exécutés.
5. Terminer les travaux dus. Les effets économiques concernent le prochain intervalle de production.
6. Construire les composantes militaires, attribuer et plafonner les secours une fois ; conserver leurs commandements.
7. Tirer l’ordre des combats puis les résoudre successivement, avec l’état local modifié par les combats précédents. Si la cible appartient désormais au commandement de l’expédition, ne pas combattre ses propres sujets : la mission rentre selon son calendrier, sans remboursement des frais engagés.
8. Faire rentrer les secours, puis les missions dues ; appliquer les règles de retour en cas de perte d’origine et déposer le butin selon les plafonds locaux.
9. Vérifier réservations et invariants, éliminations et victoire. Enregistrer rapports, résultat et trace du mois ; avancer calendrier et version de l’état.
10. Valider la transaction. Les notifications externes éventuelles ne partent qu’après cette validation.

Un ordre invalidé ne retourne pas en brouillon. Son motif est affiché. Une cité perdue ne laisse pas au joueur précédent une réservation sur les réserves du nouveau maître.

### 23.2 Reprise de tick

Une reprise signifie **réessayer le traitement d’un mois après un incident technique**, pas donner un second tour au joueur.

- Panne avant validation de transaction : les changements sont annulés ; on peut réessayer le même mois.
- Panne après validation mais avant réception de la réponse : le mois est déjà enregistré ; le nouvel appel le constate et ne repaie ni récolte ni expédition.
- Aucun état « moitié des combats terminés, moitié oubliés » n’est rendu officiel.

L’unicité partie–mois et la transaction sont complémentaires. Le verrou évite deux résolutions concurrentes ; l’enregistrement de l’exécution empêche de refaire un mois déjà achevé.

### 23.3 Graine de partie

La graine est une valeur initiale permettant de produire des tirages pseudo-aléatoires reproductibles. À état, version de code, ordre des opérations et graine identiques, le calcul donne les mêmes tirages. C’est utile pour reproduire un bug ou comparer deux stratégies.

Elle ne suffit pas à reconstituer une partie sans ses entrées et son code. Conserver aussi les commandes, versions et tirages significatifs. Garder la graine privée en compétition pour éviter que les joueurs prédisent les futurs tirages.

Dériver les tirages du mois et de leur usage de manière stable évite qu’une reprise technique change l’initiative. Les égalités d’arrondi utilisent aussi un départage enregistré. Il n’est pas nécessaire de transformer tout le stockage en journal d’événements pour obtenir cette reproductibilité.

### 23.4 Décisions pendant une même fenêtre, combats entre cibles différentes

Les décisions se prennent pendant la même fenêtre, mais l’accès à une cible est attribué au premier ordre confirmé. La simultanéité des décisions n’est donc plus parfaite : cette priorité de confirmation est assumée et visible dans la règle.

Les combats contre des cités différentes restent résolus dans un ordre tiré après clôture. L’origine de secours peut être conquise avant leur intervention ailleurs ; leur commandement reste figé jusqu’au retour. On conserve ce cas entre fronts distincts, mais on supprime les reprises successives d’une même cité dans le même mois.

## 24. Administration, information et sécurité des règles

### 24.1 Interventions MJ reportées

Aucun outil de correction de population, de stock, d’armée ou de combat en cours de partie n’est à développer pour V0/V1. Le choix des paramètres avant lancement, le traitement manuel des mois en test/solo et la pause d’exploitation restent distincts d’une correction du monde. Les scénarios compétitifs futurs pourront exclure les parties de test sans prévoir maintenant un workflow d’intervention. Une restauration technique après incident n’est pas une action de jeu.

### 24.2 Statistiques secrètes et projection par destinataire

« Statistique secrète » signifie **information conservée par le moteur mais non autorisée dans la vue du joueur concerné** : réserves adverses exactes, ordres ennemis, effectifs cachés, tirages futurs. La combativité numérique reste interne même dans la vue du propriétaire : présenter le niveau et une description qualitative.

Une projection par destinataire transforme un même événement en plusieurs récits autorisés. Exemple : le défenseur connaît ses propres pertes ; un assaillant ayant des survivants reçoit une estimation de l’ennemi ; un tiers n’apprend que le changement de souverain si cette nouvelle est publique.

Ne jamais envoyer toutes les valeurs au navigateur en les masquant seulement visuellement. Le serveur sélectionne les champs avant la réponse. Les archives ne doivent pas révéler, après un changement de propriétaire, des informations auxquelles le lecteur n’avait pas droit, sauf règle explicite de découverte d’archives.

Exemple de texte autorisé : « Les défenseurs étaient lourdement équipés. Nos hommes ont été repoussés. » Aucun « combativité 145 » ni équivalent numérique caché dans une infobulle.

## 25. Cadence, déploiement et exploitation

Le moteur reçoit un mois à résoudre ; il ne mesure pas lui-même dix minutes en dormant dans une page web. Le calendrier convertit les dates réelles en mois dus. Le bouton manuel et l’ordonnanceur appellent le même service.

Configuration de départ : projet Django, PostgreSQL, service web et commande de traitement des parties dues. Un ordonnanceur compatible avec cinq ou dix minutes suffit pour les premiers essais ; Railway documente une cadence minimale de cinq minutes et une ponctualité non garantie [S7–S8]. Un worker léger reste possible si l’expérience demande un suivi plus fin, sans changer les règles.

Les échéances proviennent du calendrier enregistré, pas de l’heure à laquelle un traitement lent se termine. Ne jamais lancer séparément « récolte annuelle » et « combat mensuel » : le bilan annuel est une phase du même tick.

**Retard court :** traiter les mois dus dans l’ordre, un par un, avec leur identifiant. **Panne longue en multijoueur :** ne pas avaler automatiquement des dizaines de mois sans fenêtre de décision. Proposition d’exploitation : après plus d’un intervalle complet de retard, suspendre et reprendre avec une nouvelle échéance annoncée. Les tests solo peuvent explicitement demander plusieurs mois d’affilée.

Une pause décale les échéances futures et conserve la durée restante ; elle ne résout pas un mois gratuitement. Une trêve se définit pour toute la partie, dans un calendrier unique. Dix minutes × douze mois = deux heures par année, vingt heures de temps actif pour dix années.

Choix techniques conservés : Python 3.13, Django 5.2 LTS avec correctifs de sécurité à jour, PostgreSQL 17 [S1–S6]. Vérifier les versions disponibles lors de l’installation. Avant une mise en ligne : migrations sur copie de données, configuration de sécurité, test de restauration, secrets hors dépôt et vérification de la commande de tick [S9–S10]. Les coûts d’hébergement sont à vérifier sur le projet choisi, sans montant supposé.

## 26. Tests : stubs, exemples et vérifications utiles

### 26.1 La correction sur le stub est fondée

Le `StubUtilisateurFetcher` fourni par le concepteur est bien un **stub** : il renvoie une liste figée. Il n’implémente ni stockage ni comportement de recherche. Le test de `RapportUtilisateurs.compter_actifs()` vérifie que le service compte les deux entrées actives.

Un fake serait, par exemple, un petit stockage en mémoire implémentant ajout et recherche. Il n’est pas nécessaire ici. La recommandation précédente ne devait pas substituer un fake à cette demande.

Pour Yaara, un stub peut fournir un état de partie fixé ou un tirage prévu. Les fonctions de combat peuvent aussi recevoir directement leurs entrées, sans double de test. Utiliser un espion seulement si l’on veut vérifier un appel ou une écriture. Ne pas fabriquer une seconde base de données pour éviter de tester PostgreSQL.

### 26.2 Les tests qui protègent vraiment le jeu

| Risque | Vérification utile |
|---|---|
| Double dépense | Deux connexions réelles confirment sur les mêmes réserves ; une seule combinaison finançable est acceptée |
| Double chantier | Deux confirmations simultanées ne réservent pas le même emplacement |
| Deux ticks | Deux appels ne produisent qu’une récolte et qu’une résolution |
| Clôture | Une confirmation ayant attendu le verrou vérifie à nouveau l’échéance |
| Secours dupliqués | Chaque homme affecté intervient dans une seule bataille et manque bien à son origine |
| Cible exclusive | Deux confirmations concurrentes, y compris raid contre capture et onglet périmé : un seul ordre ; refus sans frais ; libération correcte |
| Combats sur plusieurs fronts | Capturer une origine de secours pendant son intervention ailleurs ; vérifier commandements et retours |
| Capture initiale impossible | Vérifier budget initial strictement inférieur au coût minimal de capture dans le scénario standard |
| Combats limites | Égalités à campagne, moitié de campagne, murs et 1,5 fois murs |
| Stocks locaux | Financement, capture, siège, réserve d’ordre et débordement ne créent ni double stock ni négatif |
| Fiscalité proposée | Absence courte, chantier achevé en cours d’année et capture avant récolte |
| Information | Aucun destinataire ne reçoit les champs interdits, même dans le JSON |
| Plusieurs parties | Un identifiant d’une autre partie est rejeté et son tick reste indépendant |
| Panne | Annulation complète avant commit ; appel répété sans effet après commit |

Les tests de verrouillage utilisent des transactions et connexions effectives, avec les précautions Django `TransactionTestCase` [S5]. Un stub ne démontre pas qu’un verrou PostgreSQL fonctionne.

### 26.3 Invariants

Les effectifs engagés, présents et morts se réconcilient par origine ; un Fidèle est compté une fois dans la population rattachée. Les transferts politiques ne créent pas de personnes. Les seules variations démographiques viennent des morts et de la croissance autorisée.

Les réservations ne sont pas des dépenses : elles réduisent la disponibilité, pas le stock total. Les transferts et le butin déplacent des Mesures ; les prix, destructions, vivres de siège et débordements les retirent. L’impôt annuel les ajoute. Le prélèvement en préparation n’est pas encore un stock : son accumulation mensuelle ne crée pas simultanément des Mesures dépensables.

### 26.4 Ce que les calculs de ce dossier prouvent

Les exemples de la partie II peuvent vérifier l’arithmétique et révéler certains avantages. Ils ne prouvent pas l’équilibre d’un règne. Il faut ensuite comparer, sur plusieurs graines et positions, investissement, raids, capture précoce, défense et stratégies mixtes.

Mesurer notamment : probabilité de victoire après première capture, délai de récupération économique, exposition des origines, priorité de confirmation et raids bloquant une capture, gain net des raids selon richesse observée, durée des blocages et fréquence des ordres invalidés. Comparer aussi la récolte instantanée et le cumul mensuel si cet arbitrage reste ouvert.

## 27. Développer avec l’IA sans multiplier les dispositifs

L’environnement actuel sait exécuter les tests, migrations et déboguer : c’est une capacité confirmée par le concepteur. Il n’y a aucune raison d’imposer un changement d’outil ou une extension IDE pour commencer.

Quelques documents Markdown et une méthode habituelle suffisent :

- `rules.md` : règles humaines et exemples, source de vérité du jeu ;
- `architecture.md` : frontières, transactions, modèles et conventions utiles ;
- `AGENTS.md` : commandes du projet, règles de travail stables et liens vers ces documents ;
- `decisions.md` : quelques arbitrages datés, seulement quand leur raison mérite d’être conservée.

Ce dossier peut rester unique pendant la conception, puis être découpé lorsque le dépôt existe. Éviter de recopier les mêmes règles dans tous les fichiers. Ni armée d’agents, ni catalogue de skills ne constitue un prérequis. Les sources sur ces capacités établissent leur disponibilité, pas leur nécessité [S14–S23].

### Les prompts restent importants

Une bonne demande contient le résultat attendu, les règles concernées, les limites du changement et quelques cas décisifs. Les adjectifs de rôle ne remplacent pas ces informations.

Exemple :

> Implémente la confirmation d’une expédition selon les règles de réservation. Normalise les contributions avant de calculer le prix. Réserve hommes, fonds locaux et emplacement dans la même transaction de partie. Vérifie deux confirmations concurrentes et un ordre arrivé après clôture. N’ajoute ni brouillon persistant ni nouvelle règle de combat. Exécute les tests utiles et indique toute ambiguïté de spécification.

Procéder par comportements complets : lecture de la règle, clarification d’une ambiguïté réelle, exemple ou test significatif, implémentation, tests exécutés, revue du changement. Une conversation peut porter sur plusieurs étapes ; une modification livrable doit rester cohérente et vérifiable.

### Ordre de réalisation

1. Partie, participants, cités, liens et isolation des droits.
2. Économie et calendrier manuel ; choisir explicitement la fiscalité avant de coder les récoltes.
3. Confirmation définitive V0, réservation exclusive des cibles, réservations de ressources et concurrence ; annulation avant clôture ajoutée en V1.
4. Chantiers, projets et échéances.
5. Expéditions, raid et retour.
6. Secours, capture V0 et transferts successifs.
7. Rapports autorisés et interface jouable.
8. Parties automatiques à dix minutes, sauvegarde/restauration et première partie complète.
9. Comparaisons d’équilibre, puis siège V1 si retenu.

Ne pas commencer le classement global, les révoltes ou les convois pour préparer abstraitement V2. En revanche, ne pas reporter l’isolation des parties, les versions de règles et la conservation des résultats finaux.

# Annexes

## A. Les arbitrages restant ouverts

| Sujet | Recommandation de cette révision | Ce qu’il reste à décider |
|---|---|---|
| Stock | Local par cité confirmé ; financement automatique proposé | Accepter le financement à travers un domaine coupé et les débordements locaux |
| Confirmation | V0 définitive ; V1 annulable avant clôture ; aucun draft | Décision retenue |
| Cible militaire | Une seule attaque engagée, priorité au premier ordre confirmé | Surveiller les raids de blocage ; pas de nouvelle mécanique préventive pour V0 |
| Départ | Capture initiale impossible ; proposition de 600 000 par cité | Tester le rythme jusqu’à la première récolte |
| Fiscalité | Cumul des habitants présents chaque mois, versement annuel | Accepter ce changement explicite ou conserver l’instantané annuel |
| Récolte d’une cité capturée | Le prélèvement en préparation suit la cité | Principe conservé ; mesurer le calendrier sans ajouter de compensation |
| Minimum militaire | 20 au raid, 80 à la capture | Ajuster après essais, sans confondre seuil et équilibre |
| Départage | Population rattachée, puis égalité | Valider le critère et sa visibilité |
| Occupation | Pas de système supplémentaire V0/V1 | Tester une installation temporaire en V2 |
| Coûts et mortalité | Configuration chiffrée de la partie II | Calibrer par parties, pas par simple plausibilité historique |

« Conserver l’instantané annoncé » signifiait : garder le calcul annuel initial tant qu’un changement n’est pas accepté, et mesurer son effet de calendrier. Cette révision expose désormais une alternative motivée par les habitants sur place. Elle ne prétend pas que le concepteur a déjà validé une mensualisation.

« Arme améliorée à petit prix puis expansion » devient une convention assumée : une forge et son organisation équipent automatiquement les nouvelles populations du Prétendant. Aucun coût supplémentaire par cité acquise en V0. Le prix du projet reste un paramètre d’équilibrage, sans traiter ce bénéfice futur comme un défaut à corriger d’office.

## B. Sources et limites


Sources consultées le **15 octobre 2026**. Les dates de publication sont indiquées lorsqu’elles sont explicitement disponibles. Une documentation courante peut évoluer ; sa date de consultation n’est pas une date de lancement de fonctionnalité. Les références proviennent notamment des éditeurs, auteurs et institutions concernés ; certaines références historiques sont des synthèses, comme précisé ci-dessous. Ils n’approuvent pas les arbitrages de jeu ou l’architecture particulière proposés ici.

### Technique et déploiement

- **[S1] Django, 2 avril 2025 — [Django 5.2 released](https://www.djangoproject.com/weblog/2025/apr/02/django-52-released/).** Statut LTS et sortie de la branche choisie.
- **[S2] Django, 6 octobre 2026 — [Security releases: 6.1.2, 6.0.9, 5.2.18](https://www.djangoproject.com/weblog/2026/oct/06/security-releases/).** Correctifs publiés avant la date du dossier ; ne remplace pas un suivi des avis ultérieurs.
- **[S3] Django 5.2 — [Installation et compatibilité Python](https://docs.djangoproject.com/en/5.2/faq/install/) ; [bases de données](https://docs.djangoproject.com/en/5.2/ref/databases/).** Pages de référence de la branche, consultées à la date du dossier.
- **[S4] Django 5.2 — [Database transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/).** Atomicité et opérations après commit. La taille de la transaction reste un choix de conception de Yaara.
- **[S5] Django 5.2 — [QuerySet API](https://docs.djangoproject.com/en/5.2/ref/models/querysets/).** `select_for_update`, avertissement sur `TransactionTestCase`, écritures groupées et leurs limites.
- **[S6] PostgreSQL — [Explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html).** Référence courante consultée en version 18 ; les principes de verrous utilisés ici ne nécessitent pas une fonctionnalité spécifique à cette version. La cible proposée reste PostgreSQL 17.
- **[S7] Railway — [Deploy a Django App](https://docs.railway.com/guides/django).** Guide courant, pas garantie d’un prix ou d’un forfait particulier.
- **[S8] Railway — [Cron Jobs](https://docs.railway.com/cron-jobs).** Minimum cinq minutes, UTC, irrégularité possible, nécessité que le processus termine.
- **[S9] Django 5.2 — [Deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).** Configuration de production et sécurité de déploiement.
- **[S10] Railway — [Volume backups](https://docs.railway.com/volumes/backups).** Planification, rétention et restauration ; conditions à vérifier sur le projet effectif.

### Histoire : repères et limites

- **[S11] UCL, page portant copyright 2003 — [Aspects of war in ancient Egypt](https://www.ucl.ac.uk/museums-static/digitalegypt/foreignrelations/war.html).** Difficultés d’interprétation des textes/images et ambiguïtés de certaines architectures. N’établit aucun taux de pertes pour le jeu.
- **[S12] Metropolitan Museum — [Disc-shaped macehead](https://www.metmuseum.org/art/collection/search/547108).** Objet daté d’environ 3850–3500 av. n.è. : appui au vocabulaire d’armement, pas aux bonus de 20 ou 45 %.
- **[S13] Hierakonpolis Expedition — [The ceremonial enclosure of Khasekhemwy](https://www.hierakonpolis-online.org/index.php/explore-the-fort).** Dimensions, matériau, phases de construction et absence de fonction militaire de l’ouvrage présenté. Aucun rendement de main-d’œuvre exploitable directement pour les coûts de Yaara n’a été établi ici.
- **[S24] Swansea University — [Warfare in Western Europe in the Central Middle Ages](https://www.swansea.ac.uk/history/history-study-guides/warfare-in-western-europe-in-the-central-middle-ages/).** Synthèse universitaire sur une autre période, utile pour distinguer raids, sièges et batailles ; ce n’est pas une série de données primaires permettant de calibrer la mortalité en Égypte vers −3000. Les sources médiévales qu’elle discute ne sont pas transposées en coefficients du jeu.

Les sources [S11–S13, S24] ne permettent pas de fournir honnêtement une fréquence de bataille ou une productivité d’ouvrier « réaliste à deux décimales ». Les coûts de la partie II sont donc des hypothèses transparentes de gameplay et de travail, avec une analyse de sensibilité. Il n’a pas été trouvé ici de mesure contextualisée suffisante pour transformer les pourcentages de morts en faits historiques.

### Michaël Azerhad et développement avec l’IA

- **[S14] [WealCome](https://wealcomecompany.com/).** Site professionnel, identité et présentation des formations ; page courante sans date de publication absolue.
- **[S15] Michaël Azerhad, Medium, 25 mars 2018 — [TDD n’est pas ce que tu crois](https://medium.com/wealcomecompany/tdd-nest-pas-ce-que-tu-crois-6b8390cb40c9).** Article directement consulté.
- **[S16] Michaël Azerhad, LinkedIn — [Human TDD vs Claude Code TDD: A Fundamental Shift](https://www.linkedin.com/posts/michael-azerhad_human-tdd-vs-claude-code-tdd-a-fundamental-activity-7414806516337274880-S7pn).** Texte public accessible ; date relative « 9mo », mention de modification. Plus de dix fichiers de skills dans l’exemple, pas un décompte exhaustif d’agents. Date exacte de la version publiée non établie.
- **[S17] Michaël Azerhad, LinkedIn — [Usage de Claude Code en formation](https://fr.linkedin.com/posts/michael-azerhad_micha%C3%ABl-dans-tes-formations-wealcome-activity-7412804546281877504-te-J).** Texte public accessible, date relative et mention de modification. Contenu intégral des fichiers de formation non accessible.
- **[S18] Michaël Azerhad, LinkedIn — [Le défi des tâches non exprimées](https://fr.linkedin.com/posts/michael-azerhad_en-d%C3%A9veloppement-logiciel-le-vrai-d%C3%A9fi-activity-7457125317141360640-oN6A).** Texte public consulté ; utilisé pour son propos explicite sur la compétence nécessaire à la délégation.
- **[S19] OpenAI — [ChatGPT & Codex changelog](https://learn.chatgpt.com/docs/changelog).** Entrées datées citées : 27 août 2025, 19 décembre 2025, 22 janvier 2026 et mars 2026. Les entrées sont utilisées pour établir l’existence des fonctionnalités avant le 15 octobre, sans reprendre les anciens modèles comme recommandations actuelles.
- **[S20] OpenAI — [Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).** Documentation actuelle des instructions de dépôt.
- **[S21] OpenAI — [Build skills](https://learn.chatgpt.com/docs/build-skills).** Structure et sélection/chargement des skills ; aucun quota d’abonnement supposé.
- **[S22] OpenAI — [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents).** Capacités actuelles et rôles spécialisés ; leur usage reste optionnel dans cette proposition.
- **[S23] OpenAI — [Codex IDE extension](https://learn.chatgpt.com/docs/codex/ide).** Fonctions de contexte éditeur, revue des modifications et délégation. Disponibilité exacte à vérifier dans le compte utilisé.

La méthode recommandée, les niveaux de prix du jeu, les choix de verrouillage et la sélection minimale de fichiers restent **les recommandations de ce dossier**. Ils ne sont pas présentés comme des prescriptions de Michaël Azerhad, OpenAI, Django, Railway ou des historiens cités.




### Compléments historiques de cette révision

- **[S25] Metropolitan Museum — [Tablet with Chariot Scene](https://www.metmuseum.org/art/collection/search/548483).** Notice datée de 1396–1386 av. n.è. ; l’introduction égyptienne des chevaux et chars est située autour de 1600 av. n.è. Cela justifie un emprunt assumé à une époque postérieure, pas leur présence en Égypte vers −3000.
- **[S26] UCL — [Horses in ancient Egypt](https://www.ucl.ac.uk/museums-static/digitalegypt/foodproduction/horse.html).** Page portant copyright 2003 : introduction à la Deuxième Période intermédiaire et usage des chars.
- **[S27] Adrian Goldsworthy, 1er novembre 1999 — [Compte rendu de Jonathan Roth, The Logistics of the Roman Army at War](https://bmcr.brynmawr.edu/1999/1999.11.01/).** Compte rendu universitaire, non série de prix antiques : ravitaillement des hommes et animaux, transports et contraintes des armées. Appuie la diversité des coûts, pas le coefficient monétaire d’une expédition Yaara.
- **[S28] Karen Radner, projet universitaire ORACC — [The Medes, purveyors of fine horses](https://oracc2.museum.upenn.edu/saao/aebp/Essentials/Countries/TheMedes/).** Résultat indexé consulté ; page complète indisponible lors de la vérification. L’extrait évoque la résistance dans les provinces nouvellement annexées et le retour de l’armée. Cette référence limitée ne sert pas à chiffrer une occupation.

Les chars, chevaux, animaux de bât et trains de siège constituent des inspirations logistiques de périodes différentes, annoncées comme telles. Les prix proposés restent des paramètres de jeu ; aucune conversion fiable de ces sources en Mesures n’est revendiquée.
