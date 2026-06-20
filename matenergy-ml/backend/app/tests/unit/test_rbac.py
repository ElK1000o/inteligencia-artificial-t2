"""Tests for RBAC permission system."""
import pytest
from app.core.permissions import has_permission, ROLE_PERMISSIONS
from app.core.constants import UserRole

class TestRBAC:
    def test_admin_has_dataset_write(self):
        assert has_permission(UserRole.ADMIN, "dataset:write") is True

    def test_viewer_cannot_write_dataset(self):
        assert has_permission(UserRole.VIEWER, "dataset:write") is False

    def test_viewer_can_read_dataset(self):
        assert has_permission(UserRole.VIEWER, "dataset:read") is True

    def test_researcher_can_train_model(self):
        assert has_permission(UserRole.RESEARCHER, "model:write") is True

    def test_viewer_cannot_train_model(self):
        assert has_permission(UserRole.VIEWER, "model:write") is False

    def test_admin_has_user_management(self):
        assert has_permission(UserRole.ADMIN, "user:delete") is True

    def test_researcher_cannot_manage_users(self):
        assert has_permission(UserRole.RESEARCHER, "user:delete") is False

    def test_unknown_permission_returns_false(self):
        assert has_permission(UserRole.ADMIN, "nonexistent:permission") is False

    def test_admin_has_all_researcher_permissions(self):
        researcher_perms = ROLE_PERMISSIONS[UserRole.RESEARCHER]
        for perm in researcher_perms:
            assert has_permission(UserRole.ADMIN, perm), f"Admin missing: {perm}"
