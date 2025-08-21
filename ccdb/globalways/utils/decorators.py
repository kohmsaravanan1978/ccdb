from collections import namedtuple
from collections.abc import Hashable

from celery.utils.log import get_task_logger
from django.db import transaction
from django.db.models.fields.related_descriptors import (
    ForwardManyToOneDescriptor,
    ManyToManyDescriptor,
)
from simple_history import register
from simple_history.utils import update_change_reason

__all__ = ["historify"]

logger = get_task_logger(__name__)


Change = namedtuple("Change", ["field", "old", "new"])


def _diff_recursive(old, new):
    if isinstance(old, dict):
        changes = []
        for key in set(old.keys()) | set(new.keys()):
            if key not in old:
                changes.append("+{}:{}".format(key, new[key]))
                continue
            if key not in new:
                changes.append("-{}:{}".format(key, old[key]))
                continue
            if old[key] != new[key]:
                changes.append(
                    "{}: {}".format(key, _diff_recursive(old[key], new[key]))
                )
        return "{{{}}}".format(", ".join(changes))
    elif isinstance(old, list):
        changes = []
        # lists are assumed to contain only atoms
        # convert not hashable values to string
        new_hashable = [str(i) if not isinstance(i, Hashable) else i for i in new]
        old_hashable = [str(i) if not isinstance(i, Hashable) else i for i in old]
        for added in set(new_hashable) - set(old_hashable):
            changes.append("+{}".format(added))
        for removed in set(old_hashable) - set(new_hashable):
            changes.append("-{}".format(removed))
        return "[{}]".format(", ".join(changes))
    else:
        return "{} -> {}".format(old, new)


def _history_diff(diff):
    changes = []
    for change in diff:
        if change.field in ("modified", "computed_gnom_id_informations"):
            continue
        if isinstance(change.old, (list, dict)):
            changes.append(
                "{}: {}".format(change.field, _diff_recursive(change.old, change.new))
            )
        else:
            changes.append("{}: {} -> {}".format(change.field, change.old, change.new))
    return "; ".join(changes)


def historify(cls):
    register(cls, app=cls._meta.app_label)
    old_save = cls.save
    differ = getattr(cls, "_history_diff", _history_diff)

    def save(self, **kwargs):
        with transaction.atomic():
            write_history_entry = kwargs.pop("write_history_entry", True)

            res = old_save(self, **kwargs)

            if write_history_entry:
                now = self.history.first()
                before = now.prev_record

                if before:
                    changes = now.diff_against(before).changes
                    diff = []
                    for change in changes:
                        if isinstance(
                            getattr(cls, change.field), ForwardManyToOneDescriptor
                        ):
                            foreign = getattr(cls, change.field).get_queryset().first()
                            if not foreign:
                                diff.append(change)
                            else:
                                Foreign = foreign.__class__
                                new = Foreign.objects.filter(pk=change.new).first()
                                old = Foreign.objects.filter(pk=change.old).first()
                                if not (
                                    hasattr(old, "get_name")
                                    and hasattr(new, "get_name")
                                ):
                                    continue
                                diff.append(
                                    Change(
                                        change.field,
                                        old.get_name() if old else "-",
                                        new.get_name() if new else "-",
                                    )
                                )
                        else:
                            diff.append(change)
                    update_change_reason(self, differ(diff)[:100])  # varchar(100)

            else:
                self.history.first().delete()

            return res

    @property
    def _history_user(self):
        return self.modified_by

    cls.save = save
    if not hasattr(cls, "_history_user"):
        cls._history_user = _history_user

    # m2m:
    for name in dir(cls):
        attr = getattr(cls, name)
        if isinstance(attr, ManyToManyDescriptor):
            logger.warning("Currently not tracking M2M changes in history (%s)", cls)
            break

    #         def handle_m2m(name, sender, **kwargs):
    #             # We currently have no unittests for m2m changes. If we implement the first use case we need/can to test ít
    #             raise Exception('Write unittests for m2m historify')
    #             instance = kwargs.get("instance")
    #             action = kwargs.get("action")
    #             pks = kwargs.get("pk_set")
    #             Model = kwargs.get("model")
    #             name = Model.__name__
    #             if action not in ["post_add", "post_remove"]:
    #                 return
    #             old_reason = instance.history.first().history_change_reason
    #             if old_reason:
    #                 old_reason = "{}, ".format(old_reason)
    #             objs = ",".join(map(str, Model.objects.filter(pk__in=pks)))
    #             if action == "post_remove":
    #                 update_change_reason(instance, "{} {}: -{}".format(old_reason, name, objs).strip())
    #             if action == "post_add":
    #                 update_change_reason(instance, "{} {}: +{}".format(old_reason, name, objs).strip())

    #         receiver(m2m_changed, sender=attr.through, weak=False)(partial(handle_m2m, name))

    return cls
