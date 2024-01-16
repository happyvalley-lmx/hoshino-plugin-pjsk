import json
import requests
import os
import random
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
def math_game(max_level,min_level):
    '''
    比赛曲目池更新
    :param max_level: 最高难度等级
    :param min_level: 最低难度等级
    '''
    global math_musics
    for charts in music_difficulties:
        if charts['musicDifficulty'] == 'master' or charts['musicDifficulty'] == 'expert':
            if charts['playLevel'] <= max_level and charts['playLevel'] >= min_level:
                music_id = charts['musicId']
                music = id_search_song(music_id)
                music_title = music['title']
                music_assetbundleName = music['assetbundleName']
                # download_jackets(music_assetbundleName)
                music_difficulty = charts['musicDifficulty']
                music_level = charts['playLevel']
                math_musics.append([music_id,music_title,music_difficulty,music_level,music_assetbundleName])

math_game(34,32)

def random_songs(num:int):
    '''
    从比赛曲目池中抽取n首歌
    :param num: 抽取的歌曲数目
    '''
    result = random.sample(math_musics,num)
    return result

random_songs(7)
random_songs(1)