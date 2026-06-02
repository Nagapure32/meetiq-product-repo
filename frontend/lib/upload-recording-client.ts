"use client";

import { supabaseBrowserClient } from "@/lib/supabase/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type UploadedRecordingResult = {
  status: "processing" | "ready" | "failed";
  meeting: {
    id: string;
  };
  job: {
    error_message?: string | null;
  };
};

export async function uploadMeetingRecording(formData: FormData): Promise<UploadedRecordingResult> {
  const {
    data: { session },
  } = await supabaseBrowserClient.auth.getSession();

  const headers = new Headers();
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/meetings/uploads`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Meeting upload failed: ${response.status}`);
  }

  return response.json();
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const data = await response.json();
    return typeof data.detail === "string" ? data.detail : null;
  } catch {
    return null;
  }
}
