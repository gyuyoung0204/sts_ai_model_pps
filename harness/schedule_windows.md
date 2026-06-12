# Windows 작업 스케줄러 등록 (자동화 하네스)

매달 1일 09:00에 PPS 파이프라인을 자동 실행하는 예시.

## 1) 배치 파일 만들기 — `harness/run_monthly.bat`
```bat
@echo off
cd /d "%~dp0\.."
"C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe" harness\run_pipeline.py >> harness\run.log 2>&1
```
(파이썬 경로는 `where python`으로 확인 후 맞춘다.)

## 2) 스케줄 등록 (PowerShell, 관리자)
```powershell
$action  = New-ScheduledTaskAction -Execute "C:\tmpfile\sts_mes_model\harness\run_monthly.bat"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am   # 또는 매월 1일
Register-ScheduledTask -TaskName "PPS_Monthly" -Action $action -Trigger $trigger -Description "PPS 월간 예측 파이프라인"
```
> 매월 1일 트리거는 작업 스케줄러 GUI에서 "월별"로 지정하는 게 가장 간단하다.

## 3) 동작 확인
- 수동 실행: 작업 스케줄러에서 `PPS_Monthly` → 실행
- 로그: `harness/run.log` 확인
- 결과: `data/results/` 의 `*_예측결과.csv`

## 운영 흐름
1. 매달 그달 패트롤 엑셀을 `data/incoming/` 에 저장(또는 MES에서 추출 자동화)
2. 스케줄러가 `run_pipeline.py` 실행 → 재학습 + 예측 + 결과 저장
3. (MES 연동 시) 결과를 MES 테이블에 업로드
4. config `move_processed=true` 면 처리된 파일이 `data/history/`로 이동해 다음 달 학습에 누적
