import json, base64, time
import requests as req
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import re
import traceback
from io import BytesIO
import pymysql
import datetime
import random

from hoshino.typing import CQEvent, MessageSegment
from hoshino import Service, priv, config, get_self_ids, get_bot

from .config import bot_db, pjsk_predit_link
import asyncio

help_str = """广西吗了科技 世界计划助手
[/pjsk绑定 <id>] 绑定世界计划(日服)账号至bot
[/pjskpf] 查询个人信息，亦可直接使用 [个人信息]
[/pjsk 比赛抽歌 <最低难度> <最高难度> <难度级别(可选)>] 从选定的范围进行比赛随机抽歌(7首)
""".strip()

sv = Service(
    name = 'pjsk信息查询',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.SUPERUSER, #管理权限
    visible = False, #False隐藏
    enable_on_default = True, #是否默认启用
    bundle = '娱乐', #属于哪一类
    help_= help_str.strip())

def circle_corner(img, radii):  #把原图片变成圆角，这个函数是从网上找的，原址 https://www.pyget.cn/p/185266
    """
    圆角处理
    :param img: 源图象。
    :param radii: 半径，如：30。
    :return: 返回一个圆角处理后的图象。
    """
    # 画圆（用于分离4个角）
    circle = Image.new('L', (radii * 2, radii * 2), 0)  # 创建一个黑色背景的画布
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radii * 2, radii * 2), fill=255)  # 画白色圆形
    # 原图
    img = img.convert("RGBA")
    w, h = img.size
    # 画4个角（将整圆分离为4个部分）
    alpha = Image.new('L', img.size, 255)
    alpha.paste(circle.crop((0, 0, radii, radii)), (0, 0))  # 左上角
    alpha.paste(circle.crop((radii, 0, radii * 2, radii)), (w - radii, 0))  # 右上角
    alpha.paste(circle.crop((radii, radii, radii * 2, radii * 2)), (w - radii, h - radii))  # 右下角
    alpha.paste(circle.crop((0, radii, radii, radii * 2)), (0, h - radii))  # 左下角
    # alpha.show()
    img.putalpha(alpha)  # 白色区域透明可见，黑色区域不可见
    return img

@sv.on_fullmatch('/pjsk help')
async def pjsk_help(bot, ev):
    await bot.send(ev, help_str)
    
def circle_corner(img, radii):  #把原图片变成圆角，这个函数是从网上找的，原址 https://www.pyget.cn/p/185266
    """
    圆角处理
    :param img: 源图象。
    :param radii: 半径，如：30。
    :return: 返回一个圆角处理后的图象。
    """
    # 画圆（用于分离4个角）
    circle = Image.new('L', (radii * 2, radii * 2), 0)  # 创建一个黑色背景的画布
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radii * 2, radii * 2), fill=255)  # 画白色圆形
    # 原图
    img = img.convert("RGBA")
    w, h = img.size
    # 画4个角（将整圆分离为4个部分）
    alpha = Image.new('L', img.size, 255)
    alpha.paste(circle.crop((0, 0, radii, radii)), (0, 0))  # 左上角
    alpha.paste(circle.crop((radii, 0, radii * 2, radii)), (w - radii, 0))  # 右上角
    alpha.paste(circle.crop((radii, radii, radii * 2, radii * 2)), (w - radii, h - radii))  # 右下角
    alpha.paste(circle.crop((0, radii, radii, radii * 2)), (0, h - radii))  # 左下角
    # alpha.show()
    img.putalpha(alpha)  # 白色区域透明可见，黑色区域不可见
    return img

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
url_getmD = 'https://musics.pjsekai.moe/musicDifficulties.json'
url_getmc = 'https://musics.pjsekai.moe/musics.json'
url_e_data = 'https://database.pjsekai.moe/events.json'
color={"ap":"#d89aef","fc":"#ef8cee","clr":"#f0d873","all":"#6be1d9"}
load_path = os.path.dirname(__file__)     #更改为自动获取

def save_request(filename,byte):
    '''
    保存request的二进制数据到文件
    :param filename: 需要保存的文件名路径
    :param byte: 需要保存的二进制数据
    '''
    with open(load_path+f'\\{filename}','wb') as f:
        f.write(byte)

music_difficulties = ''
musics = ''
def update_musicdb():
    '''更新乐曲数据库'''
    global music_difficulties,musics
    try:
        music_difficulties_raw = req.get("https://sekai-world.github.io/sekai-master-db-diff/musicDifficulties.json").content
        musics_raw = req.get("https://sekai-world.github.io/sekai-master-db-diff/musics.json").content
        save_request('musicDifficulties.json',music_difficulties_raw)
        save_request('musics.json',musics_raw)
    except:
        music_difficulties_raw = open(load_path + '\\musicDifficulties.json', encoding='UTF-8').read()
        musics_raw = open(load_path + '\\musics.json', encoding='UTF-8').read()
    music_difficulties = json.loads(music_difficulties_raw)
    musics = json.loads(musics_raw)
