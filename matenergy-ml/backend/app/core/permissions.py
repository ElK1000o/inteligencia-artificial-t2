"""
Role-based access control (RBAC) permission matrix for MatEnergy-ML.

Permissions follow a "<resource>:<action>" convention.
The ROLE_PERMISSIONS dict is the single source of truth; all FastAPI
dependency factories read from it at runtime.

Usage in a route:
    @router.delete("/datasets/{id}", dependencies=[Depends(require_permission_dep("dataset:delete"))])

Or with the role shorthand:
    @router.get("/admin/users", dependencies=[Depends(require_roles(UserRole.ADMIN))])
"""
from __future__ import annotations

from app.core.constants import UserRole

# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.ADMIN: {
        # datasets
        "dataset:read", "dataset:write", "dataset:delete",
        # materials
        "material:read", "material:write",
        # descriptors
        "descriptor:read", "descriptor:write",
        # models
        "model:read", "model:write", "model:delete",
        # predictions
        "prediction:read", "prediction:write",
        # rankings
        "ranking:read", "ranking:write",
        # user management
        "user:read", "user:write", "user:delete",
        # audit & security
        "audit:read",
        "security:read",
        # reports
        "report:read", "report:write",
        # settings
        "settings:read", "settings:write",
    },
    UserRole.RESEARCHER: {
        # datasets
        "dataset:read", "dataset:write",
        # materials
        "material:read", "material:write",
        # descriptors
        "descriptor:read", "descriptor:write",
        # models
        "model:read", "model:write",
        # predictions
        "prediction:read", "prediction:write",
        # rankings
        "ranking:read", "ranking:write",
        # reports
        "report:read", "report:write",
    },
    UserRole.VIEWER: {
        "dataset:read",
        "material:read",
        "descriptor:read",
        "model:read",
        "prediction:read",
        "ranking:read",
        "report:read",
    },
}

# Pre-built mapping for fast lookup: permission -> set of roles that hold it
_PERMISSION_TO_ROLES: dict[str, set[UserRole]] = {}
for _role, _perms in ROLE_PERMISSIONS.items():
    for _perm in _perms:
        _PERMISSION_TO_ROLES.setdefault(_perm, set()).add(_role)


# ---------------------------------------------------------------------------
# Pure helper (no FastAPI dependency, usable anywhere)
# ---------------------------------------------------------------------------


def has_permission(role: UserRole, permission: str) -> bool:
    """
    Return True if *role* includes *permission*.

    Args:
        role:       A ``UserRole`` enum value.
        permission: Permission string in "<resource>:<action>" format.

    Returns:
        bool
    """
    return permission in ROLE_PERMISSIONS.get(role, set())


def get_all_permissions(role: UserRole) -> frozenset[str]:
    """Return an immutable set of all permissions held by *role*."""
    return frozenset(ROLE_PERMISSIONS.get(role, set()))


def roles_with_permission(permission: str) -> frozenset[UserRole]:
    """Return the set of roles that hold *permission*."""
    return frozenset(_PERMISSION_TO_ROLES.get(permission, set()))
