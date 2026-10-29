# Yaara — Référence de jouabilité

## Présentation du 29 octobre 2026 — Bureau et clôture

Préparée depuis `b369e07`. Sur ordinateur (900px et plus), les préparations
restent à côté de la carte, avec l’en-tête accessible. Le lien de clôture ouvre
un feuillet dédié aux conséquences et au bouton de confirmation existants.
Le Règne garde ses comptes complets. Les panneaux mobiles et les règles
économiques, militaires et calendaires restent inchangés.

## Révision du 29 octobre 2026 — Retours et chantiers lisibles

Préparée depuis `098fda0`, sans attester un déploiement. La correction explicite
du propriétaire s’applique aux retours militaires de l’économie quatre, y compris
les règnes en cours : seul un voisin routier direct et encore ami de la cité
attaquée peut servir de refuge. Une cité amie située à deux routes ne suffit pas.
Sans refuge valable, les survivants rentrent comme Fidèles du maître actuel de
leur cité d’origine, avec le reliquat de sa restriction de départ, sans prolonger
celle-ci. Les convois et les économies antérieures gardent leurs règles.

Les effets des forges expliquent leur rôle en attaque et en défense sans chiffre
de combativité. Les ouvrages achevés gardent leur description. La liste resserre
les illustrations et les espacements, évite le titre répété et place l’action
près du nom ; les prix, durées, motifs de refus et commandes natives restent
accessibles dans les deux langues.

## Présentation du 27 octobre 2026 — Carte illustrée et navigation fluide

Préparée depuis `d9671c8`. Les cités reprennent le style des illustrations de
chantiers, sans meurtrières ni socles circulaires. Leur disposition graphique est
plus organique et les frontières plus irrégulières ; seules les routes de la cité
sélectionnée apparaissent, tandis que les flèches des expéditions restent visibles.
Le réseau enregistré, la portée et les règles de déplacement ne changent pas.
L’en-tête partagé remplace le menu inférieur ; les onglets des panneaux restent
accessibles au-dessus de leur contenu défilant. Le terrain reste décoratif.

## Présentation du 27 octobre 2026 — Feuillets inspirés de la maquette

Préparée depuis `9714b9d`. Le feuillet d’une cité propre réunit stocks, capacités,
équipe et devis locaux ; une cible accessible ouvre directement la préparation.
Les curseurs facultatifs modifient les mêmes effectifs que les champs numériques.
Le courrier dispose d’une fenêtre distincte, avec ses trois classements conservés.
Les couleurs, illustrations et règles actuelles sont conservées : la maquette ne
remplace ni les prix réels, ni le devis, ni le sceau, ni les limites de renseignement.

## Présentation du 26 octobre 2026 — Carte et courrier

Préparée depuis `a62af6e`, sans attester un déploiement Railway. L’entrée ouvre
la carte et ses routes enregistrées. Les travaux locaux conservent les devis,
réservations et clôtures existants ; le traitement multi-cités reste secondaire.
Le courrier distingue affaires à traiter, échéances et chronique. Les trajets
propres sont dessinés ; les alertes adverses restent limitées à la surveillance
acquise. Un prévisionnel de débordement ne représente pas des fonds disponibles.
Aucune règle économique, militaire ou de calendrier n’est modifiée.


## Révision du 26 octobre 2026 — Heure de Paris et fin du règne

Correction préparée depuis `98fe393` de `codex/yaara-deployment`, sans attester
un déploiement Railway. Les échéances visibles des joueurs et de l’organisateur
sont affichées à l’heure de Paris : UTC+1 en hiver, UTC+2 en été, avec changement
automatique. Les instants enregistrés et le calendrier serveur restent en UTC.
Le compte à rebours garde la même échéance réelle, même sans conversion côté
navigateur. Un traitement par cron toutes les cinq minutes peut publier les
nouvelles après l’heure de clôture des ordres.

La règle de fin reste inchangée : un règne de 120 lunes s’achève à la clôture
de la lune 120, y compris à égalité. Le classement compare les cités puis la
population rattachée ; une égalité persistante partage le premier rang.
Les tests PostgreSQL couvrent les deux dernières clôtures à cadence de cinq
minutes, à l’heure ou avec deux minutes de retard, pour les deux calendriers
enregistrés. Ils ne prouvent pas l’état du processus de production.

