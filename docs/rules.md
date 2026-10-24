# Implemented rules

The current code-grounded reference is [the gameplay review](gameplay-review-prompt.fr.md). [Decisions](decisions.md) record compatibility and implementation choices. The [original dossier](design-source.fr.md) is historical, and the [backlog](backlog.fr.md) contains unimplemented ideas.

New games use the approved eight-family catalogue, city-local funding, 100/115/130/200 yield, annual payment after seasonal crop raids, fixed surveillance mobilization, a two-Moon respite and fortification coefficients 3/4/5.5/7 from initial defenses through level III. Strategy version two adds paid departure intelligence, three-Moon restrictions on inherited conquered troops, automatic frontier assembly and reciprocal road encounters for every raid/capture combination. Equipment, transport and siege benefits follow origin contingents; walls and siege equipment do not affect field encounters. There is no production interruption after raids. Old snapshots retain their saved economy and strategic behavior.

| Behavior | Implementation |
| --- | --- |
| Monthly sequence, victory and elimination | `advance_month`, `check_end` |
| Accrual, annual payment, growth and renewal | `annual_economy`, `harvest_city` |
| Local funding, atomic confirmation, cancellation | `prepare_order`, application services |
| Seasonal raids and two-Moon arrival protection | `raid_result`, `resolve_combats`, admission/departure checks |
| Mixed-origin transport and siege | `carrying_capacity`, `siege_reduction` |
| Fortification damage and bonus-only reduction | `wall_multiplier`, `capture_result` |
| Building catalogue and completion | `work_prices`, `work_spec`, `finish_works` |
| Private dated reports and public map | `player_view`, recipient `Report` records |
| Calendar deadlines and retry safety | `tick`, `toggle_pause`, scheduler commands |

## French quick start

1. Créez un règne, choisissez son calendrier et ses adversaires. Le calendrier automatique attend votre départ explicite.
2. Le **Conseil** rassemble les comptes locaux, nouvelles et échéances.
3. Dans **Chantiers**, ouvrez une famille et cochez les cités concernées. Chaque ligne affiche le passage, son effet, son coût et sa durée. Les cités paient séparément ; un seul ordre peut les réunir.
4. Dans **Expéditions**, choisissez une cible sur la carte, Piller ou Capturer, puis les effectifs par origine.
5. **Vérifier l’ordre** ouvre une relecture sans réservation. **Confirmer et sceller l’ordre** réserve les moyens ; la clôture les paie et déclenche le départ ou chantier.
6. Un raid partant en lune N combat en N+1 et revient en N+2. Les cibles les plus tardives dans l’année peuvent offrir davantage de récolte, sans garantie de profit. Consultez les bilans de butin et de dépenses.
7. La récolte restante est versée toutes les douze lunes. Irrigation et arsenaux deviennent abordables dès l’ouverture ; une capture coûte 50 000 + 2 000 par homme, soit 210 000 au minimum, mais sa réussite dépend des forces et réserves ennemies.
8. Des murailles très fortes n’empêchent pas une capitulation par manque de réserves. Les réparations restaurent un bonus partiellement perdu et occupent l’équipe locale.

Le règne standard dure 120 lunes ; 24, 60 et 240 sont aussi disponibles. Posséder toutes les cités donne la victoire ; au terme, le nombre de cités puis la population déterminent le classement. Aucun prestige ni score de trésorerie. Les tests vérifient les règles et leurs frontières, pas l’équilibre stratégique de toutes les ouvertures.
