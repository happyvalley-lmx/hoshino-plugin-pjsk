# SBGA还我API！！  
目前本插件数据源已换用 Unibot 所提供的 API 来查询，在Unibot上传数据时请勾选 “公开API读取” 后方可在本插件中获取详细资料。

# hoshino-pjsk-plugin  
~~因为频道里的pjsk查询没有开源，翻了翻pjsk信息网站发现有api于是决定自己做~~  
Unibot不但开源了还开放了API，所以把本插件所用的API接过去了，很是方便。

## 指令  
下表中指令部分均以斜杠"/"开头，中括号在指令中为可选输入  
使用例: `/pjskpf @FLAG250` 可用于查询FLAG的pjsk个人信息  
|指令|说明|
|------|------|
| `/pjsk绑定 [pjskID]`|绑定发送者的qq与pjsk|
|`/pjsk进度`|查询master难度的完成情况|
|`/pjskpf [pjskid/@用户]`|查询pjsk档案，若未加pjskid或@人时默认查询本人所绑定的pjsk账号|
|`/sk`|查询当前活动分数线|

python初学者 第一次写hoshino的插件  
所以你将可以在py文件中看到：屎山、多段重复代码、莫名其妙的变量名称……  

## 部署方法  
1. git本项目 将文件夹放在\hoshino\modulus\下  
2. 在\config\_bot_.py中加入“hoshino-pjsk-plugin”，  
3. 在pjskinfo.py中修改load_path的路径（指向你放本插件的目录）  
例load_path = "C:\\Users\\Administrater\\Desktop\\haru-bot-setup\\hoshino\\modules\\hoshino-pjsk-plugin"  
4. 重启并运行hoshino  
运行前最好在account.json里先加上你自己的qqID和pjsk信息  
（因为没试过空文件测试 不知道会有什么问题）  

## 未来功能  
* 谱面查询
* 歌曲查询
* 猜歌（谱面猜歌，曲绘猜歌，歌曲切片猜歌）
* 按歌曲别称检索
* 向频道的Unibot靠拢
* 大部分bug打算随新功能加入一起修复

## 已知问题  
~~每次更新活动需重启一次hoshino，原因应该是插件在开头获取一次的活动资源为静态缓存在本地）~~  
