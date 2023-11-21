import json, base64, time
import requests as req
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import re
import traceback
from io import BytesIO
import pymysql
import datetime

from hoshino.typing import CQEvent, MessageSegment
from hoshino import Service, priv, config, get_self_ids, get_bot

from .config import bot_db
import asyncio

sv = Service(
    name = 'pjsk信息查询',  #功能名
    use_priv = priv.NORMAL, #使用权限   
    manage_priv = priv.SUPERUSER, #管理权限
    visible = False, #False隐藏
    enable_on_default = True, #是否默认启用
    bundle = '娱乐', #属于哪一类
    )
    

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
url_getmD = 'https://musics.pjsekai.moe/musicDifficulties.json'
url_getmc = 'https://musics.pjsekai.moe/musics.json'
url_e_data = 'https://database.pjsekai.moe/events.json'
color={"ap":"#d89aef","fc":"#ef8cee","clr":"#f0d873","all":"#6be1d9"}
load_path = os.path.dirname(__file__)     #更改为自动获取

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
    url = f'https://api.unipjsk.com/api/user/{pjsk_uid}/profile'
    getdata = req.get(url)
    try:
        data1 = json.loads(getdata.text)
        u = data1['user']['name']
        return u
    except:
        return False


@sv.on_prefix(('/pjsk绑定'))
async def pjsk_bind(bot, ev: CQEvent):
    #绑定PJSK ID到QQ上（使用本地数据库）
    input_id_raw = ev.message.extract_plain_text().strip()
    if len(input_id_raw) == 0:
        await bot.send(ev, '请输入您的PJSK ID！')
    elif input_id_raw.isdigit() == True:
        input_id = int(input_id_raw)
        u_name = await pjsk_uid_check(input_id)
        if not u_name:
            await bot.send(ev, "无法查询到对应UID绑定的PJSK账号，请检查您的PJSK UID是否正确")
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