#初始化时尝试更新一次musicdb
update_musicdb()

@sv.on_fullmatch(('/pjsk refresh cache'))
async def refresh_cache(bot, ev):
    try:
        update_musicdb()
        await bot.send(ev, '刷新歌曲缓存成功')
    except Exception as e:
        await bot.send(ev, '刷新歌曲缓存失败')
        print(e)

def id_search_song(music_id):
    '''
    乐曲id找歌，从musics.json返回对应单曲的详情数据
    :params music_id: 乐曲id
    :return: 单曲详情数据
    '''
    for music in musics:
        if music['id'] == music_id:
            return music

def id_search_diff(music_id):
    '''
    乐曲id找难度，从musicDifficulties.json返回对应单曲的难度数据
    :params music_id: 乐曲id
    :return: 单曲谱面数据字典list
    '''
    charts_list = []
    for charts in music_difficulties:
        if charts['musicId'] == music_id:
            charts_list.append(charts)
    return charts_list

async def get_usericon(user):
    """通过Q号获取QQ头像。"""
    p_icon = req.get(f'https://q1.qlogo.cn/g?b=qq&nk={user}&s=640')
    return p_icon

def data_req(url):  #现场请求相关数据，耗时较长，但是数据永远是最新的
    temp_res = req.get(url, headers = headers)
    re = json.loads(temp_res.text)
    return re

# # 遍历账号池对比UID，若已有绑定返回False
# def a_check(uid,account): #bot, ev: CQEvent
#     n_a = len(account)
#     for a in range(n_a):
#         if uid != account[a]["qqid"]:
#             continue
#         else:
#             return False
#     else:
#         return True
    
async def pjsk_uid_check(pjsk_uid):
    url = f'https://api.unipjsk.com/api/user/{{user_id}}/{pjsk_uid}/profile'
    try:
        getdata = req.get(url)
        data1 = json.loads(getdata.text)
        u = data1['user']['name']
        return u
    except:
        return False


@sv.on_prefix(('/pjsk绑定','/pjsk bind'))
async def pjsk_bind(bot, ev: CQEvent):
    #绑定PJSK ID到QQ上（使用本地数据库）
    input_id_raw = ev.message.extract_plain_text().strip()
    if len(input_id_raw) == 0:
        await bot.send(ev, '请输入您的PJSK ID！')
    elif input_id_raw.isdigit() == True:
        input_id = int(input_id_raw)
        u_name = await pjsk_uid_check(input_id)
        if not u_name:
            await bot.send(ev, "无法查询到对应UID绑定的PJSK账号，请检查您的PJSK UID是否正确，或是当前Unibot数据API是否正常")
            return 0
        db_bot = pymysql.connect(
            host=bot_db.host,
            port=bot_db.port,
            user=bot_db.user,
            password=bot_db.password,
            database=bot_db.database
        )
        apu_cursor = db_bot.cursor()
        qqid = ev.user_id
        apu_getuid_sql = "SELECT QQ,pjsk_uid FROM grxx WHERE QQ = %s" % (qqid)
        # 先执行一次查询，查询是否已经签到注册过
        try:
            apu_cursor.execute(apu_getuid_sql)
            result_cx = apu_cursor.fetchall()
            apu_bind_sql = "UPDATE `grxx` SET `pjsk_uid`='%s' WHERE `QQ`='%s'" % (input_id, qqid)
            if not result_cx:
                await bot.send(ev, "无法查询到您的数据，请先发送“签到”来注册bot功能", at_sender = True)
            elif result_cx[0][1] == None:
                # 在此后进行绑定语句编程
                try:
                    apu_cursor.execute(apu_bind_sql)
                    db_bot.commit()
                    await bot.send(ev, f'已为您绑定成功账号:{u_name}')
                except Exception as e:
                    await bot.send(ev, f'绑定过程中发生错误:{e}')
            else:
                await bot.send(ev, f'您已经绑定过了，即将为您重新绑定')
                try:
                    apu_cursor.execute(apu_bind_sql)
                    db_bot.commit()
                    await bot.send(ev, f'已为您绑定成功账号:{u_name}')
                except Exception as e:
                    await bot.send(ev, f'重新绑定过程中发生错误:{e}')
        except Exception as e:
            await bot.send(ev, f'查询过程中发生错误:{e}')
        db_bot.close()
    else:
        await bot.send(ev, '请输入纯数字的PJSK ID')

async def lg(user_id):  
    """获取PJSK昵称ID的函数。

    若玩家不存在，则返回``FALSE``。
    ``user_id``:纯数字的PJSK_ID
    """
    qqid = user_id
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    apu_getuid_sql = "SELECT QQ,pjsk_uid FROM grxx WHERE QQ = %s" % (qqid)
    # 先执行一次查询，查询是否已经签到注册过
    try:
        apu_cursor.execute(apu_getuid_sql)
        result_cx = apu_cursor.fetchall()
        pjsk_uid = result_cx[0][1]
        db_bot.close()
        if pjsk_uid:
            return pjsk_uid
        else:
            return False
    except Exception as e:
        print(e)
        db_bot.close()
        return 0

