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
#    ★ 이 부분이 반드시 parselmouth를 import 하기 전에 와야 합니다
sys.modules['parselmouth.adapters']    = types.ModuleType('parselmouth.adapters')
sys.modules['parselmouth.adapters.dfp'] = types.ModuleType('parselmouth.adapters.dfp')

iface_mod = types.ModuleType('parselmouth.adapters.dfp.interface')
setattr(iface_mod, 'DFPInterface', type('DFPInterface', (), {}))
sys.modules['parselmouth.adapters.dfp.interface'] = iface_mod

sys.modules['parselmouth.adapters.dfp.client'] = types.ModuleType('parselmouth.adapters.dfp.client')

cfg_mod = types.ModuleType('parselmouth.adapters.dfp.config')
setattr(cfg_mod, 'DFPConfig', type('DFPConfig', (), {}))
sys.modules['parselmouth.adapters.dfp.config'] = cfg_mod
# ───────────────────────────────────────────────────────

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS, cross_origin
import numpy as np
from dtw import dtw
from pydub import AudioSegment
import os

# ── 여기만 바꾸시면 됩니다! ──
from parselmouth import Sound as PM_Sound
try:
    # C-extension 모듈에서 직접 로드
    from parselmouth._parselmouth import Sound as PM_Sound
except ImportError:
    # fallback: 루트 패키지에 노출되어 있으면 이걸 씁니다
    import parselmouth
    PM_Sound = parselmouth.Sound
# ───────────────────────────

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/analyze", methods=["POST"])
@cross_origin()
def analyze():
    try:
        # 1) 업로드된 WebM 저장
        uploaded  = request.files["file"]
        webm_path = f"temp_{uploaded.filename}"
        uploaded.save(webm_path)

        # 2) WebM → WAV
        wav_path = webm_path.rsplit(".",1)[0] + ".wav"
        AudioSegment.from_file(webm_path, format="webm")\
                    .export(wav_path, format="wav")

        # 3) Sound 로딩 (static/native/ch1_1.wav 예시)
        snd_native  = PM_Sound(os.path.join(app.static_folder, "native", "ch1_1.wav"))
        snd_learner = PM_Sound(wav_path)

        # 4) 피치·강도 추출
        def extract_pitch_arr(s):     return np.nan_to_num(s.to_pitch().selected_array["frequency"])
        def extract_intensity_arr(s): return np.nan_to_num(s.to_intensity().values.T.flatten())

        p_native  = extract_pitch_arr(snd_native)
        p_learner = extract_pitch_arr(snd_learner)
        i_native  = extract_intensity_arr(snd_native)
        i_learner = extract_intensity_arr(snd_learner)

        # 5) DTW 거리
        dist_p = dtw(p_native, p_learner, dist_method="euclidean").distance
        dist_i = dtw(i_native, i_learner, dist_method="euclidean").distance

        # 6) 리듬 비율
        dur_n = snd_native.get_total_duration()
        dur_l = snd_learner.get_total_duration()
        rhythm_ratio = min(dur_n, dur_l) / max(dur_n, dur_l)

        # 7) 점수 환산
        max_dp = max(len(p_native), len(p_learner)) * 200
        max_di = max(len(i_native), len(i_learner)) * 200

        score_p = max(0, 100*(1 - dist_p/max_dp))
        score_i = max(0, 100*(1 - dist_i/max_di))
        score_r = rhythm_ratio * 100
        final_score = round(score_p*0.5 + score_i*0.3 + score_r*0.2, 1)

        # 8) 차트 데이터
        pitch_dict     = {"native": p_native.tolist(),     "learner": p_learner.tolist()}
        intensity_dict = {"native": i_native.tolist(),     "learner": i_learner.tolist()}

        # 9) 임시 파일 삭제
        os.remove(webm_path); os.remove(wav_path)

        return jsonify({
            "score": final_score,
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
