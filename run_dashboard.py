#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import time
import json
import logging
from dashboard import app, socketio
from auto_trader import BinanceAutoTrader

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_auto_trader():
    """자동매매 시스템 실행"""
    try:
        # 설정 파일에서 API 키 읽기
        with open('config.json', 'r') as f:
            config = json.load(f)
            api_key = config.get('api_key')
            api_secret = config.get('api_secret')
            test_mode = config.get('test_mode', True)
            max_trade_amount = config.get('max_trade_amount')
            symbol = config.get('symbol', 'BTCUSDT')
            timeframe = config.get('timeframe', '4h')
            
        if not api_key or not api_secret:
            raise ValueError("API 키가 설정되지 않았습니다.")
            
        # 자동 매매 시스템 초기화
        trader = BinanceAutoTrader(
            api_key=api_key,
            api_secret=api_secret,
            symbol=symbol,
            timeframe=timeframe,
            max_trade_amount=max_trade_amount,
            test_mode=test_mode
        )
        
        logger.info("자동매매 시스템이 백그라운드에서 시작됩니다.")
        
        # 자동 매매 시스템 실행
        trader.run(check_interval=300)  # 5분마다 매매 신호 확인
        
    except FileNotFoundError:
        logger.error("config.json 파일을 찾을 수 없습니다. API 키 설정이 필요합니다.")
    except json.JSONDecodeError:
        logger.error("config.json 파일 형식이 잘못되었습니다.")
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.error(f"자동매매 시스템 실행 중 오류 발생: {e}")

def main():
    """메인 함수"""
    print("=" * 60)
    print("트렌드 팔로잉 자동매매 대시보드")
    print("=" * 60)
    print()
    print("🚀 시스템 시작 중...")
    print()
    
    # 자동매매 시스템을 별도 스레드에서 실행
    trader_thread = threading.Thread(target=run_auto_trader)
    trader_thread.daemon = True
    trader_thread.start()
    
    # 잠시 대기 (자동매매 시스템 초기화 시간)
    time.sleep(3)
    
    print("📊 웹 대시보드 시작 중...")
    print()
    print("🌐 대시보드 URL: http://localhost:8080")
    print("📱 모바일에서도 접속 가능: http://[컴퓨터IP]:8080")
    print()
    print("⚠️  주의사항:")
    print("   - 테스트 모드에서는 실제 주문이 실행되지 않습니다")
    print("   - 실제 거래 전에 충분한 테스트를 진행하세요")
    print("   - Ctrl+C로 시스템을 종료할 수 있습니다")
    print()
    print("=" * 60)
    
    try:
        # Flask 대시보드 실행
        socketio.run(app, debug=False, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n\n시스템이 사용자에 의해 종료되었습니다.")
    except Exception as e:
        logger.error(f"대시보드 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    main() 