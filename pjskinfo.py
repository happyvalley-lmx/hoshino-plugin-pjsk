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

from .config import bot_db
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
    try:
        getdata = req.get(url)
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
@sv.on_fullmatch(('/pjskcs','参赛查询'))
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
        api_error = False
        for single in cx_list:
            num += 1
            uid = single[0]
            qqid = single[1]
            u_name = await pjsk_uid_check(uid)
            if u_name == False:
                u_name = str(uid)
                bm_list_add = f"{num}.UID:{u_name} - QQ:{qqid}\n"
                api_error = True
            else:
                bm_list_add = f"{num}.昵称:{u_name} - QQ:{qqid}\n"
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