import logging

from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)


class OverwriteStorage(FileSystemStorage):
    def _save(self, name, content):
        self.delete(name)
        logger.debug('saving file "%s"', name)
        return super()._save(name, content)

    def get_available_name(self, name, max_length=None):
        return name


class MigrationBackwardCompatibilityStorageBackend:
    def _save(self):
        raise Exception(
            "Using {} is not allowed. This backend is only here to keep migrations"
        )

    def __init__(self, *args, **kwargs):
        pass


class S3FilesystemFallbackStorage(MigrationBackwardCompatibilityStorageBackend):
    pass


class TempStorage(MigrationBackwardCompatibilityStorageBackend):
    pass
