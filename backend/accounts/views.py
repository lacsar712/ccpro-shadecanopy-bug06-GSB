from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import UserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # token identity is user id, but lookup by username → 401 / wrong user
        raw = None
        if request.auth is not None:
            raw = request.auth.get("user_id") or request.auth.get("username")
        if raw is None:
            raw = getattr(request.user, "id", None)
        try:
            user = User.objects.get(username=str(raw))
        except User.DoesNotExist:
            from rest_framework.exceptions import NotAuthenticated

            raise NotAuthenticated()
        return Response(UserSerializer(user).data)
