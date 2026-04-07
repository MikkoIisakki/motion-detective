---
name: mobile-patterns
description: Mobile app patterns for motion-detective. Covers React Native architecture, video capture and upload, API integration, and result display. Phase 1 targets iOS.
---

# Mobile Patterns

Mobile app patterns for the motion-detective client. The mobile app captures video, uploads it to the backend API, and displays the annotated result with coach feedback.

---

## Technology Choice

**React Native (Expo managed workflow)** — recommended for this project.

Rationale:
- Single codebase for iOS and Android
- Expo simplifies camera access, video recording, and file system APIs
- TypeScript first-class
- Large ecosystem for video playback (`expo-video`, `expo-av`)
- Expo Go for rapid iteration without native builds

Alternative considered: Flutter — stronger performance but Dart adds learning curve and video processing libraries are less mature.

---

## App Architecture

```
mobile/
  app/               ← Expo Router file-based routing
    (tabs)/
      index.tsx      ← record screen (camera)
      history.tsx    ← past sessions
      settings.tsx   ← lift type selection, backend URL
    analysis/
      [sessionId].tsx ← results screen
  components/
    CameraView.tsx   ← video recording UI
    ResultVideo.tsx  ← annotated video playback
    FaultCard.tsx    ← single fault display
    ScoreGauge.tsx   ← composite score display
  services/
    api.ts           ← backend API client
    storage.ts       ← local session history (AsyncStorage)
  types/
    analysis.ts      ← shared types matching backend JSON schema
```

**Routing**: Expo Router (file-based). Navigation is a stack: Record → Analysis Result.

**State**: React state + Context for active session. No Redux — scope doesn't justify it.

---

## Video Capture

Use `expo-camera` for recording:

```typescript
import { CameraView, useCameraPermissions } from "expo-camera";

// Key constraints for good analysis:
const RECORDING_CONSTRAINTS = {
  maxDuration: 15,        // seconds — one lift attempt
  quality: "1080p",       // minimum for keypoint accuracy
  orientation: "portrait", // lifter must be fully visible
};
```

**UX requirements** (from coach domain):
- Display a guide overlay showing where the lifter should stand in frame (full body visible, side-on view preferred for snatch/clean)
- Record countdown (3-2-1) so lifter is ready before recording starts
- Auto-stop after `maxDuration`

**Camera angle guidance**: For Olympic lifts, a 45-degree side view (sagittal plane) gives the most information for first/second pull and catch analysis. Note this in the onboarding flow.

---

## Upload and Polling Pattern

Video processing is async — a 10-second video takes 20–60 seconds to process.

```typescript
// services/api.ts

export async function uploadVideo(
  videoUri: string,
  liftType: "snatch" | "clean_and_jerk",
): Promise<string> {
  const formData = new FormData();
  formData.append("video", {
    uri: videoUri,
    name: "lift.mp4",
    type: "video/mp4",
  } as unknown as Blob);
  formData.append("lift_type", liftType);

  const response = await fetch(`${API_BASE_URL}/v1/sessions`, {
    method: "POST",
    body: formData,
  });
  const { session_id } = await response.json();
  return session_id;
}

export async function pollSession(sessionId: string): Promise<AnalysisResult | null> {
  const response = await fetch(`${API_BASE_URL}/v1/sessions/${sessionId}`);
  const data = await response.json();
  if (data.status === "complete") return data.result;
  if (data.status === "failed") throw new Error(data.error);
  return null; // still processing
}
```

Poll every 3 seconds with exponential backoff. Show a progress indicator — "Analysing your lift…" with a spinner.

---

## Result Display

### Annotated Video

Stream or download the annotated video from the backend. Use `expo-video` for playback:

```typescript
import { VideoView, useVideoPlayer } from "expo-video";

const player = useVideoPlayer(annotatedVideoUrl, (p) => {
  p.loop = true;
  p.play();
});
```

Allow scrubbing — the user wants to pause on the catch position to see their elbow angle.

### Fault Cards

Display each fault as a card in priority order (most severe first):

```typescript
// types/analysis.ts
interface Fault {
  phase: string;
  joint: string;
  severity: "fault" | "warning";
  feedback: string;  // coaching cue from weightlifting-biomechanics skill
  frame_start: number;
  frame_end: number;
}
```

Tapping a fault card should seek the annotated video to `frame_start`.

### Score

Display as a gauge (0–100). Break down by phase so the lifter sees which part needs the most work.

---

## Lift Type Selection

Allow the user to select lift type before recording:
- **Snatch**
- **Clean & Jerk**

This is passed to the backend so the correct phase detection and fault thresholds are applied. Store the selection persistently — most users always do the same lift.

---

## Local Session History

Store session metadata in `AsyncStorage` (not on the backend in Phase 1):

```typescript
interface SessionRecord {
  sessionId: string;
  liftType: "snatch" | "clean_and_jerk";
  recordedAt: string;  // ISO 8601
  score: number;
  topFault: string;
}
```

In Phase 2+, sync history to the backend for trend analysis.

---

## Phase 1 Scope (iOS only)

- Record video (up to 15 seconds)
- Select lift type
- Upload to backend
- Poll for result
- Display annotated video + fault cards + score
- Local session history

**Out of scope for Phase 1**: real-time analysis, Android, sharing, social features, coaching subscriptions.
