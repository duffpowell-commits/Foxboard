# Prompts (exact), chaosisthemotheroforder

Copied from `docs/art-notes.md` section 6 in the private game repo. Names in
brackets are the reference images attached to each call. "you front/back" is the
protagonist (Duff) sprite (`sprites/duff/`), used as the style and pose reference
for every character. Scene prompts start with the standard preamble in
`style-anchor.md` and list props from `prop-bible.md`.

Shared sprite tail (appended to every sprite prompt below as **[TAIL]**):
> Semi-realistic painted graphic-novel comic style matching the attached images:
> thin dark ink outline slightly thicker around the whole silhouette, light
> crosshatching, realistic painted shading, light from the upper left. Full body,
> isolated on a plain flat light grey background, no ground shadow, no text, no
> weapons.

Back-view pose clause (**[BACK]**): "turned around, three-quarter back view seen
from behind and slightly to one side, same A-pose with arms angled out leaving a
clear gap from the torso, hands open and empty, legs slightly apart, feet visible."

Front pose clause (**[FRONT]**): "Three-quarter front view, A-pose with arms
angled out leaving a clear gap from the torso, hands open and empty, legs
slightly apart, feet visible."

All sprite prompts: aspect 3:4. References in brackets.

**guard_back** [guard front + you back]:
> Same character, same style as the first attached image (regime riot guard):
> [BACK] Full dark blue-grey (#1A1F2B) riot armour from behind: back of the
> full-face helmet, padded shoulders, back plate, belt, shin guards, no face or
> skin visible, no red anywhere, no insignia on the back. [TAIL]

**mara_back** [mara front + you back]:
> Same character, same style as the first attached image (Mara, woman late 30s,
> dark hair in a low bun, dark green field jacket, grey hoodie, cargo trousers,
> worn boots, canvas shoulder bag, red armband on her LEFT arm): [BACK] From
> behind: the low bun with loose strands, hood of the grey hoodie over the jacket
> collar, bag strap across her back with the bag at her hip, the red armband
> (#9E1A14) still on her left arm. [TAIL]

**kesh_back** [kesh front + you back]:
> Same character, same style as the first attached image (Kesh, wiry young man
> early 20s, messy black curls under a black beanie, dark olive bomber jacket,
> dark tee, slim dark jeans, grey high-top sneakers, red scarf/bandana at his
> neck): [BACK] From behind: curls poking out under the beanie, the red (#9E1A14)
> scarf knot visible at the back of his neck, bomber jacket back with ribbed hem. [TAIL]

**teodor_back** [teodor front + you back]:
> Same character, same style as the first attached image (Teodor, broad
> heavy-shouldered dock foreman in his 50s, dark knit cap, heavy dark canvas work
> jacket with grey reflective stripes over a grimy vest, dark work trousers,
> steel-toe boots, red rag tucked in his back pocket): [BACK] From behind: back
> of the knit cap and close-cropped grey hair, the reflective stripes across the
> jacket back, the red (#9E1A14) rag hanging clearly from his back trouser pocket. [TAIL]

**guard_defector_front** (v2, used) [guard front only]:
> Same character and same style as the attached image (regime riot guard in full
> dark blue-grey #1A1F2B riot armour with long sleeves, padded shoulders,
> armoured forearms, gloves, chest number patch, belt, knee and shin guards,
> black boots), but the DEFECTOR variant: the helmet is gone, his head is bare.
> Tired, ordinary human face: a man in his late 20s, pale, short cropped brown
> hair flattened and sweaty from the helmet, a faint pressure line on the
> forehead from the helmet rim, light stubble, dark circles under his eyes,
> uncertain exhausted expression. Armour exactly as in the attached image, fully
> covering arms and neck; NO tattoos anywhere, no bare arms, no red cloth.
> [FRONT, gloved hands] [TAIL]

**visor_operative_front** [you front + guard front]:
> Same art style as the attached images, a different character: a movement
> operative in a dark ending who has started to look like the regime. Street
> clothes: a worn dark charcoal hoodie, dark jeans, scuffed black boots, a faded
> red (#9E1A14) armband on the left upper arm, but wearing the regime's
> full-face dark blue-grey (#1A1F2B) riot helmet from the attached guard image
> with the visor DOWN and a cold blue glint (#6A8CB3) on the visor, so no face is
> visible. Unsettling mix: civilian body, faceless regime head. [FRONT] [TAIL]

**operative_a_front** (v2, used) [operative_a v1 + you front]:
> Same art style, line weight, shading and lighting as the attached image, but a
> different character: movement operative A, a woman in her late 20s, slim, mixed
> East-Asian features, short choppy dark bob haircut, small silver nose stud,
> alert determined expression, face fully visible. Street clothes in muted
> desaturated colours: a worn olive-drab canvas work jacket over a grey knit
> sweater, dark grey trousers, worn brown lace-up boots, and ONE red item: a red
> (#9E1A14) knit scarf wrapped around her neck. The scarf is the only warm
> colour. Grounded, practical, slightly grimy. [FRONT] [TAIL]

**operative_b_front** [you front]:
> Same art style, line weight, shading and lighting as the attached image, but a
> different character: movement operative B, a man in his mid 40s, stocky, dark
> brown skin, North-African features, shaved head, short black-and-grey beard,
> steady weary expression, face fully visible. Street clothes: a brown corduroy
> jacket over a dark green work shirt, grey cargo trousers, scuffed black work
> boots, and ONE red item: a red (#9E1A14) flat cap. Grounded, working-class,
> slightly grimy. [FRONT] [TAIL]

**operative_c_front** (v2, used) [operative_c v1]:
> v1: Same art style ... movement operative C, a woman in her late 50s, sturdy,
> pale weathered skin, silver-grey hair cut short, reading glasses pushed up on
> her head, wry resolute expression, face fully visible. Street clothes: a long
> dark navy-brown wool coat, unbuttoned, over a cream turtleneck, brown trousers,
> sensible dark ankle boots, and ONE red item: a red (#9E1A14) armband on her
> right upper arm over the coat sleeve. Grounded, ordinary neighbourhood elder.
> [FRONT] [TAIL]
> v2: Same character and same style as the attached image ..., identical in
> every way except the armband on her upper arm is now a PLAIN solid red
> (#9E1A14) cloth band with no symbol, no emblem, no star, no pattern. [FRONT] [TAIL]

**operative_{a,b,c}_back** [that operative's front + you back]:
> Same character, same style as the first attached image ([one-line recap of
> the front]): [BACK] From behind: [the red item and hair as seen from behind]. [TAIL]

### Portraits (1:1)

Second pass: extra emotions use the character's first cold portrait as the reference, with "same chest-up three-quarter framing ... but [EMOTION]". Where that came out too close to the reference (neutral, betrayed, resolved), the regen asked for "a clearly DIFFERENT pose" plus a gesture: Duff neutral with arms folded, looking at the viewer; Teodor betrayed pointing; Teodor resolved with a gloved hand at his collar, cranes behind. Defector: the guard_defector sprite as reference, "holding his removed full-face riot helmet against his chest in both gloved hands ... shaken, uncertain, on the edge of a decision ... No red anywhere." Warm versions are made from each cold one as before.

Cold, [that character's sprite front]:
> Chest-up portrait of the attached character ([recap]), three-quarter view,
> looking just off camera, [EMOTION]. Painterly oil style, visible brush
> strokes, dramatic single light source from the side, deep shadow on the far
> side of the face, desaturated blurred night street behind. COLD GREY version:
> cold blue-grey near-monochrome palette, regime district mood, the red [item]
> the only warm note. Documentary mood, not glamour. No text.

Emotions: Duff "tired and steady"; Mara "calm and tired, kind but hard eyes";
Kesh "alert and suspicious, shoulders slightly hunched"; Teodor "unimpressed and
watchful" (v2 used: added "deep dark brown skin", referenced v1 for composition).

Warm, [that character's cold portrait]:
> The same portrait as the attached image ([recap], same pose and composition),
> repainted as the WARM AMBER version for a liberated district: warm amber and
> sodium-orange side light on his/her face, softer glow, the blurred night
> street behind now lit with warm windows and amber streetlamps, colour
> returning. Same expression [+ small softening]. Painterly oil style, visible
> brush strokes, deep shadow on the far side of the face. Documentary mood, not
> glamour. No text.

### Woodcut (no references)

Every woodcut prompt ends with: "Thick carved black lines (#1B1714) on cream
paper (#E9E0CC), [flat red #9E1A14 | flat cold blue-grey #1A1F2B] as the only
other colour, no [blue | red]. ... Absolutely no letters, no words, no numbers,
no text. Visible wood grain and gouge marks."

- **title** (16:9, red): a lone figure in street clothes with a bandana at his
  neck standing on a rail-yard footbridge, seen from below in heroic 1930s
  protest poster composition, rail tracks and freight cars converging behind
  him, a dormitory block skyline, a single red flag-like cloth caught in the
  wind; large empty band across the top third for the in-engine title.
- **report_frame_cn24** (16:9, blue-grey): ornate cold official border; a
  stylised CRT television whose screen is a large EMPTY cream rectangle;
  broadcast antenna rays; rows of faceless helmeted riot police along the
  bottom; monumental government building at the top corners; an eye-like lens
  emblem; blank ribbon banner top and blank strip bottom for text.
- **report_frame_unbroken** (16:9, red): rough hand-carved border; battered
  valve radio and rooftop wire antenna sending jagged waves; a hand holding up a
  microphone; rail tracks and dormitory rooftops at the bottom; a red bandana
  tied to the mast; EMPTY centre rectangle and blank ribbon banner.
- **opening_dormitory_raid** (16:9, blue-grey): state-TV still of a night
  dormitory raid; helmeted faceless riot police storming a dormitory stairwell,
  a door kicked in, residents in nightclothes pushed back, searchlights from a
  police van; no weapons fired, no gore; blank band along the bottom for a caption.
- **stamp_*** (1:1, red): circular carved stamp border with a blank ring for text.
  blackmail = a hand sliding a sealed envelope across a table while another hand
  closes over cargo-manifest papers; the_lie = a handshake with crossed fingers,
  barred prison window behind; fake_radio = valve radio wearing a grinning
  theatre mask, jagged waves; killing_guards (v2, empty boots per art-needs) = a pair of empty heavy riot-police boots alone on cobblestones, laces loose, a dropped red cloth band beside them, no body, no blood, no weapons; secrecy = a heavy closed dormitory door with a chain lock, a line of light under it, a small red cloth on the handle; clean_slot = a single open empty hand, palm up, radiating carved lines, thin red ring; lay_low = a figure in a cap and bandana crouched under a dormitory
  stairwell while a searchlight passes above.
