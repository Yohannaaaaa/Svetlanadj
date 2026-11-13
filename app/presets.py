"""Bibliothèque de presets : environnements, gestes DJ, mouvements de caméra,
modèles de scénario et construction des prompts.

Les prompts sont en anglais : les modèles vidéo (Kling, Veo, Runway, Seedance)
les suivent nettement mieux qu'en français.
"""
import copy

ENVIRONMENTS = {
    "festival": {
        "label": "Festival géant",
        "prompt": (
            "on a gigantic open-air festival main stage at night, colossal LED walls, "
            "dozens of red laser beams cutting through thick haze, CO2 jets, "
            "pyrotechnic flames, a massive crowd of tens of thousands with raised hands"
        ),
    },
    "club": {
        "label": "Discothèque / club",
        "prompt": (
            "in a dark underground industrial techno club, raw concrete walls, "
            "dense fog, strobe lights, red and white laser grid on the ceiling, "
            "packed sweaty dance floor right in front of the booth"
        ),
    },
    "rooftop": {
        "label": "Rooftop",
        "prompt": (
            "on a luxury rooftop at blue hour above a glittering megacity skyline, "
            "chrome DJ booth, subtle haze, red accent lights, elegant crowd dancing"
        ),
    },
    "studio": {
        "label": "Studio",
        "prompt": (
            "in a dark high-end music studio, black acoustic panels, red LED strips, "
            "moody cinematic lighting, light haze, monitors glowing"
        ),
    },
    "futuristic": {
        "label": "Scène futuriste",
        "prompt": (
            "on a futuristic cyberpunk stage made of black glass and brushed steel, "
            "holographic projections, volumetric red and ice-blue lasers, "
            "floating LED structures, dense haze, sci-fi megastructure"
        ),
    },
    "warehouse": {
        "label": "Hangar industriel (rave)",
        "prompt": (
            "in a huge abandoned industrial warehouse rave, steel beams, "
            "red stroboscopes, thick smoke, sweeping laser fans, raw industrial atmosphere"
        ),
    },
}

ACTIONS = {
    "closeup_face": {
        "label": "Gros plan visage",
        "prompt": "extreme close-up portrait of her face, she slowly opens her ice-blue eyes and looks straight into the camera, hair moving gently, subtle breathing",
    },
    "mixing": {
        "label": "Mixe aux platines",
        "prompt": "she is DJing on a Pioneer DJ CDJ-3000 and DJM-A9 mixer setup, her hands precisely turning EQ knobs and moving a channel fader, focused expression",
    },
    "riser": {
        "label": "Montée (filtre + fader)",
        "prompt": "during a tense build-up she slowly turns the filter knob on the Pioneer DJ mixer with one hand, the other hand raised, head nodding to the beat, anticipation",
    },
    "drop": {
        "label": "Drop – énergie maximale",
        "prompt": "at the drop she throws both arms up then hits the mixer, dancing powerfully to a hard 150 BPM beat, hair flying, euphoric commanding energy",
    },
    "headphones": {
        "label": "Écoute au casque",
        "prompt": "she holds one ear cup of her professional DJ headphones against her ear, cueing the next track, nodding to the beat",
    },
    "dancing": {
        "label": "Danse derrière les platines",
        "prompt": "she dances naturally behind the decks, shoulders and head moving on the beat, confident and charismatic",
    },
    "crowd_interaction": {
        "label": "Interaction public",
        "prompt": "she points at the crowd and raises her hand to hype them up, smiling, the crowd responds jumping",
    },
    "look_camera": {
        "label": "Regard caméra",
        "prompt": "she looks directly into the camera with a mysterious confident gaze, a slight smile, while keeping the rhythm",
    },
}

CAMERAS = {
    "static": {"label": "Fixe", "prompt": "locked-off static camera"},
    "push_in": {"label": "Travelling avant lent", "prompt": "slow dolly push-in toward her face"},
    "pull_out": {"label": "Travelling arrière (révélation)", "prompt": "smooth dolly pull-back revealing the DJ booth and the stage"},
    "orbit": {"label": "Orbite", "prompt": "camera slowly orbits around her in a half circle"},
    "crane_up": {"label": "Grue montante", "prompt": "crane shot rising from the decks up over the crowd"},
    "handheld": {"label": "Caméra épaule", "prompt": "energetic handheld camera, slight shake, documentary concert style"},
    "low_angle": {"label": "Contre-plongée", "prompt": "low-angle hero shot from below the booth"},
    "drone": {"label": "Drone / plan large", "prompt": "aerial drone shot sweeping over the crowd toward the stage"},
}

