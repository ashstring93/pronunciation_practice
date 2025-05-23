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
sys.modules['parselmouth.adapters']               = types.ModuleType('parselmouth.adapters')
sys.modules['parselmouth.adapters.dfp']           = types.ModuleType('parselmouth.adapters.dfp')

# interface 모듈 스텁
iface_mod = types.ModuleType('parselmouth.adapters.dfp.interface')
setattr(iface_mod, 'DFPInterface', type('DFPInterface', (), {}))
sys.modules['parselmouth.adapters.dfp.interface'] = iface_mod

# client 모듈 스텁
sys.modules['parselmouth.adapters.dfp.client']    = types.ModuleType('parselmouth.adapters.dfp.client')

# config 모듈 스텁
cfg_mod = types.ModuleType('parselmouth.adapters.dfp.config')
setattr(cfg_mod, 'DFPConfig', type('DFPConfig', (), {}))
sys.modules['parselmouth.adapters.dfp.config']    = cfg_mod
# ───────────────────────────────────────────────────────

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import parselmouth
import numpy as np
from dtw import dtw
from pydub import AudioSegment
import os

# Flask 앱 선언부: static_folder와 static_url_path를 지정하여
# server/static 디렉토리의 파일을 루트 URL로 서빙합니다.
app = Flask(
    __name__,
    static_folder="static",
    static_url_path=""
)

# 모든 엔드포인트에 대해 CORS 허용
CORS(app)

@app.route("/")
def hello():
    return "서버가 잘 켜졌어요!"

@app.route("/api/analyze", methods=["POST"])
@cross_origin()
def analyze():
    try:
        # 1) 업로드된 WebM 파일 저장
        uploaded  = request.files["file"]
        webm_path = f"temp_{uploaded.filename}"
        uploaded.save(webm_path)

        # 2) WebM → WAV 변환
        wav_path = webm_path.rsplit(".", 1)[0] + ".wav"
        AudioSegment.from_file(webm_path, format="webm") \
                    .export(wav_path, format="wav")

        # 3) Sound 객체 준비
        snd_native  = parselmouth.Sound("static/native/ch1_1.wav")
        snd_learner = parselmouth.Sound(wav_path)

        # 4) 피치·강도 추출 헬퍼
        def extract_pitch_arr(sound):
            return np.nan_to_num(sound.to_pitch().selected_array["frequency"])

        def extract_intensity_arr(sound):
            return np.nan_to_num(sound.to_intensity().values.T.flatten())

        p_native    = extract_pitch_arr(snd_native)
        p_learner   = extract_pitch_arr(snd_learner)
        i_native    = extract_intensity_arr(snd_native)
        i_learner   = extract_intensity_arr(snd_learner)

        # 5) DTW 거리 계산
        dist_pitch     = dtw(p_native,    p_learner,     dist_method="euclidean").distance
        dist_intensity = dtw(i_native,    i_learner,     dist_method="euclidean").distance

        # 6) 발화 길이 비율 (rhythm)
        dur_native   = snd_native.get_total_duration()
        dur_learner  = snd_learner.get_total_duration()
        rhythm_ratio = min(dur_native, dur_learner) / max(dur_native, dur_learner)

        # 7) 개별 점수(0~100) 환산
        max_dp = max(len(p_native), len(p_learner)) * 200
        max_di = max(len(i_native), len(i_learner)) * 200

        score_pitch     = max(0, 100 * (1 - dist_pitch     / max_dp))
        score_intensity = max(0, 100 * (1 - dist_intensity / max_di))
        score_rhythm    = rhythm_ratio * 100

        # 8) 최종 가중합 (50% : 30% : 20%)
        final_score = (
            score_pitch     * 0.5 +
            score_intensity * 0.3 +
            score_rhythm    * 0.2
        )
        final_score = round(final_score, 1)

        # 9) 차트 그리기용 배열
        pitch_dict     = {"native": p_native.tolist(),    "learner": p_learner.tolist()}
        intensity_dict = {"native": i_native.tolist(),    "learner": i_learner.tolist()}

        # 10) 임시 파일 삭제
        os.remove(webm_path)
        os.remove(wav_path)

        return jsonify({
            "score":     final_score,
            "breakdown": {
                "pitch":     round(score_pitch,1),
                "intensity": round(score_intensity,1),
                "rhythm":    round(score_rhythm,1)
            },
            "pitch":     pitch_dict,
            "intensity": intensity_dict
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # 로컬 테스트 시 포트를 0.0.0.0:5000으로 바인딩
    app.run(host="0.0.0.0", port=5000, debug=True)
