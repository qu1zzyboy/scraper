# -*- coding:utf-8 -*-
from controllers.service_api.doc import nostrCli, setKeys, setRelayers
from nostr_sdk import *
import asyncio
import os
# if not os.environ.get("DEBUG") or os.environ.get("DEBUG").lower() != 'true':
#     from gevent import monkey
#     monkey.patch_all()

import logging
import json
import threading

from flask import Flask, Response
from flask_cors import CORS

from extensions import ext_migrate, ext_database
from extensions.ext_database import db
import logging

# DO NOT REMOVE BELOW
from models import block
# from events import event_handlers
# DO NOT REMOVE ABOVE

from config import Config
from commands import register_commands
from micro_conn import send_ip_to_microservice
import warnings
warnings.simplefilter("ignore", ResourceWarning)


class PDFIndexer(Flask):
    pass

# -------------
# Configuration
# -------------


# config_type = os.getenv('EDITION', default='SELF_HOSTED')  # ce edition first

# ----------------------------
# Application Factory Function
# ----------------------------


def create_app() -> Flask:
    app = PDFIndexer(__name__)

    app.config.from_object(Config())

    app.secret_key = app.config['SECRET_KEY']

    logging.basicConfig(level=app.config.get('LOG_LEVEL', 'DEBUG'))
    uri = app.config.get("SQLALCHEMY_DATABASE_URI")
    print(f"db uri:{uri}")
    logging.info(f"db uri:{uri}")

    privKey = app.config.get("NOSTR_PRIV_KEY")
    ikeys = Keys.parse(privKey)
    setKeys(ikeys)
    setRelayers(app.config.get("NOSTR_RELAY_URIS"))
    signer = NostrSigner.keys(ikeys)
    nostrCli.signer = signer

    initialize_extensions(app)
    register_blueprints(app)
    register_commands(app)
    app.nostrCli = nostrCli
    return app


def initialize_extensions(app):
    # Since the application instance is now created, pass it to each Flask
    # extension instance to bind it to the Flask application instance (app)
    ext_database.init_app(app)
    ext_migrate.init_app(app, db)


# register blueprint routers
def register_blueprints(app):
    from controllers.service_api import bp as service_api_bp

    CORS(service_api_bp,
         resources={
             r"/*": {"origins": app.config['WEB_API_CORS_ALLOW_ORIGINS']}},
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'PUT', 'POST', 'DELETE', 'OPTIONS', 'PATCH'],
         expose_headers=['X-Version', 'X-Env']
         )
    app.register_blueprint(service_api_bp)


# create app
app = create_app()


@app.after_request
def after_request(response):
    """Add Version headers to the response."""
    response.headers.add('X-Version', app.config['CURRENT_VERSION'])
    response.headers.add('X-Env', app.config['DEPLOY_ENV'])
    return response


@app.route('/health')
def health():
    return Response(json.dumps({
        'status': 'ok',
        'version': app.config['CURRENT_VERSION']
    }), status=200, content_type="application/json")


@app.route('/threads')
def threads():
    num_threads = threading.active_count()
    threads = threading.enumerate()

    thread_list = []
    for thread in threads:
        thread_name = thread.name
        thread_id = thread.ident
        is_alive = thread.is_alive()

        thread_list.append({
            'name': thread_name,
            'id': thread_id,
            'is_alive': is_alive
        })

    return {
        'thread_num': num_threads,
        'threads': thread_list
    }


if __name__ == '__main__':
    send_ip_to_microservice()
    app.run(host='0.0.0.0', port=5001)
