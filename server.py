#!/usr/bin/env python3
"""
魔镜 Mojing App - 云端后端 (Railway部署版)
提供人脸检测、颜值评分、TTS功能
"""
import os
import json
import base64
import random
import io
import tempfile
import subprocess
import urllib.request
import urllib.parse
from flask import Flask, request, jsonify, send_file, Response

app = Flask(__name__)

# ========== 配置（通过环境变量注入， Railway 面板设置）==========
BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")
PORT = int(os.environ.get("PORT", 8080))

# ========== 百度AI ==========
_baidu_token = None
_baidu_token_time = 0

def get_baidu_token():
    global _baidu_token, _baidu_token_time
    # 缓存token，25小时后刷新
    import time
    if _baidu_token and (time.time() - _baidu_token_time) < 90000:
        return _baidu_token
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())
    _baidu_token = data["access_token"]
    _baidu_token_time = time.time()
    return _baidu_token

def get_beauty_score_baidu(image_bytes):
    token = get_baidu_token()
    url = f"https://aip.baidubce.com/rest/2.0/face/v3/detect?access_token={token}"
    img_b64 = base64.b64encode(image_bytes).decode()
    data = urllib.parse.urlencode({
        "image": img_b64,
        "image_type": "BASE64",
        "face_field": "age,gender,beauty,emotion",
        "max_face_num": 1
    }).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read().decode("utf-8", errors="replace"))
        if result.get("error_code"):
            return None, f"百度API错误: {result.get('error_msg', '未知')}"
        faces = result.get("result", {}).get("face_list", [])
        if not faces:
            return None, "未检测到人脸"
        face = faces[0]
        return {
            "beauty": face.get("beauty", 0),
            "gender": face.get("gender", {}).get("type", "male"),
            "age": face.get("age", 0)
        }, None
    except Exception as e:
        return None, f"请求失败: {e}"

# ========== 建议库 ==========
ADVICE_LIBRARY = {
    "male": [
        "皮肤状态不错，注意保持清洁和保湿。",
        "注意防晒，保护皮肤免受紫外线伤害。",
        "晚上注意护肤，保持皮肤水润。",
        "油性皮肤建议用控油洁面，早晚各一次。",
        "鼻翼两侧容易出油，注意定期去黑头。",
        "嘴唇容易干裂的话，随身带润唇膏吧。",
        "剃须后记得用须后水，减少刺激。",
        "痘痘肌切忌用手挤，容易留疤。",
        "男士也需要用爽肤水和乳液，别偷懒。",
        "眼周细纹开始出现了，该用眼霜了。",
        "发型可以尝试更有层次感的造型。",
        "发际线后移的话，尽早做好护发功课。",
        "头顶扁塌可以试试蓬松喷雾。",
        "两侧鬓角修整齐，整个人精神很多。",
        "染发别太频繁，对发质伤害大。",
        "建议定期修整眉形，提升精气神。",
        "眉毛太淡可以用眉笔轻轻填色。",
        "眉峰位置定好了，整个人气质会不一样。",
        "杂毛修干净，眼神会更有神。",
        "男士眉形不要修太细，自然粗一点更有男人味。",
        "穿搭可以试试同色系，显高又高级。",
        "鞋子干净很重要，脏鞋毁一身。",
        "合身的衣服比名牌更重要。",
        "黑色显瘦，白色显精神，基础款永不过时。",
        "配饰不用多，一块手表就够了。",
        "色彩不要超过三种，简约即高级。",
        "坚持健身，线条出来整个人气质不一样。",
        "坐姿要正，驼背很影响气质。",
        "肩宽一点穿衣服更好看，可以练肩。",
        "肚子上的肉藏不住，核心训练安排上。",
        "脖子前倾的话，靠墙站每天10分钟。",
        "微笑是最好的化妆品，多笑一笑。",
        "眼神要坚定，别躲闪，自信最重要。",
        "说话放慢语速，听起来更有底气。",
        "站姿挺拔，气场立刻两米八。",
        "指甲修剪干净，别留黑边。",
        "口气问题要重视，随身带薄荷糖。",
        "眼镜框型选对了，颜值翻倍。",
        "胡须如果留，就要修剪整齐，别邋遢。",
    ],
    "female": [
        "皮肤状态很好，继续保持哦！",
        "可以尝试更精致的妆容，突出五官优势。",
        "注意防晒和保湿，保持皮肤年轻状态。",
        "晚上一定要卸妆干净，别带妆睡觉。",
        "面膜一周2-3次就够了，别过度。",
        "眼霜从现在开始用，预防细纹。",
        "痘痘不要手挤，用祛痘贴更卫生。",
        "唇部去角质后涂润唇膏，嘴唇更饱满。",
        "精华液含抗氧化成分，早晚用起来。",
        "脖子也要涂防晒，不然色差会很尴尬。",
        "发型可以尝试新的造型，换个心情。",
        "刘海长度刚好在眉毛附近最减龄。",
        "发色不要太浅，深色更显肤白。",
        "编发可以试试，增加造型感。",
        "头顶蓬松显脸小，用倒吹的方法。",
        "发尾分叉要定期修剪，别舍不得。",
        "帽子是懒人造型神器，选对款式很加分。",
        "扎发不要太紧，留一点碎发修饰脸型。",
        "底妆轻薄自然，别涂太厚。",
        "口红颜色选对，整个人气色提升。",
        "眉毛画好了，五官立体感立刻出来。",
        "腮红位置打高了显嫩，打低了显成熟。",
        "眼线不需要太粗，自然拉长就好。",
        "假睫毛选自然的，太长会显得夸张。",
        "高光打在鼻梁和苹果肌，立体感满分。",
        "定妆做好了，一整天不脱妆。",
        "穿搭可以更有层次感，突出身材优势。",
        "腰线提高显腿长，小个子必学。",
        "颜色不要超过三种，全身呼应更高级。",
        "配饰是灵魂，耳环项链选对款式。",
        "裙长选对，膝盖附近最显瘦。",
        "高腰裤是神器，腿短也能穿出大长腿。",
        "同色系穿搭显高级，黑白灰怎么搭都不错。",
        "鞋子选裸色，腿长立刻+5cm。",
        "驼背会影响整体气质，靠墙站纠正。",
        "脖子前倾练天鹅颈，线条会很好看。",
        "笑容练习，露齿笑比抿嘴笑更自信。",
        "体态好了，整个人气场完全不一样。",
        "指甲油颜色选好，和衣服呼应更高级。",
        "香水喷在脉搏处，味道更持久。",
        "包包选对款式，整体造型加分。",
        "眼镜框型选对，脸型修饰效果很好。",
    ],
}

