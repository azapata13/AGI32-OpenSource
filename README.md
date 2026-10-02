# AGI32 OpenSource

Simulation d'éclairage horticole open source. On donne les documents du client (plans, courriels,
fiches techniques), et le logiciel produit un **sommaire de simulation PDF** au même format qu'un
rapport AGi32 de designer : couverture, fiche luminaire, informations fournies, Results Summary
(PPFD moyen, max, min, uniformité, LPD), légende des réflectances, plan coté, point par point et
élévations.

Il couvre les sites qu'on rencontre en pratique : serres poly et verre (gable, barrel, Venlo
multi-pics), chambres de culture et granges converties, racking vertical et propagation,
fermes en conteneur.

```
documents du client ──intake──▶ project.json ──engine──▶ PPFD point par point ──report──▶ PDF
```

## Démarrage

```bash
pip install -e .
python -m agiopen run examples/greenhouse_poly_leafy.json -o out
```

Le PDF est nommé selon la convention habituelle :
`{Compagnie} Light Simulation - {Client} - {Projet} - {AAAA-MM-JJ}.pdf` (avec ` V2`, ` V3` pour les révisions).

Autres commandes :

| Commande | Rôle |
|----------|------|
| `python -m agiopen check project.json` | Valide le projet et liste ce qu'il faut confirmer avec le client. |
| `python -m agiopen results project.json` | Affiche les résultats en JSON, sans PDF. |
| `python -m agiopen catalog vertex 1050` | Cherche un luminaire dans le catalogue DLI / P.L. Light. |
| `python -m agiopen intake plan.pdf courriel.txt -o project.json` | Rédige un `project.json` à partir des documents du client (Claude, `ANTHROPIC_API_KEY`). |

## Exemples

| Fichier | Site | Ce qu'il montre |
|---------|------|-----------------|
| `greenhouse_poly_leafy.json` | Serre poly 30 × 102 pi, laitue | Grille de toplights sous la ferme |
| `greenhouse_glass_metric.json` | Serre verre Venlo, 11 chapelles, métrique | Gros projet (594 luminaires) |
| `indoor_flower_room.json` | Salle de floraison cannabis | Périmètre à 100 %, intérieur gradé à 75 % |
| `vertical_propagation_rack.json` | Racking 3 niveaux | Barres de 4 pi, occultation entre niveaux |
| `barn_auto_layout.json` | Grange convertie, fraises | Disposition automatique à partir d'une cible PPFD, DLI NXS 670W du catalogue |
| `greenhouse_tomato_parfx.json` | Serre verre, tomates haute tige | P.L. Light ParFX Ultra Plus du catalogue, plan supplémentaire 1 m sous la tête |

Les exemples reproduisent des projets réels, anonymisés. Un exemple de rapport généré se trouve
dans `docs/sample-report.pdf`.

## Moteur de calcul

- **Luminaires** : catalogue DLI (NXS, Vertex) et P.L. Light (ParFX, VertiMax, BalensBeam,
  BudBoost, TriPlane), 66 variantes tirées des fiches techniques. `"catalog": "<id>"` remplit
  le luminaire (voir `docs/fixture-catalog.md`).
- **Photométrie** : lecture des fichiers IES LM-63 (type C, toutes symétries). Le flux est normalisé
  sur le PPF du luminaire, donc les intensités sortent en µmol/s/sr. Sans fichier IES : courbes
  du catalogue (ParFX numérisées des fiches, NXS calé sur un rapport réel), ou distributions
  génériques `batwing` (toplights larges « WD ») et `cosine` (barres, Lambert).
- **Direct** : calcul point par point (loi en 1/d² et cosinus), avec les luminaires linéaires
  découpés en segments et l'occultation par les tablettes supérieures en racking.
- **Réfléchi** : sources-images de premier ordre sur les murs réfléchissants, plus une composante
  uniforme issue d'un bilan de flux sur les surfaces de la pièce. Le verre et le poly laissent passer
  80 % de la lumière.
- **Cultures hautes** : `calc.extra_planes` calcule des plans sous le dessus de la canopée. La
  feuille qu'on mesure descend à mesure que la culture monte, alors que le capteur reste en place
  (voir `docs/modeling-conventions.md`).

### Précision

`python benchmarks/run.py` compare le moteur à des rapports AGi32 de référence :

| Cas | Moy. réf. | Moy. moteur | Écart | Confiance dans la géométrie |
|-----|-----------|-------------|-------|------------------------------|
| Serre poly laitue | 180 | 178 | −1 % | Élevée (nombre de points identique) |
| Chambre de floraison | 1263 | 1367 | +8 % | Moyenne |
| Racking propagation | 227 | 265 | +17 % | Moyenne |
| Serre verre Venlo | 302 | 258 | −15 % | Faible |

Les écarts viennent surtout de la géométrie reconstruite et des distributions génériques. Avec le
fichier IES du fabricant (`fixtures[].ies_file`), la forme du faisceau devient exacte.

## Documentation

- `docs/report-format.md` : le format du sommaire, page par page.
- `docs/modeling-conventions.md` : réflectances, construction du modèle et hauteur de canopée.
- `docs/project-spec.md` : les champs de `project.json`.
- `docs/fixture-catalog.md` : le catalogue de luminaires et l'origine de chaque courbe photométrique.
- `schemas/project.schema.json` : le schéma JSON (régénéré par `tools/gen_schema.py`).

## Feuille de route

1. Fichiers IES réels pour le catalogue (DLI et P.L. Light ne les publient pas), puis Arize,
   Philips, Fluence…
2. Radiosité complète pour remplacer l'approximation des réflexions.
3. Import des plans DWG/DXF pour la géométrie.
4. Intake : extraction des dimensions directement sur les plans PDF, puis boucle de validation
   avec le designer.
5. Comparaison d'options dans un même rapport (pages côte à côte).

## Licence

À définir par le propriétaire du dépôt.