## Révision du 24 octobre 2026 — Choix des places et notifications

Préparée depuis `b9832f8` de `codex/yaara-deployment`, sans attester un déploiement
Railway. Les nouveaux règnes partagés proposent un lien de recrutement commun :
chaque invité choisit un territoire libre de trois cités et nomme sa maison
(1 à 80 caractères, nom distinct). Le compteur passe de trois places restantes
à zéro. La troisième arrivée déclenche le départ atomiquement, avec une première
lune complète. Les salles déjà créées gardent leur départ explicite par
l’organisateur. Le calendrier, la carte et les règles des sauvegardes ne changent
pas. Le lien commun ne permet jamais de reprendre une place occupée ; chaque
joueur conserve son propre lien privé de retour.

Des notifications facultatives, également accessibles aux invités sans compte,
peuvent annoncer le départ, les captures et les récoltes annuelles. Les raids
sont désactivés par défaut ; leur option produit un résumé au plus une fois par
24 heures réelles. L’adresse doit être confirmée et peut être retirée à tout
moment. Les envois sont désactivés tant que le transport SMTP ou sendmail n’est
pas configuré ; aucun prestataire de notifications n’est ajouté. Seuls les titres
des lettres déjà autorisées au destinataire sont repris, avec retour vers sa
maison. La file d’envoi est enregistrée avec les lettres ; l’envoi intervient
ensuite, hors transaction de jeu. Sources : `multiplayer.py`, `notifications.py`,
tests `test_recruitment.py` et `test_notifications.py`.

## Révision du 24 octobre 2026 — Accès invité et règnes partagés

Implémentation préparée depuis `1754956` de `codex/yaara-deployment`, sans attester
son déploiement Railway. Les règles économiques et militaires restent inchangées.
L’entrée publique ouvre un règne solo privé en calendrier manuel, sans inscription.
Le visiteur peut ensuite conserver ce même règne dans un compte. La présentation
conserve trois destinations, des ressources légendées, un papier chaud et calme,
de petites fresques et des séparateurs discrets. Après le scellement, un lien précis
mène à la clôture ; les téléchargements JSON du livre sont secondaires.

Un organisateur autorisé prépare les règnes partagés à trois maisons humaines,
sur la carte existante de neuf cités. Chaque lien privé ouvre une identité distincte
et permet de revenir à cette maison, sans inscription ni étape de disponibilité
supplémentaire. Dans cette première version, les salles attendaient le départ de
l’organisateur après l’arrivée des trois joueurs ; ce comportement reste celui
des salles anciennes. Les nouvelles salles suivent la révision ci-dessus.
Le lien secret n’authentifie jamais le compte inscrit auquel une maison est liée.
Un organisateur qui joue garde sa session de gestion en rejoignant sa maison.

Les règnes partagés emploient le calendrier serveur, une première fenêtre complète
et des pauses communes gérées par l’organisateur. À dix minutes par lune, 120 lunes
représentent vingt heures de calendrier actif ; les plages de séance sont annoncées
avant l’entrée. Une absence n’ajoute aucun ordre ni remplacement automatique.
Les sauvegardes solo conservent leur calendrier et leurs règles enregistrées.
Un essai solo demeure attaché à son identité d’origine lors d’une visite en partie
partagée ; le même navigateur peut le reprendre sans transfert de propriété.

Les décrets secrets d’une autre maison ne modifient ni la version visible de votre
page ni la validité de votre devis. Une modification propre ou une clôture impose
la relecture nécessaire. Les lettres et le livre personnel restent privés ; le livre
toutes maisons d’un règne partagé exige le droit d’organisation et la fin du règne.
La rotation ou suspension d’un lien invalide son ancien accès et ses sessions de
maison ; une connexion indépendante au compte inscrit lié conserve son accès.
Ces capacités ne démontrent pas l’équilibre des parties humaines.

## Révision du 24 octobre 2026 — Frontières, surveillance et intégration

