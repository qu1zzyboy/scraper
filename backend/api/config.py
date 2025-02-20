# -*- coding:utf-8 -*-
import os
from datetime import timedelta

import dotenv

from extensions.ext_database import db

dotenv.load_dotenv()

DEFAULTS = {
    'COOKIE_HTTPONLY': 'True',
    'COOKIE_SECURE': 'False',
    'COOKIE_SAMESITE': 'None',
    'DB_USERNAME': 'admin',
    'DB_PASSWORD': 'admin',
    'DB_HOST': 'localhost',
    'DB_PORT': '3306',
    'DB_DATABASE': 'tg',
    'DEPLOY_ENV': 'PRODUCTION',
    'SQLALCHEMY_POOL_SIZE': 10,
    'SQLALCHEMY_ECHO': 'False',
    'LOG_LEVEL': 'DEBUG',
    'WEB_API_CORS_ALLOW_ORIGINS': '*',
    'CONSOLE_CORS_ALLOW_ORIGINS': '*',
}


def get_env(key):
    return os.environ.get(key, DEFAULTS.get(key))


def get_bool_env(key):
    return get_env(key).lower() == 'true'


def get_cors_allow_origins(env, default):
    cors_allow_origins = []
    if get_env(env):
        for origin in get_env(env).split(','):
            cors_allow_origins.append(origin)
    else:
        cors_allow_origins = [default]

    return cors_allow_origins


class Config:
    """Application configuration class."""

    def __init__(self):
        # app settings
        self.CURRENT_VERSION = "0.0.1"
        self.COMMIT_SHA = get_env('COMMIT_SHA')
        self.DEPLOY_ENV = get_env('DEPLOY_ENV')
        self.TESTING = False
        self.LOG_LEVEL = get_env('LOG_LEVEL')
        self.SERVICE_ID= get_env('SERVICE_ID')
        self.MICR_SERVER_URL= get_env('MIRCRO_SERVER_URL')
        self.SECRET_KEY = get_env('SECRET_KEY')
        self.NOSTR_PRIV_KEY = get_env('NOSTR_PRIV_KEY')
        self.NOSTR_RELAY_URIS = get_env('NOSTR_RELAY_URIS')


        # cors settings
        self.CONSOLE_CORS_ALLOW_ORIGINS = get_cors_allow_origins(
            'CONSOLE_CORS_ALLOW_ORIGINS', '*')
        self.WEB_API_CORS_ALLOW_ORIGINS = get_cors_allow_origins(
            'WEB_API_CORS_ALLOW_ORIGINS', '*')

        # database settings
        db_credentials = {
            key: get_env(key) for key in
            ['DB_USERNAME', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_DATABASE']
        }
        
        self.SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{db_credentials['DB_USERNAME']}:{db_credentials['DB_PASSWORD']}@{db_credentials['DB_HOST']}:{db_credentials['DB_PORT']}/{db_credentials['DB_DATABASE']}?charset=utf8mb4"
        self.SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_size': int(get_env('SQLALCHEMY_POOL_SIZE'))}

        self.SQLALCHEMY_ECHO = get_bool_env('SQLALCHEMY_ECHO')
