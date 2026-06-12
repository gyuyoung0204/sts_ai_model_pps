# -*- coding: utf-8 -*-
"""공정패트롤 표준화 + 우선순위 스코어링 공용 모듈."""
import re
import numpy as np
import pandas as pd

# ---------- 스프링 공정 유형 우선순위 (사용자 지정) ----------
# 와이어 이탈(1순위) > 와이어 튐(2순위) > 다이스 마모(3순위). 나머지 유형은 기존 학습값 유지.
# 가중치 숫자만 바꾸면 순위·강도 조정 가능.
SPRING_TYPE_WEIGHT = {
    '와이어 이탈': 2.0,   # 1순위
    '와이어 튐': 1.8,     # 2순위
    '다이스 마모': 1.6,   # 3순위
}
SPRING_TYPE_RANK = {'와이어 이탈': 1, '와이어 튐': 2, '다이스 마모': 3}

# 스프링 지정 유형은 점수와 무관하게 등급을 직접 고정(사용자 지정).
SPRING_TYPE_GRADE = {
    '와이어 이탈': '긴급',
    '와이어 튐': '주의',
    '다이스 마모': '일반',
}
GRADE_CODE = {'긴급': 1, '주의': 2, '일반': 3}


def grade_for(score, 공정군, 표준세분류, urgent=60, warn=25):
    """등급 결정: 스프링 지정 유형은 유형으로 고정, 그 외는 점수 컷으로.
    반환 (등급, 등급코드)."""
    if str(공정군) == '스프링' and 표준세분류 in SPRING_TYPE_GRADE:
        g = SPRING_TYPE_GRADE[표준세분류]
    else:
        g = '긴급' if score >= urgent else ('주의' if score >= warn else '일반')
    return g, GRADE_CODE[g]

# ---------- 표준 분류 규칙 (위에서부터 우선 적용) ----------
RULES = [
 ('표면품질', '가시발생', r'가시'),
 ('표면품질', '탈지불량', r'탈지'),
 ('표면품질', '변색/외관', r'색상|변색|외관'),
 ('표면품질', '스크래치', r'스크래치'),
 ('표면품질', '탄화물 부착', r'탄화물'),
 ('소모품·마모', '다이스 마모', r'광택|늘어남|마모|선경빠짐|파손|감면율|사용량|비율'),
 ('소모품·마모', '윤활제 관리', r'윤활제|윤활재'),
 ('소모품·마모', '도유/보루', r'도유|보루'),
 ('소모품·마모', '수세미 사용', r'수세미'),
 ('와이어 주행', '와이어 튐', r'튐'),
 ('와이어 주행', '와이어 이탈', r'이탈|올라탐'),
 ('와이어 주행', '와이어 꼬임', r'꼬임'),
 ('와이어 주행', '와이어 데임/간섭', r'데임|간섭'),
 ('와이어 주행', '선떨림', r'떨림|흔들림'),
 ('와이어 주행', '권취불량', r'권취|벌어짐|꿀렁|타이트'),
 ('설비·기계', '덴샤/가이드', r'덴샤|가이드|방지봉'),
 ('설비·기계', '냉각 이상', r'냉각|누수'),
 ('설비·기계', '정렬/구동', r'어라이먼트|움직임|소음|로라'),
 ('설비·기계', '급기/여과(필터·브로워)', r'필터|세라믹볼|브로워|블로워'),
 ('관리·기록', '기록 누락/오류', r'기록|MES|에러'),
 ('관리·기록', '선습성/공정조건', r'선습성|PCD선경'),
 ('소모품·마모', '교체 지시(일반)', r'교체지시'),
]
PART_RULES = [
 ('다이스(초경)', r'초경'), ('다이스(PCD)', r'PCD'),
 ('윤활제', r'윤활제|윤활재'), ('다이스', r'다이스'),
 ('마스터드럼', r'마스터\s*드럼'), ('덴샤', r'덴샤'),
 ('가이드(방지봉)', r'가이드|방지봉'), ('로라', r'로라'),
 ('드럼', r'드럼'), ('공급대', r'공급대'),
 ('수세조/산탈지조', r'수세조|산탈지조'), ('냉각수', r'냉각수|냉각'),
 ('필터', r'필터'), ('세라믹볼', r'세라믹볼'), ('도유(보루/밸브)', r'도유|보루'),
 ('피막', r'피막'), ('브로워', r'브로워|블로워'), ('트레버스', r'트레버스'),
]


