import time
from .. import interface
from .. import Util

def tip_waimai():
    if not will_tip_waimai():
        return False

    # 提示点外卖
    tip_user = 'wxid_lz1szqmjnx4721'

    interface.new_send_msg(tip_user, '到点外卖的时间了，有人要点外卖吗？'.encode(encoding="utf-8"))
    return True

def will_tip_waimai():
    current_time = time.strftime('%H:%M')

    if current_time == "10:31" or current_time == "10:32":
        return True
    return False
