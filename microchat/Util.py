import logging
import http.client
import time
import hashlib
import zlib
import struct
import os
import sys
import webbrowser
import ctypes
import platform
import subprocess
import sqlite3
from . import define
from . import dns_ip
from Crypto.Cipher import AES, DES3
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as Cipher_pkcs1_v1_5
from google.protobuf.internal import decoder, encoder
from ctypes import *
from .plugin.logger_wrapper import logger
from .ecdh import ecdh

################################全局变量################################
# cgi http头
headers = {
    "Accept": "*/*",
    "Cache-Control": "no-cache",
    "Connection": "close",
    "Content-type": "application/octet-stream",
    "User-Agent": "MicroMessenger Client"
}

# 好友类型
CONTACT_TYPE_ALL = 0xFFFF  # 所有好友
CONTACT_TYPE_FRIEND = 1  # 朋友
CONTACT_TYPE_CHATROOM = 2  # 群聊
CONTACT_TYPE_OFFICAL = 4  # 公众号
CONTACT_TYPE_BLACKLIST = 8  # 黑名单中的好友
CONTACT_TYPE_DELETED = 16  # 已删除的好友

# ECDH key
EcdhPriKey = b''
EcdhPubKey = b''

# session key(封包解密时的aes key/iv)
sessionKey = b''

# cookie(登陆成功后返回,通常长15字节)
cookie = b''

# uin
uin = 0

# wxid
wxid = ''

# sqlite3数据库
conn = None


########################################################################

# md5
def GetMd5(src):
    m1 = hashlib.md5()
    m1.update(src.encode('utf-8'))
    return m1.hexdigest()


# padding
def pad(s): return s + bytes([16 - len(s) % 16] * (16 - len(s) % 16))
def unpad(s): return s[0:(len(s) - s[-1])]

# 先压缩后AES-128-CBC加密
def compress_and_aes(src, key):
    compressData = zlib.compress(src)
    aes_obj = AES.new(key, AES.MODE_CBC, key)                                                   # IV与key相同
    encrypt_buf = aes_obj.encrypt(pad(compressData))
    return (encrypt_buf, len(compressData))                                                     # 需要返回压缩后protobuf长度,组包时使用

# 不压缩AES-128-CBC加密
def aes(src, key):
    aes_obj = AES.new(key, AES.MODE_CBC, key)                                                   # IV与key相同
    encrypt_buf = aes_obj.encrypt(pad(src))
    return encrypt_buf

# 先压缩后RSA加密
def compress_and_rsa(src):
    compressData = zlib.compress(src)
    rsakey = RSA.construct((int(define.__LOGIN_RSA_VER158_KEY_N__, 16), define.__LOGIN_RSA_VER158_KEY_E__))
    cipher = Cipher_pkcs1_v1_5.new(rsakey)
    encrypt_buf = cipher.encrypt(compressData)
    return encrypt_buf

# 不压缩RSA2048加密
def rsa(src):
    rsakey = RSA.construct((int(define.__LOGIN_RSA_VER158_KEY_N__, 16), define.__LOGIN_RSA_VER158_KEY_E__))
    cipher = Cipher_pkcs1_v1_5.new(rsakey)
    encrypt_buf = cipher.encrypt(src)
    return encrypt_buf

# AES-128-CBC解密解压缩
def decompress_and_aesDecrypt(src, key):
    aes_obj = AES.new(key, AES.MODE_CBC, key)                                                   # IV与key相同
    decrypt_buf = aes_obj.decrypt(src)
    return zlib.decompress(unpad(decrypt_buf))

# AES-128-CBC解密
def aesDecrypt(src, key):
    aes_obj = AES.new(key, AES.MODE_CBC, key)                                                   # IV与key相同
    decrypt_buf = aes_obj.decrypt(src)
    return unpad(decrypt_buf)

