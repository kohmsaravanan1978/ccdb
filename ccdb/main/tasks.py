from globalways.utils.celery import get_celery_app

app = get_celery_app()


@app.task
def send_queue_task(exchange, message_type, payload, source=None):
    from main.queue import send_queue

    send_queue(exchange, message_type, payload, source)
