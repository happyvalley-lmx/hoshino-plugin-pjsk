import json
import requests
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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
        music_difficulties_raw = requests.get("https://sekai-world.github.io/sekai-master-db-diff/musicDifficulties.json").content
        musics_raw = requests.get("https://sekai-world.github.io/sekai-master-db-diff/musics.json").content
        save_request('musicDifficulties.json',music_difficulties_raw)
        save_request('musics.json',musics_raw)
    except:
        music_difficulties_raw = open(load_path + '\\musicDifficulties.json', encoding='UTF-8').read()
        musics_raw = open(load_path + '\\musics.json', encoding='UTF-8').read()
    music_difficulties = json.loads(music_difficulties_raw)
    musics = json.loads(musics_raw)

#初始化时尝试更新一次musicdb
update_musicdb()

def id_search_song(music_id):
    '''
    乐曲id找歌，从musics.json返回对应单曲的详情数据
    :params music_id: 乐曲id
    :return: 单曲详情数据
    '''
    for music in musics:
        if music['id'] == music_id:
            return music
        
def download_jackets(music_assetbundleName):
    '''
    从在线数据库下载乐曲封面至"/jackets"文件夹内
    :param music_assetbundleName: 封面文件名信息(由musics.json单曲信息储存)
    '''
    links = f'https://storage.sekai.best/sekai-assets/music/jacket/{music_assetbundleName}_rip/{music_assetbundleName}.png'
    try:
        jacket = requests.get(links).content
        jacket_path = load_path + f"\\jackets\\{music_assetbundleName}.png"
        with open(jacket_path, 'wb') as f:
            f.write(jacket)
        print(f"成功下载 {music_assetbundleName}")
    except:
        print(f"获取 {music_assetbundleName} 出错")

math_musics = []
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

math_musics = math_game(32,28,"apd")
# for song in math_musics:
#     print(song[2] + ' ' + str(song[3]) + ' | ' + song[1])

def random_songs(num:int):
    '''
    从比赛曲目池中抽取n首歌
    :param num: 抽取的歌曲数目
    '''
    result = random.sample(math_musics,num)
    return result

# print(random_songs(7))
# random_songs(1)

def ban_and_pick_img():
    image = Image.open(load_path+'\\PJSK_7songs.png')
    draw = ImageDraw.Draw(image)
    font_count = ImageFont.truetype(load_path + f"\\zzaw.ttf", 20)
    songs = random_songs(7)
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
    image.show()

member_list = ["PH","甘城","颂歌","冬霜颖落","幸运币","想你了冰红茶","劍靈幻辰","兮沫"]

select_mode = input("请输入选择程序(0:随机抽一首歌/1:随机分组/2:抽取比赛曲目池7首歌)")
if select_mode == "0":
    print(random_songs(1))
elif select_mode == "1":
    random.shuffle(member_list)
    i = 1
    g = []
    print("本次抽签的分组如下:")
    for member in member_list:
        if i % 2 == 0:
            g.append([member_list[i-2],member])
        i+=1
    print(g)
elif select_mode == "2":
    ban_and_pick_img()
else:
    print("输入有误，请重试")