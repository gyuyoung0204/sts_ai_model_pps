# -*- coding: utf-8 -*-
"""공정패트롤 불량 우선순위 예측 대시보드 (Streamlit).
실행:  streamlit run dashboard.py
브라우저에서 엑셀 업로드 → 학습된 모델로 등급/코드/점수/사유 예측 → 표·차트·다운로드.
"""
import io, os, json
import pandas as pd
import streamlit as st
import patrol_api as API
import patrol_lib as P

HERE = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(HERE, 'knowledge_base.json')
GCOLOR = {'긴급': '#F4C0C0', '주의': '#FBE2B7', '일반': '#E5EFD9'}
GFONT = {'긴급': '#901010', '주의': '#7A4B00', '일반': '#3B5A1E'}

st.set_page_config(page_title='PPS · 공정패트롤 우선순위 예측', page_icon='🔧', layout='wide')


def load_kb():
    if not os.path.exists(KB_PATH):
        return None
    with open(KB_PATH, encoding='utf-8') as f:
        return json.load(f)


def regrade(row, urgent, warn):
    # 스프링 지정유형은 유형으로 고정, 나머지는 점수 컷 (patrol_lib와 동일 규칙)
    return P.grade_for(row['점수'], row.get('공정군', ''), row.get('표준세분류', ''), urgent, warn)


def style_rows(df):
    def _row(r):
        c = GCOLOR.get(r['등급'], '#FFFFFF'); f = GFONT.get(r['등급'], '#000')
        return [f'background-color:{c};color:{f}'] * len(r)
    return df.style.apply(_row, axis=1)


# ===== 사이드바 =====
st.sidebar.title('🔧 PPS 모델 설정')
kb = load_kb()
if kb:
    st.sidebar.success(f"학습됨: {kb['n_train']}건\n\n기간 {kb['train_period']}")
    st.sidebar.caption(f"위치 프로파일 {len(kb['loc_profile'])}곳 · 단기빈발 반감기 {kb.get('burst_half_life_days',10)}일")
else:
    st.sidebar.error('knowledge_base.json 없음 — 먼저 모델을 학습하세요.')

st.sidebar.markdown('---')
st.sidebar.subheader('등급 컷 (점수 기준)')
urgent = st.sidebar.slider('긴급 ≥', 30, 120, 60, 5)
warn = st.sidebar.slider('주의 ≥', 10, 60, 25, 5)

st.sidebar.markdown('---')
with st.sidebar.expander('📚 모델 재학습 (누적 데이터)'):
    train_file = st.file_uploader('학습용 전체 데이터(.xlsx)', type=['xlsx'], key='train')
    if train_file and st.button('이 데이터로 재학습'):
        d = pd.read_excel(train_file)
        d.columns = [str(c).strip() for c in d.columns]
        new_kb = P.train_kb(d)
        with open(KB_PATH, 'w', encoding='utf-8') as f:
            json.dump(new_kb, f, ensure_ascii=False, indent=1)
        st.success(f"재학습 완료: {new_kb['n_train']}건 ({new_kb['train_period']})")
        st.rerun()


# ===== 본문 =====
st.title('PPS — Patrol Priority Scorer')
st.caption('공정패트롤 불량 우선순위 예측 모델 · 엑셀을 올리면 등급·코드·점수·사유를 예측합니다.')

up = st.file_uploader('예측할 패트롤 엑셀(.xlsx)을 올리세요', type=['xlsx'], key='predict')

if up is None:
    st.info('⬆️ 엑셀 파일을 올리면 예측이 시작됩니다. 필요한 컬럼: 불량처리 일시 · 공정 · 설비 · 불량내용')
    st.stop()
if kb is None:
    st.stop()

raw = pd.read_excel(up)
raw.columns = [str(c).strip() for c in raw.columns]
need = {'불량처리 일시', '공정', '설비', '불량내용'}
miss = need - set(raw.columns)
if miss:
    st.error(f'필수 컬럼 누락: {miss}')
    st.stop()

# 예측
records = raw.to_dict('records')
scored = pd.DataFrame(API.score_records(records, kb=kb))
# 사이드바 컷으로 등급 재계산 (스프링 지정유형은 유형으로 고정)
g = scored.apply(lambda r: regrade(r, urgent, warn), axis=1)
scored['등급'] = [x[0] for x in g]
scored['등급코드'] = [x[1] for x in g]
scored = scored.sort_values(['등급코드', '점수'], ascending=[True, False]).reset_index(drop=True)

# ----- 요약 지표 -----
n = scored['등급'].value_counts()
c1, c2, c3, c4 = st.columns(4)
c1.metric('총 건수', len(scored))
c2.metric('🔴 긴급', int(n.get('긴급', 0)))
c3.metric('🟡 주의', int(n.get('주의', 0)))
c4.metric('🟢 일반', int(n.get('일반', 0)))

# ----- 차트 -----
col1, col2 = st.columns(2)
with col1:
    st.subheader('등급 분포')
    gd = scored['등급'].value_counts().reindex(['긴급', '주의', '일반']).fillna(0)
    st.bar_chart(gd, color='#888780', horizontal=True)
with col2:
    st.subheader('공정군 분포')
    if '공정군' in scored.columns:
        st.bar_chart(scored['공정군'].value_counts(), color='#378ADD', horizontal=True)

# ----- 긴급/주의 우선 처리 리스트 -----
st.subheader('🚨 우선 처리 대상 (긴급·주의)')
top = scored[scored['등급'].isin(['긴급', '주의'])]
show_cols = [c for c in ['등급', '등급코드', '점수', '공정군', '표준세분류', '설비', '불량내용', '사유'] if c in scored.columns]
if len(top):
    st.dataframe(style_rows(top[show_cols]), use_container_width=True, hide_index=True)
else:
    st.write('긴급·주의 해당 없음')

# ----- 필터 + 전체 표 -----
st.subheader('전체 예측 결과')
fcol1, fcol2 = st.columns(2)
gsel = fcol1.multiselect('등급 필터', ['긴급', '주의', '일반'], default=['긴급', '주의', '일반'])
psel = fcol2.multiselect('공정군 필터', sorted(scored['공정군'].unique()) if '공정군' in scored else [],
                         default=sorted(scored['공정군'].unique()) if '공정군' in scored else [])
view = scored[scored['등급'].isin(gsel)]
if '공정군' in scored and psel:
    view = view[view['공정군'].isin(psel)]
st.dataframe(style_rows(view[show_cols]), use_container_width=True, hide_index=True)

# ----- 다운로드 -----
st.subheader('결과 내보내기')
out_cols = list(raw.columns) + [c for c in ['공정군', '등급', '등급코드', '점수', '사유'] if c in scored.columns]
out = scored[[c for c in out_cols if c in scored.columns]]
d1, d2 = st.columns(2)
csv = out.to_csv(index=False).encode('utf-8-sig')
d1.download_button('📥 MES 업로드용 CSV', csv, file_name='예측결과.csv', mime='text/csv')
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as w:
    out.to_excel(w, index=False, sheet_name='예측결과')
d2.download_button('📥 검토용 엑셀', buf.getvalue(), file_name='예측결과.xlsx',
                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
