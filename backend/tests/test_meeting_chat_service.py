import asyncio

import pytest
from fastapi import HTTPException


class FakeSupabaseGateway:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {
            "meetings": [],
            "transcript_segments": [],
            "ai_chat_messages": [],
            "meeting_ai_indexes": [],
        }

    async def get(self, path: str, params: dict | None = None) -> list[dict]:
        rows = [row.copy() for row in self.tables[path]]
        if not params:
            return rows

        for key, value in params.items():
            if key in {"select", "order", "limit"}:
                continue
            if isinstance(value, str) and value.startswith("eq."):
                expected = value[3:]
                rows = [row for row in rows if str(row.get(key)) == expected]

        if params.get("limit"):
            rows = rows[: int(params["limit"])]
        return rows

    async def insert(self, path: str, payload: dict | list[dict]) -> list[dict]:
        payloads = payload if isinstance(payload, list) else [payload]
        rows = []
        for item in payloads:
            row = item.copy()
            row.setdefault("id", f"{path}-{len(self.tables[path]) + 1}")
            self.tables[path].append(row)
            rows.append(row.copy())
        return rows

    async def upsert(
        self,
        path: str,
        payload: dict,
        on_conflict: str | None = None,
    ) -> list[dict]:
        if on_conflict:
            existing = [
                row for row in self.tables[path] if row.get(on_conflict) == payload.get(on_conflict)
            ]
            if existing:
                existing[0].update(payload)
                return [existing[0].copy()]
        return await self.insert(path, payload)


class FakeSearchClient:
    def __init__(self) -> None:
        self.uploaded_documents: list[dict] = []
        self.search_calls: list[dict] = []
        self.results: list[dict] = []

    async def upload_documents(self, documents: list[dict]) -> None:
        self.uploaded_documents.extend(documents)

    async def search_meeting_chunks(
        self,
        *,
        meeting_id: str,
        user_id: str,
        query: str,
        top: int,
    ) -> list[dict]:
        self.search_calls.append(
            {
                "meeting_id": meeting_id,
                "user_id": user_id,
                "query": query,
                "top": top,
            }
        )
        return self.results


def run(coro):
    return asyncio.run(coro)


def test_index_meeting_transcript_uploads_meeting_scoped_chunks(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Launch sync",
        }
    ]
    fake_db.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "meeting_id": "meeting-1",
            "speaker": "Asha",
            "text": "The launch stays on Friday.",
            "created_at": "2026-05-20T10:00:00Z",
        },
        {
            "id": "segment-2",
            "meeting_id": "meeting-1",
            "speaker": "Ravi",
            "text": "Ravi will send the customer email.",
            "created_at": "2026-05-20T10:01:00Z",
        },
    ]
    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)

    result = run(meeting_chat.index_meeting_transcript("meeting-1"))

    assert result["status"] == "ready"
    assert result["indexed_chunk_count"] == 1
    assert fake_search.uploaded_documents[0]["meeting_id"] == "meeting-1"
    assert fake_search.uploaded_documents[0]["user_id"] == "user-1"
    assert fake_search.uploaded_documents[0]["source_segment_ids"] == ["segment-1", "segment-2"]
    assert fake_db.tables["meeting_ai_indexes"][0]["status"] == "ready"


def test_ensure_index_does_not_update_existing_search_index():
    from app.services import meeting_chat

    class ExistingIndexSearchClient(meeting_chat.AzureMeetingSearchClient):
        def __init__(self) -> None:
            self.put_payloads: list[dict] = []

        async def _get_search(self, path: str) -> dict | None:
            return {"name": "meeting-transcript-chunks"}

        async def _put_search(self, path: str, payload: dict) -> dict:
            self.put_payloads.append(payload)
            return payload

    fake_search = ExistingIndexSearchClient()

    run(fake_search._ensure_index())

    assert fake_search.put_payloads == []


def test_embed_texts_requests_configured_embedding_dimensions(monkeypatch):
    from app.services import meeting_chat

    class FakeResponse:
        status_code = 200
        text = "{}"

        def json(self) -> dict:
            return {"data": [{"index": 0, "embedding": [0.0] * 1536}]}

    class FakeAsyncClient:
        last_json: dict | None = None

        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            pass

        async def post(self, url: str, headers: dict, json: dict) -> FakeResponse:
            FakeAsyncClient.last_json = json
            return FakeResponse()

    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(meeting_chat.settings, "azure_openai_embedding_dimensions", 1536)
    monkeypatch.setattr(meeting_chat.httpx, "AsyncClient", FakeAsyncClient)

    result = run(meeting_chat.AzureMeetingSearchClient()._embed_texts(["hello"]))

    assert FakeAsyncClient.last_json == {"input": ["hello"], "dimensions": 1536}
    assert len(result[0]) == 1536


