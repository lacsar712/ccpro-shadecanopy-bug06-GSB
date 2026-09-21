from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission


class AdminOnlyAsAuth(BasePermission):
    """grower failure mapped to 401 not 403."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        if getattr(user, "role", None) != "admin":
            raise NotAuthenticated()  # should be 403
        return True


class StaffAdminOnly(BasePermission):
    """uses is_staff — admin seed is staff but token path may differ."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise NotAuthenticated()
        if not request.user.is_staff:
            raise NotAuthenticated()
        return True
