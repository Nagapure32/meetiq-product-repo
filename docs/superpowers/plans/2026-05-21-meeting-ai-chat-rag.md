# Meeting AI Chat RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add meeting-scoped AI chat over Supabase transcript segments using Azure AI Search and Azure OpenAI.

**Architecture:** The .NET bot continues to write transcript segments to FastAPI/Supabase. FastAPI chunks those segments, pushes embeddings-backed documents into Azure AI Search, retrieves chunks filtered by `meeting_id` and `user_id`, asks Azure OpenAI for an answer, and stores chat history in Supabase. The frontend exposes the chat from both the meeting detail page and `/ai-chat`.

**Tech Stack:** FastAPI, Supabase REST, Azure AI Search REST API, Azure OpenAI REST API, Next.js, React, Tailwind CSS.

---

### Task 1: Backend RAG Service

**Files:**
- Create: `backend/app/services/meeting_chat.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/v1/schemas.py`
- Modify: `backend/app/api/v1/routes/meetings.py`
- Test: `backend/tests/test_meeting_chat_service.py`

- [x] Write tests for meeting-scoped indexing, chat history persistence, and ownership checks.
- [x] Add Azure AI Search and embedding configuration.
- [x] Add service functions for indexing, index status, chat history, and chat response generation.
- [x] Add meeting chat endpoints under `/api/v1/meetings/{meeting_id}/chat`.
- [x] Verify Python syntax with `python -m compileall app`.

### Task 2: Supabase Schema

**Files:**
- Create: `backend/supabase/005_meeting_ai_chat.sql`
- Modify: `.env.example`

- [x] Add `meeting_id` to `ai_chat_messages`.
- [x] Add `meeting_ai_indexes` for per-meeting index status.
- [x] Add indexes and RLS read policies.
- [x] Document required Azure AI Search and embedding environment variables.

### Task 3: Frontend Chat UI

**Files:**
- Modify: `frontend/lib/api.ts`
- Create: `frontend/app/meetings/[id]/meeting-chat-panel.tsx`
- Create: `frontend/app/meetings/[id]/meeting-transcript-tabs.tsx`
- Modify: `frontend/app/meetings/[id]/page.tsx`
- Create: `frontend/app/ai-chat/ai-chat-workspace.tsx`
- Modify: `frontend/app/ai-chat/page.tsx`

- [x] Add API helpers for chat messages, index status, indexing, and asking questions.
- [x] Add a transcript/AI chat toggle to the meeting detail page.
- [x] Add searchable meeting selection to `/ai-chat`.
- [x] Verify frontend build with `npm run build`.
