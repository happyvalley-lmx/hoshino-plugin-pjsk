"""
图片翻译模块 - 使用 qwen-mt-image 模型
用户带图片发送"翻译"时，翻译图片中的文字并返回翻译后的图像
"""

import base64
import time
import requests as req
import traceback

from hoshino.typing import CQEvent
from hoshino import Service, priv

from .config import API_KEY

sv = Service(
    name='图片翻译功能',
    use_priv=priv.NORMAL,
    manage_priv=priv.SUPERUSER,
    visible=True,
    enable_on_default=True,
    bundle='娱乐',
    help_='带图片发送"翻译"来翻译图片中的文字'
)

# 支持的语言代码
SUPPORTED_LANGS = {
    'zh': '中文', 'cn': '中文', 'chinese': '中文', '中国': '中文',
    'en': '英文', 'english': '英文', '英语': '英文',
    'ja': '日文', 'jp': '日文', 'japanese': '日文', '日语': '日文', '日本': '日文',
    'ko': '韩语', 'korean': '韩语', '朝鲜语': '韩语',
    'fr': '法语', 'french': '法语',
    'es': '西班牙语', 'spanish': '西班牙语',
    'de': '德语', 'german': '德语',
    'ru': '俄语', 'russian': '俄语',
    'pt': '葡萄牙语', 'portuguese': '葡萄牙语',
    'it': '意大利语', 'italian': '意大利语',
    'ar': '阿拉伯语', 'arabic': '阿拉伯语',
    'th': '泰语', 'thai': '泰语',
    'vi': '越南语', 'vietnamese': '越南语'
}

# API 端点
UPLOAD_ENDPOINT = 'https://dashscope.aliyuncs.com/api/v1/uploads'
TRANSLATE_ENDPOINT = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis'
TASK_ENDPOINT = 'https://dashscope.aliyuncs.com/api/v1/tasks'


def get_lang_code(lang_input):
    """获取标准语种代码"""
    lang_lower = lang_input.lower().strip()
    if lang_lower in SUPPORTED_LANGS:
        for code, name in SUPPORTED_LANGS.items():
            if code in ['zh', 'en', 'ja', 'ko', 'fr', 'es', 'de', 'ru', 'pt', 'it', 'ar', 'th', 'vi']:
                if SUPPORTED_LANGS[code] == SUPPORTED_LANGS[lang_lower]:
                    return code
    return lang_lower[:2] if len(lang_lower) >= 2 else lang_lower


