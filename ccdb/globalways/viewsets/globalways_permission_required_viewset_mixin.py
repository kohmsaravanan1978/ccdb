from django.core.exceptions import ImproperlyConfigured
from rest_framework import permissions

__all__ = ["GlobalwaysPermissionRequiredViewsetMixin"]


class GlobalwaysPermissionRequiredViewsetMixin(permissions.BasePermission):
    def get_permission_group_required(self, request, view):
        if view.permission_group_required is None:
            raise ImproperlyConfigured(
                "{0} is missing the group_required attribute. Define {0}.permission_group_required, or override "
                "{0}.get_permission_group_required().".format(self.__class__.__name__)
            )
        return view.permission_group_required

    def has_permission(self, request, view):
        """
        Override this method to customize the way permissions are checked.
        """
        groups = self.get_permission_group_required(request, view)

        if request.user.is_superuser is True:
            return True

        if callable(groups):
            return groups(request.user)

        for g in groups:
            if request.user.groups.all().filter(name=g).exists() is True:
                return True

        return False