Implémentation préparée depuis `dbcba62` de `codex/yaara-deployment`. Cette section remplace, pour les nouvelles parties `strategy_version=2`, les descriptions historiques de réservation exclusive et de signalement gratuit ci-dessous. Elle n’atteste pas un déploiement Railway. Les sauvegardes sans marqueur stratégique, ou marquées 1, conservent leurs règles ; l’économie, les prix, les revenus et les dates des raids restent inchangés.

**Après une conquête en N**, les Fidèles locaux hérités assurent la défense, sans participer aux départs offensifs ni aux secours durant N+1, N+2 et N+3. Ils deviennent disponibles en N+4. Les contingents amis revenant de voyage et les nouvelles recrues ne sont pas ajoutés à ce contingent hérité. Les pertes locales réduisent proportionnellement les effectifs libres et restreints ; les morts en voyage ne réduisent pas le contingent local restreint. Une nouvelle conquête réinitialise la période pour les Fidèles alors présents. Les comptes propres affichent l’effectif concerné et sa lune de disponibilité. Aucun malus fiscal ou de classement n’est introduit.

**Surveillance payante :** les ordres ennemis seulement scellés restent secrets. Après les départs et les achèvements de travaux, la surveillance effective I signale la cité menacée et la lune d’arrivée ; II ajoute le type de mission et une bande d’effectifs : moins de 50, 50–99, 100–199, au moins 200. Sans surveillance, aucune alerte anticipée, mais la défense automatique subsiste. Un dommage réduit le niveau effectif pour les nouvelles détections ; il n’efface pas une information déjà apprise. Les lettres restent datées, immuables et réservées au destinataire. Une autre maison conquérant la cité n’hérite pas de ces renseignements.

**Secret des engagements :** carte, formulaires et validation ne révèlent plus les réservations militaires ennemies ni les dates privées de répit de leurs villages. Plusieurs ordres peuvent viser une même cité. Un ordre n’est refusé au scellement ou au départ ni pour une réservation cachée ni pour un répit caché. À l’arrivée, les règles existantes continuent de s’appliquer : villages encore protégés ou objectif devenu amical entraînent retour au calendrier prévu, sans remboursement. Les combats de cité concurrents restent résolus dans l’ordre déterminé par le moteur après clôture ; aucun privilège ne découle de l’heure du sceau.

**Départ frontalier automatique :** chaque expédition rejoint une cité amie directement reliée à sa cible par une route. Tous les contributeurs doivent pouvoir l’atteindre par des routes entièrement amies. Parmi les candidats valides, choisir celui qui fournit le plus d’hommes, puis l’identifiant stable de cité à égalité. Ce choix utilise uniquement géographie, propriétaires publics et contributions propres, jamais les ordres ennemis. Il est revalidé au départ puis figé pour l’expédition ; aucun nouveau champ de choix n’est imposé au joueur. Des contributeurs appartenant à des composantes amies disjointes doivent former des expéditions distinctes.

**Bataille rangée :** les expéditions parties durant la même lune sur une même route en sens opposés se rencontrent avant les combats de cité. Regrouper les contingents d’un même côté pour une seule rencontre par route et par lune de départ, y compris raid/raid, capture/capture et raid/capture. Des départs différents, des routes différentes ou des armées de la même maison ne déclenchent pas cette rencontre. Seuls hommes engagés et équipement figé des origines déterminent la force ; murs, garnisons restées sur place, secours automatiques, protection des récoltes et matériel de siège n’interviennent pas.

Soit E le plus petit effectif engagé et R le rapport entre force équipée supérieure et inférieure. Arrondir les décès au plus proche, demi-entier au-dessus :

| Rapport R | Issue | Pertes du côté supérieur / inférieur | Suite |
| --- | --- | --- | --- |
| R < 1,25 | Rencontre indécise | 6 % E / 6 % E | Les deux côtés rentrent |
| 1,25 ≤ R < 2 | Victoire nette | 2 % E / 12 % E | Le vainqueur poursuit |
| R ≥ 2 | Supériorité écrasante | 0 / 4 % E | Le vainqueur poursuit |

