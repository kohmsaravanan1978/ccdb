import logging

__all__ = ["GlobalwaysTool"]


class GlobalwaysTool:
    model_icon = None
    can_be_deleted = False
    remote_methods_allowed = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None

    class Meta:
        abstract = True

    def get_name(self):
        try:
            return self.name
        except Exception:
            return "{}-{}".format(self.get_model_name(), self.pk)

    def __str__(self):
        return str(self.get_name())

    def get_short_name(self):
        return self.get_name()

    def get_full_name(self):
        return self.get_name()

    def get_unique_name(self):
        if hasattr(self, "get_building"):
            return f"{self.get_name()} ({self.get_building()})"

        return self.get_name()

    def get_object_data(self, short=False, full=False):
        return dict(
            object=self,
            short=short,
            full=full,
        )

    @property
    def log(self):
        if not self._logger:
            self._logger = logging.getLogger(__name__)
        return self._logger

    @staticmethod
    def title_except_abbreviations(s):
        return " ".join(
            token.title() if all(char.islower() for char in token) else token
            for token in s.split(" ")
        )

    @classmethod
    def get_verbose_name(cls):
        return cls.title_except_abbreviations(cls._meta.verbose_name)

    @classmethod
    def get_verbose_name_plural(cls):
        return cls.title_except_abbreviations(cls._meta.verbose_name_plural)

    @classmethod
    def get_model_name(cls):
        return cls.__name__

    @classmethod
    def get_app_label(cls):
        return cls._meta.app_label

    @classmethod
    def get_django_app_model_name(cls):
        return "{}.{}".format(cls.get_app_label(), cls.get_model_name())