def get_upload_policy(api_key, model_name):
    """获取文件上传凭证"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    params = {
        'action': 'getPolicy',
        'model': model_name
    }
    response = req.get(UPLOAD_ENDPOINT, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        raise Exception(f"获取上传凭证失败：{response.status_code} - {response.text}")
    result = response.json()
    data = result.get('data', {})
    if not data:
        raise Exception(f"上传凭证响应格式错误：{result}")
    return data


def upload_file_to_oss(policy_data, file_bytes, file_name):
    """将文件上传到临时存储 OSS"""
    key = f"{policy_data['upload_dir']}/{file_name}"
    files = {
        'OSSAccessKeyId': (None, policy_data['oss_access_key_id']),
        'Signature': (None, policy_data['signature']),
        'policy': (None, policy_data['policy']),
        'x-oss-object-acl': (None, policy_data['x_oss_object_acl']),
        'x-oss-forbid-overwrite': (None, policy_data['x_oss_forbid_overwrite']),
        'key': (None, key),
        'success_action_status': (None, '200'),
        'file': (file_name, file_bytes)
    }
    response = req.post(policy_data['upload_host'], files=files, timeout=300)
    if response.status_code != 200:
        raise Exception(f"文件上传失败：{response.status_code} - {response.text}")
    oss_url = f"oss://{key}"
    return oss_url


def create_translation_task(api_key, oss_url, source_lang, target_lang):
    """创建图像翻译任务"""
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'X-DashScope-Async': 'enable',
        'X-DashScope-OssResourceResolve': 'enable'
    }
    payload = {
        'model': 'qwen-mt-image',
        'input': {
            'image_url': oss_url,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'ext': {
                'config': {
                    'imageSegment': False
                }
            }
        }
    }
    response = req.post(TRANSLATE_ENDPOINT, headers=headers, json=payload, timeout=60)
    if response.status_code != 200:
        raise Exception(f"创建任务失败：{response.status_code} - {response.text}")
    result = response.json()
    task_id = result.get('output', {}).get('task_id')
    if not task_id:
        raise Exception(f"任务创建响应格式错误：{result}")
    return task_id


def poll_task_result(api_key, task_id, timeout=300, interval=5):
    """轮询任务结果"""
    headers = {
        'Authorization': f'Bearer {api_key}'
    }
    start_time = time.time()
    while time.time() - start_time < timeout:
        time.sleep(interval)
        response = req.get(f"{TASK_ENDPOINT}/{task_id}", headers=headers, timeout=30)
        if response.status_code != 200:
            continue
        result = response.json()
        task_status = result.get('output', {}).get('task_status', 'PENDING')
        if task_status == 'SUCCEEDED':
            output_image_url = result.get('output', {}).get('image_url')
            if not output_image_url:
                raise Exception(f"任务成功但无输出图像：{result}")
            return output_image_url
        elif task_status in ['FAILED', 'CANCELED']:
            error_msg = result.get('output', {}).get('message', '未知错误')
            raise Exception(f"任务失败：{error_msg}")
    raise Exception(f"任务超时（{timeout}秒）")


async def translate_image_qwen(image_bytes, target_lang='zh'):
    """
    翻译图像中的文字并生成翻译后的图片
    Args:
        image_bytes: 输入图像的二进制数据
        target_lang: 目标语言（默认中文）
    Returns:
        翻译后图像的二进制数据
    """
    if not API_KEY:
        raise ValueError("未设置 API_KEY 环境变量")
    
    # 获取目标语言代码
    target_code = get_lang_code(target_lang)
    
    # 步骤 1: 获取上传凭证
    policy_data = get_upload_policy(API_KEY, 'qwen-mt-image')
    
    # 步骤 2: 上传到 OSS
    file_name = f"translate_{int(time.time())}.jpg"
    oss_url = upload_file_to_oss(policy_data, image_bytes, file_name)
    
    # 步骤 3: 创建翻译任务
    task_id = create_translation_task(API_KEY, oss_url, 'auto', target_code)
    
    # 步骤 4: 轮询结果
    result_url = poll_task_result(API_KEY, task_id)
    
    # 步骤 5: 下载结果
    response = req.get(result_url, stream=True, timeout=300)
    if response.status_code != 200:
        raise Exception(f"下载失败：{response.status_code}")
    
    return response.content


@sv.on_prefix('翻译')
async def translate_image(bot, ev: CQEvent):
    """处理带图片的翻译请求"""
    # 检查消息中是否包含图片
    image_url = None
    image_file = None
    
    for m in ev.message:
        if m.type == 'image':
            image_file = m.data['file']
            image_url = m.data['url']
            break
    
    if not image_url:
        await bot.send(ev, '请附带一张需要翻译的图片~')
        return
    
    # 获取目标语言（如果有指定）
    target_lang = ev.message.extract_plain_text().strip().replace('翻译', '').strip()
    if not target_lang:
        target_lang = 'zh'  # 默认翻译为中文
    
    lang_name = SUPPORTED_LANGS.get(target_lang, target_lang)
    await bot.send(ev, f'正在翻译图片，目标语言：{lang_name}...')
    
    try:
        # 处理图片链接
        if 'c2cpicdw.qpic.cn/offpic_new/' in image_url:
            md5 = image_file[:6].upper()
            image_url = f"http://gchat.qpic.cn/gchatpic_new/0/0-0-{md5}/0?term=2"
        
        # 下载图片
        img_data = req.get(image_url, timeout=30).content
        
        # 调用翻译函数
        translated_img = await translate_image_qwen(img_data, target_lang)
        
        # 发送翻译后的图片
        base64_str = f'base64://{base64.b64encode(translated_img).decode()}'
        await bot.send(ev, f'[CQ:image,file={base64_str}]')
        
    except Exception as e:
        print(f"图片翻译失败：{e}")
        traceback.print_exc()
        await bot.send(ev, f'翻译失败...请稍后再试')
