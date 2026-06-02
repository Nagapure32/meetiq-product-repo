"use client";

import { Link2, Plus, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import type { Meeting } from "@/lib/api";
import { manualJoinMeeting } from "@/lib/api";

type Props = {
  meetings: Meeting[];
};

export function ManualJoinControl({ meetings }: Props) {
  const router = useRouter();
  const joinableMeetings = useMemo(
    () => meetings.filter((meeting) => meeting.join_url),
    [meetings],
  );
  const [open, setOpen] = useState(false);
  const [meetingId, setMeetingId] = useState(joinableMeetings[0]?.id ?? "");
  const [meetingIdentifier, setMeetingIdentifier] = useState("");
  const [passcode, setPasscode] = useState("");
  const [useServiceHostedMedia, setUseServiceHostedMedia] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submitManualJoin() {
    const identifier = meetingIdentifier.trim();
    const hasExistingMeeting = Boolean(meetingId);
    if (!hasExistingMeeting && !identifier) {
      setMessage(null);
      setError("Select an existing meeting or enter a meeting URL or ID.");
      return;
    }

    setSaving(true);
    setMessage(null);
    setError(null);

    try {
      const identifierIsUrl = /^https?:\/\//i.test(identifier);
      const result = await manualJoinMeeting({
        meeting_id: meetingId || null,
        join_web_url: identifierIsUrl ? identifier : null,
        join_meeting_id: !identifierIsUrl && identifier ? identifier : null,
        passcode: passcode.trim() || null,
        use_service_hosted_media: useServiceHostedMedia,
      });
      setMessage(result.message || "Manual join request accepted.");
      router.refresh();
    } catch (joinError) {
      setError(joinError instanceof Error ? joinError.message : "Manual join failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="relative">
      <button
        className="flex h-8 items-center gap-2 rounded-[10px] bg-brand px-4 text-xs font-medium text-white transition hover:bg-brand-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:opacity-60"
        onClick={() => setOpen((current) => !current)}
        disabled={saving}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Link2 size={13} />
        Join meeting
      </button>

      {open ? (
        <div
          role="dialog"
          aria-labelledby="manual-join-title"
          className="absolute right-0 z-20 mt-3 w-[380px] rounded-[14px] border border-line bg-white p-4 text-left shadow-panel"
        >
          <div className="mb-4 flex items-start justify-between gap-3 border-b border-line pb-3">
            <div>
              <p id="manual-join-title" className="text-sm font-semibold text-ink">
                Join meeting
              </p>
              <p className="mt-1 text-xs text-muted">Send a Teams meeting request to the bot.</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="grid size-8 shrink-0 place-items-center rounded-[9px] border border-line bg-[#efefeb] text-muted transition hover:bg-white hover:text-ink"
              aria-label="Close join meeting form"
            >
              <X size={14} />
            </button>
          </div>

          <div className="space-y-4">
            <div className="manual-join-field">
              <label className="manual-join-label" htmlFor="manual-join-existing-meeting">
                Existing meeting
              </label>
              <span id="manual-join-existing-help" className="manual-join-help">
                Choose a synced meeting, or leave this empty and paste details below.
              </span>
              <select
                id="manual-join-existing-meeting"
                className="manual-join-input"
                value={meetingId}
                onChange={(event) => setMeetingId(event.target.value)}
                aria-describedby="manual-join-existing-help"
              >
                <option value="">Paste details manually</option>
                {joinableMeetings.map((meeting) => (
                  <option key={meeting.id} value={meeting.id}>
                    {meeting.subject}
                  </option>
                ))}
              </select>
            </div>

            <div className="manual-join-field">
              <label className="manual-join-label" htmlFor="manual-join-identifier">
                Meeting URL or ID
              </label>
              <span id="manual-join-identifier-help" className="manual-join-help">
                Use this when the meeting is not listed above.
              </span>
              <input
                id="manual-join-identifier"
                className="manual-join-input"
                value={meetingIdentifier}
                onChange={(event) => setMeetingIdentifier(event.target.value)}
                placeholder="Paste Teams link or enter meeting ID"
                aria-describedby="manual-join-identifier-help"
                aria-invalid={Boolean(error && !meetingId && !meetingIdentifier.trim())}
              />
            </div>

            <div className="manual-join-field">
              <label className="manual-join-label" htmlFor="manual-join-passcode">
                Passcode <span className="text-[#8a8f98]">(optional)</span>
              </label>
              <span id="manual-join-passcode-help" className="manual-join-help">
                Leave blank when the invite does not include a passcode.
              </span>
              <input
                id="manual-join-passcode"
                className="manual-join-input"
                value={passcode}
                onChange={(event) => setPasscode(event.target.value)}
                placeholder="Required only if the meeting asks for one"
                aria-describedby="manual-join-passcode-help"
              />
            </div>

            <label className="flex items-center gap-2 rounded-[10px] border border-line bg-[#faf9f5] px-3 py-2 text-xs text-muted">
              <input
                type="checkbox"
                checked={useServiceHostedMedia}
                onChange={(event) => setUseServiceHostedMedia(event.target.checked)}
              />
              Use service-hosted media
            </label>

            {message ? <p className="rounded-[10px] bg-[#e6f4ec] p-3 text-xs text-[#2a7a4b]">{message}</p> : null}
            {error ? (
              <p className="rounded-[10px] bg-[#fff5d8] p-3 text-xs text-[#8a5d00]" role="alert">
                {error}
              </p>
            ) : null}

            <div className="flex items-center justify-end gap-2 border-t border-line pt-3">
              <button
                type="button"
                className="flex h-9 items-center justify-center rounded-[10px] border border-line bg-white px-3 text-xs font-medium text-ink transition hover:bg-[#faf9f5]"
                onClick={() => setOpen(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="button"
                className="flex h-9 items-center justify-center gap-2 rounded-[10px] bg-brand px-3 text-xs font-medium text-white transition hover:bg-brand-dark disabled:opacity-60"
                onClick={submitManualJoin}
                disabled={saving}
              >
                <Plus size={13} />
                {saving ? "Sending..." : "Send to bot"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
