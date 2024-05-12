import logging


logging.getLogger('pymongo').setLevel(logging.ERROR)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
