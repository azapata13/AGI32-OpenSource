# Format du sommaire de simulation

Ce document décrit, page par page, le sommaire que le logiciel doit produire. Il est dérivé
d'une analyse de rapports réels de simulation horticole (serres, chambres de culture,
racking vertical, propagation, comparaisons de luminaires). Le but est que le PDF généré soit
indiscernable, dans sa structure et son contenu, d'un rapport fait à la main dans AGi32.

Toutes les valeurs entre `{accolades}` viennent du `ProjectSpec` (voir `project-spec.md`)
ou des résultats de calcul.

## Nom du fichier

```
{company} Light Simulation - {client} - {project_name} - {YYYY-MM-DD}.pdf
```

- Ajouter ` V2`, ` V3`… à la fin du nom de projet à chaque révision.
- Pour une comparaison : `{project_name} - {Option A} Vs {Option B}`.

## En-tête et pied de page (toutes les pages)

En-tête :

- `{company} - {designer} - Horticulture Light Design`
- `Project Name : {project_name}`
- `{site_address}`
- `Prepared For: {prepared_for}`

Pied de page :

- Avertissement standard sur la précision des calculs (normes IES/CIE, tolérances, conditions
  réelles différentes des données d'entrée).
- `Filename: {model_filename}`
- `By : {designer}` · `Units: Imperial|Metric` · `Date: {date}`
- `Engine: agiopen {version}` · `Total Time (Hrs.): {design_hours}`
- `Page {n} of {N}`

## Pages

| # | Page | Contenu obligatoire |
|---|------|---------------------|
| 1 | Couverture | `LED Grow Light Plan Using: {fixture_family}` et un rendu 3D isométrique du site. |
| 2 | Fiche luminaire | Nom commercial, `Power: {W}W`, `PPF: {ppf} umols/s`, `Efficacy: {eff} umols/J`, `Warranty`, `DLC Listing Reference` si connu. Une page par famille de luminaire. |
| 3 | Information Provided | Les données fournies par le client, telles quelles (ex. « 1 serre de 30 x 102 - 9.5 pieds hauteur - Leafy greens », « PPFD requis = 180-200 µmol/m²/s »). Omise si vide. |
| 4 | Results Summary | Voir détail ci-dessous. |
| 5 | Lighting Design Legend and Reflectivities Applied | Légende des surfaces (plantes, structure, racking, plancher, murs/toit) avec réflectivité et transparence, plus vues Overhead et Front. |
| 6 | Plan view | Plan à l'échelle : murs, structure, luminaires, cotes principales, horaire des luminaires, sommaire de calcul et sommaire LPD superposés. |
| 7 | Point par point | Grille de valeurs PPFD (entiers) sur tout le plan de calcul, avec cotes. |
| 8 | Zoom point par point | Agrandissement d'une zone représentative pour que les valeurs soient lisibles. |
| 9+ | Élévations | Front et Side : hauteur des luminaires, hauteur de canopée, cote « distance plan de calcul – luminaire ». |

Pour une comparaison d'options (ex. luminaire A vs B), les pages 6 à 8 montrent les deux
cartes côte à côte et le sommaire de calcul a une ligne par option. *Pas encore implémenté :
voir la feuille de route du README.*

## Results Summary (page 4)

1. Ligne d'introduction : `Distance Between Calculation Plane and Fixture: {d} {unit} - See Layout`.
2. **Calculation Summary**

   | Label | CalcType | Units | Avg | Max | Min | Min/Avg | Min/Max | # Pts |
   |-------|----------|-------|-----|-----|-----|---------|---------|-------|
   | Plant Canopy_Top | PPFD | µmol/s/m² | 180.01 | 208 | 129 | 0.72 | 0.62 | 2028 |

   - Avg à 2 décimales, Max/Min en entiers, ratios à 2 décimales.
   - Une ligne par grille (par niveau de racking, par option comparée, par zone).
3. **Luminaire Schedule**

   | Symbol | Qty | LLF | Description | Lum. Watts | Total Watts | Manufacturer | Luminaire PPF |
   |--------|-----|-----|-------------|-----------|-------------|--------------|---------------|

   - Une ligne par type ou par niveau de gradation (ex. « 900 W LED » et « 900 W LED (dimmed 75) »).
4. **LPD Area Summary** : `Label · Area · Total Watts · LPD · LPD Units` (W/ft² en impérial, W/m² en métrique).
5. Note d'uniformité facultative : les valeurs couvrent tous les points de la zone de culture,
   y compris les bords ; l'uniformité mesurée entre quelques luminaires au centre sera plus élevée.
6. **Light Level Approval** : cases `Customer Signature` / `Date` et `Rep` / `Date`.

## Conventions de calcul visibles dans le rapport

- Le type de calcul est toujours `PPFD`, en µmol/s/m², affiché sans décimale sur les grilles.
- Le plan de calcul est posé sur le dessus de la canopée (`_Top`).
- LLF = 1.000 par défaut (pas de dépréciation), sauf demande contraire.
- La puissance totale et le LPD sont calculés à partir des watts réels de chaque luminaire,
  y compris ceux qui sont gradés.
