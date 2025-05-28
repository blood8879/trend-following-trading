# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail
# 또는
./check_trades.sh d

# 손익 분석
./check_trades.sh profit
# 또는  
./check_trades.sh p

# CSV 내보내기
./check_trades.sh export
# 또는
./check_trades.sh e
```

### 출력 예시
```
🤖 선물 자동매매 로그 체크
==========================

📊 최근 활동 (로그 파일):
-----------------------
2025-05-28 16:22:00,724 - INFO - 선물 매매 신호 확인 중...
2025-05-28 16:22:00,913 - INFO - 포지션 없음

💰 현재 BTC 가격:
---------------
$108,860.00

📈 매매 내역 요약:
----------------
총 거래: 54회
매수: 40회
매도: 14회
최근 거래: 2025-05-28 05:10:42
```

---

## 📊 방법 3: 로그 파일 직접 확인

### 실시간 로그 모니터링
```bash
# 실시간으로 로그 확인 (Ctrl+C로 종료)
tail -f futures_trading.log

# 최근 20줄만 확인
tail -20 futures_trading.log

# 매매 관련 로그만 필터링
grep -E "(매수|매도|신호|주문)" futures_trading.log

# 오늘 날짜 로그만 확인
grep "$(date +%Y-%m-%d)" futures_trading.log
```

### 주요 로그 패턴
- `매수 신호 발생`: 진입 신호 감지
- `매수 주문`: 실제 매수 실행
- `매도 신호`: 익절/손절 신호
- `테스트 모드`: 가상 거래 실행
- `포지션 없음`: 현재 포지션 상태

---

## 🗃️ 방법 4: 데이터베이스 직접 쿼리

### 기본 쿼리들
```bash
# 최근 10개 거래 내역
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    side as 방향,
    ROUND(quantity,6) as 수량,
    ROUND(price,2) as 가격,
    trade_type as 타입
FROM trades 
ORDER BY timestamp DESC 
LIMIT 10;
"

# 총 손익 계산
sqlite3 trading_history.db "
SELECT 
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 총손익
FROM trades;
"

