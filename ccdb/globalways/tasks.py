from celery.utils.log import get_task_logger

from globalways.utils.celery import get_celery_app

app = get_celery_app()

logger = get_task_logger(__name__)


@app.task
def task_test_result_backend_works():
    return 42


@app.task
def task_test_result_backend_raises():
    raise ValueError("foo")