def standardize(df):
    """원본 데이터프레임에 표준 필드 컬럼을 추가해 반환."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df['txt'] = df['불량내용'].fillna('').astype(str).str.strip()
    df['dt'] = pd.to_datetime(df['불량처리 일시'], errors='coerce')

    def _loc(row):
        t, proc = row['txt'], row['공정']
        m = re.match(r'^\s*(\d+)\s', t)
        if m and str(proc).find('열처리') >= 0:
            return ('보빈', int(m.group(1)))
        m = re.search(r'(\d+)번\s*(?:초경)?(?:다이스|PCD|다이스박스)', t)
        if m:
            return ('다이스', int(m.group(1)))
        m = re.search(r'(\d+)번\s*드럼', t)
        if m:
            return ('드럼', int(m.group(1)))
        return (None, None)
    df[['위치유형', '위치번호']] = df.apply(_loc, axis=1, result_type='expand')

    def _part(t):
        for name, pat in PART_RULES:
            if re.search(pat, t):
                return name
        return ''
    df['관련부품'] = df['txt'].apply(_part)

    def _cls(row):
        t = row['txt']
        for major, minor, pat in RULES:
            if re.search(pat, t):
                return (major, minor)
        old = str(row.get('설비불량유형', ''))
        if '와이어' in old:
            return ('와이어 주행', '와이어 이탈')
        if old == '다이스':
            return ('소모품·마모', '다이스 마모')
        return ('미분류', old)
    df[['표준대분류', '표준세분류']] = df.apply(_cls, axis=1, result_type='expand')

    df['심각도'] = np.where(df['txt'].str.contains('심함|심하'), '심함', '보통')
    df['조치요청'] = df['txt'].str.contains('지시|요망|바람|요함|확인|교체|교정|업데이트')
    df['loc_key'] = df['설비'].astype(str) + '|' + df['위치유형'].fillna('-').astype(str) + '|' + df['위치번호'].fillna(0).astype(int).astype(str)

    # 공정군: 크게 열처리 / 스프링 / 기타로 묶음
    def _pgroup(p):
        p = str(p)
        if '열처리' in p:
            return '열처리'
        if '스프링' in p:
            return '스프링'
        return '기타'
    df['공정군'] = df['공정'].apply(_pgroup)
    return df


def train_kb(df_hist, half_life_days=30, burst_half_life_days=10):
    """과거 표준화 데이터에서 지식베이스(우선순위 기준)를 학습.
    burst_half_life_days: 단기 빈발 가중의 반감기(작을수록 '최근에 몰린 발생'을 더 크게 봄)."""
    d = standardize(df_hist)
    ref = d['dt'].max()
    d['_recency'] = np.power(0.5, (ref - d['dt']).dt.days / half_life_days)

    # 세분류별 위험가중치: 심함 발생률을 베이지안 평활(글로벌 심함률로 prior)
    g_sev = (d['심각도'] == '심함').mean()
    g_sev_safe = g_sev if g_sev > 0 else 0.1   # 심함 0건이어도 0나누기 방지
    sev = d.groupby('표준세분류')['심각도'].apply(lambda s: ((s == '심함').sum() + g_sev_safe * 5) / (len(s) + 5))
    type_w = (sev / g_sev_safe).clip(lower=0.5, upper=3.0).to_dict()  # 글로벌 대비 배수

    # 위치별 이벤트 이력(시점기준 채점을 위해 발생일·심함일 목록 저장)
    loc_profile = {}
    dl = d[d['위치번호'].notna() & d['dt'].notna()]
    for key, g in dl.groupby('loc_key'):
        g = g.sort_values('dt')
        dates = [str(x.date()) for x in g['dt']]
        sev_dates = [str(x.date()) for x in g.loc[g['심각도'] == '심함', 'dt']]
        loc_profile[key] = {'dates': dates, 'severe_dates': sev_dates}

    # 설비 단위 프로파일(위치 없는 건도 포함)
    eq = d.groupby('설비').agg(n=('txt', 'size'), sev=('심각도', lambda s: (s == '심함').sum()),
                              recent_w=('_recency', 'sum')).to_dict('index')

    return {
        'ref_date': str(ref.date()),
        'half_life_days': half_life_days,
        'burst_half_life_days': burst_half_life_days,
        'global_severe_rate': float(g_sev),
        'type_weight': type_w,
        'loc_profile': loc_profile,
        'eq_profile': {k: {kk: float(vv) for kk, vv in v.items()} for k, v in eq.items()},
        'n_train': int(len(d)),
        'train_period': f"{d['dt'].min().date()} ~ {ref.date()}",
    }


def score(df_new, kb, asof=None):
    """새 데이터에 우선순위 점수/등급/사유를 부여."""
    d = standardize(df_new)
    asof = pd.to_datetime(asof) if asof is not None else d['dt'].max()
    g_sev = kb['global_severe_rate']

    rows = []
    for _, r in d.iterrows():
        reasons = []
        score = 10.0  # 기본점

        # (1) 유형 위험가중치 (스프링은 지정 순위 우선: 이탈>튐>마모, 나머지는 학습값)
        tw = kb['type_weight'].get(r['표준세분류'], 1.0)
        spring_pri = (str(r.get('공정군')) == '스프링' and r['표준세분류'] in SPRING_TYPE_WEIGHT)
        if spring_pri:
            tw = SPRING_TYPE_WEIGHT[r['표준세분류']]
        score *= tw
        if spring_pri:
            reasons.append(f"스프링 {SPRING_TYPE_RANK[r['표준세분류']]}순위 유형({r['표준세분류']})")
        elif tw >= 1.5:
            reasons.append(f"고위험 유형({r['표준세분류']})")

        # (2) 본 건 심각도
        if r['심각도'] == '심함':
            score *= 2.2
            reasons.append("심함 표기")

        # (3) 위치 이력 — '단기 빈발(최근 급증)'을 전체 횟수보다 크게 반영. 시점 이전만 집계.
        lp = kb['loc_profile'].get(r['loc_key'])
        rdt = r['dt']
        HL = kb.get('burst_half_life_days', 10)
        if lp and r['위치번호'] is not None and not pd.isna(r['위치번호']) and pd.notna(rdt):
            cutoff = rdt.normalize()
            prior = sorted(pd.Timestamp(x) for x in lp['dates'] if pd.Timestamp(x) < cutoff)
            n = len(prior)
            if n > 0:
                db = [(cutoff - d).days for d in prior]
                # 단기 가중 빈도: 최근일수록 큰 가중(반감기 HL일). 오래된 다수보다 최근 소수가 더 큼.
                intensity = float(sum(0.5 ** (x / HL) for x in db))
                r14 = sum(1 for x in db if x <= 14)
                r30 = sum(1 for x in db if x <= 30)
                if intensity >= 2.0:
                    score *= 2.1; reasons.append(f"단기 급증(최근14일 {r14}회·30일 {r30}회)")
                elif intensity >= 1.2:
                    score *= 1.7; reasons.append(f"단기 빈발(최근14일 {r14}회·30일 {r30}회)")
                elif intensity >= 0.6:
                    score *= 1.35; reasons.append(f"최근 재발(30일내 {r30}회)")
                elif intensity >= 0.15:
                    score *= 1.12; reasons.append(f"근래 발생(총 {n}회·분산)")
                else:
                    reasons.append(f"과거 발생(총 {n}회·오래됨)")
                # 장기 누적은 보조적으로만(작게) — 전체 횟수의 비중을 낮춤
                if n >= 6:
                    score *= 1.1; reasons.append(f"장기 누적 {n}회")
            prior_sev = [x for x in lp['severe_dates'] if pd.Timestamp(x) < cutoff]
            if prior_sev:
                score *= 1.2; reasons.append("과거 심함 이력")

        # (4) 설비 위험도(상위 설비)
        ep = kb['eq_profile'].get(str(r['설비']))
        if ep and ep['n'] >= 15:
            score *= 1.3; reasons.append(f"다발 설비({int(ep['n'])}건)")

        # (5) 조치요청 명시
        if r['조치요청']:
            score *= 1.25; reasons.append("조치요청 문구")

        rows.append((round(score, 1), ' · '.join(reasons) if reasons else '특이사항 없음'))

    d['우선순위점수'] = [x[0] for x in rows]
    d['우선순위사유'] = [x[1] for x in rows]
    # 등급: 스프링 지정유형은 유형으로 고정, 나머지는 점수 컷
    grades = [grade_for(sc, pg, sub) for sc, pg, sub in
              zip(d['우선순위점수'], d['공정군'], d['표준세분류'])]
    d['긴급도'] = [g[0] for g in grades]
    d['등급코드'] = [g[1] for g in grades]
    # 등급 우선, 그 안에서 점수순 정렬
    return d.sort_values(['등급코드', '우선순위점수'], ascending=[True, False])
