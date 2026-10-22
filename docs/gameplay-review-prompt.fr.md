# Yaara — Référence de jouabilité

Révision du 20 octobre 2026 : implémentation de la demande de jouabilité et de son GO, puis renforcement des fortifications demandé pendant le développement. Base récupérée : `d9747b1` de `codex/yaara-deployment`. Cette référence décrit le code de cette révision, pas une preuve du déploiement Railway ni les paramètres d’une sauvegarde particulière.

## Maintien et compatibilité

Toute modification du cœur doit mettre à jour les faits et exemples concernés dans ce document, ainsi que `docs/decisions.md`. Vérifier le code et le marqueur économique de la sauvegarde avant de répondre sur les règles. Le dossier `design-source.fr.md` reste historique.

Les nouvelles parties utilisent `economy_version=3`, les forges locales, la carte à douze routes et le calendrier ouvrant la lune 1. Les économies précédentes conservent leurs tarifs, niveaux, équipements, raids sur stocks et calendrier de récolte. Aucun ordre, chantier, devis accepté ou rapport archivé n’est réécrit. V0/V1 disparaissent de l’interface de création et des étiquettes ; les identifiants nécessaires aux anciennes sauvegardes restent internes.

## Cadre et victoire

Trois maisons possèdent initialement trois cités chacune. Le mode livré est solo contre deux adversaires automatiques actifs ou passifs. Une année compte douze lunes. Le règne standard dure 120 lunes ; les durées 24, 60 et 240 restent disponibles. Calendrier manuel ou automatique à cinq/dix minutes ; les parties automatiques attendent un départ explicite et suivent les échéances stockées.

Posséder toutes les cités donne la victoire immédiate. Au terme du règne, classement par nombre de cités puis population de rattachement. Pas de prestige ni de classement aux mesures restantes. Pilleur, producteur, défenseur et conquérant sont des orientations possibles, pas des classes ni une promesse d’équilibre démontré.

## Ressources et rythme

Chaque cité commence avec 1 000 habitants, dont 100 Fidèles, 600 000 mesures disponibles, un prélèvement accumulé nul et une capacité de 2 400 000. Chaque cité finance seule ses travaux ; chaque origine finance ses hommes et sa part proportionnelle du forfait d’expédition. Aucune trésorerie mutualisée ni transfert manuel.

Le rendement par habitant présent est 100 / 115 / 130 / 200 mesures par lune. Les hommes absents ne produisent pas ; le départ intervient après la comptabilisation et le retour après elle. La récolte s’accumule sans être dépensable puis est versée aux clôtures 12, 24, etc., sous réserve de capacité. Le surplus est perdu. Croissance annuelle de 0,5 %, arrondie à l’entier inférieur ; renouvellement des Fidèles dans les habitants existants, plafonné à 1 % et à l’écart au contingent cible de 10 %.

Dans la nouvelle économie, la clôture comptabilise le prélèvement, exécute les départs et achèvements, résout les combats, effectue le versement annuel et le renouvellement éventuels, puis les retours et le résultat. Les raids de la lune 12 atteignent donc sa récolte avant versement. Un siège utilise les réserves déjà engrangées ; une cité conquise reçoit sa récolte restante sous son nouveau propriétaire. Les anciennes économies gardent leur ordre précédent, avec versement avant les combats.

Le scellement exige les fonds déjà disponibles ; une récolte attendue ne finance pas un ordre encore inabordable. La préparation et la relecture ne réservent rien ; le scellement réserve, la clôture paie. L’annulation libère les réservations avant départ dans les règles qui l’autorisent.

## Catalogue courant

Coûts par passage, effets totaux remplaçant le niveau précédent. Une équipe locale par cité ; lots multi-cités atomiques.

