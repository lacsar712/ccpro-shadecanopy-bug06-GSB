from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # JWT 认证已按令牌中的 user_id 解析出用户，直接返回，
        # 保证与登录回包、各写入口认成同一人。
        return Response(UserSerializer(request.user).data)
