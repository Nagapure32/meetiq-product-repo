import type { TranscriptSegment } from "@/lib/api";

const MAX_CONTEXT_LENGTH = 500;

export type MeetingTaskPrefillInput = {
  meetingSubject: string;
  summary?: string | null;
  transcriptSegments?: TranscriptSegment[];
};

export type MeetingTaskPrefill = {
  title: string;
  description: string;
};

export function buildMeetingTaskPrefill({
  meetingSubject,
  summary,
  transcriptSegments = [],
}: MeetingTaskPrefillInput): MeetingTaskPrefill {
  const context = summary?.trim() || buildTranscriptContext(transcriptSegments);

  return {
    title: `Follow up from ${meetingSubject}`,
    description: context ? `Meeting context:\n${context}` : "",
  };
}

function buildTranscriptContext(transcriptSegments: TranscriptSegment[]) {
  return transcriptSegments
    .slice(-3)
    .map((segment) => {
      const speaker = segment.speaker?.trim() || "Unknown speaker";
      return `${speaker}: ${segment.text.trim()}`;
    })
    .filter((line) => line.length > 0)
    .join("\n")
    .slice(0, MAX_CONTEXT_LENGTH);
}
