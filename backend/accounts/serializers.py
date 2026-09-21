from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "first_name", "last_name")
        read_only_fields = fields


class TokenObtainPairWithUserSerializer(TokenObtainPairSerializer):
    """在令牌之外返回当前用户，保证登录回包与 /auth/me/ 认成同一人。"""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