# HTTP短链接发包
def mmPost(cgi, data):
    ret = False
    retry = 3
    response = b''
    while not ret and retry > 0:
        retry = retry - 1
        try:
            conn = http.client.HTTPConnection(dns_ip.fetch_shortlink_ip(), timeout=3)
            conn.request("POST", cgi, data, headers)
            response = conn.getresponse().read()
            conn.close()
            ret = True
        except Exception as e:
            if 'timed out' == str(e):
                logger.info('{}请求超时,正在尝试重新发起请求,剩余尝试次数{}次'.format(cgi, retry), 11)
            else:
                raise RuntimeError('mmPost Error!!!')
    return response

# HTTP短链接发包
def post(host, api, data, head=''):
    try:
        conn = http.client.HTTPConnection(host, timeout=2)
        if head:
            conn.request("POST", api, data, head)
        else:
            conn.request("POST", api, data)
        response = conn.getresponse().read()
        conn.close()
        return response
    except:
        logger.info('{}请求失败!'.format(api) ,11)
        return b''


# 退出程序
def ExitProcess():
    logger.info('===========bye===========')
    os.system("pause")
    sys.exit()

# 使用IE浏览器访问网页(阻塞)
def OpenIE(url):
    logger.info("授权链接：{}".format(url))
    subprocess.call('python3 ./microchat/plugin/browser.py {}'.format(url))

# 使用c接口生成ECDH本地密钥对
def GenEcdhKey(old=False):
    global EcdhPriKey, EcdhPubKey
    if old:
        # 载入c模块
        loader = ctypes.cdll.LoadLibrary
        if platform.architecture()[0] == '64bit':
            lib = loader("./microchat/dll/ecdh_x64.dll")
        else:
            lib = loader("./microchat/dll/ecdh_x32.dll")
        # 申请内存
        priKey = bytes(bytearray(2048))                                                         # 存放本地DH私钥
        pubKey = bytes(bytearray(2048))                                                         # 存放本地DH公钥
        lenPri = c_int(0)                                                                       # 存放本地DH私钥长度
        lenPub = c_int(0)                                                                       # 存放本地DH公钥长度
        # 转成c指针传参
        pri = c_char_p(priKey)
        pub = c_char_p(pubKey)
        pLenPri = pointer(lenPri)
        pLenPub = pointer(lenPub)
        # secp224r1 ECC算法
        nid = 713
        # c函数原型:bool GenEcdh(int nid, unsigned char *szPriKey, int *pLenPri, unsigned char *szPubKey, int *pLenPub);
        bRet = lib.GenEcdh(nid, pri, pLenPri, pub, pLenPub)
        if bRet:
            # 从c指针取结果
            EcdhPriKey = priKey[:lenPri.value]
            EcdhPubKey = pubKey[:lenPub.value]
        return bRet
    else:

        try:
            pub_key, len_pub, pri_key, len_pri = ecdh.gen_ecdh(713)
            EcdhPubKey = pub_key[:len_pub]
            EcdhPriKey = pri_key[:len_pri]
            return True
        except Exception as e:
            print(e)
            return False


# 密钥协商
def DoEcdh(serverEcdhPubKey, old=False):
    if old:
        EcdhShareKey = b''
        # 载入c模块
        loader = ctypes.cdll.LoadLibrary
        if platform.architecture()[0] == '64bit':
            lib = loader("./microchat/dll/ecdh_x64.dll")
        else:
            lib = loader("./microchat/dll/ecdh_x32.dll") #修改在32环境下找不到ecdh_x32.dll文件 by luckyfish 2018-04-02
        # 申请内存
        shareKey = bytes(bytearray(2048))                                                       # 存放密钥协商结果
        lenShareKey = c_int(0)                                                                  # 存放共享密钥长度
        # 转成c指针传参
        pShareKey = c_char_p(shareKey)
        pLenShareKey = pointer(lenShareKey)
        pri = c_char_p(EcdhPriKey)
        pub = c_char_p(serverEcdhPubKey)
        # secp224r1 ECC算法
        nid = 713
        # c函数原型:bool DoEcdh(int nid, unsigned char * szServerPubKey, int nLenServerPub, unsigned char * szLocalPriKey, int nLenLocalPri, unsigned char * szShareKey, int *pLenShareKey);
        bRet = lib.DoEcdh(nid, pub, len(serverEcdhPubKey), pri,len(EcdhPriKey), pShareKey, pLenShareKey)
        if bRet:
            # 从c指针取结果
            EcdhShareKey = shareKey[:lenShareKey.value]
        return EcdhShareKey
    else:
        try:
            _, EcdhShareKey = ecdh.do_ecdh(713, serverEcdhPubKey, EcdhPriKey)
            return EcdhShareKey
        except Exception as e:
            print(e)
            return b''


