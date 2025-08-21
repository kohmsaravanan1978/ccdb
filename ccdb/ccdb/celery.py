import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ccdb.settings.dev")
try:
    from django.conf import settings
except ImportError:
    raise ValueError("Could not find django.conf")

app = Celery("ccdb")

if os.environ["DJANGO_SETTINGS_MODULE"] == "ccdb.settings.dev":
    import types

    def task_replacement(taskname):
        def replacement(*args, **kwargs):
            print("tries to call task {} but is mocked away".format(taskname))

        replacement.__name__ = taskname

        return replacement

    old_task_from_fun_impl = app._task_from_fun

    def _task_from_fun(self, fun, name=None, base=None, bind=False, **options):
        func_name = name or self.gen_task_name(fun.__name__, fun.__module__)

        if func_name not in settings.DEBUG_ALLOWED_CELERY_TASKS:
            print("Mocked task {}".format(func_name))

            return old_task_from_fun_impl(
                task_replacement(fun.__name__),
                name=func_name,
                base=base,
                bind=bind,
                **options
            )

        return old_task_from_fun_impl(fun, name=name, base=base, bind=bind, **options)

    app._task_from_fun = types.MethodType(_task_from_fun, app)

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
