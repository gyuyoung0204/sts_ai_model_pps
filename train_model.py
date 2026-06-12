# -*- coding: utf-8 -*-
"""[1단계] 모델 학습 — 지금까지 누적된 전체 데이터로 AI 모델(지식베이스)을 만든다.
사용법: python train_model.py <누적_전체데이터.xlsx> [추가파일...]
        (여러 달 파일을 함께 줄 수 있음. 중복 자동 제거)
출력: knowledge_base.json  ← 이게 학습된 모델. 예측 단계에서 불러 씀.
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import patrol_lib as P

HERE = os.path.dirname(os.path.abspath(__file__))
NEEDED = {'불량처리 일시', '공정', '설비', '불량내용'}

def main():
    paths = sys.argv[1:] or [r'C:\Users\Admin\Downloads\스텐 공정패트롤활동 데이터(260612).xlsx']
    frames = []
    for p in paths:
        d = pd.read_excel(p)
        d.columns = [str(c).strip() for c in d.columns]
        if not NEEDED.issubset(set(d.columns)):
            print(f'  ! 컬럼부족 건너뜀: {os.path.basename(p)}'); continue
        frames.append(d)
        print(f'  + {os.path.basename(p)}  ({len(d)}건)')
    if not frames:
        print('학습할 데이터가 없습니다.'); return

    alldf = pd.concat(frames, ignore_index=True)
    before = len(alldf)
    alldf = alldf.drop_duplicates(subset=['불량처리 일시', '설비', '불량내용'])
    kb = P.train_kb(alldf)
    with open(os.path.join(HERE, 'knowledge_base.json'), 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=1)

    # 학습 요약
    std = P.standardize(alldf)
    loc_n = std[std['위치번호'].notna()].groupby('loc_key').size()
    print(f'\n[학습 완료] {kb["n_train"]}건 (중복 {before-len(alldf)}건 제거), 기간 {kb["train_period"]}')
    print(f'  · 위치 프로파일 {len(loc_n)}곳 (3회+ 신뢰가능 {int((loc_n>=3).sum())}곳)')
    print(f'  · 유형 위험가중치 {len(kb["type_weight"])}종, 설비 프로파일 {len(kb["eq_profile"])}대')
    print(f'  · 모델 저장: knowledge_base.json')
    print('\n다음: python predict_new.py <그달_새데이터.xlsx>')

if __name__ == '__main__':
    main()