# bytes转hex输出
def b2hex(s): return ''.join(["%02X " % x for x in s]).strip()

# sqlite3数据库初始化
def init_db():
    global conn
    # 建db文件夹
    if not os.path.exists(os.getcwd() + '/db'):
        os.mkdir(os.getcwd() + '/db')
    # 建库
    conn = sqlite3.connect('./db/mm_{}.db'.format(wxid))
    cur = conn.cursor()
    # 建消息表
    cur.execute('create table if not exists msg(svrid bigint unique,clientMsgId varchar(1024),utc integer,createtime varchar(1024),fromWxid varchar(1024),toWxid varchar(1024),type integer,content text(65535))')
    # 建联系人表
    cur.execute('create table if not exists contact(wxid varchar(1024) unique,nick_name varchar(1024),remark_name varchar(1024),alias varchar(1024),avatar_big varchar(1024),v1_name varchar(1024),type integer default(0),sex integer,country varchar(1024),sheng varchar(1024),shi varchar(1024),qianming varchar(2048),register_body varchar(1024),src integer,chatroom_owner varchar(1024),chatroom_serverVer integer,chatroom_max_member integer,chatroom_member_cnt integer)')
    # 建sync key表
    cur.execute('create table if not exists synckey(key varchar(4096))')
    return

# 获取sync key
def get_sync_key():
    cur = conn.cursor()
    cur.execute('select * from synckey')
    row = cur.fetchone()
    if row:
        return bytes.fromhex(row[0])
    return b''

# 刷新sync key
def set_sync_key(key):
    cur = conn.cursor()
    cur.execute('delete from synckey')
    cur.execute('insert into synckey(key) values("{}")'.format(b2hex(key)))
    conn.commit()
    return

# 保存消息
def insert_msg_to_db(svrid, utc, from_wxid, to_wxid, type, content, client_msg_id = ''):
    cur = conn.cursor()
    try:
        cur.execute("insert into msg(svrid, clientMsgId, utc, createtime, fromWxid, toWxid, type, content) values('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')".format(
            svrid, client_msg_id, utc, utc_to_local_time(utc), from_wxid, to_wxid, type, content))
        conn.commit()
    except Exception as e:
        logger.info('insert_msg_to_db error:{}'.format(str(e)))
    return

# 保存/刷新好友消息
def insert_contact_info_to_db(wxid, nick_name, remark_name, alias, avatar_big, v1_name, type, sex, country, sheng, shi, qianming, register_body, src, chatroom_owner, chatroom_serverVer, chatroom_max_member, chatroom_member_cnt):
    cur = conn.cursor()
    try:
        # 先删除旧的信息
        cur.execute("delete from contact where wxid = '{}'".format(wxid))
        # 插入最新联系人数据
        cur.execute("insert into contact(wxid,nick_name,remark_name,alias,avatar_big,v1_name,type,sex,country,sheng,shi,qianming,register_body,src,chatroom_owner,chatroom_serverVer,chatroom_max_member,chatroom_member_cnt) values('{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}','{}')".format(
            wxid, nick_name, remark_name, alias, avatar_big, v1_name, type, sex, country, sheng, shi, qianming, register_body, src, chatroom_owner, chatroom_serverVer, chatroom_max_member, chatroom_member_cnt))
        conn.commit()
    except Exception as e:
        logger.info('insert_contact_info_to_db error:{}'.format(str(e)))
    return

# utc转本地时间
def utc_to_local_time(utc):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(utc))

# 获取本地时间
def get_utc():
    return int(time.time())

# str转bytes
def str2bytes(s): return bytes(s, encoding="utf8")