def get_advice(gender, beauty):
    advice_list = ADVICE_LIBRARY.get(gender, ADVICE_LIBRARY["male"])
    return random.sample(advice_list, min(3, len(advice_list)))

# ========== TTS ==========
def generate_tts(text):
    """使用 edge-tts 生成语音，返回字节"""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    try:
        subprocess.run(
            ["edge-tts", "--voice", "zh-CN-XiaoxiaoNeural", "--text", text, "--write-media", tmp_path],
            capture_output=True, timeout=30, check=True
        )
        with open(tmp_path, "rb") as f:
            return f.read()
    except Exception as e:
        print(f"TTS error: {e}")
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except:
            pass

# ========== 路由 ==========
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/api/status")
def status():
    return jsonify({
        "status": "ok",
        "service": "mojing-api",
        "version": "2.0"
    })

@app.route("/api/grade", methods=["POST"])
def grade():
    try:
        data = request.get_json(force=True)
        img_bytes = base64.b64decode(data["image"])
        result, error = get_beauty_score_baidu(img_bytes)
        if error:
            return jsonify({"error": error}), 400
        beauty = result["beauty"]
        gender = result["gender"]
        advice = get_advice(gender, beauty)
        return jsonify({
            "score": round(beauty, 1),
            "gender": gender,
            "age": result.get("age", 0),
            "advice": advice
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/tts", methods=["GET", "POST"])
def tts():
    try:
        if request.method == "GET":
            text = request.args.get("text", "")
        else:
            data = request.get_json(force=True)
            text = data.get("text", "")
        if not text:
            return jsonify({"error": "缺少 text 参数"}), 400
        text = urllib.parse.unquote(text)
        mp3_bytes = generate_tts(text)
        if mp3_bytes and len(mp3_bytes) > 100:
            return Response(mp3_bytes, mimetype="audio/mpeg",
                          headers={"Content-Length": str(len(mp3_bytes))})
        return jsonify({"error": "TTS生成失败"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print(f"魔镜 API 启动中... 端口 {PORT}")
    app.run(host="0.0.0.0", port=PORT)
