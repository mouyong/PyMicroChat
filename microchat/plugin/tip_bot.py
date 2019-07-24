import time
from .. import interface
from .. import Util
from .logger_wrapper import logger

current_time = time.strftime('%H:%M')

def tip_eat():
    tip_waimai()
    tip_lunch()

# 提示吃饭
def tip_lunch():
    logger.debug("当前时间 {}，是否需要通知消息点外卖？{}，是否需要通知消息吃饭？{}".format(current_time, will_tip_waimai(), will_tip_eat()))

    if not will_tip_eat():
        return False

    tip_user = 'wxid_lz1szqmjnx4721' # 小号发给大号 =　-　=
    tip_user = '6608588318@chatroom' # 大号发 CB-LINK 群
    interface.new_send_msg(tip_user, '当前时间 {} ，到吃饭时间了，有人要去吃饭吗？记得喊我一声，谢谢 :)'.format(current_time).encode(encoding="utf-8"))
    return True

# 提示点外卖
def tip_waimai():
    if not will_tip_waimai():
        return False

    tip_user = 'wxid_lz1szqmjnx4721' # 小号发给大号 =　-　=
    tip_user = '6608588318@chatroom' # 大号发 CB-LINK 群
    interface.new_send_msg(tip_user, '当前时间 {} ，到点外卖的时间了，有人要点外卖吗？不然待会忘了点，送到就很晚了哦 :)'.format(current_time).encode(encoding="utf-8"))
    return True

# 判断当前时间是否需要提示点外卖
def will_tip_waimai():
    global current_time
    current_time = time.strftime('%H:%M')

    if current_time == "11:00" or current_time == "17:30":
        return True
    return False

# 判断当前时间是否需要提示吃饭
def will_tip_eat():
    global current_time
    current_time = time.strftime('%H:%M')

    if current_time == "12:00" or current_time == "18:30":
        return True
    return False
