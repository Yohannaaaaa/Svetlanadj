# Garder exactement le même visage dans toutes les images et vidéos

Aucun modèle vidéo ne « connaît » SVETLANA. La cohérence s'obtient par une **chaîne de contrôle**,
où chaque étape part d'images déjà validées. C'est ce que fait le studio.

## 1. Une photo officielle impeccable (fondation)

- De face, regard caméra, visage occupant ~40 % de l'image, **haute résolution** (≥ 1024 px).
- Lumière douce et neutre (pas de lasers colorés sur la peau), pas de mèches sur les yeux.
- Expression neutre ou léger sourire. Les traits signature bien visibles : yeux bleu glacier,
  sourcils platine, cheveux blond blanc polaire.
- Ajoutez 2 à 5 **références complémentaires** (profil gauche/droit, 3/4, plan taille avec la tenue)
  dans *Identité* : les modèles multi-images (Nano Banana, Seedream) s'en servent.

## 2. Keyframe d'abord, vidéo ensuite (le plus important)

Ne demandez jamais à un modèle vidéo d'*inventer* SVETLANA à partir de texte.

1. **Image → image** : on génère l'image de départ de chaque plan en *éditant* la photo
   officielle (« this exact woman, same face… on a festival stage… »). Les modèles d'édition
   (Nano Banana, Seedream, FLUX Kontext) préservent très bien l'identité.
2. **Vous validez** la keyframe (regénérez si le visage dérive : ~0,04 $).
3. **Image → vidéo** : le modèle vidéo anime cette image. La 1re image de la vidéo est votre
   keyframe : le visage de départ est donc garanti ; il suffit qu'il ne dérive pas pendant 5 s.

## 3. Limiter la dérive pendant le clip

- **Clips courts** (5 s, ou 4–6 s avec Veo) : la dérive augmente avec la durée.
- **Plans serrés ou moyens** pour les moments « visage » ; en plan très large, le visage
  fait peu de pixels et se déforme plus facilement.
- **Mouvements modérés** dans les plans visage (push-in, regard caméra) ; garder l'énergie
  maximale (cheveux qui volent, bras levés) pour les plans plus larges du drop, montés en cuts rapides.
- Le prompt négatif du studio interdit : *face morphing, identity change, deformed hands, extra fingers…*
- Le prompt contient toujours la même **description d'identité** (onglet *Identité*) : vocabulaire constant.
- Kling 2.6 Pro est actuellement le plus stable sur les visages et les mains ; Veo 3.1 pour les plans
  d'ambiance (foule, lasers, pyrotechnie) où le visage est petit.

## 4. Le montage aide aussi

- Les cuts sur les temps (drop) raccourcissent chaque fragment : une légère dérive n'a pas le temps d'être visible.
- Si une prise a un défaut au bout de 3 s, ne gardez que le début (le plan ne dure que 3–4 s dans la timeline).
- Gardez plusieurs **prises** par plan (le studio les conserve) et choisissez la meilleure.

## 5. Phase 2 : verrouillage avancé

| Technique | Quand | Coût |
|---|---|---|
| **LoRA SVETLANA** (FLUX, 20–30 images validées) | Quand vous avez une banque d'images cohérentes | ~2–5 $ une fois |
| Références multi-images Kling (« Elements ») / Runway References / Veo « ingredients » | Plans où SVETLANA doit apparaître sans keyframe | inclus dans le prix vidéo |
| **Face swap / restauration** en post (FaceFusion, etc.) sur les rares plans ratés | Correction ponctuelle | gratuit (GPU local) ou quelques centimes |
| **Motion control** (Kling Motion Control, Runway Act-Two) : une vraie personne filme les gestes de mix, le modèle les applique à SVETLANA | Pour des gestes de DJ parfaitement crédibles et calés sur la musique | ~0,05–0,10 $/s |

> Le face swap ne doit être utilisé que sur **votre propre personnage** (SVETLANA), jamais
> pour reproduire le visage d'une personne réelle sans son consentement.

## Transparence

Indiquez que SVETLANA est une artiste virtuelle générée par IA et activez les étiquettes
« contenu IA » de TikTok, Instagram et YouTube : c'est exigé par leurs règles et cela renforce
le concept (comme les autres DJ virtuelles).
