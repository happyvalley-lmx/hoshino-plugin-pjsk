import json
import requests
import os
load_path = os.path.dirname(__file__)     #更改为自动获取

music_difficulties_raw = requests.get("https://sekai-world.github.io/sekai-master-db-diff/musicDifficulties.json")
musics_raw = requests.get("https://sekai-world.github.io/sekai-master-db-diff/musics.json")
music_difficulties = json.loads(music_difficulties_raw.content)
musics = json.loads(musics_raw.content)
# print(musics)

def id_search_song(music_id):
    for music in musics:
        if music['id'] == music_id:
            return music
        
def download_jackets(music_assetbundleName):
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

for charts in music_difficulties:
    if charts['musicDifficulty'] == 'master' or charts['musicDifficulty'] == 'expert':
        if charts['playLevel'] <= 34 and charts['playLevel'] >= 32:
            music_id = charts['musicId']
            music = id_search_song(music_id)
            music_title = music['title']
            music_assetbundleName = music['assetbundleName']
            # download_jackets(music_assetbundleName)
            music_difficulty = charts['musicDifficulty']
            music_level = charts['playLevel']
            math_musics.append([music_id,music_title,music_difficulty,music_level,music_assetbundleName])

print(math_musics)