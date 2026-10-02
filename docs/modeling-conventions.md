# Conventions de modélisation

Ces conventions reproduisent la façon dont un concepteur expérimenté construit un modèle de
simulation horticole. Elles servent de valeurs par défaut quand les documents du client ne
précisent rien. Chaque valeur peut être remplacée dans le `ProjectSpec`.

## Types de site

| Type (`site.type`) | Cas typiques | Unités habituelles |
|--------------------|--------------|--------------------|
| `greenhouse` | Serre poly ou verre, gable, barrel vault, Venlo multi-pics | Impérial (poly), métrique (verre) |
| `indoor_room` | Chambre de culture cannabis, grange ou bâtiment converti, salle de recherche | Impérial |
| `vertical_rack` | Ferme verticale, propagation sur étagères, tours | Impérial |
| `container` | Ferme en conteneur | Impérial |

## Réflectances par défaut

| Surface | Réflectance | Transparence | Remarque |
|---------|-------------|--------------|----------|
| Canopée (plantes vertes) | 26 % | 0 % | Toujours la surface du plan de calcul. |
| Toit et murs de serre (verre ou poly) | 0 % | 80 % | La lumière qui traverse est perdue. |
| Poteaux et fermes, serre poly | 50 % | – | Métal galvanisé. |
| Poteaux et fermes, serre verre | 80 % | – | Peints en blanc. |
| Plancher de serre | 29 % | – | |
| Murs et plafond intérieurs blancs | 80 % | – | Chambre de culture, ferme verticale. |
| Racking blanc | 80 % | – | |
| Plancher intérieur (béton) | 20 % | – | |

## Construction du modèle

1. **Enveloppe.** Une serre ne garde que ses murs extérieurs : les chapelles intérieures sont
   ouvertes. Une chambre intérieure est une boîte fermée.
2. **Structure.** Les fermes définissent la hauteur de montage : en serre, les luminaires sont
   suspendus sous la ferme.
3. **Canopée.** Un objet vert par chapelle ou par tablette, avec un dégagement entre le mur
   extérieur et la canopée.
4. **Grille de calcul.** Posée automatiquement sur le dessus de la canopée, type PPFD, valeurs
   entières.
5. **Disposition.** On traite une chapelle comme un bloc répété (plus simple pour
   l'installateur). Dispositions usuelles : normale ou en quinconce sous la ferme ; barres de
   4 pi ou 8 pi au-dessus de chaque tablette en vertical.
6. **Itération.** On ajoute, retire ou déplace des luminaires jusqu'à atteindre le PPFD visé
   et une uniformité acceptable.

## La hauteur de la canopée bouge, le capteur non

La plupart des producteurs dirigent leur capteur vers une feuille mature, saine et bien
exposée, ce qui semble logique au départ. Mais dans les deux semaines qui suivent, cette
feuille descend d'environ 60 centimètres tandis que le capteur reste en place. Ce que l'on
croyait mesurer n'est plus là.

Conséquences pour le logiciel :

- Le PPFD d'une simulation n'est valable qu'à la hauteur du plan de calcul. Le rapport affiche
  donc toujours la ligne « Distance Between Calculation Plane and Fixture ».
- Pour les cultures hautes (high wire : tomate, concombre, poivron), `calc.extra_planes`
  permet de calculer d'autres plans (ex. dessus de canopée, -30 cm, -60 cm). On montre ainsi
  la lumière réellement reçue par les feuilles actives à mesure que la culture monte.
- Quand on compare une mesure terrain à la simulation, il faut d'abord vérifier que le capteur
  est à la hauteur du plan calculé.

## Précision attendue

Le moteur calcule la composante directe point par point à partir des fichiers IES (ou d'une
distribution générique), puis il ajoute une composante réfléchie estimée par un bilan de flux
sur les surfaces de la pièce. C'est volontairement plus simple qu'une radiosité complète. Les
écarts avec des rapports AGi32 de référence sont suivis dans `benchmarks/` et doivent rester
sous 10 % sur la moyenne.
