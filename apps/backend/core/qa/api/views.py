from django.db.models.deletion import ProtectedError
from rest_framework import mixins
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.qa.importers import QuestionImportError
from core.qa.importers import QuestionYamlImporter
from core.qa.models import Proposition
from core.qa.models import Question

from .filters import QuestionFilter
from .serializers import AnswerSerializer
from .serializers import PropositionSerializer
from .serializers import QuestionCreateSerializer
from .serializers import QuestionImportSerializer
from .serializers import QuestionPropositionSerializer
from .serializers import QuestionSerializer


class QuestionImportView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = QuestionImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = QuestionYamlImporter.load_yaml(serializer.validated_data["file"])
            result = QuestionYamlImporter().import_payload(payload)
        except QuestionImportError as error:
            raise ValidationError({"file": str(error)}) from error

        return Response(
            {
                "imported_questions": result.imported_questions,
                "reused_propositions": result.reused_propositions,
                "skipped_questions": result.skipped_questions,
            },
            status=status.HTTP_201_CREATED,
        )


class QuestionViewSet(
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Question.objects.prefetch_related("answers__proposition")
    filterset_class = QuestionFilter
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == "create":
            return QuestionCreateSerializer
        return QuestionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        return Response(
            QuestionSerializer(question).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="propositions",
        url_name="propositions",
    )
    def propositions(self, request, pk=None):
        question = self.get_object()
        if request.method == "GET":
            queryset = question.answers.select_related("proposition").order_by(
                "created",
            )
            return Response(AnswerSerializer(queryset, many=True).data)

        serializer = QuestionPropositionSerializer(
            data=request.data,
            context={"question": question},
        )
        serializer.is_valid(raise_exception=True)
        answer = serializer.save()
        return Response(AnswerSerializer(answer).data, status=status.HTTP_201_CREATED)


class PropositionViewSet(
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Proposition.objects.all()
    serializer_class = PropositionSerializer
    permission_classes = [IsAdminUser]

    def destroy(self, request, *args, **kwargs):
        proposition = self.get_object()
        try:
            proposition.delete()
        except ProtectedError:
            return Response(
                {"detail": "A proposition linked to a question cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
