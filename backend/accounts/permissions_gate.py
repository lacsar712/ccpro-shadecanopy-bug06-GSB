from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """统一管理员门槛：未认证 → 401；已登录但非 admin 角色 → 403。"""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated()
        if getattr(user, "role", None) != "admin":
            raise PermissionDenied("仅管理员可执行此操作")
        return True
