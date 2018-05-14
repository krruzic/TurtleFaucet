import logging
from logging.handlers import RotatingFileHandler
from faucet import app as application

if __name__ == "__main__":
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
    handler = RotatingFileHandler('faucet.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    application.logger.addHandler(handler)
    application.logger.setLevel(logging.DEBUG)
    application.logger.addHandler(handler)
    application.logger.info("App Started!")
    application.run()
