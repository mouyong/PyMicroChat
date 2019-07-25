import time
from .. import interface
from .. import Util
from .logger_wrapper import logger

current_time = time.strftime('%H:%M')

def tip_success(wxid, msg):
    interface.new_send_msg(wxid, '北京时间 {}，{}'.format(time.strftime("%Y-%m-%d %H:%M:%S"), msg).encode(encoding="utf-8"))

def tips():
    tip_waimai()
    tip_lunch()
    tip_linzi_apply_sms()

# 提示林子申请短信
def tip_linzi_apply_sms():
    current_time = time.strftime('%H:%M')
    time_list = ("21:00", "21:05", "21:10", "21:15", "21:20", "21:25", "21:30", "21:35", "21:40", "21:45", "21:50", "21:55", "22:00")
    if current_time in time_list:
        tip_user = 'fionaguo888' # 小号中的林子账号 id
        # tip_user = 'wxid_lz1szqmjnx4721' # 小号发给大号 =　-　=
        interface.new_send_msg(tip_user, '北京时间 {}，还记得要申请「审核失败的短信」吗？不要忘了哦。后天请假，所以要争取在明天中午前申请下来呀 :)'.format(time.strftime("%Y-%m-%d %H:%M:%S")).encode(encoding="utf-8"))
        tip_success('wxid_lz1szqmjnx4721', '通知林子申请审核短信成功')
        logger.info("通知林子申请审核短信成功")

# 提示吃饭
def tip_lunch():
    logger.debug("北京时间 {}，是否需要通知消息点外卖？{}，是否需要通知消息吃饭？{}".format(time.strftime("%Y-%m-%d %H:%M:%S"), will_tip_waimai(), will_tip_eat()))

    if not will_tip_eat():
        return False

    tip_user = 'wxid_lz1szqmjnx4721' # 小号发给大号 =　-　=
    tip_user = '6608588318@chatroom' # 发 CB-LINK 群
    interface.new_send_msg(tip_user, '北京时间 {} ，到吃饭时间了，有人要去吃饭吗？记得喊我一声，谢谢 :)'.format(time.strftime("%Y-%m-%d %H:%M:%S")).encode(encoding="utf-8"))
    tip_success('wxid_lz1szqmjnx4721', '通知吃饭成功')
    logger.info("通知吃饭成功")
    return True

# 提示点外卖
def tip_waimai():
    if not will_tip_waimai():
        return False

    tip_user = 'wxid_lz1szqmjnx4721' # 小号发给大号 =　-　=
    tip_user = '6608588318@chatroom' # 发 CB-LINK 群
    interface.new_send_msg(tip_user, '北京时间 {} ，到点外卖的时间了，有人要点外卖吗？不然待会忘了点，送到就很晚了哦 :)'.format(current_time).encode(encoding="utf-8"))
    tip_success('wxid_lz1szqmjnx4721', '通知点餐成功')
    logger.info("通知点餐成功")
    return True

# 判断北京时间是否需要提示点外卖
def will_tip_waimai():
    global current_time
    current_time = time.strftime('%H:%M')

    if current_time == "11:00" or current_time == "17:30":
        return True
    return False

# 判断北京时间是否需要提示吃饭
def will_tip_eat():
    global current_time
    current_time = time.strftime('%H:%M')

    if current_time == "12:00" or current_time == "18:30":
        return True
    return False
