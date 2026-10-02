# `project.json` : les champs

Un projet est un objet JSON avec sept sections. Le schéma complet est dans
`schemas/project.schema.json`. Les longueurs sont dans les unités de `meta.units` : pieds pour
`imperial`, mètres pour `metric`. Le repère a son origine au coin du site, X sur la largeur et Y
sur la longueur.

## meta

| Champ | Rôle |
|-------|------|
| `project_name`, `client`, `prepared_for`, `site_address`, `date` | En-tête et nom du fichier. |
| `company`, `designer` | Identité qui signe le rapport. |
| `units` | `imperial` ou `metric`. Ne change pas en cours de projet. |
| `revision` | 2, 3… ajoute ` V2`, ` V3` au nom. |
| `design_hours` | Temps de conception affiché dans le cartouche. |
| `information_provided` | Phrases du client reprises en page 3. |

## site

`type` : `greenhouse`, `indoor_room`, `vertical_rack` ou `container`. Viennent ensuite `width`
(X), `length` (Y) et `height` (gouttière ou plafond).

- Serre : `bays`, `roof` (`gable`, `barrel`, `venlo`), `peaks_per_bay`, `ridge_height`,
  `truss_height` (dessous de ferme), `post_spacing`, `glazing_transmission`, `structure_reflectance`.
- Intérieur : `wall_reflectance`, `ceiling_reflectance`, `floor_reflectance`.

## fixtures

`id`, `name`, `family`, `manufacturer`, `watts`, `ppf`, `warranty`, `dlc_reference`, `image`
(photo pour la fiche). La photométrie vient de `ies_file` si possible. Sinon :

- `distribution: "batwing"` avec `beam_angle` (angle total) et `batwing_power` (2,5 environ
  pour les optiques « WD ») ;
- `distribution: "cosine"` avec `cos_power` (1 = Lambert).

`length` et `width` : les dimensions du luminaire. Si `length` > 0, la source est traitée comme
linéaire (barre).

## canopies

Un rectangle par zone de culture : `label`, `x`, `y`, `width`, `length`, `height` (dessus des
plantes au-dessus du plancher) et `reflectance` (0,26 par défaut). En racking, un rectangle par
niveau. En serre, si la section est absente, une canopée par chapelle est créée.

## layout

Un bloc par groupe de luminaires :

| `mode` | Champs |
|--------|--------|
| `grid`, `staggered` | `cols` (X), `rows` (Y), et soit `spacing_x`/`spacing_y` + `origin_x`/`origin_y`, soit une répartition égale sur la canopée. |
| `rack` | `cols` barres par niveau, `distance_to_canopy`. Les barres sont placées bout à bout sur la longueur. |
| `explicit` | `positions` : liste de `[x, y]` ou `[x, y, z]`. |
| `auto` | Le moteur cherche la plus petite grille qui atteint `target.ppfd_min`. |

Hauteur : `mounting_height` (dessous du luminaire) ou `distance_to_canopy`. Sans l'un ni
l'autre, la serre utilise `site.truss_height`. Les autres champs sont `dimming` (0 à 1),
`rotation_deg` et `canopy` (pour cibler une zone précise).

## target, calc

- `target` : `ppfd_min`, `ppfd_max`, `uniformity_min` (Min/Avg).
- `calc` : `grid_spacing` (0 = automatique), `include_reflections`, `reflection_factor`, `llf`,
  `extra_planes` (décalages sous la canopée, pour les cultures hautes).
