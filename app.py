from flask import Flask, render_template, jsonify, request
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask_cors import CORS
import time
import re

app = Flask(__name__)
CORS(app)

# 캠핑장 타입 매핑
CAMP_TYPES = {
    '1': '고급',
    '2': '일반',
    '4': '자갈',
    '5': '데크'
}

# 세션 재사용을 위한 전역 세션
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
})

@app.route('/')
def index():
    return render_template('calendar.html')

@app.route('/api/camp-data/<date>')
def get_camp_data(date):
    """특정 날짜의 모든 캠핑장 예약 현황을 병렬로 가져옵니다."""
    try:
        start_time = time.time()
        
        # ThreadPoolExecutor를 사용해서 병렬 처리
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_type = {
                executor.submit(scrape_camp_data_fast, date, part_cd): type_name 
                for part_cd, type_name in CAMP_TYPES.items()
            }
            
            results = {}
            for future in as_completed(future_to_type):
                type_name = future_to_type[future]
                try:
                    count = future.result(timeout=5)  # 5초 타임아웃
                    results[type_name] = count
                except Exception as e:
                    print(f"Error for {type_name}: {e}")
                    results[type_name] = -1
        
        end_time = time.time()
        print(f"Date {date} processed in {end_time - start_time:.2f} seconds")
        
        return jsonify({
            'success': True,
            'date': date,
            'data': results,
            'processing_time': round(end_time - start_time, 2)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/camp-data-range')
def get_camp_data_range():
    """날짜 범위의 캠핑장 예약 현황을 병렬로 가져옵니다."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'success': False, 'error': 'start_date와 end_date가 필요합니다'}), 400
    
    try:
        start_time = time.time()
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # 모든 날짜와 캠핑장 타입 조합 생성
        tasks = []
        date_type_map = {}
        
        current_date = start
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            for part_cd, type_name in CAMP_TYPES.items():
                task_id = f"{date_str}_{part_cd}"
                tasks.append((date_str, part_cd, type_name))
                date_type_map[task_id] = (date_str, type_name)
            current_date += timedelta(days=1)
        
        # 모든 작업을 병렬로 실행 (최대 8개 동시 실행)
        results = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_task = {
                executor.submit(scrape_camp_data_fast, date_str, part_cd): (date_str, type_name)
                for date_str, part_cd, type_name in tasks
            }
            
            for future in as_completed(future_to_task):
                date_str, type_name = future_to_task[future]
                try:
                    count = future.result(timeout=10)  # 10초 타임아웃
                    if date_str not in results:
                        results[date_str] = {}
                    results[date_str][type_name] = count
                except Exception as e:
                    print(f"Error for {date_str} {type_name}: {e}")
                    if date_str not in results:
                        results[date_str] = {}
                    results[date_str][type_name] = -1
        
        end_time = time.time()
        print(f"Range {start_date} to {end_date} processed in {end_time - start_time:.2f} seconds")
        
        return jsonify({
            'success': True,
            'data': results,
            'processing_time': round(end_time - start_time, 2)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def scrape_camp_data_fast(date, place_cd):
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
        
        # 세션 재사용으로 연결 시간 단축
        response = session.get(url, params=params, timeout=8)
        response.raise_for_status()
        
        # 정규식을 사용해서 더 빠르게 파싱
        possible_pattern = r'class="[^"]*li-possible[^"]*possible[^"]*"'
        matches = re.findall(possible_pattern, response.text)
        count = len(matches)
        
        print(f"Date: {date}, Place: {place_cd}, Available: {count}")
        return count
        
    except Exception as e:
        print(f"Error scraping {date}, place {place_cd}: {e}")
        return -1

# 캐시를 위한 딕셔너리 (선택사항)
cache = {}
cache_timeout = 300  # 5분

@app.route('/api/camp-data-cached/<date>')
def get_camp_data_cached(date):
    """캐시를 사용한 데이터 조회"""
    cache_key = f"camp_data_{date}"
    current_time = time.time()
    
    # 캐시 확인
    if cache_key in cache:
        cached_data, timestamp = cache[cache_key]
        if current_time - timestamp < cache_timeout:
            return jsonify({
                'success': True,
                'date': date,
                'data': cached_data,
                'cached': True
            })
    
    # 캐시에 없으면 새로 조회
    result = get_camp_data(date)
    if result.status_code == 200:
        data = result.get_json()
        if data['success']:
            cache[cache_key] = (data['data'], current_time)
    
    return result

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', threaded=True, use_reloader=False)