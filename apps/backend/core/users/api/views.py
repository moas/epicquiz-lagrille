from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import LoginSerializer

User = get_user_model()


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user_id = serializer.validated_data["user"].pk
            user = User.objects.select_for_update().get(pk=user_id)
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)

        return Response({"token": token.key}, status=status.HTTP_200_OK)


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
