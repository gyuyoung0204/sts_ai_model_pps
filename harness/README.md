# PPS 하네스 (Harness)

PPS 엔진을 "정해진 순서로 자동 실행되는 구조"로 감싼 것. 두 갈래가 있다.

```
harness/
  config.json          자동화 설정(폴더 경로·재학습 여부·MES)
  run_pipeline.py      [자동화] 수집→재학습→예측→출력 (스케줄러용)
  schedule_windows.md  Windows 작업 스케줄러 등록 방법
  agent/
    pps_tools.py       [에이전트] PPS를 도구로 노출하는 래퍼
    README.md          Claude Agent SDK 연결 방법
```

## A. 자동화 하네스 (스케줄러) — MES 연동의 최종 형태

Claude 없이 혼자 도는 운영용. 매달 자동으로:
`data/history`(누적 학습) → 재학습 → `data/incoming`(신규) 예측 → `data/results` 출력 → (MES)

```
python harness/run_pipeline.py
```

폴더에 파일만 떨어뜨리면 된다:
- 그달 신규 패트롤 엑셀 → `data/incoming/`
- 학습용 누적 데이터 → `data/history/` (config의 move_processed=true면 예측 후 자동 이동)

스케줄 등록은 `schedule_windows.md` 참고. MES 연동은 config의 `mes`를 채우고
`run_pipeline.py`의 3단계(MES 업로드)를 구현하면 된다.

## B. 에이전트 하네스 (Claude Agent SDK) — 대화형 분석

PPS를 도구(predict/explain/train)로 가진 AI 에이전트. 자연어로 유연하게 다룬다.
`agent/pps_tools.py`의 함수가 그 도구이며, 단독 동작이 검증되어 있다.
SDK 연결은 `agent/README.md` 참고. (Claude API 연결·비용 필요)

## 참고
- 두 하네스 모두 같은 PPS 엔진(`patrol_lib`·`patrol_api`·`knowledge_base.json`)을 공유한다.
- 실데이터·개인정보는 `data/` 폴더에 두며 저장소에 커밋하지 않는다(.gitignore 처리).
