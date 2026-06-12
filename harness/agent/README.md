# 에이전트 하네스 — Claude Agent SDK 연결

`pps_tools.py`의 함수(`pps_predict`·`pps_explain`·`pps_train`)를 에이전트의 도구로 등록하면,
자연어 요청을 PPS 실행으로 연결하는 대화형 에이전트가 된다.

## 개념
```
사용자: "이번 주 패트롤 데이터에서 급한 것만 알려줘"
   ↓ (에이전트가 의도 파악 → 도구 선택)
pps_predict(records) 호출 → 등급/점수/사유
   ↓
에이전트: "긴급 3건입니다: 8M-7호 가시발생심함 …(사유)"
```

## 연결 절차 (스캐폴드)
1. `pip install claude-agent-sdk` (또는 Anthropic SDK)
2. `TOOLS` 목록의 각 함수를 SDK의 tool로 등록 (이름·설명·입력 스키마는 pps_tools.py의 TOOLS 참고)
3. 시스템 프롬프트에 PPS 역할·등급 기준 요약(등급기준.md) 주입
4. 에이전트 루프 실행 → 사용자 발화 → 도구 호출 → 응답

## 지금 상태
- 도구 함수는 SDK 없이 **단독 동작 검증됨**: `python harness/agent/pps_tools.py`
- 실제 SDK 앱(루프·인증)은 사용자의 API 키·환경이 필요하므로 연결 단계는 별도 진행.

## 주의
- 에이전트는 Claude API를 호출하므로 비용·네트워크가 필요하다(자동화 하네스는 불필요).
- 실데이터를 외부 API로 보낼 때 개인정보(검사원 실명 등) 처리 정책을 따른다.
