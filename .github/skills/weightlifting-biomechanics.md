---
name: weightlifting-biomechanics
description: Olympic weightlifting domain knowledge for the coach agent. Covers snatch and clean & jerk phases, joint angle thresholds, bar path, common errors, and feedback cues.
---

# Weightlifting Biomechanics

Domain knowledge for analysing snatch and clean & jerk technique. Used by the coach agent to define factor specifications and by the engineer to implement phase detection and fault classification.

---

## Lifts Covered

- **Snatch** — bar from floor to locked out overhead in one movement
- **Clean & Jerk** — bar from floor to front rack (clean), then driven overhead (jerk)

---

## COCO Keypoints Available from YOLOv8

YOLOv8 pose provides 17 COCO keypoints. Relevant for weightlifting:

| Keypoint | Index | Used for |
|---|---|---|
| `nose` | 0 | Head position, forward lean detection |
| `left_shoulder` / `right_shoulder` | 5, 6 | Torso angle, overhead lockout |
| `left_elbow` / `right_elbow` | 7, 8 | Arm bend detection, lockout quality |
| `left_wrist` / `right_wrist` | 9, 10 | Bar path proxy (wrist ≈ hands on bar) |
| `left_hip` / `right_hip` | 11, 12 | Hip angle, phase detection |
| `left_knee` / `right_knee` | 13, 14 | Knee angle, squat depth |
| `left_ankle` / `right_ankle` | 15, 16 | Triple extension detection |

**Bar not detected by COCO** — wrist midpoint is used as bar position proxy. This is a known limitation; see `pose-estimation` skill for bar tracking options.

---

## Snatch Phases

### Phase 1: Setup (Starting Position)

**What it looks like**: Lifter stationary, bar on floor, hands in wide grip.

**Key positions**:
- Shoulders over or slightly in front of the bar
- Hips below shoulders, above knees (hip angle ~45–60° from vertical)
- Back flat — neutral lumbar, no rounding
- Arms straight, elbows rotated outward
- Weight over mid-foot

**Angle targets**:
| Joint | Target |
|---|---|
| Knee | 90–100° |
| Hip (torso-to-thigh) | 45–65° |
| Ankle | ~80° (slight dorsiflexion) |

**Detection signal**: Both feet stationary, hip height below shoulder height, wrists at ankle level.

---

### Phase 2: First Pull (Floor to Knee)

**What it looks like**: Bar lifts from floor to knee height. Controlled, not explosive.

**Key positions**:
- Back angle stays CONSTANT — hips and shoulders rise at the same rate
- Bar stays close to shins (grazes shins is correct)
- Weight shifts slightly back over mid-foot
- Knees track over toes, knees push back as bar passes

**Angle targets**:
| Joint | Target |
|---|---|
| Knee | increases from ~100° toward ~140° |
| Hip | remains ~constant or increases slightly |
| Back angle | MUST NOT change — this is the most common error |

**Common fault**: "Stripper pull" / early hip rise — hips rise before shoulders, back angle opens. Detectable as hip angle increasing faster than shoulder height.

---

### Phase 3: Transition (Knee to Hip Contact)

**What it looks like**: Knees shift backward to allow bar to pass, bar travels up the thigh toward the hip crease.

**Key positions**:
- Hips shift forward toward the bar
- Back angle increases (torso becomes more vertical, ~70–80° from horizontal)
- Knees re-bend slightly (the "double knee bend" or scoop)
- Bar maintains upward momentum

**Angle targets**:
| Joint | Target |
|---|---|
| Knee | re-bends to ~130–150° |
| Hip | increases to ~60–80° from vertical |

---

### Phase 4: Second Pull / Explosion

**What it looks like**: Explosive triple extension — ankles, knees, hips extend simultaneously. Bar contacts hip crease. Shrug at the top.

**Key positions**:
- Full extension: ankle (~105–110°), knee (~175–180°), hip (~175–180°)
- Shoulders shrug upward at peak extension
- Bar contacts hip crease — wrist midpoint should be at hip level at peak
- Feet may leave the ground momentarily

**Angle targets**:
| Joint | Target |
|---|---|
| Knee | 175–180° (full extension) |
| Hip | 175–180° (full extension) |
| Ankle | 100–110° (plantar flexion / rise on toes) |

**Common fault**: "No hip contact" — bar travels in front of hip, loses energy. Detectable as wrist trajectory not passing close to hip midpoint.

**Common fault**: "Early turnover" — arms bend and pull under before full extension. Detectable as elbow flexion before knee/hip reach 170°+.

---

### Phase 5: Third Pull / Turnover (Snatch)

**What it looks like**: Lifter actively pulls themselves under the bar by bending elbows high and wide, then punching up.

**Key positions**:
- Elbows high and to the side (not behind)
- Aggressive footwork: feet move from pulling stance to squat stance
- Arms punch overhead as lifter drops into squat

**Detection**: Rapid downward movement of hip keypoints with upward movement of wrist keypoints.

---

### Phase 6: Catch / Overhead Squat (Snatch)

**What it looks like**: Lifter in full squat, bar locked out overhead.

**Key positions**:
- Arms fully locked: elbow angle 175–180°
- Bar directly over back of neck / base of skull (directly over base of support)
- Hip crease below knee (below parallel)
- Torso as upright as possible
- Active shoulder — press the bar up, don't just hold it

