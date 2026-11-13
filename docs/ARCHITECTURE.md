# Architecture — SVETLANA AI DJ STUDIO

## Vue d'ensemble

```
 Navigateur (HTML/CSS/JS natif, noir · argent · rouge)
        │  fetch JSON + upload multipart (en-tête X-Studio = anti-CSRF)
        ▼
 Flask (gunicorn, 1 worker × 8 threads)  ── app/routes.py
        │
        ├── storage.py ........ projets, identité, médias sur disque (DATA_DIR)
        ├── secrets_store.py .. clés API chiffrées (Fernet, clé dérivée de APP_SECRET_KEY)
        ├── audio_analysis.py . BPM, temps, mesures, drops, énergie (NumPy + FFmpeg)
        ├── presets.py ........ environnements, gestes, caméras, scénarios, prompts
        ├── pipeline.py ....... tâches de fond (keyframes, clips, rendu) + reprise
        ├── providers/
        │     ├── demo.py ..... animatic gratuit (FFmpeg) pour tester sans payer
        │     └── fal.py ...... fal.ai : Kling, Veo, Seedance, Nano Banana, FLUX…
        ├── assembly.py ....... montage FFmpeg (cuts au BPM, transitions, logo, exports)
        └── branding.py ....... logo SVETLANA par défaut (chrome + lueur rouge)

 DATA_DIR (disque persistant Render : /var/data)
   identity/   reference_*.jpg, extra_*.jpg, logo_*.png, identity.json
   projects/<id>/  project.json, audio.wav, keyframes/, clips/, exports/
   secrets.enc     models.json (facultatif : surcharge des modèles/tarifs)
```

## Ce qui est développé ici vs. ce qui est externe (payant)

| Fonction | Où | Coût |
|---|---|---|
| Interface, gestion des projets, stockage | **Cette appli** | 0 |
| Analyse BPM / temps / drops / sections | **Cette appli** (NumPy) | 0 |
| Construction des prompts (identité + geste + caméra + lieu + style) | **Cette appli** | 0 |
| Montage synchronisé, transitions, flash/zoom sur les temps, logo, 9:16/16:9, normalisation -14 LUFS, miniature, textes | **Cette appli** (FFmpeg) | 0 |
| Animatic de test (photo animée) | **Cette appli** (FFmpeg) | 0 |
| **Images photoréalistes** de SVETLANA dans chaque scène (keyframes) | **Service externe** : Nano Banana, Seedream, FLUX Kontext (via fal.ai) | ~0,03–0,04 $/image |
| **Vidéos photoréalistes** (mouvements, mains, foule, lasers) | **Service externe** : Kling, Veo, Seedance (via fal.ai) ou Runway | ~0,07–0,40 $/s |
| Hébergement | Render (Starter + disque) | ~7 $/mois + ~2,50 $/mois pour 10 Go |

> Un programme Python seul **ne peut pas** produire une vidéo photoréaliste de SVETLANA qui mixe :
> cette partie repose sur des modèles de diffusion vidéo hébergés (GPU), facturés à la seconde.

## Flux de création d'une vidéo

1. **Identité** : photo officielle (+ références de profil / 3/4) + description visuelle + logo.
2. **Projet** : choix d'un scénario (ex. *THE AWAKENING*), du lieu, du format, du moteur.
3. **Musique** : import MP3/WAV → analyse → l'extrait est calé pour que le drop principal
   tombe exactement au moment prévu (10 s pour *THE AWAKENING*), aligné sur un 1er temps de mesure.
4. **Keyframes** (recommandé) : pour chaque plan, une image fixe photoréaliste est générée
   *à partir de la photo officielle* (modèle d'édition qui préserve le visage).
   Vous validez/regénérez les images — c'est bien moins cher que de rater une vidéo.
5. **Clips** : chaque keyframe est animée en image→vidéo (Kling 2.6 Pro par défaut).
   Vous pouvez aussi **importer** des clips générés ailleurs (application web Kling, Runway, Veo/Flow…).
6. **Montage** : FFmpeg découpe, cale sur la grille de temps, applique le montage cut sur
   les temps du drop, les flashs et zooms « punch », l'étalonnage rouge, les transitions,
   le logo, la musique normalisée, puis exporte 1080×1920 et/ou 1920×1080 + miniature + textes.

## Choix techniques

- **Flask + gunicorn (1 worker, threads)** : les tâches longues tournent dans des pools de threads
  du même processus ; l'état est écrit dans `project.json`, donc l'interface suit la progression
  par simple polling et les jobs fal.ai en cours sont **repris après un redémarrage**
  (les URLs de statut sont sauvegardées).
- **Pas de base de données** au départ : des fichiers JSON suffisent pour un seul utilisateur.
  Évolution possible : PostgreSQL (Render) + stockage objet (Cloudflare R2 / S3) + file Redis/RQ.
- **Analyse audio sans librosa** : spectral flux + autocorrélation, puis affinage conjoint
  tempo/phase sur les attaques (précision ±0,01 BPM et quelques ms sur des pistes à tempo fixe).
- **Modèles déclaratifs** (`providers/fal.py`) : endpoint, champs, durées et prix ; surchargeables
  via `DATA_DIR/models.json` quand fal.ai publie un nouveau modèle.
- **Sécurité** : mot de passe d'accès (`STUDIO_PASSWORD`), cookies HttpOnly/SameSite, en-tête
  anti-CSRF, noms de fichiers assainis, clés API chiffrées et jamais renvoyées au navigateur.

## Évolutions prévues (phase 2+)

- Entraînement d'un **LoRA SVETLANA** (20–30 images validées) pour des keyframes encore plus fidèles.
- **Contrôle du mouvement** (Kling Motion Control / Runway Act-Two) : piloter les gestes de
  SVETLANA à partir d'une vraie vidéo de DJ filmée au téléphone → gestes réellement synchronisés.
- **Lip-sync / avatar audio-driven** pour les annonces micro.
- Génération par lots (plusieurs prises par plan) et choix de la meilleure prise.
- Publication directe (API TikTok / YouTube / Instagram Graph).
- Stockage objet + CDN, multi-utilisateurs, file de tâches Redis.
