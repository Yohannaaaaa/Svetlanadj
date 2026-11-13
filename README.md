# SVETLANA AI DJ STUDIO

Studio web pour créer les vidéos de **SVETLANA**, DJ virtuelle (hard techno, industrial,
hardstyle, rawstyle, reverse bass, 150–155 BPM) : identité visuelle constante, génération IA
des plans, synchronisation sur vos productions (Suno ou autres), montage au BPM, logo,
exports 9:16 et 16:9 prêts pour TikTok, Instagram et YouTube.

| Doc | Contenu |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture, ce qui est développé ici vs. services payants |
| [docs/OUTILS_ET_TARIFS.md](docs/OUTILS_ET_TARIFS.md) | Kling, Veo, Runway, Seedance, Nano Banana… comparatif et prix |
| [docs/COHERENCE_DU_VISAGE.md](docs/COHERENCE_DU_VISAGE.md) | Méthode pour garder exactement le même visage |
| [docs/PROMPTS_THE_AWAKENING.md](docs/PROMPTS_THE_AWAKENING.md) | Prompts plan par plan de la 1re vidéo |

## Ce que fait la v1

1. **Identité** : photo officielle + références + description + logo (PNG, ou logo chrome généré).
2. **Projets** à partir de scénarios (*SVETLANA — THE AWAKENING* 15 s, Club 10 s, vide).
3. **Musique** : import MP3/WAV/FLAC → BPM, temps, mesures, **drops** ; l'extrait est calé
   automatiquement pour que le drop tombe au bon moment de la vidéo.
4. **Plans** : geste DJ, mouvement caméra, lieu (festival, club, rooftop, studio, scène futuriste,
   hangar), transition, effets ; prompts générés automatiquement et modifiables.
5. **Génération IA** via **fal.ai** (Kling 2.6 Pro, Kling 2.5 Turbo, Veo 3.1 / Fast, Seedance)
   avec keyframes fidèles au visage (Nano Banana, Seedream, FLUX Kontext). Coût estimé affiché
   et confirmé avant chaque génération. Import manuel de clips possible (Kling/Runway/Veo web).
6. **Mode démo gratuit** : anime la photo avec FFmpeg pour tester tout le pipeline sans payer.
7. **Montage FFmpeg** : cuts sur les temps pendant le drop, flash et zoom « punch » sur les kicks,
   étalonnage rouge, transitions (fondu, flash blanc, zoom, glitch…), logo au drop ou en filigrane,
   musique normalisée −14 LUFS.
8. **Exports** 1080×1920 et 1920×1080 (H.264 + AAC 320k, faststart), miniature et textes/hashtags.

> Les vidéos photoréalistes sont produites par des **services externes payants** (GPU).
> L'application orchestre, synchronise et monte : elle ne « fabrique » pas seule le photoréalisme.

## Démarrage local

Prérequis : Python 3.11+ et **FFmpeg** (`brew install ffmpeg`, `sudo apt install ffmpeg`,
ou `winget install ffmpeg`).

```bash
git clone https://github.com/<vous>/svetlanadj.git
cd svetlanadj
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # puis éditez les valeurs
export $(grep -v '^#' .env | xargs)                    # Windows : définissez les variables à la main
python wsgi.py
```

Ouvrez http://localhost:5000, puis :

1. **Identité** → importez la photo officielle de SVETLANA.
2. **Projets** → *SVETLANA — THE AWAKENING* → moteur **Démo** → Créer.
3. **Musique** → importez votre morceau → vérifiez le cadre blanc (extrait) et le trait rouge (drop).
4. **Générer toutes les keyframes** puis **Générer tous les clips** → **Monter & exporter**.

Vous obtenez un premier montage animé gratuit. Passez ensuite au moteur **fal.ai** pour la version photoréaliste.

## Clés API (uniquement quand vous passez au photoréalisme)

Une seule clé est nécessaire pour commencer : **fal.ai** (https://fal.ai → Dashboard → Keys, ajoutez
quelques dollars de crédit). Deux façons de la fournir :

