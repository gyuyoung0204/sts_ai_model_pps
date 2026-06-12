# -*- coding: utf-8 -*-
"""[자동화 하네스] PPS 월간 파이프라인 — 한 번 실행하면 수집→재학습→예측→출력까지.
스케줄러(Windows 작업 스케줄러/cron)에 등록하면 사람 개입 없이 매달 자동 실행.

폴더 구조(config.json):
  data/history/   누적 학습 데이터(.xlsx)  — 매달 그달 파일이 여기에 쌓임
  data/incoming/  이번 달 신규 데이터(.xlsx) — 예측 대상
  data/results/   예측 결과 출력(.csv)
실행: python harness/run_pipeline.py
"""
import sys, os, json, glob
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import patrol_lib as P
import patrol_api as API

NEED = {'불량처리 일시', '공정', '설비', '불량내용'}


def _resolve(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def _read_valid(folder):
    frames = []
    for f in glob.glob(os.path.join(folder, '*.xlsx')):
        if os.path.basename(f).startswith('~$'):
            continue
        d = pd.read_excel(f)
        d.columns = [str(c).strip() for c in d.columns]
        if NEED <= set(d.columns):
            frames.append((f, d))
    return frames


def main():
    cfg = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf-8'))
    hist, inc, res = map(lambda k: _resolve(cfg[k]), ('history_dir', 'incoming_dir', 'results_dir'))
    for d in (hist, inc, res):
        os.makedirs(d, exist_ok=True)

    # 1) 재학습 (누적 history 전체)
    if cfg.get('retrain', True):
        frames = [d for _, d in _read_valid(hist)]
        if frames:
            alld = pd.concat(frames, ignore_index=True).drop_duplicates(
                subset=['불량처리 일시', '설비', '불량내용'])
            kb = P.train_kb(alld)
            json.dump(kb, open(os.path.join(ROOT, 'knowledge_base.json'), 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
            print(f"[재학습] {kb['n_train']}건 ({kb['train_period']})")
        else:
            print("[재학습] history 비어있음 — 기존 모델 유지")

    # 2) 예측 (incoming 각 파일)
    kb = API.load_model()
    incoming = _read_valid(inc)
    if not incoming:
        print("[예측] incoming 신규 데이터 없음 — 종료")
        return
    for f, raw in incoming:
        scored = pd.DataFrame(API.score_records(raw.to_dict('records'), kb=kb))
        base = os.path.splitext(os.path.basename(f))[0]
        out_csv = os.path.join(res, base + '_예측결과.csv')
        scored.to_csv(out_csv, index=False, encoding='utf-8-sig')
        n = scored['등급'].value_counts()
        print(f"[예측] {base}: {len(scored)}건 → "
              f"긴급{n.get('긴급',0)}/주의{n.get('주의',0)}/일반{n.get('일반',0)} → {os.path.basename(out_csv)}")
        # 처리 완료 파일을 history로 이동(다음 달 학습에 누적)
        if cfg.get('move_processed'):
            os.replace(f, os.path.join(hist, os.path.basename(f)))

    # 3) MES 업로드 (연동 시 구현 지점)
    if cfg.get('mes', {}).get('enabled'):
        print("[MES] 연동 활성 — DB/API 업로드 구현 위치 (현재 미구현)")
    else:
        print(f"[MES] 비활성 — 결과 CSV는 {os.path.relpath(res, ROOT)} 에 저장됨")


if __name__ == '__main__':
    main()
