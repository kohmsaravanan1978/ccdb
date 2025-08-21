from django.db import models
from django_extensions.db.models import TimeStampedModel


class LogLevels(models.TextChoices):
    CRITICAL = 50, "Critical"
    ERROR = 40, "Error"
    WARNING = 30, "Warning"
    INFO = 20, "Info"
    DEBUG = 10, "Debug"


# Not @historify because this model is intended to be write-only
class LogEntry(TimeStampedModel):
    log_level = models.IntegerField(choices=LogLevels.choices, default=LogLevels.DEBUG)
    origin = models.CharField(max_length=200)
    text = models.TextField()
