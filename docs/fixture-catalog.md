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

Aucun des deux fabricants ne publie de fichier IES. Les courbes du catalogue sont donc des
approximations, avec un niveau de confiance affiché par `agiopen check` :

| Courbe | Utilisée par | Origine | Confiance |
|--------|--------------|---------|-----------|
| `dli-nxs-wd` | DLI NXS | Batwing générique (150°, p = 2,5) calé sur un rapport AGi32 réel avec le NXS 540W WD : −1 % sur la moyenne | Moyenne |
| `dli-vertex` | DLI Vertex | Même optique que le NXS supposée ; aucune donnée publiée | Faible |
| `pl-parfx-medium-wide` | ParFX Ultra Lite / Ultra / Ultra Plus | Diagramme polaire de la fiche ParFX numérisé (`tools/digitize_polar.py`) : plan large mesuré, plan étroit lu à la main | Moyenne |
| `pl-parfx-ultra-wide` | ParFX Ultra Max | Idem, optique Ultra-Wide | Moyenne |
| `lambertian` | VertiMax, BalensBeam, BudBoost, TriPlane | Cosinus (barres et panneaux sans optique secondaire) | Moyenne |

Le plan large des ParFX est supposé dans l'axe de la longueur du luminaire. Si ce n'est pas le
cas, tourner les luminaires avec `layout[].rotation_deg`. On peut aussi choisir l'autre optique
pour un luminaire : `"photometry": "pl-parfx-ultra-wide"`.

Format d'un fichier de courbe :

```json
{"name": "...", "source": "...", "confidence": "medium", "model": "tabulated",
 "angles_deg": [0, 2.5, ...], "planes": {"0": [...], "90": [...]}}
```

`model` peut aussi être `batwing` (`beam_angle`, `batwing_power`) ou `cosine` (`cos_power`).
Entre les deux plans, I(θ, φ) = I₀(θ) cos²φ + I₉₀(θ) sin²φ, normalisé au flux total.

## Avant d'envoyer un rapport

Le fichier IES reste la référence. Deux façons de l'obtenir :

1. L'exporter d'un projet AGi32 existant qui utilise ce luminaire.
2. Le demander au représentant DLI ou P.L. Light.

Puis `"ies_file": "ies/mon_luminaire.ies"` dans le projet, en gardant `catalog` pour le reste.
Le PPF du projet a priorité sur le flux du fichier IES.
