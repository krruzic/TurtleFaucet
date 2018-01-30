from logging.handlers import RotatingFileHandler
from faucet import app
if __name__ == "__main__":
    handler = RotatingFileHandler('faucet.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    app.logger.addHandler(handler)
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.logger.info("App Started!")
    app.run()