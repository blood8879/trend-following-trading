#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
from binance.client import Client
import logging
import re
import requests
import sqlite3

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradeMonitor:
    """
    자동매매 시스템 모니터링 도구
    """
    
    def __init__(self, api_key=None, api_secret=None, symbol='BTCUSDT', webhook_url=None):
        """
        초기화
        
        Args:
            api_key (str): Binance API 키
            api_secret (str): Binance API 시크릿
            symbol (str): 모니터링할 심볼
            webhook_url (str): Discord/Slack 웹훅 URL
        """
        self.symbol = symbol
        
        # API 키가 제공되지 않은 경우 config.json에서 로드
        if api_key is None or api_secret is None:
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                    api_key = config.get('api_key')
                    api_secret = config.get('api_secret')
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"config.json 파일 로드 오류: {e}")
                raise ValueError("API 키 설정이 필요합니다.")
        
        # Binance 클라이언트 초기화
        self.client = Client(api_key, api_secret)
        
        # 기본 설정
        self.quote_asset = self.symbol[-4:] if self.symbol.endswith('USDT') else self.symbol[-3:]
        self.base_asset = self.symbol.replace(self.quote_asset, '')
        
        # 로그 파일 경로
        self.log_file = 'trading.log'
        
        self.webhook_url = webhook_url
        self.last_check = datetime.now()
    
    def get_account_info(self):
        """
        계정 정보 조회
        
        Returns:
            dict: 계정 정보
        """
        try:
            account_info = self.client.get_account()
            
            # 필요한 정보만 추출
            base_balance = 0
            quote_balance = 0
            
            for balance in account_info['balances']:
                if balance['asset'] == self.base_asset:
                    base_balance = float(balance['free']) + float(balance['locked'])
                elif balance['asset'] == self.quote_asset:
                    quote_balance = float(balance['free']) + float(balance['locked'])
            
            # 현재 가격 조회
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            
            # 총 자산 가치 계산 (USDT)
            total_value = quote_balance + (base_balance * current_price)
            
            return {
                'base_balance': base_balance,
                'quote_balance': quote_balance,
                'current_price': current_price,
                'total_value': total_value
            }
            
        except Exception as e:
            logger.error(f"계정 정보 조회 오류: {e}")
            return None
    
    def get_recent_trades(self, limit=20):
        """
        최근 거래 내역 조회
        
        Args:
            limit (int): 조회할 거래 수
            
        Returns:
            pandas.DataFrame: 거래 내역
        """
        try:
            # 거래 내역 조회
            trades = self.client.get_my_trades(symbol=self.symbol, limit=limit)
            
            # DataFrame으로 변환
            if not trades:
                return pd.DataFrame()
                
            df = pd.DataFrame(trades)
            
            # 타임스탬프 변환
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            
            # 수량과 가격을 숫자로 변환
            df['price'] = df['price'].astype(float)
            df['qty'] = df['qty'].astype(float)
            df['quoteQty'] = df['quoteQty'].astype(float)
            
            # 매수/매도 구분
            df['type'] = df['isBuyer'].apply(lambda x: '매수' if x else '매도')
            
            # 필요한 컬럼만 선택
            result = df[['time', 'type', 'price', 'qty', 'quoteQty']]
            
            return result
            
        except Exception as e:
            logger.error(f"거래 내역 조회 오류: {e}")
            return pd.DataFrame()
    
    def parse_trading_log(self):
        """
        거래 로그 파일 분석
        
        Returns:
            dict: 로그 분석 결과
        """
        if not os.path.exists(self.log_file):
            logger.warning(f"로그 파일이 존재하지 않습니다: {self.log_file}")
            return None
            
        try:
            # 로그 파일 읽기
            with open(self.log_file, 'r') as f:
                logs = f.readlines()
            
            # 로그 분석 결과
            signals = []
            orders = []
            errors = []
            
            # 매매 신호, 주문, 오류 추출
            for log in logs:
                # 타임스탬프 추출
                timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', log)
                if not timestamp_match:
                    continue
                    
                timestamp = timestamp_match.group(1)
                
                # 매매 신호
                if "매수 신호 발생" in log or "매도 신호 발생" in log:
                    signals.append({
                        'timestamp': timestamp,
                        'content': log.strip()
                    })
                
                # 주문
                elif "시장가 주문" in log:
                    orders.append({
                        'timestamp': timestamp,
                        'content': log.strip()
                    })
                
                # 오류
                elif "오류" in log or "ERROR" in log:
                    errors.append({
                        'timestamp': timestamp,
                        'content': log.strip()
                    })
            
            return {
                'signals': signals,
                'orders': orders,
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"로그 분석 오류: {e}")
            return None
    
    def plot_balance_history(self):
        """
        계정 잔고 변화 그래프 출력
        """
        # 거래 내역 가져오기
        trades_df = self.get_recent_trades(limit=100)
        
        if trades_df.empty:
            logger.warning("거래 내역이 없습니다.")
            return
            
        # 현재 계정 정보
        account_info = self.get_account_info()
        
        if not account_info:
            logger.warning("계정 정보를 가져올 수 없습니다.")
            return
            
        # 그래프 설정
        plt.figure(figsize=(12, 8))
        
        # 가격 그래프
        plt.subplot(2, 1, 1)
        plt.plot(trades_df['time'], trades_df['price'])
        plt.title(f'{self.symbol} 거래 가격')
        plt.xlabel('시간')
        plt.ylabel('가격 (USDT)')
        plt.grid(True)
        
        # 수량 그래프
        plt.subplot(2, 1, 2)
        
        # 매수와 매도 구분
        buy_trades = trades_df[trades_df['type'] == '매수']
        sell_trades = trades_df[trades_df['type'] == '매도']
        
        # 매수/매도 막대 그래프
        if not buy_trades.empty:
            plt.bar(buy_trades['time'], buy_trades['qty'], color='green', width=0.01, label='매수')
        if not sell_trades.empty:
            plt.bar(sell_trades['time'], -sell_trades['qty'], color='red', width=0.01, label='매도')
            
        plt.title('거래 수량')
        plt.xlabel('시간')
        plt.ylabel(f'수량 ({self.base_asset})')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.show()
        
        # 현재 상태 출력
        print(f"\n현재 {self.base_asset} 잔고: {account_info['base_balance']:.8f}")
        print(f"현재 {self.quote_asset} 잔고: {account_info['quote_balance']:.2f}")
        print(f"현재 {self.symbol} 가격: {account_info['current_price']:.2f}")
        print(f"총 자산 가치 (USDT): {account_info['total_value']:.2f}")
    
    def show_logs_summary(self):
        """
        로그 요약 정보 출력
        """
        log_data = self.parse_trading_log()
        
        if not log_data:
            logger.warning("로그 데이터가 없습니다.")
            return
            
        print("\n===== 자동매매 시스템 로그 요약 =====")
        
        # 매매 신호
        print(f"\n최근 매매 신호 (총 {len(log_data['signals'])}개):")
        for i, signal in enumerate(log_data['signals'][-5:], 1):
            print(f"{i}. {signal['timestamp']} - {signal['content'].split(' - ')[-1]}")
        
        # 주문
        print(f"\n최근 주문 (총 {len(log_data['orders'])}개):")
        for i, order in enumerate(log_data['orders'][-5:], 1):
            print(f"{i}. {order['timestamp']} - {order['content'].split(' - ')[-1]}")
        
        # 오류
        print(f"\n최근 오류 (총 {len(log_data['errors'])}개):")
        for i, error in enumerate(log_data['errors'][-5:], 1):
            print(f"{i}. {error['timestamp']} - {error['content'].split(' - ')[-1]}")
    
    def run_dashboard(self, refresh_interval=60):
        """
        실시간 대시보드 실행
        
        Args:
            refresh_interval (int): 새로고침 주기 (초)
        """
        try:
            print(f"\n===== {self.symbol} 자동매매 모니터링 대시보드 =====")
            print(f"새로고침 주기: {refresh_interval}초")
            print("종료하려면 Ctrl+C를 누르세요.")
            
            while True:
                # 화면 지우기
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # 현재 시간
                print(f"\n===== {self.symbol} 자동매매 모니터링 대시보드 =====")
                print(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 계정 정보
                account_info = self.get_account_info()
                if account_info:
                    print("\n----- 계정 정보 -----")
                    print(f"{self.base_asset} 잔고: {account_info['base_balance']:.8f}")
                    print(f"{self.quote_asset} 잔고: {account_info['quote_balance']:.2f}")
                    print(f"현재 {self.symbol} 가격: {account_info['current_price']:.2f}")
                    print(f"총 자산 가치 (USDT): {account_info['total_value']:.2f}")
                
                # 최근 거래
                trades = self.get_recent_trades(limit=5)
                if not trades.empty:
                    print("\n----- 최근 거래 -----")
                    for i, row in trades.iterrows():
                        print(f"{row['time'].strftime('%Y-%m-%d %H:%M:%S')} - {row['type']} {row['qty']:.8f} {self.base_asset} @ {row['price']:.2f} {self.quote_asset}")
                
                # 로그 요약
                log_data = self.parse_trading_log()
                if log_data:
                    print("\n----- 최근 활동 -----")
                    
                    # 매매 신호
                    if log_data['signals']:
                        print(f"\n최근 매매 신호:")
                        for signal in log_data['signals'][-3:]:
                            print(f"{signal['timestamp']} - {signal['content'].split(' - ')[-1]}")
                    
                    # 주문
                    if log_data['orders']:
                        print(f"\n최근 주문:")
                        for order in log_data['orders'][-3:]:
                            print(f"{order['timestamp']} - {order['content'].split(' - ')[-1]}")
                    
                    # 오류
                    if log_data['errors']:
                        print(f"\n최근 오류:")
                        for error in log_data['errors'][-3:]:
                            print(f"{error['timestamp']} - {error['content'].split(' - ')[-1]}")
                
                # 대기
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\n모니터링 대시보드를 종료합니다.")
        except Exception as e:
            logger.error(f"대시보드 실행 중 오류: {e}")
    
    def check_system_health(self):
        """시스템 상태 확인"""
        try:
            # 데이터베이스 연결 확인
            conn = sqlite3.connect('trading.db')
            cursor = conn.cursor()
            
            # 최근 1시간 내 활동 확인
            one_hour_ago = datetime.now() - timedelta(hours=1)
            cursor.execute("""
                SELECT COUNT(*) FROM market_data 
                WHERE timestamp > ?
            """, (one_hour_ago,))
            
            recent_activity = cursor.fetchone()[0]
            conn.close()
            
            if recent_activity == 0:
                self.send_alert("⚠️ 경고: 1시간 동안 시장 데이터 업데이트가 없습니다!")
                return False
            
            return True
            
        except Exception as e:
            self.send_alert(f"🚨 시스템 오류: {str(e)}")
            return False
    
    def check_trading_activity(self):
        """거래 활동 확인"""
        try:
            conn = sqlite3.connect('trading.db')
            cursor = conn.cursor()
            
            # 최근 24시간 거래 내역
            yesterday = datetime.now() - timedelta(days=1)
            cursor.execute("""
                SELECT COUNT(*), SUM(total_value) FROM trades 
                WHERE timestamp > ? AND test_mode = 0
            """, (yesterday,))
            
            trade_count, total_volume = cursor.fetchone()
            total_volume = total_volume or 0
            
            # 현재 포지션 확인
            cursor.execute("""
                SELECT long_position, short_position, unrealized_pnl 
                FROM positions 
                ORDER BY timestamp DESC LIMIT 1
            """)
            
            position_data = cursor.fetchone()
            conn.close()
            
            if position_data:
                long_pos, short_pos, pnl = position_data
                
                message = f"""
📊 일일 거래 리포트
• 거래 횟수: {trade_count}회
• 거래량: {total_volume:.2f} USDT
• 롱 포지션: {long_pos:.4f}
• 숏 포지션: {short_pos:.4f}
• 미실현 손익: {pnl:.2f} USDT
                """
                
                self.send_alert(message)
            
        except Exception as e:
            self.send_alert(f"거래 활동 확인 오류: {str(e)}")
    
    def send_alert(self, message):
        """알림 전송 (Discord/Slack 웹훅)"""
        if not self.webhook_url:
            print(f"[{datetime.now()}] {message}")
            return
        
        try:
            payload = {
                "content": f"🤖 **트레이딩 봇 알림**\n{message}",
                "username": "Trading Bot"
            }
            
            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 204:
                print(f"알림 전송 성공: {message}")
            else:
                print(f"알림 전송 실패: {response.status_code}")
                
        except Exception as e:
            print(f"알림 전송 오류: {e}")
    
    def run_monitoring(self):
        """모니터링 실행"""
        print("트레이딩 모니터링 시작...")
        
        while True:
            try:
                # 시스템 상태 확인 (5분마다)
                if (datetime.now() - self.last_check).total_seconds() >= 300:
                    self.check_system_health()
                    self.last_check = datetime.now()
                
                # 일일 리포트 (매일 오전 9시)
                now = datetime.now()
                if now.hour == 9 and now.minute == 0:
                    self.check_trading_activity()
                    time.sleep(60)  # 1분 대기로 중복 실행 방지
                
                time.sleep(30)  # 30초마다 체크
                
            except KeyboardInterrupt:
                print("모니터링 중단됨")
                break
            except Exception as e:
                print(f"모니터링 오류: {e}")
                time.sleep(60)


if __name__ == "__main__":
    try:
        # 모니터 객체 생성
        webhook_url = None  # "https://discord.com/api/webhooks/YOUR_WEBHOOK_URL"
        monitor = TradeMonitor(symbol='BTCUSDT', webhook_url=webhook_url)
        
        # 명령줄 인터페이스
        while True:
            print("\n===== 자동매매 모니터링 도구 =====")
            print("1. 계정 정보 조회")
            print("2. 최근 거래 내역 조회")
            print("3. 거래 그래프 표시")
            print("4. 로그 요약 정보")
            print("5. 실시간 대시보드 실행")
            print("6. 시스템 상태 확인")
            print("7. 거래 활동 확인")
            print("8. 모니터링 실행")
            print("0. 종료")
            
            choice = input("\n선택: ")
            
            if choice == '1':
                account_info = monitor.get_account_info()
                if account_info:
                    print(f"\n{monitor.base_asset} 잔고: {account_info['base_balance']:.8f}")
                    print(f"{monitor.quote_asset} 잔고: {account_info['quote_balance']:.2f}")
                    print(f"현재 {monitor.symbol} 가격: {account_info['current_price']:.2f}")
                    print(f"총 자산 가치 (USDT): {account_info['total_value']:.2f}")
            
            elif choice == '2':
                trades = monitor.get_recent_trades()
                if not trades.empty:
                    print("\n최근 거래 내역:")
                    for i, row in trades.iterrows():
                        print(f"{row['time'].strftime('%Y-%m-%d %H:%M:%S')} - {row['type']} {row['qty']:.8f} @ {row['price']:.2f} {monitor.quote_asset}")
                else:
                    print("\n거래 내역이 없습니다.")
            
            elif choice == '3':
                monitor.plot_balance_history()
            
            elif choice == '4':
                monitor.show_logs_summary()
            
            elif choice == '5':
                refresh = input("새로고침 주기(초, 기본값 60): ")
                refresh_interval = int(refresh) if refresh.isdigit() else 60
                monitor.run_dashboard(refresh_interval=refresh_interval)
            
            elif choice == '6':
                if monitor.check_system_health():
                    print("\n시스템 상태: 정상")
                else:
                    print("\n시스템 상태: 비정상")
            
            elif choice == '7':
                monitor.check_trading_activity()
            
            elif choice == '8':
                monitor.run_monitoring()
            
            elif choice == '0':
                print("\n프로그램을 종료합니다.")
                break
            
            else:
                print("\n잘못된 선택입니다. 다시 시도하세요.")
                
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류 발생: {e}") 