Les pertes sont réparties proportionnellement entre expéditions et contingents. Un petit détachement ne prélève jamais un pourcentage de la grande armée entière. Le vainqueur poursuit son objectif à la lune de combat prévue, N+1, avec ses survivants, même si les pertes l’ont fait passer sous le minimum exigé au départ. Il doit encore affronter les défenses restantes de sa cible. Les perdants rentrent en N+2, sans remboursement, sans renforcer instantanément leur cité pendant la résolution. Les récits donnent les pertes et survivants propres, avec seulement une appréciation qualitative des pertes adverses. Les valeurs numériques de force restent privées.

Exemples : 80 soldats équipés à 145 contre 80 à 100 donnent R=1,45 : 2 morts du côté supérieur, 10 de l’autre ; les 78 premiers poursuivent leur capture et doivent encore franchir les murs. Trois cents soldats ordinaires contre vingt raiders ordinaires donnent zéro perte du côté supérieur et un mort chez les raiders. Deux raids de 40 rencontrant un raid de 80 produisent une seule rencontre indécise avec cinq morts de chaque côté, pas deux prélèvements séparés.

Les seuils et taux sont les premiers paramètres de l’essai humain, pas une démonstration d’équilibrage. La durée des raids reste départ N, combat N+1 et retour N+2. Sources : `simulation/tactics.py`, `engine.py`, `projections.py`, tests `test_frontier_rules.py` et `test_frontier_http.py`.

Révision du 22 octobre 2026 : préparation stratégique, raids, sièges, convois et réserves initiales. Base récupérée : `6bd894e7be47ddf4790c1d56f3f74db821cbc834` de `codex/yaara-deployment`. Décrit l’implémentation de cette révision, sans attester son déploiement Railway. Sources : `simulation/rules.py`, `engine.py`, `projections.py`, `narration.py`, `views.py` et tests `test_strategy_*`.

## Maintien et compatibilité

Synchroniser ce document et `docs/decisions.md` avec chaque changement des règles. Le dossier `design-source.fr.md` conserve l’intention historique. La discussion jointe n’est pas un rejeu des anciennes parties.

Les nouvelles parties utilisent `economy_version=4`, forges locales, carte à douze routes et calendrier ouvrant la lune 1. Les sauvegardes précédentes conservent leurs réserves, tarifs, murs, combats, ordres acceptés et rapports. L’économie 3 conserve notamment les raids saisonniers et murs ×1/2/4/7 ; les économies 1/2 gardent leurs raids sur stocks et versement annuel avant combats. Les marqueurs V0/V1 sont internes, sans sélecteur public. Aucune conversion automatique d’une partie en cours.

## Cadre et ressources

Trois maisons possèdent trois cités chacune ; solo contre deux adversaires actifs ou passifs. Un tour, ou lune, représente **un mois**. Règne standard de 120 lunes, également configurable à 24, 60 ou 240. Calendrier manuel ou automatique cinq/dix minutes, avec départ explicite des parties automatiques. Victoire immédiate avec les neuf cités ; sinon classement au terme par cités puis population de rattachement. Aucun prestige.

Chaque cité commence avec 1 000 habitants dont 100 Fidèles, **900 000 Mesures**, prélèvement nul, capacité 2 400 000. Les anciennes économies commencent toujours à 600 000. L’augmentation laisse financer les rigoles (300 k) et un raid de 30 hommes (35 k) avec 565 k encore en réserve, sans garantir deux mois de ravitaillement. Chaque cité finance ses travaux ; chaque origine finance ses hommes et sa part proportionnelle du forfait, répartie en mesures entières par la méthode des plus grands restes. Les convois permettent un transfert différé, jamais un financement implicite.

Rendement par habitant présent : 100 / 115 / 130 / 200 Mesures par lune. Absents non producteurs. Prélèvement accumulé indisponible avant les clôtures 12, 24, etc. ; surplus sans place perdu. Croissance annuelle de 0,5 %, arrondie au-dessous ; renouvellement des Fidèles parmi les habitants existants plafonné à 1 % de population et à l’écart au contingent cible de 10 %.

Clôture : prélèvement, départs, achèvements, combats, versement annuel éventuel et croissance, retours militaires, arrivées des convois, résultat. Un raid de lune 12 réduit la récolte avant versement. Un convoi arrivant ce mois ne nourrit pas le siège déjà résolu. Préparer ou relire ne réserve rien ; sceller réserve les moyens existants, la clôture les dépense. Annulation avant départ selon les règles de la sauvegarde.

