# Outils de génération : comparatif et tarifs

> ⚠️ Les tarifs changent souvent (baisse quasi mensuelle). Chiffres relevés en novembre 2026
> dans des sources publiques, **à vérifier** sur les pages officielles avant tout budget.
> Je n'ai pas pu consulter directement le site fal.ai depuis l'environnement de développement :
> les endpoints et prix fal.ai de l'application sont configurables (`DATA_DIR/models.json`).

## Vidéo (image → vidéo)

| Modèle | Accès | Prix indicatif | Points forts pour SVETLANA | Limites |
|---|---|---|---|---|
| **Kling 2.6 Pro** (défaut) | fal.ai, Kling API, app Kling | ~0,07 $/s sans audio (0,14 $/s avec) | Excellente stabilité du visage et des mains, mouvements de danse crédibles, 5 ou 10 s | Lasers/foule parfois « bouillie » en plan très large |
| Kling 2.5 Turbo Pro | fal.ai | ~0,07 $/s | Rapide, bon rapport qualité/prix | Un peu moins détaillé |
| Kling 3.x / 4.0 | fal.ai, Kling | ~0,11–0,24 $/s selon version/résolution | Qualité supérieure, références multiples | Plus cher ; vérifier les endpoints |
| **Google Veo 3.1 Fast** | fal.ai, Gemini API, Vertex AI, Flow | ~0,10 $/s (720p) – 0,12 $/s (1080p) via Google | Rendu très cinématographique, lumière/fumée/lasers superbes, 9:16 natif | Clips de 4/6/8 s ; visage parfois moins fidèle que Kling |
| Google Veo 3.1 | idem | ~0,40 $/s (1080p) | Qualité maximale | Cher |
| Veo 3.1 Lite | Gemini API | ~0,05 $/s (720p) | Brouillons pas chers | Qualité moindre |
| Runway Gen-4 Turbo | API Runway | ~0,05 $/s (5 crédits/s) | Bon outil « References » pour la cohérence de personnage | Mains/instruments moins précis |
| Runway Gen-4.5 | API Runway | ~0,12 $/s | Très bonne qualité | Intégration API séparée (non branchée en v1) |
| Seedance 1.0 Pro (ByteDance) | fal.ai | ~0,10–0,15 $/s | Mouvements dynamiques, caméra énergique | Visage parfois retouché |

**Coût de *THE AWAKENING* (15 s, 4 plans) avec Kling 2.6 Pro** : 4 clips de 5 s = 20 s × 0,07 $ ≈ **1,40 $**
+ 4 keyframes × 0,04 $ ≈ 0,16 $ → **≈ 1,60 $ par essai complet**. Comptez 3 à 5 essais par plan
pour obtenir le meilleur résultat : **5 à 8 $ pour la première vidéo finie**.
Avec Veo 3.1 Fast (4 clips de 4–6 s) : ≈ 2,50–3 $ par essai.

## Images (keyframes fidèles au visage)

| Modèle | Accès | Prix indicatif | Usage |
|---|---|---|---|
| **Nano Banana** (Gemini 2.5 Flash Image) — défaut | fal.ai, Gemini API | ~0,04 $/image | Le meilleur pour « même personne, nouvelle scène » à partir de 1 à 4 photos |
| Seedream 4 Edit | fal.ai | ~0,03 $/image | Multi-références, haute résolution |
| FLUX.1 Kontext Pro | fal.ai, BFL | ~0,04 $/image | Édition contextuelle précise |
| LoRA FLUX personnalisé | fal.ai (entraînement) | ~2–5 $ l'entraînement | Phase 2 : visage verrouillé sur des centaines d'images |

## Abonnements « interface web » (sans API)

Pour expérimenter manuellement puis **importer les clips dans le studio** (bouton *Importer*) :
Kling (≈ 10–90 $/mois), Runway (≈ 15–95 $/mois), Google AI Pro / Flow (Veo), Higgsfield, Hailuo.
C'est souvent la façon la moins chère de faire beaucoup d'essais au début.

## Pourquoi fal.ai comme premier connecteur ?

- **Une seule clé** pour Kling, Veo, Seedance, Nano Banana, FLUX… → on change de modèle en un clic.
- Paiement à l'usage, pas d'abonnement ; API « file d'attente » robuste (reprise après coupure).
- Les endpoints officiels (API Kling, Gemini/Vertex pour Veo, API Runway) pourront être ajoutés
  comme nouveaux fournisseurs dans `app/providers/` si les prix directs deviennent plus intéressants.

## Hébergement

| Service | Prix | Remarque |
|---|---|---|
| Render Starter (web service Docker) | ~7 $/mois | Toujours allumé, 512 Mo RAM — suffisant pour des vidéos de 15–60 s |
| Disque persistant Render | ~0,25 $/Go/mois | 10 Go ≈ 2,50 $/mois |
| Render Free | 0 $ | ⚠️ pas de disque : fichiers effacés à chaque mise en veille — tests uniquement |
| GitHub | gratuit | Dépôt privé |

## Sources

- fal.ai — Kling 2.6 Pro image-to-video : https://fal.ai/models/fal-ai/kling-video/v2.6/pro/image-to-video
- Comparatifs prix Kling (2026) : https://aireiter.com/blog/kling-3-api-pricing-guide-2026 · https://aireiter.com/blog/kling-4-0-api-pricing-fal-cost-vs-seedance-vidu
- Veo 3.1 / Lite (prix Gemini API) : https://the-decoder.com/googles-veo-3-1-lite-cuts-video-generation-costs-by-more-than-half/ · https://benchlm.ai/media-pricing/veo
- Runway API (crédits à 0,01 $) : https://www.activepieces.com/blog/runway-api-pricing-per-second-for-every-video-model · https://magichour.ai/blog/runway-gen-45-pricing
- Pages officielles à consulter : https://fal.ai/pricing · https://ai.google.dev/gemini-api/docs/pricing · https://docs.dev.runwayml.com · https://klingai.com
