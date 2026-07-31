from tools.contact_support import CONTACT_CHANNELS, contact_support


def test_no_grounding_returns_contact_channels_and_no_conflicting_facts():
    result = contact_support("no_grounding", "Học phí bao nhiêu?")
    assert result.contact_channels == CONTACT_CHANNELS
    assert result.suggested_question == "Học phí bao nhiêu?"
    assert result.conflicting_facts == []
    assert "chưa tìm thấy" in result.message.lower() or "chưa đủ" in result.message.lower()


def test_out_of_scope_message_differs_from_no_grounding():
    out_of_scope = contact_support("out_of_scope", "Hồ sơ của em đến đâu rồi?")
    no_grounding = contact_support("no_grounding", "Hồ sơ của em đến đâu rồi?")
    assert out_of_scope.message != no_grounding.message


def test_conflicting_sources_splits_partial_context_into_facts():
    result = contact_support(
        "conflicting_sources",
        "Lịch học buổi sáng mấy giờ?",
        partial_context="Nguồn A: học từ 9:00.\nNguồn B: học từ 8:30.",
    )
    assert result.conflicting_facts == ["Nguồn A: học từ 9:00.", "Nguồn B: học từ 8:30."]


def test_strips_whitespace_from_user_question():
    result = contact_support("personal_data_request", "  điểm thi của em bao nhiêu  ")
    assert result.suggested_question == "điểm thi của em bao nhiêu"


def test_no_partial_context_yields_empty_conflicting_facts():
    result = contact_support("conflicting_sources", "Địa điểm học ở đâu?")
    assert result.conflicting_facts == []
