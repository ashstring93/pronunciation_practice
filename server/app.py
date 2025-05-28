# server/app.py

# ───────────────────────────────────────────────────────
# 1) Python3.11: UserDict·collections.Mapping 패치
import sys, types, collections, collections.abc
collections.Mapping = collections.abc.Mapping
fake_ud = types.ModuleType("UserDict")
fake_ud.DictMixin = collections.abc.Mapping
sys.modules["UserDict"] = fake_ud

# 2) Python3.11: urllib.quote 패치
import urllib, urllib.parse
urllib.quote = urllib.parse.quote

# 3) parselmouth DFP 어댑터 스텁 (interface, client, config)
sys.modules['parselmouth.adapters']             = types.ModuleType('parselmouth.adapters')
sys.modules['parselmouth.adapters.dfp']         = types.ModuleType('parselmouth.adapters.dfp')

# interface 모듈 스텁
iface_mod = types.ModuleType('parselmouth.adapters.dfp.interface')
setattr(iface_mod, 'DFPInterface', type('DFPInterface', (), {}))
sys.modules['parselmouth.adapters.dfp.interface'] = iface_mod

# client 모듈 스텁
sys.modules['parselmouth.adapters.dfp.client']  = types.ModuleType('parselmouth.adapters.dfp.client')

# config 모듈 스텁
cfg_mod = types.ModuleType('parselmouth.adapters.dfp.config')
setattr(cfg_mod, 'DFPConfig', type('DFPConfig', (), {}))
sys.modules['parselmouth.adapters.dfp.config']    = cfg_mod
# ───────────────────────────────────────────────────────

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin

# ── 여기가 핵심 수정 부분 ──
import parselmouth
from parselmouth.praat import Sound as PM_Sound
# parselmouth.Sound 가 없을 경우를 대비해 복원
parselmouth.Sound = PM_Sound
# ──────────────────────────

import numpy as np
from dtw import dtw
from pydub import AudioSegment
import os

# 이제 Flask 앱 선언부: static_folder 설정도 잊지 마세요
app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

@app.route("/")
def hello():
    return "서버가 잘 켜졌어요!"

@app.route("/api/analyze", methods=["POST"])
@cross_origin()
def analyze():
    try:
        # 1) WebM 업로드
        uploaded  = request.files["file"]
        webm_path = f"temp_{uploaded.filename}"
        uploaded.save(webm_path)

        # 2) WebM → WAV
        wav_path = webm_path.rsplit(".", 1)[0] + ".wav"
        AudioSegment.from_file(webm_path, format="webm") \
                    .export(wav_path, format="wav")

        # 3) 파셀마우스 Sound 로드
        snd_native  = parselmouth.Sound("static/native/ch1_1.wav")
        snd_learner = parselmouth.Sound(wav_path)

        # 4) 피치·강도 추출 헬퍼
        def extract_pitch_arr(sound):
            return np.nan_to_num(sound.to_pitch().selected_array["frequency"])
        def extract_intensity_arr(sound):
            return np.nan_to_num(sound.to_intensity().values.T.flatten())

        p_native  = extract_pitch_arr(snd_native)
        p_learner = extract_pitch_arr(snd_learner)
        i_native  = extract_intensity_arr(snd_native)
        i_learner = extract_intensity_arr(snd_learner)

        # 5) DTW 거리 계산
        dp = dtw(p_native, p_learner, dist_method="euclidean").distance
        di = dtw(i_native, i_learner, dist_method="euclidean").distance

        # 6) 리듬(rhythm) 비율
        rn = min(snd_native.get_total_duration(),
                 snd_learner.get_total_duration()) \
             / max(snd_native.get_total_duration(),
                   snd_learner.get_total_duration())

        # 7) 점수 환산
        max_dp = max(len(p_native), len(p_learner)) * 200
        max_di = max(len(i_native), len(i_learner)) * 200

        score_p = max(0, 100 * (1 - dp / max_dp))
        score_i = max(0, 100 * (1 - di / max_di))
        score_r = rn * 100

        final = round(score_p*0.5 + score_i*0.3 + score_r*0.2, 1)

        # 8) 차트용 데이터
        pitch_dict     = {"native": p_native.tolist(),     "learner": p_learner.tolist()}
        intensity_dict = {"native": i_native.tolist(),     "learner": i_learner.tolist()}

        # 9) 임시 파일 삭제
        os.remove(webm_path)
        os.remove(wav_path)

        return jsonify({
            "score":     final,
            "breakdown": {
                "pitch":     round(score_p,1),
                "intensity": round(score_i,1),
                "rhythm":    round(score_r,1)
            },
            "pitch":     pitch_dict,
            "intensity": intensity_dict
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
