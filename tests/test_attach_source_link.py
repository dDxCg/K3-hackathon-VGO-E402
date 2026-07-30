import pytest

from tools.attach_source_link import (
    ChunkRef,
    attach_source_link,
    build_source_registry,
)


def test_registry_includes_facebook_source_with_correct_group_link():
    registry = build_source_registry()
    fb = registry["ai_thuc_chien_facebook_feedback_clean"]
    assert fb.source_type == "community_facebook"
    assert fb.source_url == "https://www.facebook.com/groups/2125430681651241"


def test_registry_includes_all_three_official_web_sources():
    registry = build_source_registry()
    web_entries = {
        slug: meta for slug, meta in registry.items() if meta.source_type == "official_web"
    }
    assert len(web_entries) == 3
    urls = {meta.source_url for meta in web_entries.values()}
    assert urls == {
        "https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh-chuong-trinh-dao-tao-nhan-tai-ai-thuc-chien-khoa-co-ban/",
        "https://vinuni.edu.vn/wp-content/uploads/2025/04/20K-AI-Handbook_final.pdf",
        "https://vinuni.edu.vn/vi/vingroup-tang-toc-dao-tao-20-000-nhan-tai-ai-thuc-chien/",
    }


def test_attach_source_link_flags_community_source_with_warning():
    [attachment] = attach_source_link(
        [ChunkRef("fb_1", "community_facebook", "https://www.facebook.com/groups/2125430681651241")]
    )
    assert attachment["source_type"] == "community_facebook"
    assert "warning" in attachment
    assert "không phải nguồn chính thức" in attachment["label_hien_thi"]


def test_attach_source_link_official_web_has_no_warning():
    [attachment] = attach_source_link(
        [
            ChunkRef(
                "web_1",
                "official_web",
                "https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh-chuong-trinh-dao-tao-nhan-tai-ai-thuc-chien-khoa-co-ban/",
            )
        ]
    )
    assert "warning" not in attachment
    assert attachment["label_hien_thi"] == "Thông tin tuyển sinh chính thức — VinUni"


def test_attach_source_link_preserves_order_and_does_not_merge_mixed_sources():
    attachments = attach_source_link(
        [
            ChunkRef(
                "web_1",
                "official_web",
                "https://vinuni.edu.vn/vi/thong-tin-tuyen-sinh-chuong-trinh-dao-tao-nhan-tai-ai-thuc-chien-khoa-co-ban/",
            ),
            ChunkRef("fb_1", "community_facebook", "https://www.facebook.com/groups/2125430681651241"),
        ]
    )
    assert [a["chunk_id"] for a in attachments] == ["web_1", "fb_1"]
    assert attachments[0]["source_type"] != attachments[1]["source_type"]


def test_attach_source_link_unknown_url_falls_back_to_url_as_label():
    [attachment] = attach_source_link(
        [ChunkRef("x_1", "official_web", "https://example.com/unknown-page")]
    )
    assert attachment["label_hien_thi"] == "https://example.com/unknown-page"


def test_attach_source_link_normalizes_trailing_slash_for_known_label():
    [attachment] = attach_source_link(
        [
            ChunkRef(
                "fb_old",
                "community_facebook",
                "https://www.facebook.com/groups/2125430681651241/",
            )
        ]
    )
    assert "không phải nguồn chính thức" in attachment["label_hien_thi"]