## Travaux et équipes

Une équipe par cité, partagée entre construction et réparation et réservée dès le scellement. Lots multi-cités atomiques. Coûts par passage, effets totaux remplaçant le niveau précédent.

| Famille | Niveau I : prix / lunes | Niveau II | Niveau III | Effet, avec état initial |
| --- | --- | --- | --- | --- |
| Irrigation | 300 k / 3 | 400 k / 5 | 1,5 M / 10 | Rendement 100 / 115 / 130 / 200 |
| Stockage | 200 k / 3 | 420 k / 5 | 900 k / 8 | Capacité 2,4 / 3,6 / 5,4 / 8,1 M |
| Arsenal | 150 k / 3 | 450 k / 5 | 1 M / 8 | Force 100 / 110 / 125 / 145, interne au moteur |
| Fortifications | 200 k / 5 | 900 k / 10 | 2,4 M / 20 | Défense locale contre capture ×3 / ×4 / ×5,5 / ×7 |
| Surveillance | 120 k / 3 | 360 k / 5 | — | Mobilisation de raid aléatoire 20/30/40 %, puis fixe 40 %, puis 60 % |
| Protection | 150 k / 3 | 450 k / 5 | — | Seuil 200 / 400 / 800 k, plafonné à 90 % du prélèvement |
| Transport | 200 k / 4 | 600 k / 6 | — | Butin par survivant 5 000 / 6 250 / 7 500 ; frais de convoi 10 / 7 / 5 % |
| Siège | 300 k / 5 | 750 k / 8 | — | Réduction du bonus des murs 0 / 25 / 50 % |

Départ d’un chantier N, durée trois lunes : achèvement N+3, premier prélèvement amélioré N+4 pour l’irrigation. Un achèvement après la fin configurée est refusé ; l’égalité est autorisée mais un premier effet économique trop tardif est signalé. La prévision de récolte conserve le nombre actuel de présents et le rendement actuel : elle exclut mouvements, pertes et effets futurs des travaux.

Arsenal, transport et siège de chaque contingent figés au départ. Transport calculé sur les survivants ; réduction du bonus des murs pondérée par les forces des contingents. Seuls les défenseurs locaux bénéficient des murs. La combativité numérique reste absente des projections et du navigateur.

## Raids

Minimum 20 Fidèles ; prix **5 000 + 1 000 × effectif**. Départ N, combat N+1, retour N+2. Une cible engagée est réservée jusqu’au combat. Deux cités ennemies initialement à portée, une de chaque maison rivale.

Soit A assaillants, D défenseurs rencontrés, E=min(A,D) et R le rapport de force équipé. L’arrondi des décès est au plus proche, demi-entier au-dessus.

| Situation | Morts assaillants / défenseurs | Butin / destruction de la part exposée |
| --- | --- | --- |
| Aucun défenseur | 0 / 0 | 60 % / 20 % |
| R > 1,25 : défense dispersée | 2 % E / 4 % E | 60 % / 20 % |
| 0,75 ≤ R ≤ 1,25 : combat disputé | 6 % E / 6 % E | Si R > 1 : 30 % / 10 % ; sinon 0 / 5 % |
| R < 0,75 : retrait sans interception | 2 % E / 1 % E | 0 / 0 |
| R < 0,75 : retrait intercepté | 20 % A / 2 % E | 0 / 0 |

Interception à 10/20/30 % selon surveillance effective 0/I/II. La surveillance ne renforce pas la combativité. Les murs n’interviennent pas dans les raids.

La récolte exposée vaut le quart entier du prélèvement après protection, celle-ci étant limitée à 90 % de ce prélèvement. Butin limité par le transport des survivants ; destruction limitée à 2 000 Mesures par survivant et au reste exposé après butin. Les stocks engrangés ne sont pas pillés, production et chantiers continuent.

Après pertes agricoles effectives, décès non combattants tirés uniformément entre zéro et le minimum entier de 0,2 % des habitants non engagés présents et 5 % des assaillants survivants. Échantillon sans remise : exclut combattants, expéditions et secours absents ; un Fidèle non engagé peut être touché et est retiré une seule fois.