# 从全部卡面中遍历获取ID对应的图片资源，并从API中获取后return
async def getLeaderIcon(data1):
    leaderId = data1['userDecks'][0]["leader"]
    for  level in data1["userCards"]:
        if leaderId == level["cardId"]:
            card_type = level["defaultImage"]
            break
    getCd = req.get('https://database.pjsekai.moe/cards.json') # 返回全部卡面信息的API
    cards_infomation = json.loads(getCd.text)
    for sc in cards_infomation:
        if leaderId == sc["id"]:
            if card_type == 'original':
                url = f'https://asset.pjsekai.moe/startapp/thumbnail/chara/{sc["assetbundleName"]}_normal.png'
            elif card_type == "special_training":
                url = f'https://asset.pjsekai.moe/startapp/thumbnail/chara/{sc["assetbundleName"]}_after_training.png'
            l_icon = req.get(url)
            return l_icon

async def countFlg(_list,TAG,difficulty,data1):
    a_count = 0
    for result in data1['userMusicResults']:
            if result['musicDifficulty'] == difficulty:
                if result[TAG] == True and result['musicId'] not in _list:
                    a_count = a_count + 1
                    _list.append(result['musicId'])
    return _list,a_count

async def countClear(_list,difficulty,data1):
    a_count = 0
    for result in data1['userMusicResults']:
            if result['musicDifficulty'] == difficulty:
                if result['fullComboFlg'] == True and result['musicId'] not in _list:
                    a_count = a_count + 1
                    _list.append(result['musicId'])
                if result['playResult'] == 'clear' and result['musicId'] not in _list:
                    a_count = a_count + 1
                    _list.append(result['musicId'])
    for a in _list:
        if _list.count(a) >= 2:
            a_count = a_count - _list.count(a) + 1
    return _list,a_count