STYLE = (
    "cinematic music video, photorealistic, shot on ARRI Alexa 35, 35mm anamorphic lens, "
    "shallow depth of field, high dynamic range, natural skin texture, realistic anatomy, "
    "consistent face, five fingers on each hand, sharp focus, 4K"
)

NEGATIVE = (
    "cartoon, anime, 3d render, CGI look, plastic skin, deformed face, face morphing, "
    "identity change, extra fingers, missing fingers, fused fingers, deformed hands, "
    "extra limbs, distorted turntables, warped text, logo artifacts, blurry, low quality, "
    "flicker, watermark, subtitles"
)

TRANSITIONS = {
    "cut": "Cut sec",
    "fade": "Fondu",
    "fadeblack": "Fondu au noir",
    "fadewhite": "Flash blanc",
    "zoomin": "Zoom",
    "pixelize": "Glitch pixel",
    "hblur": "Flou de vitesse",
}

EFFECTS = {
    "beat_flash": "Flash sur chaque temps",
    "zoom_punch": "Zoom 'punch' sur les temps",
    "beat_cuts": "Montage cut sur les temps (drop)",
    "red_grade": "Étalonnage rouge",
    "shake": "Tremblement caméra",
    "slowmo": "Ralenti",
}

# ---------------------------------------------------------------- Scénarios
TEMPLATES = {
    "awakening": {
        "label": "SVETLANA — THE AWAKENING (15 s)",
        "title": "SVETLANA — THE AWAKENING",
        "duration": 15.0,
        "drop_at": 10.0,
        "environment": "festival",
        "logo": {"mode": "drop", "at": 10.6},
        "shots": [
            {
                "label": "Éveil – gros plan visage",
                "start": 0.0, "end": 3.0,
                "action": "closeup_face", "camera": "push_in",
                "transition_in": "fadeblack", "effects": [],
                "keyframe_prompt": (
                    "Extreme close-up portrait of this exact woman, same face, same identity, "
                    "eyes closed, very long wavy polar white-blonde hair, platinum white eyebrows, "
                    "flawless professional makeup, dark festival stage behind her with soft red haze, "
                    "cinematic rim light, photorealistic"
                ),
                "extra": "the scene is dark and quiet, a single cold rim light outlines her hair, red haze far behind",
            },
            {
                "label": "Révélation des platines",
                "start": 3.0, "end": 6.0,
                "action": "look_camera", "camera": "pull_out",
                "transition_in": "fade", "effects": [],
                "keyframe_prompt": (
                    "Medium shot of this exact woman, same face, standing behind a Pioneer DJ "
                    "CDJ-3000 and DJM-A9 booth on a huge festival stage at night, wearing professional "
                    "DJ headphones around her neck, futuristic black and metallic silver outfit, "
                    "red haze and LED walls behind, photorealistic"
                ),
                "extra": "the camera reveals the full DJ booth with glowing Pioneer DJ decks, LED walls slowly lighting up",
            },
            {
                "label": "Montée hard techno",
                "start": 6.0, "end": 10.0,
                "action": "riser", "camera": "orbit",
                "transition_in": "cut", "effects": ["shake"],
                "keyframe_prompt": (
                    "Close medium shot of this exact woman, same face, DJ headphones on one ear, "
                    "hand on the filter knob of a Pioneer DJ DJM-A9 mixer, intense focus, "
                    "red laser beams above, haze, festival stage, photorealistic"
                ),
                "extra": "lights pulse faster and faster, tension builds, smoke rising",
            },
            {
                "label": "DROP hardstyle + logo",
                "start": 10.0, "end": 15.0,
                "action": "drop", "camera": "crane_up",
                "transition_in": "fadewhite", "effects": ["beat_cuts", "zoom_punch", "beat_flash", "red_grade"],
                "keyframe_prompt": (
                    "Wide shot of this exact woman, same face, arms raised behind a Pioneer DJ booth "
                    "on a gigantic festival stage, explosion of red laser beams, CO2 jets, pyrotechnic "
                    "flames, massive crowd jumping in the foreground, photorealistic"
                ),
                "extra": "explosion of red lasers, CO2 cannons and pyro flames on the drop, the crowd jumps in unison",
            },
        ],
    },
    "club_short": {
        "label": "Club — 3 plans (10 s)",
        "title": "SVETLANA — CLUB SESSION",
        "duration": 10.0,
        "drop_at": 5.0,
        "environment": "club",
        "logo": {"mode": "drop", "at": 5.5},
        "shots": [
            {"label": "Casque", "start": 0.0, "end": 2.5, "action": "headphones", "camera": "push_in",
             "transition_in": "fadeblack", "effects": [], "keyframe_prompt": "", "extra": ""},
            {"label": "Montée", "start": 2.5, "end": 5.0, "action": "riser", "camera": "handheld",
             "transition_in": "cut", "effects": [], "keyframe_prompt": "", "extra": ""},
            {"label": "Drop", "start": 5.0, "end": 10.0, "action": "drop", "camera": "low_angle",
             "transition_in": "fadewhite", "effects": ["beat_cuts", "zoom_punch", "beat_flash"],
             "keyframe_prompt": "", "extra": ""},
        ],
    },
    "blank": {
        "label": "Vide (1 plan)",
        "title": "SVETLANA",
        "duration": 5.0,
        "drop_at": 0.0,
        "environment": "festival",
        "logo": {"mode": "watermark", "at": 0.0},
        "shots": [
            {"label": "Plan 1", "start": 0.0, "end": 5.0, "action": "mixing", "camera": "orbit",
             "transition_in": "cut", "effects": [], "keyframe_prompt": "", "extra": ""},
        ],
    },
}


