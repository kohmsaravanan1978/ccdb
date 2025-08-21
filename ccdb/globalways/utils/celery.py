def get_celery_app():
    import ccdb.celery as mod

    return mod.app
