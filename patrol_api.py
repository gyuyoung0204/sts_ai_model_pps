# -*- coding: utf-8 -*-
"""MES 연동용 호출 인터페이스 (파일과 분리된 추론 API).

미래 DB 연동 흐름:
    rows = mes_db.query(...)          # MES에서 패트롤 레코드 조회 (list[dict])
    result = score_records(rows)      # 모델 호출 → 등급/코드/점수/사유 반환
    mes_db.update(result)             # MES 테이블에 4개 필드 저장

레코드는 dict 1건 또는 list[dict]. 최소 필요 키: '불량처리 일시','공정','설비','불량내용'
(있으면 활용: '설비불량유형','검사원'). 반환은 입력키 보존 + 등급/등급코드/점수/사유.
"""
import os, json
import pandas as pd
import patrol_lib as P

HERE = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(HERE, 'knowledge_base.json')
GRADE_CODE = {'긴급': 1, '주의': 2, '일반': 3}   # MES 코드체계에 맞게 조정 지점


def load_model(path=KB_PATH):
    """학습된 지식베이스(모델)를 로드."""
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def score_records(records, kb=None, asof=None):
    """레코드(dict 또는 list[dict])를 채점해 등급/코드/점수/사유를 반환.

    반환: list[dict] — 입력 컬럼 + {등급, 등급코드, 점수, 사유}
    """
    single = isinstance(records, dict)
    rows = [records] if single else list(records)
    if kb is None:
        kb = load_model()

    df = pd.DataFrame(rows)
    scored = P.score(df, kb, asof=asof).sort_index()

    out = []
    for i, r in scored.iterrows():
        grade = str(r['긴급도'])
        rec = dict(rows[i]) if i < len(rows) else {}
        rec.update({
            '공정군': str(r['공정군']),
            '표준세분류': str(r['표준세분류']),
            '등급': grade,
            '등급코드': GRADE_CODE.get(grade, 0),
            '점수': float(r['우선순위점수']),
            '사유': str(r['우선순위사유']),
        })
        out.append(rec)
    return out[0] if single else out


# ---- 단독 실행 시: DB 행을 흉내낸 입력으로 호출 데모 ----
if __name__ == '__main__':
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # MES DB에서 막 꺼낸 신규 레코드라고 가정
    incoming = [
        {'불량처리 일시': '2026-07-03 09:10:00', '공정': '1차열처리', '설비': '8M-7호',
         '검사원': '김민수', '설비불량유형': '가시발생', '불량내용': '15 가시발생심함'},
        {'불량처리 일시': '2026-07-03 09:12:00', '공정': '스프링신선', '설비': '12"X11H+SP-9호',
         '검사원': '정순철', '설비불량유형': '다이스', '불량내용': '7번다이스 광택발생'},
        {'불량처리 일시': '2026-07-03 14:05:00', '공정': '1차신선', '설비': '24"X9H+SP',
         '검사원': '배선우', '설비불량유형': '기타', '불량내용': '피막농도 기록 지시'},
    ]
    result = score_records(incoming)
    print(json.dumps(result, ensure_ascii=False, indent=2))
