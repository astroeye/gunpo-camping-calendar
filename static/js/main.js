let currentYear = 2025;
let currentMonth = 10;

// 캠핑장 타입 매핑
const campTypes = ['고급', '일반', '자갈', '데크'];
const campTypesShort = ['고급', '일반', '자갈', '데크']; // 모바일에서도 전체 이름 사용

// 월 변경
function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth > 12) {
        currentMonth = 1;
        currentYear++;
    } else if (currentMonth < 1) {
        currentMonth = 12;
        currentYear--;
    }
    
    updateTitle();
    generateCalendar();
}

// 타이틀 업데이트
function updateTitle() {
    document.getElementById('calendar-title').textContent = 
        `군포 캠핑장 예약 현황 달력 (${currentYear}년 ${currentMonth}월)`;
    document.getElementById('current-month').textContent = 
        `${currentYear}년 ${currentMonth}월`;
}

// 달력 생성
function generateCalendar() {
    const calendarBody = document.getElementById('calendar-body');
    
    // 해당 월의 첫 날과 마지막 날
    const firstDay = new Date(currentYear, currentMonth - 1, 1).getDay();
    const lastDate = new Date(currentYear, currentMonth, 0).getDate();
    
    let html = '';
    let date = 1;
    
    // 달력 행 생성 (6주)
    for (let week = 0; week < 6; week++) {
        html += '<tr>';
        
        // 각 요일
        for (let day = 0; day < 7; day++) {
            if (week === 0 && day < firstDay) {
                // 이전 달 날짜 (빈 셀)
                html += '<td></td>';
            } else if (date > lastDate) {
                // 다음 달 날짜 (빈 셀)
                html += '<td></td>';
            } else {
                // 현재 달 날짜
                const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(date).padStart(2, '0')}`;
                html += `
                    <td>
                        <div class="date-cell">${String(date).padStart(2, '0')}</div>
                        <div class="camp-info" id="info-${dateStr}">
                            <div class="loading">대기중</div>
                        </div>
                    </td>
                `;
                date++;
            }
        }
        html += '</tr>';
        
        // 모든 날짜를 표시했으면 종료
        if (date > lastDate) break;
    }
    
    calendarBody.innerHTML = html;
}

// 화면 크기에 따른 표시 형식 결정
function getDisplayFormat() {
    const isMobile = window.innerWidth <= 480;
    const isTablet = window.innerWidth > 480 && window.innerWidth <= 768;
    
    if (isMobile) {
        return 'mobile';
    } else if (isTablet) {
        return 'tablet';
    } else {
        return 'desktop';
    }
}

// 특정 날짜의 데이터 로드
async function loadDateData(date) {
    const infoElement = document.getElementById(`info-${date}`);
    if (!infoElement) return;
    
    infoElement.innerHTML = '<div class="loading">로딩중</div>';
    
    try {
        const startTime = performance.now();
        const response = await fetch(`/api/camp-data/${date}`);
        const result = await response.json();
        const endTime = performance.now();
        
        if (result.success) {
            let html = '';
            const displayFormat = getDisplayFormat();
            
            // 타입 순서와 표시 형식
            const typeOrder = ['고급', '일반', '자갈', '데크'];
            let typeDisplay;
            
            if (displayFormat === 'mobile') {
                typeDisplay = ['고급', '일반', '자갈', '데크']; // 모바일에서도 전체 이름
            } else {
                typeDisplay = ['고급', '일반', '자갈', '데크'];
            }
            
            typeOrder.forEach((typeName, index) => {
                if (result.data[typeName] !== undefined) {
                    const count = result.data[typeName];
                    let className = 'unavailable';
                    let displayText = count;
                    
                    if (count === -1) {
                        className = 'error';
                        displayText = 'X';
                    } else if (count > 0) {
                        className = 'available';
                    }
                    
                    // 표시 형식에 따라 다르게 표시
                    if (displayFormat === 'mobile') {
                        html += `<div class="${className}">${typeDisplay[index]} ${displayText}</div>`;
                    } else {
                        html += `<div class="${className}">${typeDisplay[index]}: ${displayText}</div>`;
                    }
                }
            });
            
            infoElement.innerHTML = html;
            console.log(`Date ${date} loaded in ${(endTime - startTime).toFixed(0)}ms`);
        } else {
            infoElement.innerHTML = '<div class="error">실패</div>';
        }
    } catch (error) {
        console.error('Error loading date data:', error);
        infoElement.innerHTML = '<div class="error">오류</div>';
    }
}

// 병렬로 날짜별 로드 (더 빠름)
async function loadAllData() {
    const lastDate = new Date(currentYear, currentMonth, 0).getDate();
    const notice = document.getElementById('status-notice');
    
    notice.textContent = '모든 날짜를 병렬로 로딩 중...';
    
    // 모든 날짜에 대해 동시에 요청 시작
    const promises = [];
    for (let date = 1; date <= lastDate; date++) {
        const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(date).padStart(2, '0')}`;
        promises.push(loadDateData(dateStr));
    }
    
    // 배치 단위로 처리 (5개씩)
    const batchSize = 5;
    const startTime = performance.now();
    
    for (let i = 0; i < promises.length; i += batchSize) {
        const batch = promises.slice(i, i + batchSize);
        await Promise.all(batch);
        
        const completed = Math.min(i + batchSize, lastDate);
        notice.textContent = `병렬 로딩 중... (${completed}/${lastDate})`;
        
        // 배치 간 짧은 지연 (서버 부담 줄이기)
        if (i + batchSize < promises.length) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
    }
    
    const endTime = performance.now();
    const totalTime = ((endTime - startTime) / 1000).toFixed(1);
    
    notice.textContent = `병렬 로딩 완료! (총 ${totalTime}초)`;
    setTimeout(() => {
        notice.textContent = 'Flask 서버를 통해 실제 데이터를 가져오고 있습니다.';
    }, 3000);
}

// 월 전체 데이터 한 번에 로드 (가장 빠름)
async function loadMonthData() {
    const firstDate = `${currentYear}-${String(currentMonth).padStart(2, '0')}-01`;
    const lastDate = new Date(currentYear, currentMonth, 0).getDate();
    const endDate = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(lastDate).padStart(2, '0')}`;
    
    const notice = document.getElementById('status-notice');
    const progressContainer = document.querySelector('.progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    // 모든 날짜를 로딩중으로 표시
    for (let date = 1; date <= lastDate; date++) {
        const dateStr = `${currentYear}-${String(currentMonth).padStart(2, '0')}-${String(date).padStart(2, '0')}`;
        const infoElement = document.getElementById(`info-${dateStr}`);
        if (infoElement) {
            infoElement.innerHTML = '<div class="loading">로딩중</div>';
        }
    }
    
    progressContainer.style.display = 'block';
    progressFill.style.width = '20%';
    notice.textContent = '월 전체 데이터를 한 번에 불러오는 중...';
    
    const startTime = performance.now();
    
    try {
        const response = await fetch(`/api/camp-data-range?start_date=${firstDate}&end_date=${endDate}`);
        const result = await response.json();
        
        progressFill.style.width = '80%';
        
        if (result.success) {
            // 결과를 달력에 표시
            Object.entries(result.data).forEach(([dateStr, campData]) => {
                const infoElement = document.getElementById(`info-${dateStr}`);
                if (infoElement) {
                    let html = '';
                    const displayFormat = getDisplayFormat();
                    
                    // 타입 순서와 표시 형식
                    const typeOrder = ['고급', '일반', '자갈', '데크'];
                    const typeDisplay = ['고급', '일반', '자갈', '데크'];
                    
                    typeOrder.forEach((typeName, index) => {
                        if (campData[typeName] !== undefined) {
                            const count = campData[typeName];
                            let className = 'unavailable';
                            let displayText = count;
                            
                            if (count === -1) {
                                className = 'error';
                                displayText = 'X';
                            } else if (count > 0) {
                                className = 'available';
                            }
                            
                            if (displayFormat === 'mobile') {
                                html += `<div class="${className}">${typeDisplay[index]} ${displayText}</div>`;
                            } else {
                                html += `<div class="${className}">${typeDisplay[index]}: ${displayText}</div>`;
                            }
                        }
                    });
                    
                    infoElement.innerHTML = html;
                }
            });
            
            const endTime = performance.now();
            const clientTime = ((endTime - startTime) / 1000).toFixed(1);
            
            progressFill.style.width = '100%';
            progressText.textContent = '완료!';
            notice.textContent = `월 전체 로딩 완료! (${clientTime}초)`;
        } else {
            notice.textContent = `오류: ${result.error}`;
            notice.classList.add('error');
        }
    } catch (error) {
        console.error('Error loading month data:', error);
        notice.textContent = '네트워크 오류가 발생했습니다.';
        notice.classList.add('error');
    }
    
    // 3초 후 프로그레스바 숨김
    setTimeout(() => {
        progressContainer.style.display = 'none';
        notice.textContent = 'Flask 서버를 통해 실제 데이터를 가져오고 있습니다.';
        notice.classList.remove('error');
    }, 3000);
}

// 화면 크기 변경 시 다시 로드
window.addEventListener('resize', function() {
    // 화면 크기가 변경되면 잠시 후 다시 로드
    clearTimeout(window.resizeTimeout);
    window.resizeTimeout = setTimeout(() => {
        const elements = document.querySelectorAll('.camp-info');
        elements.forEach(element => {
            if (element.innerHTML && !element.innerHTML.includes('로딩중') && !element.innerHTML.includes('대기중')) {
                // 현재 데이터를 다시 포맷팅 (새로운 화면 크기에 맞게)
                loadDateData(element.id.replace('info-', ''));
            }
        });
    }, 500);
});

// 페이지 로드 시 달력 생성
document.addEventListener('DOMContentLoaded', function() {
    updateTitle();
    generateCalendar();
});