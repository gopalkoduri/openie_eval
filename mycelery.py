from __future__ import absolute_import

from celery import Celery

app = Celery('nerpari',
             broker='amqp://guest:guest@devaraya.s.upf.edu',
             include=['nerpari.nerpari.text_processor'])

# Optional configuration, see the application user guide.
app.conf.update(
    CELERYD_CONCURRENCY=4,
    CELERYD_POOL_RESTARTS=True,
)

if __name__ == '__main__':
    app.start()