Après victoire avec survivants, opportunité de dommage d’ouvrage de 20 %. Sélection uniforme entre surveillance et protection achevées, non déjà endommagées. Une protection sélectionnée doit encore être découverte (25 %) ; aucun second tirage d’ouvrage. Au plus un dommage, appliqué après les effets de ce raid. Niveau bâti conservé, effet réduit d’un niveau ; aucune destruction de chantier ni sabotage ciblé. Amélioration d’un ouvrage endommagé refusée jusqu’à réparation ; une amélioration déjà en chantier n’efface pas le dommage.

Toute perte réelle de ressources, habitants ou ouvrage pour la cible déclenche le répit de deux lunes, même après défaite des assaillants : perte en N, prochain raid possible en N+3. Les pertes des seuls attaquants ne suffisent pas. Capture toujours possible.

Exemple : 1,2 M accumulé, 200 k protégés → 250 k exposés. 60 assaillants ordinaires contre 40 défenseurs : 1 mort assaillant, 2 défenseurs, jusqu’à 150 k de butin, 50 k détruits, coût 65 k, solde provisoire +85 k. Avec 41 contre 40 : combat disputé, 2 morts de chaque côté, 75 k de butin, 25 k détruits, coût 46 k, solde provisoire +29 k. Ces soldes excluent morts, production perdue, perte du butin ou débordement au retour.

## Captures et siège d’un mois

Minimum 80 Fidèles ; prix **50 000 + 2 000 × effectif**, soit 210 k au minimum. Captures abordables avant la première récolte ; leur réussite dépend des forces et stocks adverses. Aucun siège maintenu entre tentatives.

Secours automatiques : au plus 20 % des Fidèles disponibles de chaque cité amie reliée, répartis entre menaces et plafonnés par la force de l’assaillant. Une cité elle-même attaquée en capture pendant cette résolution n’envoie aucun secours. Ils restent absents toute la phase et leurs survivants restent attachés à leur maison.

Attaque strictement supérieure à 1,5 fois la défense fortifiée : reddition, pertes 1 % assaillants / 2 % défenseurs. Supérieure seulement à la défense fortifiée : assaut, 8 % / 12 %. Supérieure à la défense de campagne mais pas aux murs : siège ponctuel d’un mois, **500 Mesures engrangées par habitant présent**. À l’égalité des stocks la cité tient : consommation de ce besoin, pertes 2 % / 1 %. En dessous elle consomme le stock restant et capitule : 4 % / 8 %, sans mortalité civile supplémentaire. À 1 000 présents, 500 000 suffisent, 499 999 ne suffisent pas. Si l’attaque ne dépasse pas la défense de campagne : défaite 12 % / 3 %, ou déroute 25 % / 2 % sous la moitié de cette défense.

Avec 100 locaux et 40 secours ordinaires, défenses initiales : campagne 140, fortifiée 340. **150 attaquants peuvent prendre une cité ayant dépensé son stock sous le besoin de siège** ; une réserve suffisante la fait tenir. 300 sans siège ne franchissent pas ces défenses ; 300 avec siège I réduisent la défense à 290 et gagnent l’assaut. Les coefficients sont un choix de jeu, pas une mesure archéologique.

Intégrité initiale 100 %. Multiplicateur effectif = 1 + (multiplicateur intact − 1) × intégrité × (1 − réduction de siège). Assaut réussi : intégrité au plus 50 %. Siège tenu : baisse de 20 points × réduction moyenne de siège, plancher 70 %, sans remonter une intégrité déjà inférieure. Redditions/pénuries ne dégradent pas mécaniquement les murs. Précision rationnelle conservée, sans flottants.

Réparation des défenses initiales : 20 k / 2 lunes ; murs I/II/III : 40 k / 3, 180 k / 6, 480 k / 8. Surveillance I/II : 24/72 k, deux lunes ; protection I/II : 30/90 k, deux lunes. Réparer restaure l’effet, sans gagner de niveau ni restituer des habitants ou ressources perdus.

## Convois et retours

