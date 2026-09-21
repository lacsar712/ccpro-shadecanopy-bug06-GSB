from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import TokenObtainPairWithUserSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    """登录回包附带当前用户，与令牌、/auth/me/ 指向同一人。"""

    serializer_class = TokenObtainPairWithUserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 身份以 JWT 认证解析出的 request.user 为准，不做二次用户名猜测。
        return Response(UserSerializer(request.user).data)
