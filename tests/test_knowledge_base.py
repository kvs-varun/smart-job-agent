from backend.knowledge_base import KnowledgeBase


def test_infer_role_key_returns_tuple():
    kb = KnowledgeBase("backend/knowledge")
    kb.load_all()
    role_key, conf = kb.infer_role_key("Looking for a fresher backend developer with Python and Flask")
    assert isinstance(role_key, str)
    assert 0.0 <= float(conf) <= 1.0


def test_expand_synonyms_non_empty_for_known_terms():
    kb = KnowledgeBase("backend/knowledge")
    kb.load_all()
    expanded = kb.expand_synonyms(["javascript", "react"], role_key="frontend_fresher")
    assert isinstance(expanded, list)
    assert len(expanded) >= 2