Convoi entre deux cités amies distinctes reliées au scellement et au départ, de 1 à 500 000 Mesures entières. Un seul convoi confirmé/actif/en retour par origine. Prix : cargaison + frais arrondis au-dessus (10/7/5 % selon transport d’origine). Départ N, réception N+2 après combats et récolte ; seuls la cargaison et l’espace disponible comptent à réception. Aucun homme, escorte ou interception.

Si destination perdue, retour vers origine encore amie, sinon refuge ami déterminé au départ, avec une lune supplémentaire. Vérification de sa propriété à l’arrivée réelle ; sinon cargaison perdue. Débordement perdu, pas de dépôt doublé après répétition.

La capture d’une origine ne transfère pas immédiatement ses contingents absents à l’armée ennemie. Ceux-ci sont retirés de la population locale et restent comptés sous leur maison pendant le voyage. Au retour : origine amie, sinon recherche d’une cité encore amie directement reliée par une route à la cité attaquée, avec une lune supplémentaire. Les cités amies éloignées ne sont pas des refuges. Sans voisin ami, ou si le refuge change de maître avant l’arrivée, les survivants rentrent dans leur cité d’origine comme Fidèles du nouveau souverain ; l’éventuelle restriction de départ encore active s’applique aussi à eux, sans prolonger son échéance. Leur ancien maître perd le butin. Chaque contingent est déposé une seule fois, y compris les retours répartis sur plusieurs lunes. Le choix du refuge des convois et les anciennes économies ne changent pas.

## Lecture et décisions

Conseil, Expéditions et Chantiers restent les trois destinations. La carte conserve sa géographie publique ; les informations de décision sont dans les comptes et la préparation : équipement par origine, siège, transport, part à payer, reste disponible, besoin d’un mois de siège, dates et seuil de remboursement. Aucun gain ennemi garanti ni estimation issue de données cachées.

Le Conseil indique frontières accessibles, expéditions engagées, travaux/réservations d’équipe, dommages, risque de ravitaillement et récents événements liés. Les fiches de cité exposent leurs huit familles d’ouvrages. Les notes natives « i » s’ouvrent au clavier et sans JavaScript ; elles expliquent les subtilités, mais ne cachent pas coûts et alertes. Préparation et scellement restent distincts, avec sélection multi-cités.

Les nouveaux rapports relient leur cité, décrivent précisément les pertes propres et qualitativement les pertes adverses : aucune, quelques (1–4), sensibles (5–14), lourdes (15–29), très lourdes (30+). Sous dix témoins : observation non fiable. Observations datées issues uniquement des lettres du destinataire ; aucun rafraîchissement depuis les comptes ennemis. Les observations de forces et d’équipement gardent leurs seuils de témoins existants. Les lettres anciennes ne sont pas réécrites.

## Ouvertures humaines vérifiées

Les tests `test_strategy_openings.py` décrivent des plans fixes réalisables, sans supposer un comportement de bot. Deux armées alternées de 150, réparties 50/50/50, assiègent en lunes 2 et 4 : sans réaction, 900 k ne suffisent pas, capture en 4 pour 700 k de frais. Un convoi lancé après le premier combat, en lune 3, arrive en 5 et ne sauve pas la cité. Un convoi préventif de 500 k lancé en lune 1 arrive en 3 et fait tenir la seconde tentative. Ces ouvertures rendent l’anticipation importante ; une alerte « un mois » n’est pas une garantie contre les tentatives suivantes.

Contre-exemple à une attaque sans risque : la maison défendue envoie simultanément 200 hommes depuis ses deux cités arrière contre l’origine frontalière adverse, affaiblie par les départs. La cible initiale tient son siège, tandis que cette contre-attaque capture la frontière en lune 2 et coupe la route de l’assaillant vers elle. Ce résultat dépend de cette répartition des forces et ne garantit pas une réponse universelle.

Une autre série répète la même armée de 150 tous les trois mois : sans réponse capture en lune 5 ; avec un convoi anticipé capture en 8 ; trois convois de 500/500/300 k aux lunes 2/5/8 permettent quatre sièges tenus jusqu’à la première récolte. Les ressources et frais sont réellement débités. Enfin 51 raiders ordinaires contre 40 défenseurs gagnent militairement dans les deux saisons : départ en 1 donne 3 k de butin conservé et −53 k de solde monétaire ; départ en 10 donne 135 k et +79 k. Morts et production perdue s’ajoutent à ces comptes.