def test_parse_chat_route_accepts_agent_json():
    from app.services import meeting_chat

    route = meeting_chat._parse_chat_route(
        """
        {
          "intent": "person_task",
          "retrieval": "person_focused",
          "person": "Shweta Nagpure",
          "normalized_question": "Which tasks were assigned to Shweta?"
        }
        """,
        "which task are assign to shweta",
    )

    assert route.intent == "person_task"
    assert route.retrieval == "person_focused"
    assert route.person == "Shweta Nagpure"
    assert route.normalized_question == "Which tasks were assigned to Shweta?"


def test_parse_chat_route_falls_back_to_semantic_search_on_invalid_json():
    from app.services import meeting_chat

    route = meeting_chat._parse_chat_route("not json", "what is launch date")

    assert route.intent == "specific_fact"
    assert route.retrieval == "semantic_search"
    assert route.person is None
    assert route.normalized_question == "what is launch date"


def test_chat_with_meeting_transcript_saves_history_and_sources(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Launch sync",
        }
    ]
    fake_search.results = [
        {
            "id": "meeting-1-000",
            "meeting_id": "meeting-1",
            "chunk_text": "Asha: The launch stays on Friday.",
            "speaker": "Asha",
            "source_segment_ids": ["segment-1"],
            "started_at": "2026-05-20T10:00:00Z",
            "ended_at": "2026-05-20T10:00:00Z",
        }
    ]
    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="specific_fact",
            retrieval="semantic_search",
            person=None,
            normalized_question=question,
        ),
    )
    monkeypatch.setattr(
        meeting_chat,
        "_run_chat_completion",
        lambda meeting, question, sources: "The launch stays on Friday.",
    )

    result = run(meeting_chat.chat_with_meeting_transcript("meeting-1", "When is launch?"))

    assert result["answer"] == "The launch stays on Friday."
    assert fake_search.search_calls[0]["meeting_id"] == "meeting-1"
    assert fake_search.search_calls[0]["user_id"] == "user-1"
    assert fake_db.tables["ai_chat_messages"][0]["role"] == "user"
    assert fake_db.tables["ai_chat_messages"][0]["meeting_id"] == "meeting-1"
    assert fake_db.tables["ai_chat_messages"][1]["role"] == "assistant"
    assert fake_db.tables["ai_chat_messages"][1]["sources"] == []
    assert result["sources"] == []


def test_broad_meeting_question_uses_meeting_wide_transcript_context(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    captured_sources: list[dict] = []
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Bot platform demo",
        }
    ]
    fake_db.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "meeting_id": "meeting-1",
            "speaker": "Dilbagh Dhindsa",
            "text": "Today we will review the bot platform demo and understand its features.",
            "created_at": "2026-05-20T05:30:00Z",
        },
        {
            "id": "segment-2",
            "meeting_id": "meeting-1",
            "speaker": "Shweta Nagpure",
            "text": "I completed the AI chat system for individual meeting transcripts.",
            "created_at": "2026-05-20T05:41:00Z",
        },
        {
            "id": "segment-3",
            "meeting_id": "meeting-1",
            "speaker": "Simant Asawale",
            "text": "I can create the plan for the codex session that we are going to take.",
            "created_at": "2026-05-20T05:42:00Z",
        },
    ]
    fake_search.results = [
        {
            "id": "meeting-1-000",
            "meeting_id": "meeting-1",
            "chunk_text": "Only one narrow retrieved chunk.",
            "speaker": "Dilbagh Dhindsa",
            "source_segment_ids": ["segment-1"],
            "started_at": "2026-05-20T05:30:00Z",
            "ended_at": "2026-05-20T05:30:00Z",
        }
    ]

    def capture_sources(_meeting, _question, sources):
        captured_sources.extend(sources)
        return "The meeting agenda was to review the bot platform demo and related AI work."

    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="agenda",
            retrieval="meeting_wide",
            person=None,
            normalized_question="What was the agenda of this meeting?",
        ),
    )
    monkeypatch.setattr(meeting_chat, "_run_chat_completion", capture_sources)

    result = run(meeting_chat.chat_with_meeting_transcript("meeting-1", "what was agenda"))

    assert "review the bot platform demo" in captured_sources[0]["chunk_text"]
    assert "AI chat system" in captured_sources[0]["chunk_text"]
    assert "codex session" in captured_sources[0]["chunk_text"]
    assert result["sources"] == []


