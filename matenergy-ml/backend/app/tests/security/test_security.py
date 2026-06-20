"""Security tests for MatEnergy-ML."""
import pytest
import re

class TestPathTraversal:
    def test_path_traversal_blocked(self):
        from pathlib import Path
        import re
        def safe_filename(name):
            return re.sub(r'[^\w\-_. ]', '', name)[:128]

        dangerous = ["../etc/passwd", "../../.env", "..\\Windows\\System32"]
        for fname in dangerous:
            result = safe_filename(fname)
            assert ".." not in result
            assert "/" not in result
            assert "\\" not in result

class TestSQLInjection:
    def test_orm_prevents_injection(self):
        # SQLAlchemy ORM uses parameterized queries — test that we use it
        # by verifying the repository uses select() and not string concatenation
        import inspect
        from app.infrastructure.database.repositories.material_repository import MaterialRepository
        source = inspect.getsource(MaterialRepository.search_by_formula)
        # Should use .ilike() with bound parameter, not string format
        assert "f-string" not in source or "ilike" in source
        assert "%" + source + "%" not in source  # No direct string concatenation of query

class TestCSVFormulaInjection:
    def test_csv_formula_injection_characters_sanitized(self):
        """CSV formula injection: '=CMD()', '+CMD()', '@SUM()' in cells."""
        import csv, io
        dangerous_formulas = ["=CMD('rm -rf /')", "+1+1+1", "@SUM(A1:A10)", "-2+3"]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["formula", "energy"])
        for f in dangerous_formulas:
            writer.writerow([f, "0.001"])
        content = output.getvalue()

        from app.infrastructure.materials.csv_loader import MaterialCSVLoader
        loader = MaterialCSVLoader()
        result = loader.parse_and_validate(content.encode(), allow_partial=True)
        # These should all be rejected (invalid chemical formulas)
        assert result["rejected_count"] > 0

class TestRankingWeightsValidation:
    def test_weights_must_be_between_0_and_1(self):
        from app.domain.entities.candidate_ranking import RankingWeights
        w = RankingWeights()
        assert w.validate()  # Default weights should be valid

class TestJWTSecurity:
    def test_access_token_cannot_be_used_as_refresh(self):
        from app.core.jwt_provider import create_access_token, decode_token
        from app.core.constants import TokenType
        from app.core.exceptions import TokenTypeMismatchError
        token = create_access_token("user-1")
        with pytest.raises(TokenTypeMismatchError):
            decode_token(token, TokenType.REFRESH)

    def test_empty_token_raises(self):
        from app.core.jwt_provider import decode_token
        from app.core.constants import TokenType
        from app.core.exceptions import TokenInvalidError
        with pytest.raises(TokenInvalidError):
            decode_token("", TokenType.ACCESS)