# 获取添加好友方式
def get_way(src):
    if src in define.WAY.keys() or (src - 1000000) in define.WAY.keys():
        if src > 1000000:
            return '对方通过' + define.WAY[src-1000000] + '添加'
        elif src:
            return '通过' + define.WAY[src] + '添加'
    return define.WAY[0]

# 获取好友类型:
def get_frient_type(wxid):
    cur = conn.cursor()
    cur.execute("select type from contact where wxid = '{}'".format(wxid))
    row = cur.fetchone()
    if row:
        return row[0]
    else:
        return 0

# 是否在我的好友列表中
def is_in_my_friend_list(type):
    # type的最后一bit是1表示对方在我的好友列表中
    return (type & 1)

# 对方是否在我的黑名单中
def is_in_blacklist(type):
    return (type & (1 << 3))

# 获取好友列表wxid,昵称,备注,alias,v1_name,头像
def get_contact(contact_type):
    cur = conn.cursor()
    rows = []
    if contact_type & CONTACT_TYPE_FRIEND:                                                  # 返回好友列表
        cur.execute("select wxid,nick_name,remark_name,alias,v1_name,avatar_big from contact where wxid not like '%%@chatroom' and wxid not like 'gh_%%' and (type & 8) = 0 and (type & 1)")
        rows = rows + cur.fetchall()
    if contact_type & CONTACT_TYPE_CHATROOM:                                                # 返回群聊列表
        cur.execute("select wxid,nick_name,remark_name,alias,v1_name,avatar_big from contact where wxid like '%%@chatroom' and (type & 1)")
        rows = rows + cur.fetchall()
    if contact_type & CONTACT_TYPE_OFFICAL:                                                 # 返回公众号列表
        cur.execute("select wxid,nick_name,remark_name,alias,v1_name,avatar_big from contact where wxid like 'gh_%%' and (type & 1)")
        rows = rows + cur.fetchall()
    if contact_type & CONTACT_TYPE_BLACKLIST:                                               # 返回黑名单列表
        cur.execute("select wxid,nick_name,remark_name,alias,v1_name,avatar_big from contact where wxid not like '%%@chatroom' and wxid not like 'gh_%%' and (type & 8)")
        rows = rows + cur.fetchall()
    if contact_type & CONTACT_TYPE_DELETED:                                                 # 返回已删除好友列表(非主动删除对方?)
        cur.execute("select wxid,nick_name,remark_name,alias,v1_name,avatar_big from contact where wxid not like '%%@chatroom' and wxid not like 'gh_%%' and (type & 1) = 0")
        rows = rows + cur.fetchall()
    return rows

# 截取字符串
def find_str(src,start,end):
    try:
        if src.find(start)> -1:
            start_index = src.find(start) + len(start)
            if end and src.find(start)> -1:
                end_index = src.find(end,start_index)
                return src[start_index:end_index]
            else:
                return src[start_index:]
    except:
        pass
    return ''

# 转账相关请求参数签名算法
def SignWith3Des(src):
    # 首先对字符串取MD5
    raw_buf = hashlib.md5(src.encode()).digest()
    # 对16字节的md5做bcd2ascii
    bcd_to_ascii = bytearray(32)
    for i in range(len(raw_buf)):
        bcd_to_ascii[2*i]   = raw_buf[i]>>4
        bcd_to_ascii[2*i+1] = raw_buf[i] & 0xf
    # hex_to_bin转换加密key
    key = bytes.fromhex('3ECA2F6FFA6D4952ABBACA5A7B067D23')
    # 对32字节的bcd_to_ascii做Triple DES加密(3DES/ECB/NoPadding)
    des3 = DES3.new(key, DES3.MODE_ECB)
    enc_bytes = des3.encrypt(bcd_to_ascii)
    # bin_to_hex得到最终加密结果
    enc_buf = ''.join(["%02X" % x for x in enc_bytes]).strip()
    return enc_buf

# 根据svrid查询client_msg_id
def get_client_msg_id(svrid):
    try:
        cur = conn.cursor()
        cur.execute("select clientMsgId from msg where svrid = '{}'".format(svrid))
        row = cur.fetchone()
        if row:
            return row[0]
    except:
        pass
    return ''
