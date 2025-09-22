import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import re
import calendar
import pandas as pd

# 페이지 설정
st.set_page_config(
    page_title="군포 캠핑장 예약 현황",
    page_icon="🏕️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 캠핑장 타입 매핑
CAMP_TYPES = {
    '1': '고급',
    '2': '일반',
    '4': '자갈',
    '5': '데크'
}

# 세션 재사용을 위한 전역 세션
@st.cache_resource
def get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
    })
    return session

def scrape_camp_data_fast(date, place_cd, session):
    """최적화된 캠핑장 데이터 스크래핑"""
    try:
        url = "https://www.gunpouc.or.kr/rest/camp/search"
        params = {
            'comcd': 'GUNPO04',
            'part_cd': '02',
            'place_cd': place_cd,
            'sdate': date,
            'edate': '',
            'edate_dsp': '',
            'day_cnt': '1',
            'appkind': '1001'
        }
        
        response = session.get(url, params=params, timeout=8)
        response.raise_for_status()
        
        # 정규식을 사용해서 더 빠르게 파싱
        possible_pattern = r'class="[^"]*li-possible[^"]*possible[^"]*"'
        matches = re.findall(possible_pattern, response.text)
        count = len(matches)
        
        return count
        
    except Exception as e:
        print(f"Error scraping {date}, place {place_cd}: {e}")
        return -1

@st.cache_data(ttl=300)  # 5분 캐시
def get_camp_data_for_date(date_str):
    """특정 날짜의 모든 캠핑장 예약 현황을 가져옵니다."""
    session = get_session()
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_type = {
            executor.submit(scrape_camp_data_fast, date_str, part_cd, session): type_name 
            for part_cd, type_name in CAMP_TYPES.items()
        }
        
        results = {}
        for future in as_completed(future_to_type):
            type_name = future_to_type[future]
            try:
                count = future.result(timeout=10)
                results[type_name] = count
            except Exception as e:
                print(f"Error for {type_name}: {e}")
                results[type_name] = -1
    
    return results

