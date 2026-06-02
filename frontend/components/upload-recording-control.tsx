"use client";

import { Upload, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { uploadMeetingRecording } from "@/lib/upload-recording-client";

export function UploadRecordingControl() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submitUpload() {
    if (!title.trim()) {
      setError("Meeting title is required.");
      setMessage(null);
      return;
    }
    if (!file) {
      setError("Choose an audio or video file.");
      setMessage(null);
      return;
    }

    const formData = new FormData();
    formData.set("title", title.trim());
    if (meetingDate) {
      formData.set("meeting_date", new Date(meetingDate).toISOString());
    }
    formData.set("file", file);

    setSaving(true);
    setMessage(null);
    setError(null);

    try {
      const result = await uploadMeetingRecording(formData);
      if (result.status === "ready") {
        router.push(`/meetings/${result.meeting.id}`);
        router.refresh();
        return;
      }
      if (result.status === "failed") {
        setError(result.job.error_message ?? "Recording transcription failed.");
        router.refresh();
        return;
      }
      setMessage("Recording uploaded. Transcription is processing.");
      router.refresh();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="relative">
      <button
        className={[
          "flex h-8 items-center gap-2 rounded-[10px] border border-line bg-white px-4",
          "text-xs font-medium text-ink transition hover:bg-[#faf9f5]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand",
          "focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:opacity-60",
        ].join(" ")}
        onClick={() => setOpen((current) => !current)}
        disabled={saving}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Upload size={13} />
        Upload recording
      </button>

      {open ? (
        <div
          role="dialog"
          aria-labelledby="upload-recording-title"
          className={[
            "absolute right-0 z-20 mt-3 w-[420px] rounded-[14px] border border-line",
            "bg-white p-4 text-left shadow-panel",
          ].join(" ")}
        >
          <div className="mb-4 flex items-start justify-between gap-3 border-b border-line pb-3">
            <div>
              <p id="upload-recording-title" className="text-sm font-semibold text-ink">
                Upload recording
              </p>
              <p className="mt-1 text-xs text-muted">
                Create a meeting from any recorded audio or video.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className={[
                "grid size-8 shrink-0 place-items-center rounded-[9px] border border-line",
                "bg-[#efefeb] text-muted transition hover:bg-white hover:text-ink",
              ].join(" ")}
              aria-label="Close upload recording form"
            >
              <X size={14} />
            </button>
          </div>

          <div className="space-y-4">
            <div className="manual-join-field">
              <label className="manual-join-label" htmlFor="upload-recording-title-input">
                Meeting title
              </label>
              <input
                id="upload-recording-title-input"
                className="manual-join-input"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Client sync recording"
              />
            </div>

            <div className="manual-join-field">
              <label className="manual-join-label" htmlFor="upload-recording-date">
                Meeting date
              </label>
              <input
                id="upload-recording-date"
                className="manual-join-input"
                type="datetime-local"
                value={meetingDate}
                onChange={(event) => setMeetingDate(event.target.value)}
              />
            </div>

            <div className="manual-join-field">
              <label className="manual-join-label" htmlFor="upload-recording-file">
                Recording file
              </label>
              <input
                id="upload-recording-file"
                className="manual-join-input"
                type="file"
                accept="audio/*,video/mp4,video/quicktime,video/webm"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </div>

            {message ? (
              <p className="rounded-[10px] bg-[#e6f4ec] p-3 text-xs text-[#2a7a4b]">
                {message}
              </p>
            ) : null}
            {error ? (
              <p className="rounded-[10px] bg-[#fff5d8] p-3 text-xs text-[#8a5d00]" role="alert">
                {error}
              </p>
            ) : null}

            <div className="flex items-center justify-end gap-2 border-t border-line pt-3">
              <button
                type="button"
                className={[
                  "flex h-9 items-center justify-center rounded-[10px] border border-line",
                  "bg-white px-3 text-xs font-medium text-ink transition hover:bg-[#faf9f5]",
                ].join(" ")}
                onClick={() => setOpen(false)}
                disabled={saving}
              >
                Cancel
              </button>
              <button
                type="button"
                className={[
                  "flex h-9 items-center justify-center gap-2 rounded-[10px] bg-brand px-3",
                  "text-xs font-medium text-white transition hover:bg-brand-dark",
                  "disabled:opacity-60",
                ].join(" ")}
                onClick={submitUpload}
                disabled={saving}
              >
                <Upload size={13} />
                {saving ? "Uploading..." : "Upload"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
