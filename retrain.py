# -*- coding: utf-8 -*-
"""사용법: python retrain.py [데이터폴더]
폴더 안의 모든 패트롤 엑셀(.xlsx, '우선순위'/'표준화' 결과물 제외)을 합쳐
지식베이스를 재학습하고 knowledge_base.json을 갱신한다.
월별 파일이 쌓이면 이 한 줄만 다시 돌리면 모델이 최신화된다."""
import sys, io, os, glob, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import patrol_lib as P

HERE = os.path.dirname(os.path.abspath(__file__))
NEEDED = {'불량처리 일시', '공정', '설비', '불량내용'}

def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'data')
    if not os.path.isdir(folder):
        folder = HERE  # 폴더 없으면 현재 위치에서 원본 검색
    files = [f for f in glob.glob(os.path.join(folder, '*.xlsx'))
             if not any(k in os.path.basename(f) for k in ('우선순위', '표준화', '_샘플', '~$'))]
    frames = []
    for f in files:
        try:
            d = pd.read_excel(f)
            d.columns = [str(c).strip() for c in d.columns]
            if NEEDED.issubset(set(d.columns)):
                d['_src'] = os.path.basename(f)
                frames.append(d)
                print(f'  + {os.path.basename(f)}  ({len(d)}건)')
        except Exception as e:
            print(f'  ! {os.path.basename(f)} 건너뜀: {e}')
    if not frames:
        print('학습할 패트롤 파일을 찾지 못했습니다. 폴더를 확인하세요:', folder)
        return
    alldf = pd.concat(frames, ignore_index=True)
    # 중복 제거(같은 일시+설비+내용)
    before = len(alldf)
    alldf = alldf.drop_duplicates(subset=['불량처리 일시', '설비', '불량내용'])
    kb = P.train_kb(alldf)
    with open(os.path.join(HERE, 'knowledge_base.json'), 'w', encoding='utf-8') as fp:
        json.dump(kb, fp, ensure_ascii=False, indent=1)

    # 신뢰도 리포트
    std = P.standardize(alldf)
    loc_n = std[std['위치번호'].notna()].groupby('loc_key').size()
    print(f'\n재학습 완료: {kb["n_train"]}건 (중복 {before-len(alldf)}건 제거), 기간 {kb["train_period"]}')
    print(f'학습 파일 {len(files)}개 → knowledge_base.json 갱신')
    print(f'위치 프로파일 {len(loc_n)}곳 / 그중 3회 이상 관측(신뢰가능) {int((loc_n>=3).sum())}곳')

if __name__ == '__main__':
    main()
