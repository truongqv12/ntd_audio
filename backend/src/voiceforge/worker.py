import dramatiq
from dramatiq.brokers.redis import RedisBroker

from .config import settings
from .logging_setup import setup_logging

setup_logging()
broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)
