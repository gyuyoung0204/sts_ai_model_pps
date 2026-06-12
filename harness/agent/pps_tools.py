# -*- coding: utf-8 -*-
"""[에이전트 하네스] PPS를 'AI 에이전트의 도구'로 노출하는 래퍼 (스캐폴드).

Claude Agent SDK 등에서 아래 함수들을 도구(tool)로 등록하면,
자연어 요청 → 도구 호출 → PPS 실행 형태의 대화형 에이전트가 된다.
함수 자체는 SDK 없이도 단독 동작하므로, 먼저 로직을 검증한 뒤 SDK에 연결하면 된다.
"""
import sys, os, glob, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)
import pandas as pd
import patrol_lib as P
import patrol_api as API


def pps_predict(records):
    """패트롤 레코드(list[dict] 또는 dict)에 등급·코드·점수·사유를 예측한다.
    각 레코드 필수 키: 불량처리 일시, 공정, 설비, 불량내용."""
    return API.score_records(records)


def pps_explain(record):
    """단일 레코드의 등급 산정 사유를 반환한다."""
    r = API.score_records(record if isinstance(record, dict) else record[0])
    return {'등급': r['등급'], '점수': r['점수'], '사유': r['사유']}


def pps_train(file_paths):
    """주어진 엑셀 파일들(누적)로 모델을 재학습하고 요약을 반환한다."""
    frames = []
    for p in (file_paths if isinstance(file_paths, list) else [file_paths]):
        d = pd.read_excel(p)
        d.columns = [str(c).strip() for c in d.columns]
        frames.append(d)
    alld = pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=['불량처리 일시', '설비', '불량내용'])
    kb = P.train_kb(alld)
    json.dump(kb, open(os.path.join(ROOT, 'knowledge_base.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    return {'학습건수': kb['n_train'], '기간': kb['train_period']}


# SDK 연결 시 참고할 도구 메타(이름/설명/입력) — 실제 등록은 agent/README.md 참고
TOOLS = [
    {'name': 'pps_predict', 'fn': pps_predict,
     'desc': '패트롤 데이터에 우선순위 등급/점수/사유 예측', 'input': 'records: list[dict]'},
    {'name': 'pps_explain', 'fn': pps_explain,
     'desc': '특정 불량 건의 등급 산정 이유 설명', 'input': 'record: dict'},
    {'name': 'pps_train', 'fn': pps_train,
     'desc': '누적 데이터로 모델 재학습', 'input': 'file_paths: list[str]'},
]


if __name__ == '__main__':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    # 도구 단독 동작 확인
    demo = pps_predict([{'불량처리 일시': '2026-07-01 09:00', '공정': '스프링신선',
                         '설비': '12"X11H+SP-9호', '불량내용': '수세조 와이어이탈'}])
    print('pps_predict →', json.dumps(demo, ensure_ascii=False))