# 승률 계산
sqlite3 trading_history.db "
SELECT 
    COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as 익절,
    COUNT(CASE WHEN side='SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as 손절,
    ROUND(
        COUNT(CASE WHEN side='SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) * 100.0 / 
        COUNT(CASE WHEN side='SELL' THEN 1 END), 2
    ) as 승률
FROM trades;
"

# 월별 거래 요약
sqlite3 trading_history.db "
SELECT 
    strftime('%Y-%m', timestamp) as 월,
    COUNT(*) as 거래수,
    ROUND(SUM(CASE WHEN side='SELL' THEN total_value ELSE -total_value END), 2) as 손익
FROM trades 
GROUP BY strftime('%Y-%m', timestamp)
ORDER BY 월 DESC;
"
```

### 현재 포지션 확인
```bash
sqlite3 trading_history.db "
SELECT 
    datetime(timestamp,'localtime') as 시간,
    CASE 
        WHEN position = 1 THEN '롱'
        WHEN position = -1 THEN '숏'
        ELSE '없음'
    END as 포지션,
    ROUND(position_size,6) as 크기,
    ROUND(current_price,2) as 현재가,
    ROUND(unrealized_pnl,2) as 미실현손익
FROM positions 
ORDER BY timestamp DESC 
LIMIT 1;
"
```

---

## 📄 방법 5: CSV/Excel로 데이터 분석

### CSV 파일 생성
```bash
# Python 스크립트로 생성
source venv/bin/activate
python3 view_trades.py export

# 또는 bash 스크립트로 생성
./check_trades.sh export

# 생성된 파일 확인
ls -la trades_*.csv
```

### CSV 파일 내용
- timestamp: 거래 시간
- symbol: 거래 심볼 (BTCUSDT)
- side: 매수/매도 (BUY/SELL)
- quantity: 거래 수량
- price: 거래 가격
- total_value: 총 거래 금액
- trade_type: 거래 유형 (ENTRY/EXIT/STOP_LOSS)
- test_mode: 테스트 모드 여부

---

## ☁️ 방법 6: AWS에서 24시간 실행하기

### 1. AWS EC2 인스턴스 생성
```bash
# AWS 콘솔에서 EC2 인스턴스 생성
# - Ubuntu 20.04 LTS 추천
# - t2.micro (무료 티어) 또는 t3.small 선택
# - 보안 그룹에서 SSH (포트 22) 허용
```

### 2. 서버 접속 및 환경 설정
```bash
# SSH로 서버 접속
ssh -i your-key.pem ubuntu@your-ec2-ip

# 패키지 업데이트
sudo apt update && sudo apt upgrade -y

# Python, pip, git 설치
sudo apt install python3 python3-pip python3-venv git -y
```

### 3. 코드 업로드
```bash
# 방법 1: git clone (코드가 GitHub에 있는 경우)
git clone your-repository-url
cd your-project-folder

# 방법 2: scp로 파일 업로드 (로컬에서 실행)
scp -i your-key.pem -r /local/project/folder ubuntu@your-ec2-ip:~/
```

### 4. Python 환경 설정
```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install binance pandas python-binance
```

### 5. 24시간 실행 설정
```bash
# screen 설치 (터미널 종료되어도 프로그램 계속 실행)
sudo apt install screen -y

# screen 세션 시작
screen -S trading

# 프로그램 실행
source venv/bin/activate
python auto_trader_futures.py

# Ctrl+A, D로 screen에서 나오기 (프로그램은 계속 실행됨)
```

### 6. 원격에서 결과 확인 방법
```bash
# screen 세션 다시 접속
screen -r trading

# 로그 파일 실시간 확인
tail -f futures_trading.log

# 데이터베이스 결과 확인 (monitor.py가 있다면)
python monitor.py

# 또는 view_trades.py 사용
source venv/bin/activate
python3 view_trades.py
```

### 7. AWS에서 프로그램 상태 관리
```bash
# 실행 중인 screen 세션 확인
screen -list

# 프로그램 중지하려면
screen -r trading
# 그 후 Ctrl+C

# 프로그램 재시작
screen -S trading
source venv/bin/activate
python auto_trader_futures.py
```

### 8. AWS 비용 절약 팁
```bash
# EC2 인스턴스 중지 (요금 절약)
# - AWS 콘솔에서 인스턴스 중지
# - 재시작 시 IP가 바뀔 수 있음 (Elastic IP 사용 권장)

# 자동 시작 설정 (systemd 서비스 등록)
sudo nano /etc/systemd/system/trading.service

# 서비스 파일 내용:
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trend-following-trading
ExecStart=/home/ubuntu/trend-following-trading/venv/bin/python auto_trader_futures.py
Restart=always

[Install]
WantedBy=multi-user.target

# 서비스 활성화
sudo systemctl enable trading.service
sudo systemctl start trading.service
```

### 9. 원격 모니터링 설정
```bash
# SSH 터널링으로 로컬에서 원격 DB 접근
ssh -i your-key.pem -L 8080:localhost:8080 ubuntu@your-ec2-ip

# 원격에서 웹 모니터링 서버 실행 (선택사항)
# Simple HTTP server로 결과 확인
python3 -m http.server 8080
```

---

## 🔧 유용한 명령어 조합

### 1. 빠른 상태 체크
```bash
# 한 번에 모든 정보 확인
source venv/bin/activate && python3 view_trades.py
```

### 2. 실시간 모니터링
```bash
# 터미널 2개로 분할하여 사용
# 터미널 1: 자동매매 실행
python3 auto_trader_futures.py

# 터미널 2: 실시간 로그 모니터링
tail -f futures_trading.log | grep -E "(신호|주문|ERROR)"
```

### 3. 성과 분석
```bash
# 상세 손익 분석
source venv/bin/activate && python3 view_trades.py profit

# CSV로 내보내서 Excel 분석
source venv/bin/activate && python3 view_trades.py export
```

---

## 🚨 문제 해결

### 가상환경 활성화 안됨
```bash
# 가상환경 재생성
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 데이터베이스 파일 없음
```bash
# 자동매매 프로그램을 한번 실행하면 자동 생성됨
python3 auto_trader_futures.py
```

### 권한 오류
```bash
# 스크립트 실행 권한 부여
chmod +x check_trades.sh
chmod +x view_trades.py
```

### AWS 연결 문제
```bash
# SSH 키 권한 설정
chmod 400 your-key.pem

# 보안 그룹 확인 (포트 22 열려있는지)
# EC2 콘솔 > 보안 그룹 > 인바운드 규칙

# 인스턴스 상태 확인
# EC2 콘솔에서 인스턴스가 running 상태인지 확인
```

---

## 📈 주요 지표 해석

### 거래 타입
- **ENTRY**: 신규 진입
- **EXIT**: 익절 매도
- **STOP_LOSS**: 손절 매도
- **ENTRY_LONG**: 롱 포지션 진입
- **ENTRY_SHORT**: 숏 포지션 진입

### 성과 지표
- **승률**: (익절 횟수 / 전체 매도 횟수) × 100
- **평균 수익률**: 개별 거래 수익률의 평균
- **총 손익**: 모든 거래의 누적 손익
- **미실현 손익**: 현재 포지션의 평가 손익

---

## ⚡ 빠른 참조

| 목적 | 로컬 명령어 | AWS 명령어 |
|------|------------|------------|
| 전체 요약 | `source venv/bin/activate && python3 view_trades.py` | `screen -r trading` 후 동일 |
| 빠른 체크 | `./check_trades.sh` | `ssh -i key.pem user@ip './check_trades.sh'` |
| 실시간 로그 | `tail -f futures_trading.log` | `ssh -i key.pem user@ip 'tail -f futures_trading.log'` |
| 손익 분석 | `./check_trades.sh profit` | `ssh -i key.pem user@ip './check_trades.sh profit'` |
| CSV 내보내기 | `./check_trades.sh export` | `scp -i key.pem user@ip:~/trades_*.csv ./` |
| 프로그램 상태 | - | `ssh -i key.pem user@ip 'screen -list'` |

---

## 📞 도움말

문제가 발생하면:
1. **로컬 테스트**: 매일 `./check_trades.sh`로 빠른 체크
- **AWS 운영**: 주간/월간 분석은 `scp`로 CSV 파일을 다운받아 Excel에서 분석
- **비용 관리**: 테스트 완료 후 EC2 인스턴스는 중지하여 비용 절약

# 📈 선물 자동매매 결과 확인 가이드

## 🚀 시작하기 전에

### 가상환경 활성화
```bash
# 프로젝트 디렉토리로 이동
cd ~/Documents/project/trend-following-trading

# 가상환경 활성화
source venv/bin/activate

# 활성화 확인 (프롬프트에 (venv) 표시됨)
```

---

## 📋 방법 1: Python 스크립트 사용 (`view_trades.py`)

### 기본 사용법
```bash
# 가상환경 활성화 후
python3 view_trades.py
```

### 상세 옵션
```bash
# 최근 N개 매매 내역만 보기
python3 view_trades.py trades 20    # 최근 20개
python3 view_trades.py trades 5     # 최근 5개

# 손익 분석만 보기
python3 view_trades.py profit

# 현재 포지션 상태만 보기
python3 view_trades.py status

# CSV 파일로 내보내기
python3 view_trades.py export
```

### 출력 예시
```
📊 최근 10개 매매 내역
====================================================================================================
                 시간      심볼   방향       수량       가격     총액      거래타입  모드
2025-05-28 05:10:42 BTCUSDT SELL 0.006275 51316.24 322.01      EXIT 테스트
2025-05-28 03:10:42 BTCUSDT  BUY 0.006275 49629.57 311.42     ENTRY 테스트

💰 최근 10개 완성된 거래의 손익
================================================================================
🟢 05-27 18:10 → 05-27 20:10
   매수: $49,629.57 | 매도: $51,316.24
   수익률: +3.40% | 손익: $+10.58

📊 거래 요약:
   총 손익: $+38.14
   평균 수익률: +1.45%
   승률: 60.0%

📍 현재 포지션 상태
============================================================
업데이트 시간: 2025-05-28 03:10:42
포지션 타입: 롱
포지션 크기: 0.005000
현재 가격: $51,000.0
미실현 손익: $+250.00
```

---

## ⚡ 방법 2: Bash 스크립트 사용 (`check_trades.sh`)

### 실행 권한 부여 (최초 1회만)
```bash
chmod +x check_trades.sh
```

### 사용법
```bash
# 빠른 요약 (로그 + 가격 + 매매 요약)
./check_trades.sh

# 상세 매매 내역
./check_trades.sh detail