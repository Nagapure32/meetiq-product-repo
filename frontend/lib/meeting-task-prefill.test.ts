import type { TranscriptSegment } from "@/lib/api";
import { buildMeetingTaskPrefill } from "@/lib/meeting-task-prefill";

const transcriptSegments: TranscriptSegment[] = [
  {
    id: "segment-1",
    speaker: "Asha",
    text: "Please send the pricing notes to the client.",
    created_at: "2026-05-20T10:00:00Z",
  },
];

const prefill = buildMeetingTaskPrefill({
  meetingSubject: "Roadmap sync",
  summary: "The team agreed to send pricing notes after the call.",
  transcriptSegments,
});

const typedTitle: string = prefill.title;
const typedDescription: string = prefill.description;

void typedTitle;
void typedDescription;
