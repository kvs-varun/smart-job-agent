import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class RoleKnowledge:
    role_key: str
    must_have: List[str]
    good_to_have: List[str]
    tools: List[str]
    synonyms: Dict[str, List[str]]


def _load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class KnowledgeBase:
    """Local, curated knowledge base.

    This is intentionally local and deterministic (no web scraping).

    How to extend:
    - Add/modify JSON files under `backend/knowledge/`
    - Keep `roles.<role_key>` consistent across files
    - Add synonyms in `ats_keywords.json -> roles -> <role_key> -> synonyms`
    - Prefer short normalized terms (lowercase) for matching (e.g., "rest api")
    """

    def __init__(self, knowledge_dir: str):
        self.knowledge_dir = knowledge_dir
        self._ats_keywords = None
        self._role_skill_map = None
        self._hiring_patterns = None
        self._resume_practices = None
        self._cold_templates = None

    def load_all(self) -> None:
        self.ats_keywords()
        self.role_skill_map()
        self.indian_hiring_patterns()
        self.resume_best_practices()
        self.cold_email_templates()

    def ats_keywords(self) -> Dict:
        if self._ats_keywords is None:
            self._ats_keywords = _load_json(os.path.join(self.knowledge_dir, "ats_keywords.json"))
        return self._ats_keywords

    def role_skill_map(self) -> Dict:
        if self._role_skill_map is None:
            self._role_skill_map = _load_json(os.path.join(self.knowledge_dir, "role_skill_map.json"))
        return self._role_skill_map

    def indian_hiring_patterns(self) -> Dict:
        if self._hiring_patterns is None:
            self._hiring_patterns = _load_json(os.path.join(self.knowledge_dir, "indian_fresher_hiring_patterns.json"))
        return self._hiring_patterns

    def resume_best_practices(self) -> Dict:
        if self._resume_practices is None:
            self._resume_practices = _load_json(os.path.join(self.knowledge_dir, "resume_best_practices.json"))
        return self._resume_practices

    def cold_email_templates(self) -> Dict:
        if self._cold_templates is None:
            self._cold_templates = _load_json(os.path.join(self.knowledge_dir, "cold_email_templates.json"))
        return self._cold_templates

    def get_role_knowledge(self, role_key: str) -> RoleKnowledge:
        roles = self.ats_keywords().get("roles", {})
        rk = roles.get(role_key)
        if not rk:
            raise KeyError(f"Unknown role_key: {role_key}")
        return RoleKnowledge(
            role_key=role_key,
            must_have=rk.get("must_have", []),
            good_to_have=rk.get("good_to_have", []),
            tools=rk.get("tools", []),
            synonyms=rk.get("synonyms", {}),
        )

    def get_keywords_for_role(self, role_key: str) -> Dict:
        role = self.get_role_knowledge(role_key)
        return {
            "must_have": role.must_have,
            "good_to_have": role.good_to_have,
            "tools": role.tools,
            "synonyms": role.synonyms,
        }

    def expand_synonyms(self, terms: List[str], role_key: str) -> List[str]:
        role = self.get_role_knowledge(role_key)
        out: List[str] = []
        for t in terms:
            out.append(t)
            for syn in role.synonyms.get(t, []):
                out.append(syn)
        # de-dupe
        seen = set()
        final = []
        for x in out:
            k = x.lower().strip()
            if not k or k in seen:
                continue
            seen.add(k)
            final.append(x)
        return final


    def infer_role_key(self, job_text: str) -> Tuple[str, float]:
        """Infer role bucket using heuristics and return (role_key, confidence).

        Heuristics use:
        - title keywords (react/flutter/data)
        - common skill mentions
        - avoids relying on years-of-experience strings (freshers often have none)
        """

        jd = (job_text or "").lower()
        jd = re.sub(r"\s+", " ", jd)

        scores = {
            "backend_fresher": 0,
            "frontend_fresher": 0,
            "flutter_fresher": 0,
            "data_fresher": 0,
        }

        def bump(role: str, n: int) -> None:
            scores[role] = scores.get(role, 0) + n

        if "flutter" in jd or "dart" in jd:
            bump("flutter_fresher", 4)
        if "react" in jd or "frontend" in jd or "javascript" in jd or "typescript" in jd:
            bump("frontend_fresher", 4)
        if "machine learning" in jd or "data analyst" in jd or "power bi" in jd or "pandas" in jd:
            bump("data_fresher", 4)

        if "flask" in jd or "django" in jd or "fastapi" in jd:
            bump("backend_fresher", 3)
        if "sql" in jd or "rest" in jd or "api" in jd:
            bump("backend_fresher", 2)

        best_role = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = (scores[best_role] / total) if total else 0.5
        return best_role, float(round(confidence, 2))