**Angle targets**:
| Joint | Target | Fault threshold |
|---|---|---|
| Elbow | 175–180° | < 170° = soft lockout |
| Knee | < 90° | > 95° = above parallel |
| Shoulder (vertical) | ~180° (straight up) | < 160° = bar in front |

**Critical faults**:
- "Soft lockout" / pressed out: elbow angle < 170° — white lights may not be given
- "No squat": hip crease above parallel — no lift
- "Forward bar": bar in front of balance point — unstable, likely to miss forward

---

## Clean Phases

### Phases 1–4: Setup through Second Pull

Identical to snatch, except grip width is narrower (hip-width vs snatch's wide grip). All angle targets and faults are the same.

---

### Phase 5: Third Pull / Rack (Clean)

**What it looks like**: Lifter pulls under, elbows snap through to front rack position.

**Key positions**:
- Elbows snap through quickly — this is active and explosive, not passive
- Front rack: elbows parallel to floor (or higher), bar rests on deltoids/clavicle
- Wrists can relax (fingers only holding bar, not bearing weight)
- Front squat catch position

**Angle targets**:
| Joint | Target | Fault threshold |
|---|---|---|
| Elbow | 80–90° (high elbows) | < 70° = very high / typical; > 100° = low elbows |
| Shoulder elevation | elbows parallel to floor | elbows dropping = fault |
| Knee | < 90° (below parallel) | > 95° = above parallel |

**Common fault**: "Low elbows" / "no elbows" — elbows drop, bar rolls onto wrists/hands instead of sitting on deltoids. Detectable as wrist higher than elbow in rack.

---

## Jerk Phases

### Phase 1: Rack Position (pre-jerk)

**What it looks like**: Lifter standing, bar on shoulders in front rack, preparing to jerk.

**Key positions**:
- Same high-elbow rack as clean catch
- Feet in jerk stance (slightly wider than pulling stance, toes out)
- Torso upright, core braced

---

### Phase 2: Dip

**What it looks like**: Controlled descent by bending knees only — hips stay under bar.

**Key positions**:
- Torso stays VERTICAL — no forward lean
- Knee bend only, not hip hinge
- Dip depth: ~10–15 cm (proportional to height), not deep
- Controlled, not sinking

**Common fault**: "Forward lean in dip" — torso pitches forward, bar travels forward off shoulders. Detectable as shoulder keypoints moving in front of ankle keypoints during dip.

**Common fault**: "Soft dip" / "slow dip" — dip too slow, loses elastic energy.

---

### Phase 3: Drive

**What it looks like**: Explosive leg drive, driving bar upward from the dip.

**Key positions**:
- Rapid knee extension
- Bar drives straight up
- At top of drive, body is fully extended (similar to second pull extension)

---

### Phase 4: Split / Recovery

**What it looks like**: Lifter splits legs front-to-back and punches arms to lockout.

**Key positions**:
- Front foot: flat, shin vertical
- Back foot: on toes
- Arms fully locked: elbow 175–180°
- Bar over base of support (between feet, front-to-back)

**Common fault**: "Pressing out": arms not locked before feet land — no lift given.

---

## Angle Thresholds Summary

| Phase | Joint | Good | Warning | Fault |
|---|---|---|---|---|
| Setup | Knee | 90–100° | 80–90° or 100–115° | < 80° or > 115° |
| First pull | Back angle change | < 3° change | 3–8° change | > 8° change |
| Second pull | Knee at extension | > 170° | 160–170° | < 160° |
| Second pull | Hip at extension | > 170° | 160–170° | < 160° |
| Snatch catch | Elbow | > 175° | 170–175° | < 170° |
| Snatch catch | Squat depth | hip < knee | hip = knee | hip > knee |
| Clean rack | Elbow height | parallel to floor | 10° below | > 15° below |
| Jerk dip | Torso vertical | < 5° forward | 5–10° | > 10° |
| Jerk catch | Elbow | > 175° | 170–175° | < 170° |

---

## Feedback Cue Language

Keep feedback actionable and specific. Use coaching cue language, not anatomical descriptions.

| Fault | Feedback to show |
|---|---|
| Early hip rise | "Keep your back angle — push the floor away, don't lift your hips" |
| Soft lockout (snatch) | "Press the bar up — don't let the elbows bend" |
| Low elbows (clean) | "Snap your elbows through faster — high elbows in the rack" |
| Forward lean (jerk dip) | "Dip straight down — keep your chest up" |
| No hip contact | "Stay over the bar longer — brush your hip with the bar" |
| Above parallel catch | "Sit into the hole — pull yourself under" |
| Early arm bend | "Keep arms straight until you're fully extended" |

---

## Phase Detection Logic (for engineer)

Use the following heuristics to classify the current frame's phase:

1. **Setup**: hip keypoints stationary for > 1 second, wrist height < knee height
2. **First pull**: wrist height increasing, hip and shoulder heights increasing at similar rate, wrist height < hip height
3. **Transition**: knee angle decreasing (re-bending), hip moving forward relative to ankle
4. **Second pull**: rapid joint extension, hip angle rapidly increasing toward 180°
5. **Catch** (snatch): wrist height > shoulder height, arms approaching extension, hip dropping rapidly
6. **Rack** (clean): wrist height near shoulder height, elbow angle ~80–90°, hip dropping rapidly

Phase classification can use a sliding window of 5–10 frames to smooth noisy keypoint data.