def get_camp_data_for_month(year, month):
    """한 달 전체 데이터를 가져옵니다."""
    
    # 해당 월의 모든 날짜 생성
    _, last_day = calendar.monthrange(year, month)
    dates = []
    for day in range(1, last_day + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        dates.append(date_str)
    
    results = {}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, date_str in enumerate(dates):
        status_text.text(f"로딩 중... {date_str} ({i+1}/{len(dates)})")
        results[date_str] = get_camp_data_for_date(date_str)
        progress_bar.progress((i + 1) / len(dates))
    
    status_text.text("완료!")
    time.sleep(1)
    progress_bar.empty()
    status_text.empty()
    
    return results

def create_calendar_html(year, month, camp_data):
    """달력 HTML 생성"""
    cal = calendar.monthcalendar(year, month)
    
    html = f"""
    <style>
    .calendar-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
        margin: 10px 0;
    }}
    .calendar-table th {{
        background-color: #d4d4d4;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        border: 1px solid #999;
        font-size: 14px;
    }}
    .calendar-table td {{
        border: 1px solid #999;
        padding: 8px;
        text-align: left;
        vertical-align: top;
        height: 120px;
        width: 14.28%;
    }}
    .date-cell {{
        font-weight: bold;
        color: #333;
        margin-bottom: 5px;
        text-align: center;
        font-size: 14px;
    }}
    .camp-info {{
        font-size: 11px;
        line-height: 1.3;
    }}
    .camp-info div {{
        margin: 2px 0;
    }}
    .available {{ color: #0066cc; font-weight: bold; }}
    .unavailable {{ color: #cc0000; font-weight: bold; }}
    .error {{ color: #ff6b6b; font-style: italic; }}
    .loading {{ color: #666; font-style: italic; }}
    </style>
    
    <table class="calendar-table">
    <thead>
    <tr>
    <th>일</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th>토</th>
    </tr>
    </thead>
    <tbody>
    """
    
    for week in cal:
        html += "<tr>"
        for day in week:
            if day == 0:
                html += "<td></td>"
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                html += f'<td><div class="date-cell">{day:02d}</div>'
                
                if date_str in camp_data:
                    html += '<div class="camp-info">'
                    for camp_type, count in camp_data[date_str].items():
                        if count == -1:
                            html += f'<div class="error">{camp_type}: X</div>'
                        elif count > 0:
                            html += f'<div class="available">{camp_type}: {count}</div>'
                        else:
                            html += f'<div class="unavailable">{camp_type}: {count}</div>'
                    html += '</div>'
                else:
                    html += '<div class="camp-info"><div class="loading">대기중...</div></div>'
                
                html += "</td>"
        html += "</tr>"
    
    html += "</tbody></table>"
    return html

# 메인 앱
def main():
    st.title("🏕️ 군포 캠핑장 예약 현황 달력")
    
    # 현재 날짜 기준
    current_date = datetime.now()
    
    # 사이드바에서 날짜 선택
    with st.sidebar:
        st.header("📅 날짜 선택")
        
        selected_year = st.selectbox(
            "년도", 
            options=list(range(current_date.year, current_date.year + 2)),
            index=0
        )
        
        selected_month = st.selectbox(
            "월", 
            options=list(range(1, 13)),
            index=current_date.month - 1
        )
        
        st.header("🎯 조회 옵션")
        
        if st.button("🔄 이번 달 전체 로드", type="primary"):
            st.session_state.load_month = True
            st.session_state.selected_year = selected_year
            st.session_state.selected_month = selected_month
        
        if st.button("🗑️ 캐시 삭제"):
            st.cache_data.clear()
            st.success("캐시가 삭제되었습니다!")
        
        # 사용법 안내
        st.markdown("---")
        st.markdown("### 📖 사용법")
        st.markdown("""
        1. **년도와 월 선택**
        2. **'이번 달 전체 로드'** 클릭
        3. 달력에서 예약 현황 확인
        4. 개별 날짜는 아래에서 조회
        """)
    
    # 메인 영역
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"### {selected_year}년 {selected_month}월")
    
    # 월 전체 로드 처리
    if st.session_state.get('load_month', False):
        year = st.session_state.get('selected_year', selected_year)
        month = st.session_state.get('selected_month', selected_month)
        
        st.info(f"📊 {year}년 {month}월 데이터를 로딩하고 있습니다...")
        
        try:
            camp_data = get_camp_data_for_month(year, month)
            calendar_html = create_calendar_html(year, month, camp_data)
            st.components.v1.html(calendar_html, height=700, scrolling=True)
            st.success(f"✅ {year}년 {month}월 데이터 로딩 완료!")
        except Exception as e:
            st.error(f"❌ 데이터 로딩 중 오류가 발생했습니다: {str(e)}")
        
        st.session_state.load_month = False
    else:
        # 기본 빈 달력 표시
        empty_data = {}
        calendar_html = create_calendar_html(selected_year, selected_month, empty_data)
        st.components.v1.html(calendar_html, height=700, scrolling=True)
        st.info("💡 위의 '이번 달 전체 로드' 버튼을 클릭하여 실제 예약 현황을 확인하세요!")
    
    # 범례
    st.markdown("---")
    st.markdown("### 📋 범례")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("🔵 **파란색**: 예약 가능")
    with col2:
        st.markdown("🔴 **빨간색**: 예약 불가")
    with col3:
        st.markdown("⚫ **회색**: 로딩 중")
    with col4:
        st.markdown("🟠 **주황색**: 오류 발생")
    
    # 개별 날짜 조회
    st.markdown("---")
    st.subheader("📅 개별 날짜 조회")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_date = st.date_input(
            "날짜를 선택하세요",
            value=datetime.now().date(),
            help="조회할 날짜를 선택하세요"
        )
    
    with col2:
        if st.button("🔍 조회하기"):
            date_str = selected_date.strftime("%Y-%m-%d")
            
            with st.spinner(f"📡 {date_str} 데이터 로딩 중..."):
                data = get_camp_data_for_date(date_str)
            
            st.subheader(f"📊 {date_str} 예약 현황")
            
            # 결과를 표로 표시
            df_data = []
            for camp_type, count in data.items():
                if count == -1:
                    status = "❌ 오류"
                    display_count = "오류"
                elif count > 0:
                    status = "✅ 예약가능"
                    display_count = count
                else:
                    status = "❌ 예약불가"
                    display_count = 0
                
                df_data.append({
                    "캠핑장 타입": camp_type,
                    "예약 가능 수": display_count,
                    "상태": status
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # 요약 정보
            total_available = sum([count for count in data.values() if count > 0])
            st.metric("총 예약 가능 사이트", total_available)

    # 푸터
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 20px;'>
        <small>
        📊 데이터 출처: 군포시 캠핑장 공식 사이트<br>
        🔄 데이터는 5분마다 캐시됩니다<br>
        ⏰ 최종 업데이트: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """
        </small>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()