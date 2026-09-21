from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission


def _require_authenticated(request):
    """未携带/携带无效令牌 → 401；返回已认证用户。"""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise NotAuthenticated()
    return user


class IsAdminRole(BasePermission):
    """仅管理员：未认证 401，已登录但非管理员 403。"""

    def has_permission(self, request, view):
        user = _require_authenticated(request)
        if getattr(user, "role", None) != "admin":
            raise PermissionDenied("仅管理员可执行此操作")
        return True


class GreenhouseUpdatePermission(BasePermission):
    """温室编辑：管理员可改全部字段；种植员可改位置/面积/备注等字段，但不能改名称。"""

    def has_permission(self, request, view):
        _require_authenticated(request)
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if getattr(user, "role", None) == "admin":
            return True
        new_name = request.data.get("name")
        if new_name is not None and str(new_name) != obj.name:
            raise PermissionDenied("种植员不能修改温室名称")
        return True