- **Recommandé (Render)** : variable d'environnement `FAL_KEY` dans le tableau de bord Render.
- **Depuis l'interface** : *Réglages → Clés API*. La clé est chiffrée (Fernet/AES) avec
  `APP_SECRET_KEY` dans `DATA_DIR/secrets.enc` et n'est jamais renvoyée au navigateur.

Ne collez jamais une clé dans le code, dans GitHub ni dans un chat.

## Déploiement sur Render

1. Poussez ce dépôt sur GitHub (privé conseillé).
2. Render → **New → Blueprint** → choisissez le dépôt : `render.yaml` crée le service Docker
   (FFmpeg inclus), le **disque persistant** de 10 Go monté sur `/var/data` et génère `APP_SECRET_KEY`.
3. Renseignez `STUDIO_PASSWORD` (obligatoire : protège vos crédits) et éventuellement `FAL_KEY`.
4. Déployez, ouvrez l'URL `https://svetlana-ai-dj-studio.onrender.com`, connectez-vous.

Le plan **Starter** (~7 $/mois) + disque (~2,50 $/mois) est nécessaire : sur le plan gratuit,
les fichiers (photos, clips, exports) sont effacés à chaque redémarrage.

Variables disponibles :

| Variable | Rôle | Défaut |
|---|---|---|
| `APP_SECRET_KEY` | Sessions + chiffrement des clés API | (aléatoire temporaire) |
| `STUDIO_PASSWORD` | Mot de passe du studio | aucun (accès libre ⚠️) |
| `FAL_KEY` | Clé fal.ai | — |
| `DATA_DIR` | Dossier de données | `./data` |
| `DEFAULT_PROVIDER` | `demo` ou `fal` | `demo` |
| `GENERATION_TIMEOUT` | Attente max d'un clip (s) | `1200` |
| `MAX_UPLOAD_MB` | Taille max d'upload | `200` |

## Mettre à jour les modèles / tarifs sans toucher au code

Les fournisseurs publient de nouveaux modèles chaque mois. Créez `DATA_DIR/models.json` :

```json
{
  "video": {
    "kling-2.6-pro": { "price_per_second": 0.07 },
    "kling-3-pro": {
      "label": "Kling 3 Pro – image→vidéo",
      "endpoint": "fal-ai/kling-video/v3/pro/image-to-video",
      "image_field": "image_url",
      "durations": [5, 10],
      "duration_format": "{d}",
      "negative_field": "negative_prompt",
      "params": {},
      "price_per_second": 0.112,
      "output": "video.url"
    }
  }
}
```

Le nom exact de l'endpoint et des paramètres figure sur la page du modèle sur fal.ai (onglet *API*).

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

Les tests génèrent une piste hard techno synthétique (vérification du BPM et du drop),
exécutent tout le pipeline en mode démo jusqu'aux exports 9:16 et 16:9, et vérifient l'authentification,
la protection CSRF et le chiffrement des clés.

## Structure

```
app/
  __init__.py        création de l'app Flask
  config.py          configuration (variables d'environnement)
  routes.py          pages + API JSON + médias
  storage.py         projets / identité sur disque
  secrets_store.py   clés API chiffrées
  audio_analysis.py  BPM, temps, drops
  presets.py         lieux, gestes, caméras, scénarios, prompts
  pipeline.py        tâches de fond (keyframes, clips, rendu)
  assembly.py        montage FFmpeg
  branding.py        logo par défaut
  providers/         demo.py (gratuit), fal.py (Kling, Veo, Seedance, Nano Banana…)
  templates/, static/  interface
docs/                architecture, tarifs, cohérence du visage, prompts
tests/               tests automatisés
Dockerfile, render.yaml, requirements.txt
```

## Feuille de route

- **v1 (ici)** : première vidéo *THE AWAKENING*, démo gratuite + fal.ai, montage au BPM, exports.
- **v2** : plusieurs prises par plan en un clic, LoRA SVETLANA, contrôle de mouvement (gestes réels
  filmés → SVETLANA), Runway / API Kling / Gemini en direct, scénarios plus longs (30–60 s).
- **v3** : publication directe TikTok / YouTube / Instagram, stockage objet, file de tâches.