def test_task_question_uses_meeting_wide_transcript_context(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    captured_sources: list[dict] = []
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Task sync",
        }
    ]
    fake_db.tables["transcript_segments"] = [
        {
            "id": "segment-1",
            "meeting_id": "meeting-1",
            "speaker": "Shweta Nagpure",
            "text": "I am working on task assigning through email services.",
            "created_at": "2026-05-20T05:41:00Z",
        },
        {
            "id": "segment-2",
            "meeting_id": "meeting-1",
            "speaker": "Dilbagh Dhindsa",
            "text": "Please continue that and complete the integration.",
            "created_at": "2026-05-20T05:42:00Z",
        },
    ]

    def capture_sources(_meeting, _question, sources):
        captured_sources.extend(sources)
        return "Shweta's task was to work on task assignment through email services."

    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="person_task",
            retrieval="person_focused",
            person="Shweta Nagpure",
            normalized_question="Which tasks were assigned to Shweta?",
        ),
    )
    monkeypatch.setattr(meeting_chat, "_run_chat_completion", capture_sources)

    result = run(
        meeting_chat.chat_with_meeting_transcript(
            "meeting-1",
            "which task are assign to shweta in the meet",
        )
    )

    assert "Shweta Nagpure: I am working on task assigning" in captured_sources[0]["chunk_text"]
    assert "Please continue that" in captured_sources[0]["chunk_text"]
    assert fake_search.search_calls == []
    assert result["sources"] == []


def test_chat_completion_receives_only_relevant_lines_from_broad_chunks(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    captured_sources: list[dict] = []
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Engineering sync",
        }
    ]
    fake_search.results = [
        {
            "id": "meeting-1-000",
            "meeting_id": "meeting-1",
            "chunk_text": "\n".join(
                [
                    "Aditya Shinde: We should start implementing the POC for tickets.",
                    (
                        "Simant Asawale: I can create the plan for the codex session "
                        "that we are going to take."
                    ),
                    "Chaitanya Kolhe: We can do that.",
                ]
            ),
            "speaker": "Aditya Shinde",
            "source_segment_ids": ["segment-1", "segment-2", "segment-3"],
            "started_at": "2026-05-20T05:41:00Z",
            "ended_at": "2026-05-20T05:42:00Z",
        }
    ]

    def capture_sources(_meeting, _question, sources):
        captured_sources.extend(sources)
        return "Simant Asawale mentioned the Codex session plan."

    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="specific_fact",
            retrieval="semantic_search",
            person=None,
            normalized_question=question,
        ),
    )
    monkeypatch.setattr(meeting_chat, "_run_chat_completion", capture_sources)

    run(meeting_chat.chat_with_meeting_transcript("meeting-1", "who said about codex session"))

    assert captured_sources[0]["chunk_text"] == (
        "Simant Asawale: I can create the plan for the codex session that we are going to take."
    )
    assert captured_sources[0]["speaker"] == "Simant Asawale"


def test_chat_completion_ignores_generic_chat_term_when_focusing_sources(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    captured_sources: list[dict] = []
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Engineering sync",
        }
    ]
    fake_search.results = [
        {
            "id": "meeting-1-000",
            "meeting_id": "meeting-1",
            "chunk_text": "\n".join(
                [
                    "Shweta Nagpure: I completed the AI chatting system.",
                    "Simant Asawale: I can create the plan for the codex session.",
                ]
            ),
            "speaker": "Shweta Nagpure",
            "source_segment_ids": ["segment-1", "segment-2"],
            "started_at": "2026-05-20T05:41:00Z",
            "ended_at": "2026-05-20T05:42:00Z",
        }
    ]

    def capture_sources(_meeting, _question, sources):
        captured_sources.extend(sources)
        return "Simant Asawale mentioned the Codex session plan."

    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="specific_fact",
            retrieval="semantic_search",
            person=None,
            normalized_question=question,
        ),
    )
    monkeypatch.setattr(meeting_chat, "_run_chat_completion", capture_sources)

    run(meeting_chat.chat_with_meeting_transcript("meeting-1", "who said about the codex chat"))

    assert captured_sources[0]["chunk_text"] == (
        "Simant Asawale: I can create the plan for the codex session."
    )
    assert captured_sources[0]["speaker"] == "Simant Asawale"


def test_chat_completion_focuses_relevant_turn_inside_single_line_chunk(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    captured_sources: list[dict] = []
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Engineering sync",
        }
    ]
    fake_search.results = [
        {
            "id": "meeting-1-000",
            "meeting_id": "meeting-1",
            "chunk_text": (
                "Varad Raut at 05:41 AM - Shweta Nagpure: I completed the AI chatting "
                "system with transcript chat. Simant Asawale: I can create the plan for "
                "the codex session that we are going to take, right? Chaitanya Kolhe: "
                "We can do that."
            ),
            "speaker": "Varad Raut",
            "source_segment_ids": ["segment-1", "segment-2", "segment-3"],
            "started_at": "2026-05-20T05:41:00Z",
            "ended_at": "2026-05-20T05:42:00Z",
        }
    ]

    def capture_sources(_meeting, _question, sources):
        captured_sources.extend(sources)
        return "Simant Asawale mentioned the Codex session plan."

    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="specific_fact",
            retrieval="semantic_search",
            person=None,
            normalized_question=question,
        ),
    )
    monkeypatch.setattr(meeting_chat, "_run_chat_completion", capture_sources)

    result = run(
        meeting_chat.chat_with_meeting_transcript("meeting-1", "who said about the codex chat")
    )

    assert captured_sources[0]["chunk_text"] == (
        "Simant Asawale: I can create the plan for the codex session "
        "that we are going to take, right?"
    )
    assert captured_sources[0]["speaker"] == "Simant Asawale"
    assert result["sources"] == []


