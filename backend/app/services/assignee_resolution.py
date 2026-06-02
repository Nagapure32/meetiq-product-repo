import re
from dataclasses import dataclass
from typing import Any


FIRST_PERSON_ASSIGNEES = {"i", "me", "myself", "i'll", "ill", "i will"}


@dataclass(frozen=True)
class AssigneeResolution:
    user_id: str | None
    email: str | None
    display_name: str | None
    status: str
    confidence: float | None
    reason: str


def resolve_assignee(
    assignee_name: str | None,
    evidence_segment: dict[str, Any] | None,
    participants: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> AssigneeResolution:
    normalized_assignee = _normalize_name(assignee_name)
    if not normalized_assignee:
        return _unresolved("missing_assignee")

    if is_first_person_assignee(assignee_name):
        return _resolve_first_person(evidence_segment, participants, profiles)

    matched_participants = _match_named_participants(assignee_name, participants)
    if len(matched_participants) != 1:
        reason = "ambiguous_assignee" if matched_participants else "participant_not_found"
        return _unresolved(reason)

    return _resolve_participant(
        matched_participants[0],
        profiles,
        reason="unique_participant_display_name",
        confidence=0.9,
    )


def is_first_person_assignee(assignee_name: str | None) -> bool:
    return _normalize_name(assignee_name) in FIRST_PERSON_ASSIGNEES


def _resolve_first_person(
    evidence_segment: dict[str, Any] | None,
    participants: list[dict[str, Any]],
    profiles: list[dict[str, Any]],
) -> AssigneeResolution:
    if not evidence_segment:
        return _unresolved("missing_evidence_segment")

    participant = _participant_for_evidence(evidence_segment, participants)
    if participant:
        return _resolve_participant(
            participant,
            profiles,
            reason="first_person_evidence_speaker",
            confidence=1.0,
        )

    profile = _profile_for_email(
        profiles,
        evidence_segment.get("speaker_email")
        or evidence_segment.get("speaker_user_principal_name"),
    )
    if profile:
        email = _clean_email(profile.get("email"))
        return AssigneeResolution(
            user_id=profile.get("id"),
            email=email,
            display_name=profile.get("display_name") or evidence_segment.get("speaker"),
            status="resolved",
            confidence=1.0,
            reason="first_person_evidence_speaker_email",
        )

    evidence_email = _clean_email(
        evidence_segment.get("speaker_email")
        or evidence_segment.get("speaker_user_principal_name")
    )
    if evidence_email:
        return AssigneeResolution(
            user_id=None,
            email=evidence_email,
            display_name=evidence_segment.get("speaker"),
            status="resolved",
            confidence=1.0,
            reason="first_person_evidence_speaker_email_only",
        )

    return _unresolved("speaker_profile_not_found")


def _participant_for_evidence(
    evidence_segment: dict[str, Any],
    participants: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for evidence_key, participant_key in (
        ("speaker_aad_user_id", "aad_user_id"),
        ("speaker_email", "email"),
        ("speaker_user_principal_name", "user_principal_name"),
        ("source_id", "source_id"),
    ):
        value = _normalize_identifier(evidence_segment.get(evidence_key))
        if not value:
            continue
        matches = [
            participant
            for participant in participants
            if _normalize_identifier(participant.get(participant_key)) == value
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return None

    speaker = evidence_segment.get("speaker")
    matches = _match_named_participants(speaker, participants)
    return matches[0] if len(matches) == 1 else None


def _resolve_participant(
    participant: dict[str, Any],
    profiles: list[dict[str, Any]],
    reason: str,
    confidence: float,
) -> AssigneeResolution:
    profile = _profile_for_email(
        profiles,
        participant.get("email") or participant.get("user_principal_name"),
    )
    if not profile:
        participant_email = _clean_email(
            participant.get("email") or participant.get("user_principal_name")
        )
        if not participant_email:
            return _unresolved("profile_not_found")
        return AssigneeResolution(
            user_id=None,
            email=participant_email,
            display_name=participant.get("display_name"),
            status="resolved",
            confidence=confidence,
            reason=f"{reason}_email_only",
        )

    return AssigneeResolution(
        user_id=profile.get("id"),
        email=_clean_email(profile.get("email")),
        display_name=participant.get("display_name") or profile.get("display_name"),
        status="resolved",
        confidence=confidence,
        reason=reason,
    )


def _match_named_participants(
    assignee_name: str | None,
    participants: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized = _normalize_name(assignee_name)
    if not normalized:
        return []

    email_matches = [
        participant
        for participant in participants
        if normalized
        in {
            _normalize_identifier(participant.get("email")),
            _normalize_identifier(participant.get("user_principal_name")),
        }
    ]
    if email_matches:
        return email_matches

    assignee_tokens = set(normalized.split())
    return [
        participant
        for participant in participants
        if _name_matches(assignee_tokens, _normalize_name(participant.get("display_name")))
    ]


def _name_matches(assignee_tokens: set[str], display_name: str) -> bool:
    if not assignee_tokens or not display_name:
        return False
    display_tokens = set(display_name.split())
    return assignee_tokens.issubset(display_tokens)


def _profile_for_email(
    profiles: list[dict[str, Any]],
    email_or_upn: Any,
) -> dict[str, Any] | None:
    email = _normalize_identifier(email_or_upn)
    if not email:
        return None
    matches = [
        profile
        for profile in profiles
        if _normalize_identifier(profile.get("email")) == email
    ]
    return matches[0] if len(matches) == 1 else None


def _unresolved(reason: str) -> AssigneeResolution:
    return AssigneeResolution(
        user_id=None,
        email=None,
        display_name=None,
        status="unresolved",
        confidence=None,
        reason=reason,
    )


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9@._'+-]+", " ", text)
    return " ".join(text.split())


def _normalize_identifier(value: Any) -> str:
    return str(value or "").strip().lower()


def _clean_email(value: Any) -> str | None:
    email = _normalize_identifier(value)
    return email or None