@sv.on_prefix(("/pjskpf","个人信息"))
async def pj_profileGet(bot,ev:CQEvent):
    #逮捕
    uid = ev.user_id
    msgid = ev.message_id
    userID = await lg(uid)

    selection = 0
    
    for i in ev.message:
        if i.type == 'at':
            uid = int(i.data['qq'])
            userID = await lg(uid)
            break   

    _uID = ev.message.extract_plain_text().strip()
    if _uID != "":
        _userID = int(_uID)
        if isinstance(_userID,int) and _userID > 1000000000000000:
            userID = _userID
            selection = 1
        else:
            return await bot.send(ev,f'UID格式错误')

     
    
    if userID == 0:
        await bot.send(ev,f"没有绑定捏\n输入“/pjsk绑定+pjskID”来绑定吧~")
    else:
        await bot.set_group_reaction(group_id = ev.group_id, message_id = msgid, code ='124')
        try:
            url = f'https://api.unipjsk.com/api/user/{{user_id}}/{userID}/profile'
            getdata = req.get(url)
            data1 = json.loads(getdata.text)


            dict_backup=[]
            difficulty = ['easy','normal','hard','expert','master','append'] #TODO: APD难度
            for tag in difficulty:
                clr_count = 0
                fc_count = 0
                ap_count = 0
                # clr_list = []
                # fc_list = []
                # ap_list = []

                # 旧API不再使用，改用新API直接返回数据
                # fc_list,fc_count = await countFlg(fc_list,'fullComboFlg',tag,data1)
                # ap_list,ap_count = await countFlg(ap_list,'fullPerfectFlg',tag,data1)
                # clr_list,clr_count = await countClear(clr_list,tag,data1)
                for result in data1['userMusicDifficultyClearCount']:
                    if result['musicDifficultyType'] == tag:
                        fc_count = result['fullCombo']
                        ap_count = result['allPerfect']
                        clr_count = result['liveClear']

                dict_backup.append({tag:{'fc':fc_count,'ap':ap_count,'clear':clr_count}})
            #print(dict_backup)
            
            # profile_image= Image.open(load_path+'\\test1.png')
            new_pimage = load_path+'\\pjsk_profile_new.png'
            profile_image = Image.open(new_pimage)

            if selection == 0:
                picon = Image.open(BytesIO((await get_usericon(f'{uid}')).content)) #####
            else:
                picon = Image.open(BytesIO((await getLeaderIcon(data1)).content))
            
            num_font = ImageFont.truetype(load_path+'\\qiantu_houheiti.ttf',size=50) # 完成数字字体
            name_font = ImageFont.truetype(load_path+'\\MotoyaLMaru.ttf',size=47) # 名称字体
            rank_font = ImageFont.truetype(load_path+'\\FOT-NewRodin-Pro.otf',size=70) # rank字体
            word_font = ImageFont.truetype(load_path+'\\MotoyaLMaru.ttf',size=32)
            draw = ImageDraw.Draw(profile_image)
            draw_icon = ImageDraw.Draw(picon)
            
            u = data1['user']['name'].encode("utf-8")
            draw.text((290,605),data1['user']['name'],'#7C7E8F',font=name_font) # 绘制名字

            draw.text((658,348),str(data1['user']['rank']),'#FFFFFF',font=rank_font) # 绘制rank
            x_font = ImageFont.truetype(load_path+'\\MotoyaLMaru.ttf',size=40) # twitterID字体
            draw.text((379,745),str(data1['userProfile']['twitterId']),'#7C7E8F',font=x_font) # 绘制twitterID



            
            async def measure(msg, font_size, img_width):
                '''
                :params msg: 字符串
                :params font_size: 字体大小
                :params img_width: 图片宽度
                :return: 返回一个列表，列表中包含字符串中需要换行的字符的位置
                '''
                # 初始化变量i为0，l为msg的长度，length为0，positions为空列表
                i = 0
                l = len(msg)
                length = 0
                positions = []
                # 循环遍历msg
                while i < l :
                    # 如果msg[i]是数字或字母，则length加上font_size的一半
                    if re.search(r'[0-9a-zA-Z]', msg[i]):
                        length += font_size // 2
                    # 否则length加上font_size
                    else:
                        length += font_size
                    # 如果length大于等于img_width，则将i添加到positions中，length置为0，i减1
                    if length >= img_width:
                        positions.append(i)
                        length = 0
                        i -= 1
                    # i加1
                    i += 1
                # 返回positions
                return positions

            #个人简介
            
            word_text = Image.new(mode='RGBA', size=(710, 248)) # 个人简介背景(透明)
            draw1 = ImageDraw.Draw(word_text)
            

            msg = data1['userProfile']['word'] # 获取个人简介
            positions = await measure(msg,32,660)
            str_list = list(msg)
            for pos in positions:
                str_list.insert(pos,'\n')
            msg = "".join(str_list)  

            draw1.text((0,0), msg, "#7c7e8f", font=word_font)
            profile_image.paste(word_text, (1068,592), word_text)
            

            def draw_musicsCompleted():
                x = 0
                for tag in difficulty:
                    for pdata in dict_backup[x]: # 遍历 依次取出easy normal hard exp mas apd
                        if tag != 'append' and x != 5:
                            y = 0
                            for ptag in ['clear','fc','ap']:
                                dif_num = str(dict_backup[x][pdata][ptag])
                                dif_num_x1,dif_num_y1,dif_num_x2,dif_num_y2 = num_font.getbbox(dif_num)
                                draw.text((258 - (dif_num_x2-dif_num_x1)/2 + x * 143, 1222 + y * 230),dif_num,'#7c7e8f',font=num_font)
                                y = y + 1
                        else: # 让我们单独处理apd！
                            y = 0
                            for ptag in ['clear','fc','ap']:
                                dif_num = str(dict_backup[x][pdata][ptag])
                                dif_num_x1,dif_num_y1,dif_num_x2,dif_num_y2 = num_font.getbbox(dif_num)
                                draw.text((1003 - (dif_num_x2-dif_num_x1)/2, 1222 + y * 230),dif_num,'#7c7e8f',font=num_font)
                                y = y + 1
                    x = x + 1
            character_rank_font = ImageFont.truetype(load_path+'\\MotoyaLMaru.ttf',size=25)
            def characterdataGet():
                # 遍历data1字典中的'userCharacters'键对应的列表
                for i in data1['userCharacters']:
                    # 如果'characterId'能被4整除
                    if i["characterId"] % 4 == 0 and i["characterId"] <= 20:
                        # 固定生成在对应x位置，计算y坐标
                        x = 1319 + (141 * 3)
                        y = 1332 + (95 * (((i["characterId"])// 4)-1))
                    elif i["characterId"] % 4 != 0 and i["characterId"] <= 20:
                        # 计算x坐标
                        x = 1319 + (141 * ((((i["characterId"])) % 4)-1))
                        # 计算y坐标
                        y = 1332 + (95 * (((i["characterId"])//4)))
                    else:
                        # 让我们绘制v家
                        x = 1233 + (((i["characterId"])-21) * 116)
                        y = 1241
                    # 在指定位置绘制文本
                    draw.text((x, y),str(i['characterRank']),"#FFFFFF",font=character_rank_font)

            

            draw_musicsCompleted()
            characterdataGet()
            picon = picon.resize((250,250),Image.Resampling.LANCZOS)
            picon = circle_corner(picon, 20)
            profile_image.paste(picon, (253,185), picon)
            buf = BytesIO()
            profile_image.save(buf, format='PNG')
            base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}' #通过BytesIO发送图片，无需生成本地文件
            await bot.send(ev,f'[CQ:image,file={base64_str}]',at_sender = True)
        except Exception as e:
            await bot.send(ev,f"查询个人信息过程出现问题:{e}")
            traceback.print_exc()

# @sv.scheduled_job('interval', seconds=30)
@sv.on_fullmatch(('/pjskcs','参赛查询'))
async def matching_list(bot,ev:CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev,"目前仅管理员可查询参赛信息")
        return
    # bot = get_bot()
    list_sql = "SELECT pjsk_uid, QQ, pjsk_score from grxx WHERE pjsk_event IS NOT NULL"
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    try:
        apu_cursor.execute(list_sql)
        cx_list = apu_cursor.fetchall()
        print(cx_list)
    except Exception as e:
        print("查询参赛信息数据库过程出错，请稍后再试，或联系管理员咨询处理")
        print(e)
    db_bot.close()
    try:
        nowtime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        bm_list = f"截止至当前 {nowtime} 已报名信息:\n"
        font = ImageFont.truetype(load_path+'\\simhei.ttf', 20)
        left, top, right, bottom = font.getbbox(bm_list)
        text_width = right - left
        height = 20
        num = 0
        api_error = False
        for single in cx_list:
            num += 1
            uid = single[0]
            qqid = single[1]
            score = single[2]
            u_name = await pjsk_uid_check(uid)
            if u_name == False:
                u_name = str(uid)
                bm_list_add = f"{num}.[{score}]UID:{u_name} - QQ:{qqid}\n"
                api_error = True
            else:
                bm_list_add = f"{num}.[{score}]昵称:{u_name} - QQ:{qqid}\n"
            left_n, top_n, right_n, bottom_n = font.getbbox(bm_list_add)
            if(right_n > right): # 更新最长的一行
                right = right_n
                text_width = right - left_n
            bm_list += bm_list_add
            height += 24 # 每行高度为20, 留白4
        if api_error == True:
            bm_list += "查询过程中Unibot数据API异常，可能部分报名信息仅返回UID号"
            height += 24 # 每行高度为20, 留白4
        print(bm_list)

        text_width += 20 # 给左右各留白10
        height += 20 # 给上下各留白10
        image = Image.new('RGB', (text_width, height), (0,0,0)) # 设置画布大小及背景色
        draw = ImageDraw.Draw(image)

        # 分行写入，避免换行时每行高度无法确认
        bm_list_list = bm_list.split('\n')
        for i in range(len(bm_list_list)):
            text = bm_list_list[i]
            draw.text((10, 10 + i * 24), text, 'white', font)

        image.save(load_path + '\\bmlist.jpg') # 保存图片
        data = open(load_path + f'\\bmlist.jpg', "rb")
        base64_str = base64.b64encode(data.read())
        img_b64 =  b'base64://' + base64_str
        img_b64 = str(img_b64, encoding = "utf-8")

        # await bot.send_group_msg(self_id=2407717967, group_id=908041977, message=f'[CQ:image,file={img_b64}]')
        await bot.send(ev,f'[CQ:image,file={img_b64}]')

    except Exception as error:
        print(error)
        traceback.print_exc()

@sv.on_fullmatch(('成绩查询'))
async def matching_top(bot, ev:CQEvent):
    # 1.获取全部成员成绩
    list_sql = "SELECT * from pjsk WHERE (QQ AND song1) IS NOT NULL;"
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    try:
        apu_cursor.execute(list_sql)
        cx_list = apu_cursor.fetchall()
    except Exception as e:
        print(f"error:{e}")
        return
    # 2.对成绩进行提取、分数计算和绘图
    # 获取列表的第二个元素
    def takeSecond(elem):
        return elem[1]
    score_list = []
    # 统分
    for player in cx_list:
        qq = player[0]
        song1 = player[1].split()
        s1_perfect = int(song1[0])
        s1_great = int(song1[1])
        s1_good = int(song1[2])
        s1_bad = int(song1[3])
        s1_miss = int(song1[4])
        s1_score = s1_perfect * 3 + s1_great * 2 + s1_good
        song2 = player[2].split()
        s2_perfect = int(song2[0])
        s2_great = int(song2[1])
        s2_good = int(song2[2])
        s2_bad = int(song2[3])
        s2_miss = int(song2[4])
        s2_score = s2_perfect * 3 + s2_great * 2 + s2_good
        song3 = player[3].split()
        s3_perfect = int(song3[0])
        s3_great = int(song3[1])
        s3_good = int(song3[2])
        s3_bad = int(song3[3])
        s3_miss = int(song3[4])
        s3_score = s3_perfect * 3 + s3_great * 2 + s3_good
        score_total = s1_score + s2_score + s3_score
        score_list.append([qq,score_total])
    score_list.sort(key=takeSecond,reverse=True)
    # 绘图
    image= Image.open(load_path+'\\PJSK_比赛查询.png')
    draw = ImageDraw.Draw(image)
    font_count = ImageFont.truetype(load_path + f"\\NotoSansSC-Regular.otf", 16)
    i = 0
    x_pos = 95
    y_pos = 146
    for single in score_list[:8]:
        if i == 4:
            i = 0
            y_pos = 421
        x_jacket = 236 * i
        qqid = single[0]
        score = single[1]
        qq_img = Image.open(BytesIO((await get_usericon(f'{qqid}')).content)).resize((180,180))
        qq_img = circle_corner(qq_img,20)
        image.paste(qq_img,(x_pos+x_jacket,y_pos),qq_img)
        draw.text((x_pos+x_jacket+15, y_pos+190), f'[Q号]{qqid}\n[分数]{score}', 'white', font_count)
        i += 1
    nowtime = datetime.datetime.today().isoformat(timespec='seconds')
    draw.text((331,679), f'Generate by AkiyamaAkari Bot | 数据截止至: {nowtime}', 'black', font_count)
    # 发送
    buf = BytesIO()
    image.save(buf, format='PNG')
    base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}' #通过BytesIO发送图片，无需生成本地文件
    await bot.send(ev,f'[CQ:image,file={base64_str}]',at_sender = True)

def download_jackets(music_assetbundleName):
    '''
    从在线数据库下载乐曲封面至"/jackets"文件夹内
    :param music_assetbundleName: 封面文件名信息(由musics.json单曲信息储存)
    '''
    links = f'https://storage.sekai.best/sekai-jp-assets/music/jacket/{music_assetbundleName}_rip/{music_assetbundleName}.png'
    try:
        jacket = req.get(links).content
        jacket_path = load_path + f"\\jackets\\{music_assetbundleName}.png"
        with open(jacket_path, 'wb') as f:
            f.write(jacket)
        print(f"成功下载 {music_assetbundleName}")
    except Exception as e:
        print(f"获取 {music_assetbundleName} 出错: {e}")

def math_game(max_level,min_level,level_name="default"):
    '''
    获取比赛曲目池
    :param max_level: 最高难度等级
    :param min_level: 最低难度等级
    '''
    math_musics = []
    select_song = False
    for charts in music_difficulties:
        if level_name == "default":
            if charts['musicDifficulty'] == 'master' or charts['musicDifficulty'] == 'expert':
                select_song = True
        elif level_name == "append" or level_name == "apd":
            if charts['musicDifficulty'] == 'append':
                select_song = True
        elif level_name == "master" or level_name == "mas":
            if charts['musicDifficulty'] == 'master':
                select_song = True
        else:
            return False
        if select_song:
            if charts['playLevel'] <= max_level and charts['playLevel'] >= min_level:
                music_id = charts['musicId']
                music = id_search_song(music_id)
                music_title = music['title']
                music_assetbundleName = music['assetbundleName']
                #检查文件music_assetbundleName是否存在,若不存在则下载
                if not os.path.exists(f"{load_path}\\jackets\\{music_assetbundleName}.png"):
                    download_jackets(music_assetbundleName)
                music_difficulty = charts['musicDifficulty']
                music_level = charts['playLevel']
                math_musics.append([music_id,music_title,music_difficulty,music_level,music_assetbundleName])
        select_song = False
    return math_musics

@sv.on_prefix(['/pjsk 比赛抽歌'])
async def games_7songs(bot, ev:CQEvent):
    # 解析命令
    command_parts = ev.message.extract_plain_text().split()
    if not(len(command_parts) == 2 or len(command_parts) == 3):
        await bot.send(ev, '命令格式错误，请输入两个纯数字的难度值，以空格分开')
        return
    try:
        max_level = int(command_parts[0])
        min_level = int(command_parts[1])
        if max_level < min_level: #交换难度
            max_level,min_level = min_level,max_level
        if len(command_parts) == 3:
            math_musics = math_game(max_level,min_level,command_parts[2])
            if not math_musics:
                await bot.send(ev, '命令格式错误，请输入正确的难度类型(master/append)')
                return
        else:
            math_musics = math_game(max_level,min_level)

        image = Image.open(load_path+'\\PJSK_7songs.png')
        draw = ImageDraw.Draw(image)
        font_count = ImageFont.truetype(load_path + f"\\zzaw.ttf", 20)
        songs = random.sample(math_musics,7)
        x_pos = 370
        y_pos = 140
        i = 0
        for song in songs:
            if i == 3:
                x_pos = 150
                y_pos = 620
            title = song[1]
            difficulty = song[2]
            level = song[3]
            jacket = song[4]
            jacket_img = Image.open(load_path+f'\\jackets\\{jacket}.png').resize((300,300))
            image.paste(jacket_img,(x_pos,y_pos),jacket_img)
            print(f'曲目{i+1}: [{difficulty} {level}]{title}')

            for single_charter in title:
                if not(single_charter.isascii() or single_charter == "："):
                    if len(title) > 10:
                        title = title[:10]+'...'
                else:
                    if len(title) > 16:
                        title = title[:16]+'...'
            draw.text((x_pos, y_pos+310), f'[{difficulty} {level}]{title}', 'white', font_count)
            x_pos += 440
            i+=1
        draw.text((720, 1030), f'Generate by AkiyamaAkari Bot | 由 乐谷happyvalley 维护', 'black', font_count)
        # 发送
        buf = BytesIO()
        image.save(buf, format='PNG')
        base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}' #通过BytesIO发送图片，无需生成本地文件
        await bot.send(ev,f'[CQ:image,file={base64_str}]',at_sender = True)
    except Exception as e:
        await bot.send(ev,f'抽歌过程中出现错误...')
        print(e)

@sv.on_prefix('/pjsk song')
async def pjsk_song(bot,ev):
    try:
        update_musicdb()
    except:
        print('更新歌曲数据库失败')
    command_parts = ev.message.extract_plain_text().split()
    if len(command_parts) != 1:
        await bot.send(ev, '命令格式错误，请输入正确的曲名或歌曲id')
        return
    # 判断字符串是否为纯数字
    if command_parts[0].isdigit() == False:
        # TODO: 搜索歌曲后返回信息
        music_name = command_parts[0]
        get_song_id_link = f"https://api.unipjsk.com/getsongid/{music_name}"
        response = req.get(get_song_id_link)
        if response.status_code != 200:
            await bot.send(ev, '查询歌曲信息失败，接口异常。')
            return
        response_json = response.json()
        if response_json['status'] == 'false':
            await bot.send(ev, '查询歌曲信息失败，歌曲/别名未找到。')
            return
        music_id = response_json['musicId']
    else:
        music_id = int(command_parts[0])
    music = id_search_song(music_id)
    music_title = music['title'] #歌曲名
    music_assetbundleName = music['assetbundleName']
    music_composer = music['composer'] #作曲家
    music_lyricist = music['lyricist'] #作词家
    music_arranger = music['arranger'] #编曲家
    music_publishedAt = music['publishedAt'] #游戏内发布日期
    #检查文件music_assetbundleName是否存在,若不存在则下载
    if not os.path.exists(f"{load_path}\\jackets\\{music_assetbundleName}.png"):
        download_jackets(music_assetbundleName)
    charts = id_search_diff(music_id)
    chart_str = ""
    for chart in charts:
        playLevel = chart['playLevel']
        musicDifficulty = chart['musicDifficulty']
        totalNoteCount = chart['totalNoteCount']
        chart_str += f'[{musicDifficulty} {playLevel}]音符数{totalNoteCount}\n'
    music_str = f'歌曲名:{music_title}\n作曲:{music_composer}\n作词:{music_lyricist}\n编曲:{music_arranger}\n游戏内发布日期:{datetime.datetime.fromtimestamp(music_publishedAt/1000).strftime("%Y-%m-%d %H:%M:%S")}\n{chart_str}'
    
    try:
        data = open(f"{load_path}\\jackets\\{music_assetbundleName}.png", "rb")
        base64_str = base64.b64encode(data.read())
        jacket =  b'base64://' + base64_str
        jacket = str(jacket, encoding = "utf-8")
        music_str = f"[CQ:image,file={jacket}]"+music_str
        await bot.send(ev, music_str)
    except:
        await bot.send(ev, music_str)

@sv.on_fullmatch('活动预测')
async def pjsk_event(bot,ev:CQEvent):
    await bot.set_group_reaction(group_id = ev.group_id, message_id = ev.message_id, code ='124')
    try:
        json_data = req.get(f"{pjsk_predit_link}").json()
            # 解析JSON数据
        
        event = json_data["event"]
        data = json_data["data"]
        rank = json_data["rank"]
        
        # 转换时间戳
        def format_time(timestamp):
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp//1000))
        
        start_time = format_time(event["startAt"])
        end_time = format_time(event["aggregateAt"])
        update_time = format_time(rank["ts"])
        
        # 创建图像
        img_width, img_height = 1000, 700
        background_color = (240, 245, 249)
        img = Image.new('RGB', (img_width, img_height), background_color)
        draw = ImageDraw.Draw(img)
        
        # 加载字体
        title_font = ImageFont.truetype(load_path+"\\simhei.ttf", 36)
        header_font = ImageFont.truetype(load_path+"\\simhei.ttf", 26)
        info_font = ImageFont.truetype(load_path+"\\simhei.ttf", 22)
        data_font = ImageFont.truetype(load_path+"\\arial.ttf", 24)
        small_font = ImageFont.truetype(load_path+"\\simhei.ttf", 18)
        
        # 绘制标题
        title = f"当前活动: {event['name']}"
        title_width = draw.textlength(title, font=title_font)
        draw.text(((img_width - title_width) // 2, 30), title, fill=(25, 35, 45), font=title_font)
        
        # 绘制时间信息
        time_info = f"活动时间: {start_time} 至 {end_time}"
        update_info = f"数据更新时间: {update_time}"
        
        draw.text((50, 100), time_info, fill=(70, 85, 100), font=info_font)
        draw.text((50, 130), update_info, fill=(70, 85, 100), font=info_font)
        
        # 绘制分隔线
        draw.line([(50, 170), (img_width - 50, 170)], fill=(180, 190, 200), width=2)
        
        # 定义表格位置
        table_top = 200
        col_width = (img_width - 100) // 3
        
        # 表头
        headers = ["排名", "当前分数", "预测分数"]
        header_colors = [(53, 108, 176), (76, 145, 65), (175, 100, 88)]
        
        for i, header in enumerate(headers):
            x_pos = 50 + i * col_width
            draw.rectangle([(x_pos, table_top), (x_pos + col_width, table_top + 50)], fill=(220, 230, 240))
            header_width = draw.textlength(header, font=header_font)
            draw.text((x_pos + (col_width - header_width) // 2, table_top + 10), 
                    header, fill=header_colors[i], font=header_font)
        
        # 表格数据
        rankings = [50, 100, 500, 1000, 5000, 10000, 50000, 100000]
        row_height = 50
        
        for idx, rank_pos in enumerate(rankings):
            row_y = table_top + 50 + idx * row_height
            bg_color = (250, 252, 255) if idx % 2 == 0 else (235, 241, 247)
            
            # 行背景
            draw.rectangle([(50, row_y), (img_width - 50, row_y + row_height)], fill=bg_color)
            
            # 排名
            rank_text = f"Top {rank_pos}"
            rank_width = draw.textlength(rank_text, font=data_font)
            draw.text((50 + (col_width - rank_width) // 2, row_y + 15), 
                    rank_text, fill=(40, 50, 60), font=data_font)
            
            # 当前分数
            current_score = rank.get(str(rank_pos), "N/A")
            if current_score != "N/A":
                current_score = f"{current_score:,}"
            current_width = draw.textlength(current_score, font=data_font)
            draw.text((50 + col_width + (col_width - current_width) // 2, row_y + 15), 
                    current_score, fill=(50, 90, 50), font=data_font)
            
            # 预测分数
            predicted_score = data.get(str(rank_pos), "N/A")
            if predicted_score != "N/A":
                predicted_score = f"{predicted_score:,}"
            predicted_width = draw.textlength(predicted_score, font=data_font)
            draw.text((50 + 2 * col_width + (col_width - predicted_width) // 2, row_y + 15), 
                    predicted_score, fill=(150, 70, 60), font=data_font)
        
        # 底部说明
        note = "数据来源: https://3-3.dev/pjsk-predict"
        note_width = draw.textlength(note, font=small_font)
        draw.text((img_width - note_width - 30, img_height - 40), note, fill=(120, 130, 140), font=small_font)
        
        # 发送图片
        buf = BytesIO()
        img.save(buf, format='PNG')
        base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}' #通过BytesIO发送图片，无需生成本地文件
        await bot.send(ev,f'[CQ:image,file={base64_str}]')
    except Exception as e:
        await bot.send(ev,f'查询失败，请稍后再试\n错误信息：{e}')

@sv.on_prefix(('参赛报名'))
async def pjsk_bind(bot, ev: CQEvent):
    db_bot = pymysql.connect(
        host=bot_db.host,
        port=bot_db.port,
        user=bot_db.user,
        password=bot_db.password,
        database=bot_db.database
    )
    apu_cursor = db_bot.cursor()
    qqid = ev.user_id
    apu_getuid_sql = "SELECT QQ,pjsk_uid,pjsk_event FROM grxx WHERE QQ = %s" % (qqid)
    # 先执行一次查询，查询是否已经签到注册过
    try:
        apu_cursor.execute(apu_getuid_sql)
        result_cx = apu_cursor.fetchall()
        if not result_cx:
            await bot.send(ev, "无法查询到您的数据，请先执行以下操作：\n1.发送“签到”两个字来注册bot功能\n2.发送“/pjsk bind [您的pjsk uid]”来绑定您的pjsk账号\n绑定成功后再执行该命令可以报名参赛。", at_sender = True)
        elif result_cx[0][1] == None:
            await bot.send(ev, "您尚未绑定pjsk账号，请先执行以下操作：\n1.发送“/pjsk bind [您的pjsk uid]”来绑定您的pjsk账号\n2.绑定成功后再次发送“参赛报名”。", at_sender = True)
        elif result_cx[0][2] == 1:
            await bot.send(ev, "您已成功报名过：\n南宁7.19世界计划ONLY\n音游比赛 线上赛\n无需重复报名。", at_sender = True)
        else:
            await bot.send(ev, f'正在为您报名参赛')
            try:
                apu_bm_sql = "UPDATE `grxx` SET `pjsk_event`=1 WHERE `QQ`='%s'" % (qqid)
                apu_cursor.execute(apu_bm_sql)
                db_bot.commit()
                await bot.send(ev, f'【报名成功！】\n您已成功报名：\n南宁世界计划ONLY 2.0\n音游比赛 线上赛')
            except Exception as e:
                await bot.send(ev, f'报名过程中发生错误:{e}')
    except Exception as e:
        await bot.send(ev, f'报名过程中发生错误:{e}')
    db_bot.close()