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
import urllib.request
import urllib.parse
from gtts import gTTS
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

# ========== TTS (gTTS 模式) ==========
def generate_tts(text):
    """使用 gTTS 生成语音，返回字节"""
    try:
        import sys
        mp3_fp = io.BytesIO()
        tts = gTTS(text=text, lang='zh-cn', slow=False)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        audio = mp3_fp.read()
        print(f"gTTS generated {len(audio)} bytes", file=sys.stderr)
        return audio if len(audio) > 1000 else None
    except Exception as e:
        import sys, traceback
        print(f"TTS error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
魔镜 API - AI点评模块
从 server.py 中提取，便于单独编写
"""

AI_COMMENT_TEMPLATES = {
    "male": {
        # 7个分数段 + 7个年龄段
        "90": {  # S级：天赋型
            "young": "兄弟，这颜值是被老天爷追着喂饭吃吧！走在街上回头率爆表，明星脸无误。建议把精力放在提升内在，因为外表已经无敌了。",
            "mid":   "哥们这长相，成熟与帅气并存，事业加成。客户见了秒签合同，对象见了秒变女朋友。天选之人。",
            "old":   "叔圈天花板。岁月只给你加了气场，颜值依旧能打。活成了别人想要的样子。",
        },
        "80": {  # A级：高质量
            "young": "清爽少年感，五官端正上镜。底子很好，稍微打理下就能甩开同龄人一大截。",
            "mid":   "耐看型帅哥，第一眼不惊艳但越看越有味道。这种长相最扛老，30岁后会越来越帅。",
            "old":   "气质型大叔，胡子拉碴都是帅的。属于女生会主动搭讪的类型。",
        },
        "70": {  # B级：中上
            "young": "基础分不错，是校园里会被偷看的学长。提升下衣品和发型，能直接跨级。",
            "mid":   "长相端正，工作面试都加分。建议练下肩宽和气质，能把7分穿成8分。",
            "old":   "成熟稳重款，相亲市场抢手货。自信最重要，自信的男人最帅。",
        },
        "60": {  # C级：普通
            "young": "五官没硬伤，但还没找到自己的风格。建议换个发型和穿衣路线，颜值能+20。",
            "mid":   "长相普通但有亲和力。努力提升气质和谈吐，会比同龄帅哥更受欢迎。",
            "old":   "长相踏实，不惊艳但耐看。属于过日子型，踏实可靠最重要。",
        },
        "50": {  # C-级：潜力股
            "young": "底子还在，颜值需要工程化改造。先从皮肤和发型开始，半年后能跨档。",
            "mid":   "长相不出众，但气质可以补。健身+护肤+穿搭三件套安排上。",
            "old":   "岁月这把杀猪刀对你是真狠。但男人40一枝花，别放弃。",
        },
        "40": {  # D级：需努力
            "young": "现在不是靠脸吃饭的年纪。拼才华、拼能力、拼人格魅力，一样能赢。",
            "mid":   "颜值不够，实力来凑。把精力放在事业上，比纠结长相划算。",
            "old":   "中年油腻预警。运动、控制饮食、保持清爽，颜值能回升5分。",
        },
        "0":  {  # E级
            "young": "兄弟，颜值是天生的，但气质是自己练的。健身、读书、赚钱，三条路都通罗马。",
            "mid":   "长相普通，但心灵美更珍贵。找对风格、保持整洁，自信的男人最帅。",
            "old":   "年龄不是问题，气质才是关键。学穿搭、学护肤，50岁也能焕发第二春。",
        },
    },
    "female": {
        "90": {
            "young": "仙女下凡！素颜都能吊打一片。校花级别，是被摄影师追着拍的存在。",
            "mid":   "女神本神，岁月对你格外温柔。职场上也会因为颜值被偏爱，记得善用这份优势。",
            "old":   "冻龄女神，50岁活成30岁。状态好到让同龄人羡慕，让年轻人嫉妒。",
        },
        "80": {
            "young": "小美女，五官精致上镜。校花的有力竞争者，会被很多人暗恋。",
            "mid":   "知性美，是那种越看越有味道的长相。职场和情场都很受欢迎。",
            "old":   "气质型美女，保养得当。这个年龄还能保持少女感，已经赢麻了。",
        },
        "70": {
            "young": "清新可爱型，男生缘很好。建议学化妆和穿搭，能直接冲到8分。",
            "mid":   "长相甜美，工作和社交都加分。保持身材和皮肤，状态会一直在线。",
            "old":   "温婉大气型，相亲市场抢手。贤妻良母的脸，生活幸福指数高。",
        },
        "60": {
            "young": "长相清秀，是班里会被偷偷喜欢的女生。学会化妆能加分很多。",
            "mid":   "长相普通但有亲和力。培养气质和才艺，会比纯靠颜值更长久。",
            "old":   "长相端庄，是踏实过日子的类型。家庭和睦最重要。",
        },
        "50": {
            "young": "五官还在底子，化妆和发型改造空间大。多看美妆视频，提升很快。",
            "mid":   "长相平凡，但可以靠气质取胜。读书、运动、护肤，三件套安排上。",
            "old":   "别灰心，每个年龄都有美的定义。保持心态年轻最重要。",
        },
        "40": {
            "young": "现在不是颜值定输赢的年纪。培养才艺和人格魅力，会比漂亮更吸引人。",
            "mid":   "长相普通但个性可以加分。找到自己的风格，自信的女生最美丽。",
            "old":   "抗衰是头等大事。护肤、运动、心情好，比同龄人年轻10岁不是梦。",
        },
        "0":  {
            "young": "姐妹，颜值不是全部。多读书、多运动、保持笑容，自信的女生最闪耀。",
            "mid":   "长相普通，但每个人都有独特魅力。找到自己的风格，比盲目跟风重要。",
            "old":   "年龄不是敌人，心态才是。学穿搭、学化妆，60岁也能活成30岁。",
        },
    },
}

def get_age_segment(age):
    """根据年龄返回年龄段：young/mid/old"""
    if age is None or age < 30:
        return "young"
    elif age < 50:
        return "mid"
    else:
        return "old"

def get_score_segment(score):
    """根据分数返回分数段key：90/80/70/60/50/40/0"""
    if score >= 85:
        return "90"
    elif score >= 75:
        return "80"
    elif score >= 65:
        return "70"
    elif score >= 55:
        return "60"
    elif score >= 45:
        return "50"
    elif score >= 35:
        return "40"
    else:
        return "0"

def generate_ai_comment(score, gender, age):
    """根据分数、性别、年龄生成AI点评"""
    try:
        # 标准化 gender
        g = "male" if gender in ("male", "男", "M", "m") else "female"
        # 标准化 score
        s = float(score) if score else 50.0
        # 选模板
        score_key = get_score_segment(s)
        age_key = get_age_segment(age)
        templates = AI_COMMENT_TEMPLATES.get(g, AI_COMMENT_TEMPLATES["male"])
        segment = templates.get(score_key, templates["60"])
        return segment.get(age_key, segment["mid"])
    except Exception as e:
        print(f"AI comment error: {e}")
        return "自信的你最美丽，继续保持！"


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
        "version": "2.1"
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
        ai_comment = generate_ai_comment(beauty, gender, result.get("age", 0))
        return jsonify({
            "score": round(beauty, 1),
            "gender": gender,
            "age": result.get("age", 0),
            "advice": advice,
            "ai_comment": ai_comment
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