Ces cas établissent des menaces et réponses concrètes, pas l’équilibre du multijoueur. À surveiller en essais humains : pression simultanée sur plusieurs frontières, rotation des armées, timing des convois, saisonnalité des raids et coût d’un retrait de défenseurs pour contre-attaquer.

## Évaluation et limites

`scripts/evaluate_strategy.py` exécute des parties complètes de 120 lunes (ou victoire anticipée) avec commandes normales de trois maisons automatiques et graines explicites. Compare les stocks initiaux 600/900 k avec les mêmes règles nouvelles : ordres et intervalles, occupation des équipes, victoires et rentabilité nette des raids au retour, captures/sièges/conquêtes, destructions, frais, production perdue par absence, réparations et durée des constructions tardives. Ne recalculer aucun ancien journal comme s’il s’agissait d’une simulation.

Le bot actuel n’est pas un joueur optimal : seuil de richesse pour captures, pas de politique de réparation/convoi. Ses périodes sans ordre ne prouvent pas une absence de choix humains. Les études d’ouverture et vérifications arithmétiques complètent ces observations ; elles ne démontrent pas l’équilibre de toutes les stratégies.

Sans action ni perte, première récolte 1,2 M → 2,1 M en grenier. Rigoles commencées en lune 1 : quatre prélèvements à 100 k et huit à 115 k, soit 1,32 M puis 1,92 M en stock après le prix de 300 k. Amortissement marginal à 1 000 présents : 20, environ 26,67 et 21,43 lunes de production améliorée pour les trois passages, hors construction et délai de versement.

Voir `docs/backlog.fr.md` pour reconnaissance, sièges prolongés, hospice, recrutement acheté, nouveaux bâtiments militaires, sabotage ciblé et chronique narrative tous joueurs. Ces idées restent différées.

## Livre de fin de règne — 22 octobre 2026

Ajout vérifié depuis la base `8d4a22d` de `codex/yaara-deployment`, sans modification des règles ni des résultats. À la fin du règne, le Conseil propose le livre chronologique des lettres conservées et un téléchargement JSON pour analyse. Chaque participant peut lire sa maison ; le propriétaire de la partie peut choisir toutes les maisons après la fin seulement. Ce partage de fin de règne ne modifie pas le secret en cours de partie et ne révèle ni combativité numérique, ni graines, ni tirages internes.

Les nouvelles clôtures conservent les comptes de chaque maison après résolution : cités possédées, population, stocks, prélèvement accumulé, travaux et registre des ordres/expéditions autorisés. Les comptes antérieurs à cet ajout ne sont pas reconstitués ; les lunes manquantes sont indiquées. Les lettres existantes et les comptes finaux restent disponibles. Plusieurs témoignages d’un même combat ne doivent pas être comptés comme plusieurs combats. Le JSON indique son schéma, les versions de règles de la sauvegarde et la couverture des comptes ; il ne constitue pas un journal de rejeu complet du moteur.


## Lecture après essai — 28 octobre 2026

Référence de départ : `1ed918bc6c0046d3c496aecffde16135c9e5365c`. Les règles
de simulation et les sauvegardes restent inchangées. La carte affiche toutes les
routes publiques en pointillés gris ; les trajets propres suivent leurs courbes,
en rouge vers une cité ennemie et en vert vers une cité possédée, y compris les
convois et retours. Aucun trajet adverse caché n’est ajouté.

Le compteur de l’enveloppe additionne nouvelles non lues de la dernière lune et
alertes non résolues ; lire une lettre ne résout pas une alerte. La connaissance
d’une cible n’affiche que la dernière observation conservée pour le destinataire,
les autres restant aux archives. Une menace entrante ou un avertissement de
réserves de siège ne bloque pas un ordre par ailleurs valide ; un refus de
préparation est expliqué dans le panneau. Ces descriptions ne constituent pas
une attestation de déploiement.

Un petit symbole d’outils indique une équipe réservée ou occupée dans une cité
possédée. Sans symbole, l’équipe est libre. Le nom du chantier et sa date de fin
restent dans la fiche de cité ; aucune activité d’équipe ennemie n’est dévoilée.
