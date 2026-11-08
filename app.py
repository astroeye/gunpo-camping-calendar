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

# 달력을 일요일부터 시작하도록 설정
calendar.setfirstweekday(calendar.SUNDAY)

# 세션 상태 초기화
if 'current_year' not in st.session_state:
    current_date = datetime.now()
    st.session_state.current_year = current_date.year
    st.session_state.current_month = current_date.month

# 세션 재사용을 위한 전역 세션
@st.cache_resource
def get_session():
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
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

def get_camp_data_for_date(date_str, use_cache=True, cache_minutes=5):
    """특정 날짜의 모든 캠핑장 예약 현황을 가져옵니다."""
    if use_cache:
        return _get_camp_data_cached(date_str)
    else:
        return _get_camp_data_direct(date_str)

@st.cache_data(ttl=300)
def _get_camp_data_cached(date_str):
    """캐시된 단일 날짜 데이터 조회"""
    data = _get_camp_data_direct(date_str)
    res = dict(data)
    res['_cached_time'] = datetime.now().strftime("%H:%M:%S")
    return res

def _get_camp_data_direct(date_str):
    """실시간 단일 날짜 데이터 조회"""
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
    
    results['_fetch_time'] = datetime.now().strftime("%H:%M:%S")
    return results

def _fetch_month_data_direct(year, month):
    """월 전체 실시간 데이터 일괄 병렬 조회 (초고속 병렬화)"""
    session = get_session()
    _, last_day = calendar.monthrange(year, month)
    
    tasks = []
    for day in range(1, last_day + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        for part_cd, type_name in CAMP_TYPES.items():
            tasks.append((date_str, part_cd, type_name))
            
    results = {f"{year}-{month:02d}-{day:02d}": {} for day in range(1, last_day + 1)}
    fetch_time = datetime.now().strftime("%H:%M:%S")
    
    # 한 달 전체 조합(약 120여 개)을 25개 스레드로 동시에 요청
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_task = {
            executor.submit(scrape_camp_data_fast, date_str, part_cd, session): (date_str, type_name)
            for date_str, part_cd, type_name in tasks
        }
        
        for future in as_completed(future_to_task):
            date_str, type_name = future_to_task[future]
            try:
                count = future.result(timeout=10)
                results[date_str][type_name] = count
            except Exception as e:
                print(f"Error scraping {date_str} {type_name}: {e}")
                results[date_str][type_name] = -1

    for date_str in results:
        results[date_str]['_fetch_time'] = fetch_time
        
    return results

@st.cache_data(ttl=300)
def _fetch_month_data_cached(year, month):
    """월 전체 캐시 데이터 조회"""
    data = _fetch_month_data_direct(year, month)
    cached_time = datetime.now().strftime("%H:%M:%S")
    
    cached_results = {}
    for date_str, camp_info in data.items():
        day_data = dict(camp_info)
        day_data['_cached_time'] = cached_time
        cached_results[date_str] = day_data
        
    return cached_results

def get_camp_data_for_month(year, month, use_cache=True, cache_minutes=5):
    """한 달 전체 데이터를 초고속 병렬 처리로 가져옵니다."""
    start_time = datetime.now()
    
    if use_cache:
        results = _fetch_month_data_cached(year, month)
    else:
        results = _fetch_month_data_direct(year, month)
        
    end_time = datetime.now()
    return results, start_time, end_time

def create_calendar_html(year, month, camp_data):
    """달력 HTML 생성 - 일요일부터 시작"""
    # 일요일부터 시작하는 달력 생성
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
    .calendar-table th.sunday {{
        color: #d63384;
    }}
    .calendar-table th.saturday {{
        color: #0d6efd;
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
    .date-cell.sunday {{
        color: #d63384;
    }}
    .date-cell.saturday {{
        color: #0d6efd;
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
    <th class="sunday">일</th>
    <th>월</th>
    <th>화</th>
    <th>수</th>
    <th>목</th>
    <th>금</th>
    <th class="saturday">토</th>
    </tr>
    </thead>
    <tbody>
    """
    
    for week in cal:
        html += "<tr>"
        for day_index, day in enumerate(week):
            if day == 0:
                html += "<td></td>"
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                # 요일별 클래스 설정 (일요일=0, 토요일=6)
                day_class = ""
                if day_index == 0:  # 일요일
                    day_class = "sunday"
                elif day_index == 6:  # 토요일
                    day_class = "saturday"
                
                html += f'<td><div class="date-cell {day_class}">{day:02d}</div>'
                
                if date_str in camp_data:
                    data = camp_data[date_str]
                    html += '<div class="camp-info">'
                    for camp_type, count in data.items():
                        # 메타데이터는 제외
                        if camp_type.startswith('_'):
                            continue
                        
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

def change_month(delta):
    """월 변경 함수"""
    new_month = st.session_state.current_month + delta
    new_year = st.session_state.current_year
    
    if new_month > 12:
        new_month = 1
        new_year += 1
    elif new_month < 1:
        new_month = 12
        new_year -= 1
    
    st.session_state.current_month = new_month
    st.session_state.current_year = new_year

def go_to_current_month():
    """현재 월로 이동"""
    current_date = datetime.now()
    st.session_state.current_year = current_date.year
    st.session_state.current_month = current_date.month

# CSS로 상단 여백 최소화
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    .stApp > header {
        background-color: transparent;
    }
    .stApp {
        margin-top: -20px;
    }
    h1 {
        padding-top: 0rem;
        margin-top: 0rem;
        margin-bottom: 1rem;
        font-size: 1.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# 메인 앱
def main():
    # 컴팩트한 제목
    st.markdown("# 🏕️ 군포 캠핑장 예약 현황")
    
    # 사이드바는 설정용으로만 사용
    with st.sidebar:
        st.header("⚙️ 설정")
        
        # 캐시 사용 여부 선택
        use_cache = st.radio(
            "데이터 로딩 방식",
            ["🔄 실시간 (느림, 정확)", "💾 캐시 사용 (빠름)"],
            index=1,
            help="실시간: 매번 새로운 데이터를 가져옵니다 (느림)\n캐시: 일정 시간 동안 저장된 데이터를 사용합니다 (빠름)"
        )
        use_cache_bool = "캐시 사용" in use_cache
        
        if use_cache_bool:
            cache_minutes = st.slider(
                "캐시 유지 시간 (분)",
                min_value=1,
                max_value=30,
                value=5,
                help="설정한 시간 동안 이전 데이터를 재사용합니다"
            )
        else:
            cache_minutes = 0
            st.warning("⚠️ 실시간 모드는 로딩이 오래 걸릴 수 있습니다.")
        
        if st.button("🗑️ 캐시 삭제"):
            st.cache_data.clear()
            st.success("캐시가 삭제되었습니다!")
        
        # 캐시 상태 표시
        st.markdown("---")
        st.markdown("### 📊 캐시 정보")
        if use_cache_bool:
            st.info(f"💾 캐시 모드: {cache_minutes}분")
            st.caption(f"데이터는 {cache_minutes}분 동안 저장됩니다")
        else:
            st.info("🔄 실시간 모드")
            st.caption("매번 새로운 데이터를 가져옵니다")
        
        # 사용법 안내
        st.markdown("---")
        st.markdown("### 📖 사용법")
        st.markdown("""
        1. **좌우 화살표로 월 이동**
        2. **'이번 달 전체 로드'** 클릭
        3. 달력에서 예약 현황 확인
        """)

    # 컴팩트한 년월 네비게이션 (년도 버튼 제거)
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    with col1:
        if st.button("◀", help="이전 달"):
            change_month(-1)
            st.rerun()
    
    with col2:
        if st.button("📅", help="현재 월로 이동"):
            go_to_current_month()
            st.rerun()
    
    with col3:
        # 현재 년월 표시
        current_date_str = f"{st.session_state.current_year}년 {st.session_state.current_month}월"
        st.markdown(f"<h2 style='text-align: center; margin: 10px 0;'>{current_date_str}</h2>", 
                   unsafe_allow_html=True)
    
    with col4:
        if st.button("▶", help="다음 달"):
            change_month(1)
            st.rerun()
    
    with col5:
        cache_status = f"(캐시: {cache_minutes}분)" if use_cache_bool else "(실시간)"
        
        if st.button("🔄 로드", 
                    type="primary", 
                    help=f"이번 달 전체 데이터를 {cache_status} 로딩합니다"):
            st.session_state.load_month = True
            st.session_state.use_cache = use_cache_bool
            st.session_state.cache_minutes = cache_minutes
            st.rerun()
    
    # 월 전체 로드 처리
    if st.session_state.get('load_month', False):
        year = st.session_state.current_year
        month = st.session_state.current_month
        use_cache_session = st.session_state.get('use_cache', True)
        cache_minutes_session = st.session_state.get('cache_minutes', 5)
        
        mode_text = f"캐시 모드 ({cache_minutes_session}분)" if use_cache_session else "실시간 모드"
        
        try:
            # 로딩 시작
            with st.spinner(f"📊 {year}년 {month}월 데이터를 {mode_text}로 로딩 중입니다..."):
                camp_data, start_time, end_time = get_camp_data_for_month(year, month, use_cache_session, cache_minutes_session)
            
            # 달력 표시
            calendar_html = create_calendar_html(year, month, camp_data)
            st.components.v1.html(calendar_html, height=700, scrolling=True)
            
            # 로딩 완료 메시지와 시간 정보
            loading_time = (end_time - start_time).total_seconds()
            
            # 첫 번째 데이터의 시간 정보 가져오기
            sample_date = list(camp_data.keys())[0]
            sample_data = camp_data[sample_date]
            
            if use_cache_session:
                if '_cached_time' in sample_data:
                    data_time = sample_data['_cached_time']
                    st.success(f"✅ {year}년 {month}월 캐시 데이터 로딩 완료!")
                    st.info(f"📊 캐시 데이터 생성 시간: {data_time} | 로딩 시간: {loading_time:.1f}초")
                else:
                    st.success(f"✅ {year}년 {month}월 데이터 로딩 완료! (캐시: {cache_minutes_session}분)")
            else:
                if '_fetch_time' in sample_data:
                    data_time = sample_data['_fetch_time']
                    st.success(f"✅ {year}년 {month}월 실시간 데이터 로딩 완료!")
                    st.info(f"📊 실시간 데이터 조회 시간: {data_time} | 총 로딩 시간: {loading_time:.1f}초")
                else:
                    st.success(f"✅ {year}년 {month}월 실시간 데이터 로딩 완료!")
                    
        except Exception as e:
            st.error(f"❌ 데이터 로딩 중 오류가 발생했습니다: {str(e)}")
        
        st.session_state.load_month = False
    else:
        # 기본 빈 달력 표시
        empty_data = {}
        calendar_html = create_calendar_html(st.session_state.current_year, st.session_state.current_month, empty_data)
        st.components.v1.html(calendar_html, height=700, scrolling=True)
        st.info("💡 우측 상단의 '🔄 로드' 버튼을 클릭하여 예약 현황을 확인하세요!")
    
    # 컴팩트한 범례
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

    # 간단한 푸터
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 10px;'>
        <small>
        📊 데이터 출처: 군포시 캠핑장 공식 사이트 | 
        🔄 <strong>네비게이션</strong>: ◀▶ 월 이동, 📅 현재 월 | 
        🗓️ 달력은 일요일부터 시작
        </small>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()