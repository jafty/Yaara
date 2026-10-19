# Implemented rules

The authoritative design is [the original dossier](design-source.fr.md). Prototype choices are recorded in [decisions.md](decisions.md).

The approved audit revision supersedes the original economic and geography defaults for **new** reigns: yield is 100 / 130 / 200 per present inhabitant per Moon; each city funds its works, and expedition origins pay their troop costs plus a proportional share of the fixed fee. No transfers or automatic subsidies exist. New groups initially reach one city in each rival house; captures open additional routes. Saved economies and road networks remain unchanged. New automatic reigns wait for **Begin the reign**, then advance on stored UTC deadlines processed by the scheduler or Railway cron. See [Railway setup](railway.md).

| Behavior | Dossier sections | Implementation |
| --- | --- | --- |
| Month sequence, victory, elimination | 1–3, 23 | `advance_month`, `check_end` |
| Local stocks, tax, recruitment, growth | 4, 13–14, 18 | `annual_economy`, `reservations` |
| Confirmation, targets, cancellation | 5–6, 22 | `prepare_order`, application services |
| Reachability and returns by origin | 7, 10 | `eligible_origins`, `return_expeditions` |
| Relief budgets, threat cap, fixed command | 8, 15 | `relief_allocations`, `resolve_combats` |
| Capture, siege, walls, rounding | 9, 16 | `capture_result`, `losses` |
| Raids, loot, protection | 17 | `raid_result`, `resolve_combats` |
| Construction and equipment | 18 | `work_spec`, `finish_works` |
| Private dated reports | 11, 24 | `player_view`, recipient `Report` records |
| Calendar and excessive lateness | 25 | `tick`, `toggle_pause`, scheduler commands |

The default reign lasts 120 months; 24, 60 and 240 are also offered. The calendar is manual, five minutes or ten minutes. Other balance values are source configuration, not an unrestricted in-game editor.

V0 offers first-level canals/walls, no growth, no siege and no cancellation. V1 adds higher levels, storage, repairs, equipment, growth, siege and cancellation before closure. Upgrading walls does not repair damage sustained during construction. Recruitment counts absent Fidèles and never resurrects the dead.

## French quick start

1. Créez un compte, puis un règne V1 avec calendrier manuel.
2. Dans **Domaine**, ouvrez directement le feuillet d’une cité pour lire ses réserves et ses effectifs.
3. Dans **Décrets**, choisissez un ouvrage et cochez toutes les cités concernées, sans ouvrir leurs feuillets. Un seul récapitulatif et un seul sceau suffisent pour ce lot. Les expéditions réunissent aussi plusieurs origines dans un même ordre.
4. **Sceller ce décret** réserve les moyens. Le départ et le paiement ont lieu à la clôture de la lune ouverte.
5. **Clore la lune 1** avance le monde. Un raid scellé à la lune 1 part à sa clôture, combat à la lune 2 et revient à la lune 3.
6. Consultez **Correspondance** après les événements. Le butin n’est utilisable qu’au retour.
7. Le premier prélèvement est versé à la clôture de la lune 12. Épargnez, irriguez ou préparez vos premières conquêtes.

Les rivaux actifs utilisent leurs propres ressources et les mêmes confirmations. Les rivaux passifs permettent d’explorer les mécanismes sans recevoir de nouvelles attaques. Une capture est volontairement impossible avec le budget initial ; un raid victorieux peut perdre de l’argent.

New reigns begin at the open Moon 1. Existing games keep their original simulation dates; the compatibility contract is recorded in [decisions.md](decisions.md). The footer switches between French and English.