def build_video_prompt(shot: dict, environment: str, identity_desc: str) -> str:
    env = ENVIRONMENTS.get(shot.get("environment") or environment, ENVIRONMENTS["festival"])
    action = ACTIONS.get(shot.get("action"), ACTIONS["mixing"])
    cam = CAMERAS.get(shot.get("camera"), CAMERAS["static"])
    parts = [
        f"{identity_desc}.",
        action["prompt"][0].upper() + action["prompt"][1:] + ",",
        env["prompt"] + ".",
    ]
    if shot.get("extra"):
        parts.append(shot["extra"].rstrip(".") + ".")
    parts.append(f"Camera: {cam['prompt']}.")
    parts.append("Keep her face identical to the reference image throughout the shot.")
    parts.append(STYLE + ".")
    return " ".join(parts)


def build_keyframe_prompt(shot: dict, environment: str, identity_desc: str) -> str:
    if shot.get("keyframe_prompt"):
        return shot["keyframe_prompt"]
    env = ENVIRONMENTS.get(shot.get("environment") or environment, ENVIRONMENTS["festival"])
    action = ACTIONS.get(shot.get("action"), ACTIONS["mixing"])
    return (
        "Photorealistic still of this exact woman, same face, same identity, "
        f"{identity_desc}, {action['prompt']}, {env['prompt']}, cinematic lighting"
    )


def instantiate_template(key: str, identity_desc: str, environment: str | None = None) -> dict:
    tpl = copy.deepcopy(TEMPLATES.get(key) or TEMPLATES["awakening"])
    env = environment or tpl["environment"]
    shots = []
    for i, s in enumerate(tpl["shots"]):
        s = dict(s)
        s["id"] = f"s{i + 1}"
        s["prompt"] = build_video_prompt(s, env, identity_desc)
        s["keyframe_prompt"] = build_keyframe_prompt(s, env, identity_desc)
        s["negative_prompt"] = NEGATIVE
        s["use_keyframe"] = True
        s["status"] = "draft"
        s["clip"] = None
        s["keyframe"] = None
        s["error"] = None
        shots.append(s)
    return {
        "title": tpl["title"],
        "template": key,
        "duration": tpl["duration"],
        "drop_at": tpl["drop_at"],
        "environment": env,
        "logo": tpl["logo"],
        "shots": shots,
    }


def catalog() -> dict:
    return {
        "environments": {k: v["label"] for k, v in ENVIRONMENTS.items()},
        "actions": {k: v["label"] for k, v in ACTIONS.items()},
        "cameras": {k: v["label"] for k, v in CAMERAS.items()},
        "transitions": TRANSITIONS,
        "effects": EFFECTS,
        "templates": {k: v["label"] for k, v in TEMPLATES.items()},
    }
