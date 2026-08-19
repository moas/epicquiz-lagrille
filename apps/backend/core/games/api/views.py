from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from core.games.models import Episode

from .serializers import EpisodeSerializer
from .serializers import ParticipantSerializer


class EpisodeViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Episode.objects.all()
    serializer_class = EpisodeSerializer
    permission_classes = [IsAdminUser]

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="participants",
        url_name="participants",
    )
    def participants(self, request, pk=None):
        episode = self.get_object()

        if request.method == "GET":
            queryset = episode.participants.select_related("user")
            serializer = ParticipantSerializer(queryset, many=True)
            return Response(serializer.data)

        serializer = ParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            serializer.save(episode=episode)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["get", "put", "patch", "delete"],
        url_path=r"participants/(?P<participant_id>[^/.]+)",
        url_name="participant",
    )
    def participant(self, request, participant_id=None, pk=None):
        episode = self.get_object()
        participant = get_object_or_404(
            episode.participants.select_related("user"),
            pk=participant_id,
        )

        if request.method == "GET":
            return Response(ParticipantSerializer(participant).data)

        if request.method == "DELETE":
            participant.is_active = False
            participant.save(update_fields=["is_active", "modified"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = ParticipantSerializer(
            participant,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
