import json
from .. import define
from .. import interface
from .. import mm_pb2
from .. import Util
from bs4 import BeautifulSoup
from .logger_wrapper import logger
from .tip_bot import tips
from urllib.parse import urlencode

# 图灵机器人接口
# TULING_HOST = 'openapi.tuling123.com'
# TULING_API = 'http://openapi.tuling123.com/openapi/api/v2'
# 图灵机器人key
# TULING_KEY = '460a124248234351b2095b57b88cffd2' # 460a124248234351b2095b57b88cffd2

# 通过抓取网页体验地址得到聊天的接口
TULING_HOST = 'biz.turingos.cn'
TULING_API = 'http://biz.turingos.cn/apirobot/dialog/homepage/chat' # http://biz.turingos.cn/chat 体验地址

# 图灵机器人
def tuling_robot(msg):
    # 本条消息是否回复
    need_reply = False
    # 消息内容预处理
    send_to_tuling_content = msg.raw.content
    reply_prefix = ''
    reply_at_wxid = ''
    # 群聊消息:只回复@自己的消息/消息内容过滤掉sender_wxid
    if msg.from_id.id.endswith('@chatroom'):
        # 首先判断本条群聊消息是否at我:
        try:
            soup = BeautifulSoup(msg.ex_info,'html.parser')
            at_user_list = soup.msgsource.atuserlist.contents[0].split(',')
            if Util.wxid in at_user_list:                                                               # 群聊中有@我的消息
                # 群聊消息以'sender_wxid:\n'起始
                send_to_tuling_content = msg.raw.content[msg.raw.content.find('\n') + 1:]
                # 解析@我的人的昵称
                reply_nick_name = Util.find_str(msg.xmlContent, '<pushcontent content="', '在群聊中@了你" nickname="')
                if reply_nick_name:
                    # 回复消息前缀
                    reply_prefix = '@{}'.format(reply_nick_name)                                        # 回复群聊消息时@发消息人
                # 解析@我的人的wxid
                reply_at_wxid = msg.raw.content[:msg.raw.content.find(':\n')]
                # 取@我之后的消息内容
                send_to_tuling_content = msg.raw.content[msg.raw.content.rfind('\u2005') + 1:]           # at格式: @nick_name\u2005

                if reply_prefix and reply_at_wxid:
                    # 本条消息需要回复
                    need_reply = True

        except:
            return
    # 公众号消息不回复
    elif msg.from_id.id.startswith('gh_'):
        return
    else:
        # 本条消息需要回复
        need_reply = True
        pass

    if need_reply:
        # 使用图灵接口获取自动回复信息
        # data = {
        #     'reqType': 0,
        #     'perception':
        #     {
        #         "inputText":
        #         {
        #             "text": send_to_tuling_content
        #         },
        #     },
        #     'userInfo':
        #     {
        #         "apiKey": TULING_KEY,
        #         "userId": Util.GetMd5(msg.from_id.id)
        #     }
        # }

        data = {
            "deviceId": "63ae63ae-63ae-63ae-63ae-63ae63ae63ae",
            "question": send_to_tuling_content
        }

        try:
            # robot_ret = eval(Util.post(TULING_HOST, TULING_API,json.dumps(data)).decode())
            robot_ret = json.loads(Util.post(TULING_HOST, TULING_API, urlencode(data), {'content-type': 'application/x-www-form-urlencoded'}))
            logger.info('tuling api 返回:{}'.format(robot_ret))

            if robot_ret['type'] == 'error':
                message = robot_ret['content']
            elif 4003 == robot_ret['data']['intent']['code']: # 请求次数超限制!
                message = '因个人原因，今天不能陪你聊天了，对不起啦 :('
            else:
                message = robot_ret['data']['results'][0]['values']['text']

            multi_msg = False
            if robot_ret['type'] == 'success' and len(robot_ret['data']['results']) > 1:
                multi_msg = True

            # 自动回消息
            if (multi_msg):
                send_multi_msg(robot_ret['data'], msg, reply_prefix, reply_at_wxid)
            else:
                send_msg(message, msg, reply_prefix, reply_at_wxid)

        except Exception as e:
            logger.info('tuling api 调用异常!', 1)
            print(e)

    return

def send_msg(message, msg, reply_prefix, reply_at_wxid):
    if reply_prefix and reply_at_wxid:
        # 消息前缀: @somebody  并at发消息人
        message = (reply_prefix + ' ' + message)
        interface.new_send_msg(msg.from_id.id, message.encode(encoding="utf-8"), [reply_at_wxid])
    else:
        interface.new_send_msg(msg.from_id.id, message.encode(encoding="utf-8"))

def send_multi_msg(data, msg, reply_prefix, reply_at_wxid):
    for result in data['results']:
        if result['resultType'] == 'text':
            send_msg(result['values']['text'], msg, reply_prefix, reply_at_wxid)
        elif result['resultType'] == 'voice':
            intent = data['intent']
            parameters = intent['parameters']

            title = '请点击查看'
            desc = ''
            if intent['code'] == 200101: # 唱歌
                title = parameters['name']
                desc = parameters['singer']
            elif intent['code'] == 200701: # 跳舞
                title = parameters['song']
                desc = parameters['singer']
            elif intent['code'] == 200201: # 故事
                title = parameters['name']
                desc = parameters['author']

            interface.send_app_msg(msg.from_id.id, title, desc, result['values']['voice'], thumb_url='')

