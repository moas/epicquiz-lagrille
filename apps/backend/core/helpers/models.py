from model_utils.models import UUIDModel, TimeStampedModel


class BaseModel(UUIDModel, TimeStampedModel):
    class Meta:
        abstract = True
