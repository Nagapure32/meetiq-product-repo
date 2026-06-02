from app.services.assignee_resolution import resolve_assignee


def test_resolves_first_person_to_speaker_email():
    result = resolve_assignee(
        assignee_name="I",
        evidence_segment={
            "speaker": "Ravi Sharma",
            "source_id": "7",
            "speaker_email": "ravi@example.com",
            "speaker_aad_user_id": "aad-ravi",
        },
        participants=[
            {
                "source_id": "7",
                "display_name": "Ravi Sharma",
                "email": "ravi@example.com",
                "aad_user_id": "aad-ravi",
            }
        ],
        profiles=[
            {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
        ],
    )

    assert result.user_id == "user-ravi"
    assert result.email == "ravi@example.com"
    assert result.status == "resolved"
    assert result.confidence == 1.0


def test_resolves_unique_named_participant_to_profile():
    result = resolve_assignee(
        assignee_name="Priya",
        evidence_segment={"speaker": "Asha", "source_id": "3"},
        participants=[
            {
                "display_name": "Priya Kale",
                "email": "priya@example.com",
                "aad_user_id": "aad-priya",
            },
            {"display_name": "Ravi Sharma", "email": "ravi@example.com", "aad_user_id": "aad-ravi"},
        ],
        profiles=[
            {"id": "user-priya", "display_name": "Priya Kale", "email": "priya@example.com"},
            {"id": "user-ravi", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
        ],
    )

    assert result.user_id == "user-priya"
    assert result.email == "priya@example.com"
    assert result.status == "resolved"


def test_resolves_unique_named_participant_email_without_profile():
    result = resolve_assignee(
        assignee_name="Priya",
        evidence_segment={"speaker": "Asha", "source_id": "3"},
        participants=[
            {
                "display_name": "Priya Kale",
                "email": "priya@example.com",
                "aad_user_id": "aad-priya",
            },
            {"display_name": "Ravi Sharma", "email": "ravi@example.com", "aad_user_id": "aad-ravi"},
        ],
        profiles=[],
    )

    assert result.user_id is None
    assert result.email == "priya@example.com"
    assert result.display_name == "Priya Kale"
    assert result.status == "resolved"
    assert result.reason == "unique_participant_display_name_email_only"


def test_resolves_first_person_to_speaker_email_without_profile():
    result = resolve_assignee(
        assignee_name="I",
        evidence_segment={
            "speaker": "Ravi Sharma",
            "source_id": "7",
            "speaker_email": "ravi@example.com",
            "speaker_aad_user_id": "aad-ravi",
        },
        participants=[
            {
                "source_id": "7",
                "display_name": "Ravi Sharma",
                "email": "ravi@example.com",
                "aad_user_id": "aad-ravi",
            }
        ],
        profiles=[],
    )

    assert result.user_id is None
    assert result.email == "ravi@example.com"
    assert result.display_name == "Ravi Sharma"
    assert result.status == "resolved"
    assert result.reason == "first_person_evidence_speaker_email_only"


def test_does_not_resolve_ambiguous_display_name():
    result = resolve_assignee(
        assignee_name="Ravi",
        evidence_segment={"speaker": "Asha", "source_id": "3"},
        participants=[
            {"display_name": "Ravi Sharma", "email": "ravi@example.com"},
            {"display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
        ],
        profiles=[
            {"id": "user-1", "display_name": "Ravi Sharma", "email": "ravi@example.com"},
            {"id": "user-2", "display_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
        ],
    )

    assert result.user_id is None
    assert result.email is None
    assert result.status == "unresolved"