| Famille | Niveau I : prix / lunes | Niveau II : prix / lunes | Niveau III : prix / lunes | Progression |
| --- | --- | --- | --- | --- |
| Irrigation | 300 k / 3 | 400 k / 5 | 1,5 M / 10 | Rendement 100 → 115 → 130 → 200 |
| Stockage | 200 k / 3 | 420 k / 5 | 900 k / 8 | Capacité 2,4 → 3,6 → 5,4 → 8,1 M |
| Arsenal | 150 k / 3 | 450 k / 5 | 1 M / 8 | Force de base ×1 → ×1,10 → ×1,25 → ×1,45 |
| Fortifications | 200 k / 5 | 900 k / 10 | 2,4 M / 20 | Défense locale contre capture ×1 → ×2 → ×4 → ×7 |
| Surveillance | 120 k / 3 | 360 k / 5 | — | Mobilisation de raid aléatoire 20/30/40 %, puis fixe 40 %, puis fixe 60 % |
| Protection | 150 k / 3 | 450 k / 5 | — | Récolte protégée 200 → 400 → 800 k |
| Transport | 200 k / 4 | 600 k / 6 | — | Capacité de butin ×1 → ×1,25 → ×1,50 |
| Siège | 300 k / 5 | 750 k / 8 | — | Ignore 0 → 25 → 50 % du bonus des murs |
| Réparation des fortifications | 40 k / 3 | 180 k / 6 | 480 k / 8 | Restaure le niveau endommagé existant |

Prix d’arsenal fixes, indépendants de la population. Une construction démarrant à la clôture N et durant trois lunes s’achève à N+3. L’irrigation produit au nouveau rendement à la comptabilisation suivante, sans rétroactivité.

Équipement, transport et matériel de siège restent propres à chaque origine et sont figés au départ. La capacité de transport dépend des survivants de chaque origine. La réduction de murs d’une armée mixte est pondérée par la force de chaque contingent. Les secours conservent leur propre équipement ; seuls les défenseurs locaux bénéficient des murs.

Une capture par assaut peut endommager les fortifications : leur bonus est divisé par deux. Le matériel de siège réduit ensuite le bonus restant, jamais la défense de base. Exemple : murailles intactes ×7, béliers homogènes → `1 + (7−1) × 0,5 = 4`. Murailles endommagées et béliers → ×2,5. Les réparations existaient déjà avant cette révision ; elles sont adaptées aux nouveaux prix/niveaux. Les raids ne détériorent pas les bâtiments et n’arrêtent ni production ni chantier.

## Raids saisonniers

Minimum 20 Fidèles ; coût `20 000 + 2 500 × effectif`. Départ à la clôture N, combat N+1, retour N+2. La cible est réservée exclusivement dès le scellement. Deux cités ennemies sont initialement accessibles, une de chaque maison rivale.

Le raid vise le prélèvement réellement accumulé, jamais les stocks déjà engrangés. Soustraire d’abord le seuil protégé (200/400/800 k), puis exposer un quart du reste positif. En cas de victoire stricte en force, butin = minimum entre 60 % de cette fraction et la capacité des survivants ; destructions = 20 % de la fraction. Une défaite ordinaire peut détruire 5 % de cette fraction ; une déroute ne prélève ni ne détruit. Aucune interruption de production, aucun forfait supplémentaire.

Capacité ordinaire : 5 000 mesures par survivant, modifiée par son origine. Une réserve protégée ne protège ni les combattants ni la cité. La surveillance remplace le tirage 20/30/40 par une mobilisation garantie de 40 ou 60 %. Les murs ne renforcent pas les défenseurs de raid. Les pertes militaires continuent naturellement de réduire la population productrice.

Un succès qui prélève ou détruit des ressources disperse les villages pendant les deux lunes suivantes : pillage N, prochain combat de raid N+3. Une arrivée à cette date peut être préparée avant. Une victoire sans pertes agricoles et une défaite ne déclenchent pas ce répit. Les captures restent possibles. Le butin n’est dépensable qu’au retour ; capacité et propriété des cités déterminent les dépôts et le bilan final.

Exemple à équipements ordinaires, 1,2 M accumulé et 200 k protégés : 250 k exposés, jusqu’à 150 k pillés, 50 k détruits. Avec 41 assaillants contre 40 défenseurs, coût 122 500, butin 150 000, solde provisoire +27 500. Ce solde exclut pertes humaines, production perdue pendant l’absence et éventuels débordements au retour. La récolte restante vaut 1 M. Le taux de production n’est pas suspendu.

