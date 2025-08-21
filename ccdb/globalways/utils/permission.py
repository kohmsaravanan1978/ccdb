class Permission:
    def __init__(self, group=None, name=None):
        if isinstance(group, Permission):
            self.group = group.group
            self.name = group.name
        elif isinstance(group, (tuple, list)):
            first, *rest = group
            if rest:
                self.group = Permission(first) | Permission(rest)
            else:
                self.group = Permission(first)
            self.name = self.group.name
        else:
            self.name = name if name else group
            self.group = group

    def __call__(self, user):
        return (
            None
            if self.group is None
            else (
                self.group(user)
                if callable(self.group)
                else user.groups.filter(name=self.group).exists() or user.is_superuser
            )
        )

    def __and__(self, other):
        if isinstance(other, Permission):
            if not other:
                return other
            if not self:
                return self
        return Permission(
            lambda user: self(user) and other(user),
            name="({} and {})".format(self, other),
        )

    def __invert__(self):
        return Permission(lambda user: not self(user), name="(not in {})".format(self))

    def __or__(self, other):
        if isinstance(other, Permission):
            if not other:
                return self
            if not self:
                return other
        return Permission(
            lambda user: self(user) or other(user),
            name="({} or {})".format(self, other),
        )

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return "<Permission: {}>".format(self)

    def __bool__(self):
        return self.group is not None


class UserPermission(Permission):
    def __init__(self, user=None):
        self.user = user

    def __call__(self, user):
        return (
            None
            if self.user is None
            else (
                self.user(user)
                if callable(self.user)
                else user.username == self.user or user.is_superuser
            )
        )

    def __bool__(self):
        return self.user is not None

    @property
    def name(self):
        return self.user if self.user is not None else "NOBODY"