def test_get_meeting_chat_messages_hides_saved_assistant_sources(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Engineering sync",
        }
    ]
    fake_db.tables["ai_chat_messages"] = [
        {
            "id": "message-1",
            "meeting_id": "meeting-1",
            "user_id": "user-1",
            "role": "assistant",
            "content": "Simant Asawale mentioned the Codex session plan.",
            "sources": [{"chunk_text": "Long noisy transcript chunk"}],
            "created_at": "2026-05-20T05:41:00Z",
        }
    ]

    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")

    result = run(meeting_chat.get_meeting_chat_messages("meeting-1"))

    assert result[0]["sources"] == []


def test_chat_falls_back_to_speaker_answer_when_azure_filters_prompt(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_search = FakeSearchClient()
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "user-1",
            "subject": "Engineering sync",
        }
    ]
    fake_search.results = [
        {
            "id": "meeting-1-000",
            "meeting_id": "meeting-1",
            "chunk_text": "Shweta: We discussed the Codex session setup.",
            "speaker": "Shweta",
            "source_segment_ids": ["segment-1"],
            "started_at": "2026-05-20T10:00:00Z",
            "ended_at": "2026-05-20T10:00:00Z",
        }
    ]

    def raise_content_filter(*args):
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Azure OpenAI chat request failed.",
                "status_code": 400,
                "response": '{"error":{"code":"content_filter"}}',
            },
        )

    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "search_client", fake_search)
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="specific_fact",
            retrieval="semantic_search",
            person=None,
            normalized_question=question,
        ),
    )
    monkeypatch.setattr(meeting_chat, "_run_chat_completion", raise_content_filter)

    result = run(
        meeting_chat.chat_with_meeting_transcript(
            "meeting-1",
            "who said about the codex session",
        )
    )

    assert "Shweta" in result["answer"]
    assert "content policy" in result["answer"]
    assert fake_db.tables["ai_chat_messages"][1]["role"] == "assistant"
    assert fake_db.tables["ai_chat_messages"][1]["content"] == result["answer"]


def test_content_filter_fallback_uses_only_lines_matching_question_terms():
    from app.services import meeting_chat

    answer = meeting_chat._build_content_filter_fallback_answer(
        "who said about the codex session in the meeting",
        [
            {
                "chunk_text": "\n".join(
                    [
                        "Aditya Shinde: We should start implementing the POC for tickets.",
                        "Dilbagh Dhindsa: Thanks Aditya, continue supporting that work.",
                        (
                            "Simant Asawale: If there is time, I can create the plan "
                            "for the codex session that we are going to take."
                        ),
                        "Chaitanya Kolhe: We can do that.",
                    ]
                ),
                "speaker": "Aditya Shinde",
                "started_at": "2026-05-20T05:41:00Z",
            }
        ],
    )

    assert "Simant Asawale" in answer
    assert "create the plan for the codex session" in answer
    assert "Aditya Shinde" not in answer
    assert "Dilbagh Dhindsa" not in answer
    assert "Chaitanya Kolhe" not in answer


def test_chat_rejects_meeting_for_different_user(monkeypatch):
    from app.services import meeting_chat

    fake_db = FakeSupabaseGateway()
    fake_db.tables["meetings"] = [
        {
            "id": "meeting-1",
            "user_id": "other-user",
            "subject": "Private sync",
        }
    ]
    monkeypatch.setattr(meeting_chat, "supabase_gateway", fake_db)
    monkeypatch.setattr(meeting_chat, "get_dev_user_id", lambda: "user-1")
    monkeypatch.setattr(meeting_chat, "_ensure_ai_chat_enabled", lambda: None)
    monkeypatch.setattr(
        meeting_chat,
        "_route_meeting_chat_question",
        lambda question: meeting_chat.MeetingChatRoute(
            intent="specific_fact",
            retrieval="semantic_search",
            person=None,
            normalized_question=question,
        ),
    )

    with pytest.raises(HTTPException) as exc:
        run(meeting_chat.chat_with_meeting_transcript("meeting-1", "What happened?"))

    assert exc.value.status_code == 404
