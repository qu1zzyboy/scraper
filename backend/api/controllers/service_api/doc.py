# -*- coding:utf-8 -*-
import datetime
from typing import List
from flask_restful import reqparse
from . import api
from flask_restful import Resource, marshal_with, fields, marshal
from models.block import Message, update_object_flush
import os
from extensions.ext_database import db
import logging
from sqlalchemy.exc import IntegrityError
from nostr_sdk import *
import asyncio
import hmac
import hashlib
import time
import requests
import json

API_KEY = ''
API_SECRET = ''
API_URL = ''

nostrCli = Client()

messageFields = {
    "id": fields.Integer,
    "group_id": fields.String,
    "user_id": fields.String,
    "username": fields.String,
    "message": fields.String,
    "timestamp": fields.DateTime,
    "created_at": fields.DateTime,
    "updated_at": fields.DateTime,
}

userMessagesFields = {
    "user_id": fields.String,
    "messages": fields.List(fields.Nested(messageFields)),
    "cnt": fields.Integer,
}

userMessagesCntFields = {
    "user_id": fields.String,
    "cnt": fields.Integer,
}

groupMessagesCntFields = {
    "user_msg_cnt": fields.List(fields.Nested(userMessagesCntFields)),
    "group_cnt": fields.Integer,
}


async def sendEvent(tags: List[Tag], message: str):
    builder = EventBuilder.text_note(
        message).tags(tags=tags).sign_with_keys(keys)
    relayUrilist = relayUri.split(',')
    try:
        for uri in relayUrilist:
            logging.info(f"add relay uri: {uri}")
            await nostrCli.add_relay(uri)
    except Exception as e:
        logging.error(f"add relay error: {e}")
    try:
        output = await nostrCli.connect()
        logging.info(f"connect output: {output}")
    except Exception as e:
        logging.error(f"connect error: {e}")
    try:
        output = await nostrCli.send_event(builder)
        logging.info(f"send event output: {output}")
    except Exception as e:
        logging.error(f"send event error: {e}")


class AddMessage(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('group_id', type=str)
        parser.add_argument('user_id', type=str)
        parser.add_argument('username', type=str)
        parser.add_argument('message', type=str)
        args = parser.parse_args()
        timestamp = datetime.datetime.now()
        message = Message(
            group_id=args['group_id'],
            user_id=args['user_id'],
            username=args['username'],
            message=args['message'],
            timestamp=db.func.now(),
        )
        try:
            db.session.add(message)
            db.session.commit()
        except IntegrityError as e:
            logging.error(e)
            db.session.rollback()
            return {'result': 'error'}, 500
        try:
            tagPlatform = Tag.parse(["platform", "telegram"])
            tagT = Tag.parse(["t", timestamp.strftime("%Y-%m-%d %H:%M:%S")])
            tagP = Tag.parse(["p", args['user_id']])
            tagG = Tag.parse(["g", args['group_id']])
            asyncio.run(
                sendEvent([tagPlatform, tagT, tagP, tagG], args['message']))
        except Exception as e:
            logging.error(e)
        return {'result': 'ok'}, 200


class getMessageCntByUser(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', type=str)
        parser.add_argument('group_id', type=str)
        args = parser.parse_args()
        try:
            cnt = db.session.query(Message).filter(
                Message.user_id == args['user_id']).filter(
                Message.group_id == args['group_id']).count()
            result = {
                "user_id": args['user_id'],
                "cnt": cnt
            }
        except Exception as e:
            logging.error(e)
            return {'result': 'error'}, 500
        return marshal(result, userMessagesCntFields)


class getMessageByUser(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', type=str)
        parser.add_argument('group_id', type=str)
        parser.add_argument('page_num', type=int)
        parser.add_argument('page_size', type=int)
        args = parser.parse_args()
        if args['page_num'] < 1:
            args['page_num'] = 1
        try:
            messages = db.session.query(Message).filter(
                Message.user_id == args['user_id']).filter(
                Message.group_id == args['group_id']).order_by(
                Message.id.desc()).offset(
                (args['page_num'] - 1) * args['page_size']).limit(
                args['page_size']).all()
            cnt = db.session.query(Message).filter(
                Message.user_id == args['user_id']).filter(
                Message.group_id == args['group_id']).count()
            result = {
                "user_id": args['user_id'],
                "messages": messages,
                "cnt": cnt
            }
        except Exception as e:
            logging.error(e)
            return {'result': 'error'}, 500
        return marshal(result, userMessagesFields)


class getMessageCntByGroup(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('group_id', type=str)
        args = parser.parse_args()
        user_msg_cnt = []
        try:
            # Query users in the group
            users = db.session.query(Message.user_id).filter(
                Message.group_id == args['group_id']).distinct().all()
            logging.info(f"users: {users}")
            # Query messages count of each user
            for user in users:
                logging.info(f"user: {user}")
                user_id = user[0]
                logging.info(f"user_id: {user_id}")
                cnt = db.session.query(Message).filter(
                    Message.user_id == user_id).filter(
                    Message.group_id == args['group_id']).count()
                user_msg_cnt.append({
                    "user_id": user_id,
                    "cnt": cnt
                })
            totalCnt = db.session.query(Message).filter(
                Message.group_id == args['group_id']).count()

        except Exception as e:
            logging.error(e)
            return {'result': 'error'}, 500

        result = {
            'user_msg_cnt': user_msg_cnt,
            'group_cnt': totalCnt
        }
        return marshal(result, groupMessagesCntFields)


def setKeys(ikeys: Keys):
    global keys
    keys = ikeys


def setRelayers(relayers: str):
    global relayUri
    relayUri = relayers


# POST /api/v1/binding/telegram

# //sign by api key&secret
# //signature = hmac_sha256(api_secret||path||method||body||timestamp)
# //header("X-API-Key", api_key)         // 设置API Key
# //header("X-API-Signature", signature)  // 设置生成的签名
# //header("X-API-Timestamp", timestamp.to_string()) //设置时间戳

# //request body
# {
#     "user_id": "bob001",
#     "token": "",
# }

# //response 200
# {
#     "result": {
#         "user_id": "bob001",
#         "lamport_id": "1"
#     }
# }
def generate_signature(api_secret, path, method, body, timestamp):
    message = f"{api_secret}{path}{method}{body}{timestamp}"
    signature = hmac.new(api_secret.encode(),
                         message.encode(), hashlib.sha256).hexdigest()
    return signature


def postBindingMessage(user_id: str, token: str):
    path = '/api/v1/binding/telegram'
    method = 'POST'
    timestamp = str(int(time.time()))
    body = json.dumps({
        "user_id": user_id,
        "token": token
    })

    signature = generate_signature(API_SECRET, path, method, body, timestamp)

    headers = {
        "X-API-Key": API_KEY,
        "X-API-Signature": signature,
        "X-API-Timestamp": timestamp,
        "Content-Type": "application/json"
    }
    response = requests.post(API_URL, headers=headers, data=body)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

class Ping(Resource):
    def get(self):
        return {'message': 'pong'}, 200

api.add_resource(Ping, '/ping')
api.add_resource(AddMessage, '/add_message')
api.add_resource(getMessageByUser, '/get_message_by_user')
api.add_resource(getMessageCntByGroup, '/get_message_cnt')
api.add_resource(getMessageCntByUser, '/get_message_cnt_by_user')