## Captures, siège ponctuel et ravitaillement

Minimum 80 Fidèles ; coût `900 000 + 18 000 × effectif`, soit au moins 2,34 M. Une capture reste hors de portée des seules réserves initiales d’une maison. Il n’existe pas encore de siège maintenu sur plusieurs lunes.

L’attaque doit dépasser strictement la défense fortifiée pour un assaut victorieux ; au-delà d’une fois et demie cette défense, reddition. Si elle dépasse seulement la défense hors murs, un siège ponctuel vérifie le ravitaillement : `500 × habitants présents`. Stocks suffisants : la cité tient et consomme ce montant ; stocks insuffisants : capitulation par pénurie. Des murs ×7 n’empêchent pas cette seconde issue. À 1 000 présents, 500 k suffisent exactement, 499 999 ne suffisent pas. Les pertes et dépenses normales restent dues. Pas d’immunité contre un nouvel assaut et pas de pause de chantier entre tentatives.

Les coefficients ×2/×4/×7 sont des paramètres de jeu explicitement choisis pour favoriser le siège face aux grandes murailles. Les sources historiques sur les forteresses ne prouvent pas un multiplicateur universel de sept ; ne pas présenter ce nombre comme une mesure archéologique.

## Première année et rentabilité indicative

Sans action, attaque ou absence, une cité reçoit 1,2 M en lune 12 et atteint 1,8 M de stock. Si les rigoles démarrent à la clôture 1, elles s’achèvent à la clôture 4 : quatre lunes à 100 k et huit à 115 k, soit 1,32 M récolté et 1,62 M de stock après paiement initial de 300 k. La croissance de clôture 12 ne modifie pas cette première récolte.

À population constante de 1 000 présents et sans pertes ni débordements, amortissement marginal des trois passages d’irrigation : 20, environ 26,67 et environ 21,43 lunes de production améliorée. Construction et attente du versement s’ajoutent au délai de récupération en argent disponible. Ces chiffres ne prouvent pas l’équilibre d’un règne de 120 lunes.

## Interface et idées différées

Conseil, Expéditions et Chantiers restent les destinations principales. Catalogue illustré compact, fiches de famille avec sélection multi-cités, panneau d’attaque dans la page sous la carte et contrôles natifs ; aucune popup obligatoire. « Valider l’action » ouvre la relecture ; seul le scellement engage les moyens. Suivi des ordres en attente et opérations actives, historique dans les rapports. Illustrations décoratives par contexte, sans nouvelle divulgation d’informations adverses.

Ajout de présentation du 21 octobre 2026 : les nouveaux rapports de combat conservent une illustration propre au raid ou à la capture, à l’expédition offensive ou à l’attaque reçue, et au succès ou à l’échec de l’assaillant. Une attaque ennemie réussie illustre donc une perte du destinataire. Le choix suit l’issue militaire, même sans butin, sans modifier les règles ni les textes archivés ; les anciens rapports sans ce choix gardent leur illustration générique.

Voir `docs/backlog.fr.md` pour les pistes différées : détérioration d’ouvrages extérieurs, reconnaissance, engagements visibles, sièges prolongés, hospice, ravitaillement, écuries, archers et éventuel prestige. Elles ne sont pas des règles livrées.

Ajout de présentation du 22 octobre 2026 : Conseil et archives explicitent l’issue militaire à partir du résultat d’attaque déjà enregistré avec l’illustration : attaque réussie et défense vaincue, ou attaque échouée et défense maintenue. Ce résultat reste distinct du bilan financier du raid. Les lettres de capture reçue identifient aussi la maison attaquante lorsqu’une seule expédition historique correspond à la cité et à la lune du rapport. Ces précisions s’appliquent aux rapports existants sans réécrire leur contenu ; une correspondance absente ou ambiguë et une ancienne lettre sans résultat enregistré ne conduisent à aucune déduction nouvelle. Source : `simulation/presentation.py`, révision du 22 octobre 2026 ; règles et sauvegardes inchangées.