@sv.on_prefix(("/pjskpf","/个人信息"))
async def pj_profileGet(bot,ev:CQEvent):
    #逮捕
    uid = ev.user_id
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
        try:
            url = f'https://api.unipjsk.com/api/user/{userID}/profile'
            getdata = req.get(url)
            data1 = json.loads(getdata.text)


            dict_backup=[]
            difficulty = ['easy','normal','hard','expert','master'] #TODO: APD难度
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
            
            profile_image= Image.open(load_path+'\\test1.png')
            new_pimage = load_path+'\\pjprofile.png'

            if selection == 0:
                picon = Image.open(BytesIO((await get_usericon(f'{uid}')).content)) #####
            else:
                picon = Image.open(BytesIO((await getLeaderIcon(data1)).content))
            
            num_font = ImageFont.truetype(load_path+'\\CAT.TTF',size=40)
            name_font = ImageFont.truetype(load_path+'\\zzaw.ttf',size=80)
            rank_font = ImageFont.truetype(load_path+'\\CAT.TTF',size=36)
            word_font = ImageFont.truetype(load_path+'\\zzaw.ttf',size=32)
            draw = ImageDraw.Draw(profile_image)
            draw_icon = ImageDraw.Draw(picon)
            
            #防止部分玩家ID过大导致其以期望外的方式生成
            u = data1['user']['name'].encode("utf-8")
            if len(u) < 18:
                draw.text((281,130),data1['user']['name'],'#FFFFFF',font=name_font)
            else:
                name_font = ImageFont.truetype(load_path+'\\zzaw.ttf',size=48)
                draw.text((281,162),data1['user']['name'],'#FFFFFF',font=name_font)

            draw.text((404,231),str(data1['user']['rank']),'#FFFFFF',font=rank_font)



            
            async def measure(msg, font_size, img_width):
                i = 0
                l = len(msg)
                length = 0
                positions = []
                while i < l :
                    if re.search(r'[0-9a-zA-Z]', msg[i]):
                        length += font_size // 2
                    else:
                        length += font_size
                    if length >= img_width:
                        positions.append(i)
                        length = 0
                        i -= 1
                    i += 1
                return positions

            #个人简介
            
            word_text = Image.new('RGB', (654, 157), "#5b5b5b")
            
            draw1 = ImageDraw.Draw(word_text)
            

            msg = data1['userProfile']['word']
            positions = await measure(msg,32,700)
            str_list = list(msg)
            for pos in positions:
                str_list.insert(pos,'\n')
            msg = "".join(str_list)  

            draw1.text((0,0), msg, "#FFFFFF", font=word_font)
            profile_image.paste(word_text, (103,307))
            

            def draw_musicsCompleted():
                x = 0
                for tag in difficulty:
                    for pdata in dict_backup[x]:
                        y = 0
                        for ptag in ['clear','fc','ap']:
                            draw.text((140 + x * 128,580 + y * 128),str(dict_backup[x][pdata][ptag]),'#FFFFFF',font=num_font)
                            y = y + 1
                    x = x + 1
            
            def characterdataGet():
                for i in data1['userCharacters']:
                    if i["characterId"] % 4 == 0:
                        x = 960 + (165 * 3)
                        y = 350 + (107 * (((i["characterId"])// 4)-1))
                        if i["characterId"] > 20:
                            y = 130 + (107 * ((((i["characterId"])-20)// 4)-1))
                    else:
                        x = 960 + (165 * ((((i["characterId"])) % 4)-1))
                        y = 350 + (107 * (((i["characterId"])//4)))
                        if i["characterId"] > 20:
                            y = 130 + (107 * ((((i["characterId"])-20)// 4)))
                    draw.text((x, y),str(i['characterRank']),"#000000",font=num_font)

            

            draw_musicsCompleted()
            characterdataGet()
            picon = picon.resize((177,177),Image.Resampling.LANCZOS)
            profile_image.paste(picon, (95,106))
            buf = BytesIO()
            profile_image.save(buf, format='PNG')
            base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}' #通过BytesIO发送图片，无需生成本地文件
            await bot.send(ev,f'[CQ:image,file={base64_str}]',at_sender = True)
        except Exception as e:
            await bot.send(ev,f"查询个人信息过程出现问题:{e}")
            traceback.print_exc()

# @sv.scheduled_job('interval', seconds=30)
@sv.on_fullmatch(('/pjskcs','/参赛查询'))
async def matching_list(bot,ev:CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.send(ev,"目前仅管理员可查询参赛信息")
        return
    # bot = get_bot()
    list_sql = "SELECT pjsk_uid, QQ from grxx WHERE pjsk_uid IS NOT NULL"
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
        for single in cx_list:
            num += 1
            uid = single[0]
            qqid = single[1]
            u_name = await pjsk_uid_check(uid)
            bm_list_add = f"{num}.昵称:{u_name} - QQ:{qqid}\n"
            left_n, top_n, right_n, bottom_n = font.getbbox(bm_list_add)
            if(right_n > right): # 更新最长的一行
                right = right_n
                text_width = right - left_n
            bm_list += bm_list_add
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
# def load_event_info(_data):
#     i = -2
#     close_time = int(_data[i]["closedAt"]/1000) 
#     if time.time() > close_time: #说明倒数第二个活动已关闭，按最新的算
#         i = -1
#     return _data[i]['id'], _data[i]['name'], time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(_data[i]["aggregateAt"]/1000))),  _data[i]['eventType']

# 因为API限制，无法查排名了            
# @sv.on_prefix("/sk")
# async def event_rank(bot,ev:CQEvent):    
#     uid = ev.user_id
#     userid = await lg(uid)
#     if userid == 0:
#         await bot.send(ev,f"没有绑定捏\n输入“/pjsk绑定+pjskID”来绑定吧~")
#     else:
#         try:
#             _data = data_req(url_e_data)
#             event_id, event_name, event_end_time, e_type = load_event_info(_data)
#             url1 = f'https://api.pjsekai.moe/api/user/%7Buser_id%7D/event/{event_id}/ranking?targetUserId={userid}'

#             user_event_data = req.get(url1, headers=headers)
#             _event_data = json.loads(user_event_data.text)
#             try:
#                 user_event_rank = _event_data['rankings'][0]['rank']  #你的try嵌套错地方了，如果没打活动这里就取不到值了
#                 user_event_score = _event_data['rankings'][0]['score']  #所以生成消息那边嵌套的try实际没有用
#             except:
#                 await bot.send(ev, '小可爱你还没打活动查什么呢', at_sender = True) 
#                 return  #利用return结束
#             nearest_line = []
#             event_line = [100, 200, 500,
#                         1000, 2000, 5000,
#                         10000, 20000, 50000,
#                         100000, 200000, 500000,
#                         1000000, 2000000, 5000000]

#             for a in range(len(event_line)):
#                 if int(event_line[a]) >= user_event_rank:
#                     if a != 0:
#                         nearest_line.append(event_line[a-1])
#                     nearest_line.append(event_line[a])
#                     break
#             else:
#                 nearest_line.append(event_line[-1])
                                
#             msg = f"当前活动:{event_name}\n活动类型:{e_type}\n活动截止时间:{event_end_time}\n你的分数:{str(user_event_score)} rank#{str(user_event_rank)}\n最近的分数线:"
#             for i in nearest_line:
#                 try:
#                     url2 = f'https://api.pjsekai.moe/api/user/%7Buser_id%7D/event/{event_id}/ranking?targetRank={i}'
#                     event_line_data = req.get(url2, headers=headers)
#                     _event_line_data = json.loads(event_line_data.text)
#                     msg += f"\nrank#{i} {str(_event_line_data['rankings'][0]['score'])}"
#                 except:
#                     msg += f"\nrank#{i} 最近的分数线:暂无数据"

#         except Exception as e:
#             msg = f"发生错误，错误类型：{type(e)}\n请联系管理员"
#             print(e)
#         await bot.send(ev, msg, at_sender = True)    
    
# def load_req_line(string:str):
#     return string.replace('k', '000').replace('K', '000').replace('w', '0000').replace('W', '0000')

# TODO:档线
# @sv.on_prefix('/pjsk档线')
# async def event_line_score(bot, ev):
#     try:
#         req_line = load_req_line(ev.message.extract_plain_text().strip())
#     except:
#         req_line = 0
#     try:
#         _data = data_req(url_e_data)
#         event_id, event_name, event_end_time, e_type = load_event_info(_data)
        
#         #line_score = []
#         if req_line ==0:
#             event_line = [100, 200, 500,
#                     1000, 2000, 5000,
#                     10000, 20000, 50000,
#                     100000, 200000, 500000, 1000000]
#             event_line_msg = ['100', '200', '500',
#                     '1k', '2k', '5k',
#                     '1w', '2w', '5w',
#                     '10w', '20w', '50w', '100w']
#             index = 0
#             msg = f'活动标题：{event_name}\n活动类型:{e_type}'
#             for line in event_line:
#                 url2 = f'https://api.pjsekai.moe/api/user/%7Buser_id%7D/event/{event_id}/ranking?targetRank={line}'
#                 event_line_data = data_req(url2)
#                 try:
#                     #line_score.append(str(event_line_data['rankings'][0]['score']))  #预留后期图像化
#                     line_score = event_line_data['rankings'][0]['score']
#                     msg += f'\n{event_line_msg[index]}线:{line_score}'
#                 except:
#                     #line_score.append('暂无数据')
#                     msg += f'\n{event_line_msg[index]}线:暂无数据'
#                 index += 1
#         else:
#             msg = f'活动标题：{event_name}\n活动类型:{e_type}'
#             url2 = f'https://api.pjsekai.moe/api/user/%7Buser_id%7D/event/{event_id}/ranking?targetRank={req_line}'
#             event_line_data = data_req(url2)
#             try:
#                 line_score = event_line_data['rankings'][0]['score']
#                 msg += f'\n{req_line}线:{line_score}'
#             except:
#                 msg += f'\n{req_line}线:暂无数据'
#     except Exception as e:
#         print(e)
#         msg = f"发生错误，错误类型：{type(e)}\n请联系管理员"
        
#     await bot.send(ev, msg, at_sender = True)  

# async def pj_musicCompletedDataGet(uid,data1):
#     difficulty = 'master'
#     count = 0
#     c_count = 0
#     p_count = 0
#     list1 = []
#     list2 = []
#     list3 = []
#     list4 = []

#     list1,c_count = await countFlg(list1,'fullComboFlg',difficulty,data1)
#     list2,p_count = await countFlg(list2,'fullPerfectFlg',difficulty,data1)
#     list4,count = await countClear(list4,difficulty,data1)

#     _lv = data_req(url_getmD)
#     allMusic = data_req(url_getmc)
#     #按难度分类  
#     for _ in allMusic:
#             list3.append(_['id'])
    
#     async def selectPlus(_list):
#         lv_s = {26:0,27:0,28:0,29:0,30:0,31:0,32:0,33:0,34:0,35:0,36:0}
#         for __lv in _lv:
#             if __lv['musicDifficulty'] == difficulty and __lv['musicId'] in _list:
#                 lv_s[__lv['playLevel']] += 1
#         return lv_s
    
#     lv1 = await selectPlus(list1)
#     lv2 = await selectPlus(list2)
#     lv3 = await selectPlus(list3)
#     lv4 = await selectPlus(list4)
    
    
#     async def change(lv):
#         re_lv1 = []
#         in_dex ={}
#         for i in range(26,37):
#             a = lv[i]
#             b = str(i)
#             in_dex[f"{b}"] = a
#             n_dex =in_dex
#         re_lv1.append(n_dex)     
#         return re_lv1   
    
#     re_lv1 = await change(lv1) #fc
#     re_lv2 = await change(lv2) #ap
#     _all = await change(lv3) #all
#     _clear = await change(lv4) #clear
    

#     return _clear,_all,re_lv1,re_lv2

# @sv.on_prefix("/pjsk进度")
# async def gen_pjsk_jindu_image(bot,ev:CQEvent):
#     #逮捕
#     uid = ev.user_id
#     userID = await lg(uid)

#     selection = 0
    
#     for i in ev.message:
#         if i.type == 'at':
#             uid = int(i.data['qq'])
#             userID = await lg(uid)
#             break

#     _uID = ev.message.extract_plain_text().strip()
#     if _uID != "":
#         _userID = int(_uID)
#         if isinstance(_userID,int) and _userID > 1000000000000000:
#             userID = _userID
#             selection = 1
#         else:
#             return await bot.send(ev,f'UID格式错误')



#     if userID == 0:
#         await bot.send(ev,f"没有绑定捏\n输入“/pjsk绑定+pjskID”来绑定吧~")

#     else:
#         try:
#             url = f'https://api.pjsekai.moe/api/user/{str(userID)}/profile'
#             getdata = req.get(url)
#             data1 = json.loads(getdata.text)

#             _clr,_all,_fc,_ap = await pj_musicCompletedDataGet(uid,data1)
#             image1 = Image.open(load_path+f'\\test.png')
#             new_image =load_path+f'\\pjskjindu.png'


#             if selection == 0:
#                 icon = Image.open(BytesIO((await get_usericon(f'{uid}')).content)) #####
#             else:
#                 icon = Image.open(BytesIO((await getLeaderIcon(data1)).content))

#             font = ImageFont.truetype(load_path+f'\\CAT.TTF',size=40)
#             font1 = ImageFont.truetype(load_path+f'\\zzaw.ttf',size=50)
#             font2 = ImageFont.truetype(load_path+f'\\CAT.TTF',size=36)
#             draw = ImageDraw.Draw(image1)

#             u = data1['user']['name'].encode("utf-8")
#             if len(u) < 18:
#                 draw.text((214,75),data1['user']['name'],'#000000',font=font1)
#             else:
#                 font1 = ImageFont.truetype(load_path+f'\\zzaw.ttf',size=30)
#                 draw.text((214,95),data1['user']['name'],'#000000',font=font1)

#             draw.text((315,135),str(data1['user']['rank']), "#FFFFFF",font=font2)
#             icon = icon.resize((117,117),Image.Resampling.LANCZOS)
#             image1.paste(icon, (67,57))

#             for i in _ap[0]:
#                 if i <= '31':
#                     draw.text((167,284+(97*(int(i)-26))),str(_ap[0][i]), color["ap"],font=font)
#                 else:
#                     draw.text((667,284+(97*(int(i)-32))),str(_ap[0][i]), color["ap"],font=font)
#             for i in _fc[0]:
#                 if i <= '31':
#                     draw.text((242,284+(97*(int(i)-26))),str(_fc[0][i]), color["fc"],font=font)
#                 else:
#                     draw.text((742,284+(97*(int(i)-32))),str(_fc[0][i]), color["fc"],font=font)
            
#             for i in _clr[0]:
#                 if i <= '31':
#                     draw.text((317,284+(97*(int(i)-26))),str(_clr[0][i]), color["clr"],font=font)
#                 else:
#                     draw.text((817,284+(97*(int(i)-32))),str(_clr[0][i]), color["clr"],font=font)
#             for i in _all[0]:
#                 if i <= '31':
#                     draw.text((392,284+(97*(int(i)-26))),str(_all[0][i]), color["all"],font=font)
#                 else:
#                     draw.text((892,284+(97*(int(i)-32))),str(_all[0][i]), color["all"],font=font)
            
#             buf = BytesIO()
#             image1.save(buf, format='PNG')
#             base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}'
#             await bot.send(ev,f'[CQ:image,file={base64_str}]',at_sender = True)
#         except:
#             await bot.send(ev,f"api或服务器可能寄了 或者你这个小可爱填错别人ID 不然一般是不会出现意料之外的问题的！ \n请及时联系管理员看看发生什么事了")


# '''
# userID = await lg(uid)
# url = f'https://api.pjsekai.moe/api/user/{userID}/profile'
# getdata = req.get(url)
# data1 = json.loads(getdata.text)
# #print(data1)
# '''
# ''' 备份 给新功能测试
# loop = asyncio.get_event_loop() 
# loop.run_until_complete(pj_profileGet())
# loop.close()
# '''
