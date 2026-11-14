# SVETLANA — THE AWAKENING (15 s) · Prompts de production

Ces prompts sont déjà intégrés au scénario **« SVETLANA — THE AWAKENING »** du studio.
Ils sont aussi utilisables tels quels dans les interfaces web de Kling, Runway ou Veo/Flow
(puis bouton *Importer* sur le plan correspondant).

**Réglages** : 9:16 · Kling 2.6 Pro (image→vidéo, 5 s) · keyframes avec Nano Banana ·
musique calée pour que le **drop tombe à 10,0 s** · logo à 10,6 s.

**Identité (insérée au début de chaque prompt vidéo)** :
> SVETLANA, a glamorous mysterious female DJ, very long voluminous crimped wavy polar white-blonde hair, bleached platinum white eyebrows, luminous ice-blue eyes with long lashes, sun-kissed golden tanned skin, full glossy nude-pink lips, small nose stud, sparkling diamond drop earrings, flawless glamorous makeup, black glossy latex corset top with silver studs and draped silver chains, long black latex arm sleeves, crystal bracelets and diamond rings, long white almond nails, rhinestone-studded black DJ headphones, photorealistic

**Style (ajouté à la fin)** :
> cinematic music video, photorealistic, shot on ARRI Alexa 35, 35mm anamorphic lens, shallow depth of field, high dynamic range, natural skin texture, realistic anatomy, consistent face, five fingers on each hand, sharp focus, 4K

**Prompt négatif (tous les plans)** :
> cartoon, anime, 3d render, CGI look, plastic skin, deformed face, face morphing, identity change, extra fingers, missing fingers, fused fingers, deformed hands, extra limbs, distorted turntables, warped text, logo artifacts, blurry, low quality, flicker, watermark, subtitles

---

## Plan 1 — 0 → 3 s · Éveil (gros plan visage)

**Keyframe** (image→image à partir de la photo officielle) :
> Extreme close-up portrait of this exact woman, same face, same identity, eyes closed, very long wavy polar white-blonde hair, platinum white eyebrows, flawless professional makeup, dark festival stage behind her with soft red haze, cinematic rim light, photorealistic

**Vidéo** :
> [Identité]. Extreme close-up portrait of her face, she slowly opens her ice-blue eyes and looks straight into the camera, hair moving gently, subtle breathing, on a gigantic open-air festival main stage at night, colossal LED walls, dozens of red laser beams cutting through thick haze… the scene is dark and quiet, a single cold rim light outlines her hair, red haze far behind. Camera: slow dolly push-in toward her face. Keep her face identical to the reference image throughout the shot. [Style].

Montage : entrée en fondu depuis le noir.

## Plan 2 — 3 → 6 s · Révélation des platines

**Keyframe** :
> Medium shot of this exact woman, same face, standing behind a Pioneer DJ CDJ-3000 and DJM-A9 booth on a huge festival stage at night, wearing rhinestone-studded DJ headphones around her neck, her signature black glossy latex corset outfit with silver studs and chains, black latex arm sleeves, red haze and LED walls behind, photorealistic

**Vidéo** :
> [Identité]. She looks directly into the camera with a mysterious confident gaze, a slight smile, while keeping the rhythm, on a gigantic open-air festival main stage at night… the camera reveals the full DJ booth with glowing Pioneer DJ decks, LED walls slowly lighting up. Camera: smooth dolly pull-back revealing the DJ booth and the stage. [Style].

Montage : fondu enchaîné.

## Plan 3 — 6 → 10 s · Montée hard techno

**Keyframe** :
> Close medium shot of this exact woman, same face, rhinestone-studded DJ headphones on one ear, hand on the filter knob of a Pioneer DJ DJM-A9 mixer, intense focus, red laser beams above, haze, festival stage, photorealistic

**Vidéo** :
> [Identité]. During a tense build-up she slowly turns the filter knob on the Pioneer DJ mixer with one hand, the other hand raised, head nodding to the beat, anticipation… lights pulse faster and faster, tension builds, smoke rising. Camera: camera slowly orbits around her in a half circle. [Style].

Montage : cut sec, léger tremblement caméra.

## Plan 4 — 10 → 15 s · DROP hardstyle + logo

**Keyframe** :
> Wide shot of this exact woman, same face, in her signature black glossy latex corset outfit with silver studs and chains, black latex arm sleeves, arms raised behind a Pioneer DJ booth on a gigantic festival stage, explosion of red laser beams, CO2 jets, pyrotechnic flames, massive crowd jumping in the foreground, photorealistic

**Vidéo** :
> [Identité]. At the drop she throws both arms up then hits the mixer, dancing powerfully to a hard 150 BPM beat, hair flying, euphoric commanding energy… explosion of red lasers, CO2 cannons and pyro flames on the drop, the crowd jumps in unison. Camera: crane shot rising from the decks up over the crowd. [Style].

Montage : flash blanc sur le drop, **cuts sur chaque temps** alternant le plan 4 et des fragments
des plans précédents, zoom « punch » et flash sur chaque kick, étalonnage rouge,
**logo SVETLANA** en fondu à 10,6 s, fondu final.

---

## Conseils de génération

0. **Avant tout** : lancez le scénario *Planche d'identité* (4 images : face, 3/4, profil, plan taille
   sur fond neutre) à partir de l'avatar officiel, validez-les, puis cliquez **→ Référence** sur chacune.
   L'avatar officiel est en contre-plongée, éclairé par des lasers rouges et avec le visage incliné :
   parfait pour l'ambiance, moins pour verrouiller les traits. Des références neutres corrigent ça.

1. Générez les 4 keyframes, validez le visage sur chacune (regénérez si besoin).
2. Générez d'abord le **plan 1** (le plus exigeant pour le visage) ; si le résultat est bon, lancez les autres.
3. Pour le plan 4, une variante Veo 3.1 Fast donne souvent des lasers/foule plus spectaculaires.
4. Si les mains déforment les boutons : passez en plan plus serré sur les mains, ou baissez
   l'intensité du geste (« gently turns »).

## Modération des plateformes de génération

La tenue signature (corset latex décolleté) est **acceptée** par Kling, Veo et Runway tant que les
prompts restent descriptifs (vêtements, matières, bijoux) — c'est le cas des prompts du studio.
Évitez les mots à connotation sexuelle (« sexy », « seductive », mention du corps) : ils déclenchent
des refus ou des générations « assagies ». En cas de refus, le message d'erreur s'affiche sur le plan ;
reformulez ou utilisez un plan plus serré sur le visage et les mains.
