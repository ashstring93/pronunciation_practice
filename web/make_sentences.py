import json

# ▼ 여기만 채워 주세요 ▼
# chapter_sentences 에는 챕터별로 문장 리스트를 작성합니다.
# 예: chapter_sentences[1] = [chapter1의 문장1, chapter1의 문장2, ...]
chapter_sentences = {
    1: [
        "I have a pen.",
        "This is a book.",
        "He plays soccer.",
        # … 챕터1의 나머지 문장들 …
    ],
    2: [
        "Where is the library?",
        "She likes music.",
        # … 챕터2의 나머지 문장들 …
    ],
    3: [
        "Good night.",
        # … 챕터3의 나머지 문장들 …
    ]
}

data = []
for ch, texts in chapter_sentences.items():
    for idx, text in enumerate(texts, start=1):
        data.append({
            "chapter": ch,
            "number": idx,
            "text": text,
            # audio 폴더 안에 ch{ch}_{idx}.wav 파일을 준비해 두세요
            "audio": f"audio/ch{ch}_{idx}.wav"
        })

# sentences.json 파일로 저장
with open('sentences.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ sentences.json 파일이 생성되었습니다!")
