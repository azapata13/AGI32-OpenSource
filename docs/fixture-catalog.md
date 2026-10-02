# Catalogue de luminaires

`agiopen/catalog/fixtures.json` contient les luminaires DLI (NXS, Vertex) et P.L. Light (ParFX
Ultra Lite / Ultra / Ultra Plus / Ultra Max, VertiMax, BalensBeam, BudBoost, TriPlane Linear),
une entrée par puissance et par spectre. Les valeurs viennent des fiches techniques publiques
(DLI via hortamericascanada.com, P.L. Light via pllight.com, 2026). Pour ajouter ou corriger une
entrée, modifier `tools/build_catalog.py` puis le relancer.

```bash
python -m agiopen catalog            # tout
python -m agiopen catalog nxs 540    # filtre par mots
```

Attention aux fiches DLI : elles utilisent la virgule européenne (« 2.000 µmol/s » = 2000,
« 1.050W » = 1050 W).

## Photométrie

DLI ne publie pas ses fichiers IES sur son site. Les courbes DLI du catalogue sont tirées des
fichiers du fabricant : on garde quelques plans C (0 à 90°, symétrie par quadrant) au degré près, sans
copier les fichiers du fabricant. Les plans retenus s'intègrent à 1000 lm (±0,1 %), ce qui
confirme que rien d'important n'a été perdu. P.L. Light ne publie que des fiches PDF : ses
courbes sont numérisées. `agiopen check` affiche la confiance de chaque courbe.

| Courbe | Utilisée par | Origine | Confiance |
|--------|--------------|---------|-----------|
| `dli-nxs-mw` | DLI NXS (toutes puissances) | Test photométrique DLI YP0077-1 (NXS 760W MW), 9 plans C | Élevée |
| `dli-vertex-mw` | DLI Vertex (toutes puissances) | Test DLI YP0089 (Vertex MW ; les fichiers 795W et 1050W contiennent les mêmes données), 7 plans C | Élevée |
| `dli-nxs-wd-approx` | Projets NXS spécifiés en optique WD | Batwing générique (150°, p = 2,5) calé sur un rapport AGi32 réel en optique WD : −1 % sur la moyenne | Moyenne |
| `pl-parfx-medium-wide` | ParFX Ultra Lite / Ultra / Ultra Plus | Diagramme polaire de la fiche ParFX numérisé (`tools/digitize_polar.py`) : plan large mesuré, plan étroit lu à la main | Moyenne |
| `pl-parfx-ultra-wide` | ParFX Ultra Max | Idem, optique Ultra-Wide | Moyenne |
| `lambertian` | VertiMax, BalensBeam, BudBoost, TriPlane | Cosinus (barres et panneaux sans optique secondaire) | Moyenne |

Les courbes sont normalisées : le moteur ramène le flux au PPF du luminaire. Une seule courbe
sert donc à toutes les puissances d'une même optique.

L'optique MW est nettement plus étroite que l'optique WD. Avec la MW, un seul NXS à 4 pi donne
déjà 217 µmol/m²/s sous lui. Pour un projet en WD, mettre `"photometry": "dli-nxs-wd-approx"`
jusqu'à ce que le fichier WD de DLI soit disponible.

Le plan 0 suit la longueur du luminaire (son grand côté). Pour les ParFX, le plan large est supposé dans cet axe. Si ce n'est pas le cas, tourner les luminaires avec `layout[].rotation_deg`. On peut aussi choisir l'autre optique
pour un luminaire : `"photometry": "pl-parfx-ultra-wide"`.

Format d'un fichier de courbe :

```json
{"name": "...", "source": "...", "confidence": "high", "model": "tabulated", "units": "cd/klm",
 "angles_deg": [0, 1, 2, ...], "planes": {"0": [...], "15": [...], ..., "90": [...]}}
```

`model` peut aussi être `batwing` (`beam_angle`, `batwing_power`) ou `cosine` (`cos_power`).
Avec plusieurs plans, l'intensité est interpolée linéairement en φ. Avec seulement les plans 0 et 90,
I(θ, φ) = I₀(θ) cos²φ + I₉₀(θ) sin²φ. Le tout est normalisé au flux total.

## Avant d'envoyer un rapport

Pour DLI NXS et Vertex en optique MW, les courbes du catalogue sont celles du fabricant. Pour les
autres (optique WD, P.L. Light), le fichier IES reste la référence : l'exporter d'un projet AGi32
existant ou le demander au représentant, puis mettre `"ies_file": "ies/mon_luminaire.ies"` dans le projet, en gardant `catalog` pour le reste.
Le PPF du projet a priorité sur le flux du fichier IES.
