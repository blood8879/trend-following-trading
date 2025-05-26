#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime, timedelta
import random
from database import TradingDatabase

def create_dummy_data():
    """테스트용 더미 데이터 생성"""
    db = TradingDatabase()
    
    print("더미 데이터 생성 중...")
    
    # 더미 매매 내역 생성
    base_price = 50000  # BTC 기준 가격
    current_time = datetime.now()
    
    for i in range(20):
        # 매수 주문
        buy_time = current_time - timedelta(hours=i*4)
        buy_price = base_price + random.uniform(-5000, 5000)
        quantity = random.uniform(0.001, 0.01)
        
        buy_trade = {
            'timestamp': buy_time,
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': quantity,
            'price': buy_price,
            'total_value': quantity * buy_price,
            'order_id': f'test_buy_{i}',
            'trade_type': 'ENTRY',
            'exit_stage': 0,
            'stop_loss_price': buy_price * 0.95,
            'secondary_stop_loss_price': buy_price * 0.90,
            'test_mode': True,
            'notes': '테스트 매수'
        }
        
        db.add_trade(buy_trade)
        
        # 매도 주문 (일부만)
        if i % 3 == 0:  # 3번에 1번씩 매도
            sell_time = buy_time + timedelta(hours=2)
            sell_price = buy_price + random.uniform(-1000, 3000)
            
            trade_type = 'EXIT' if sell_price > buy_price else 'STOP_LOSS'
            exit_stage = random.choice([1, 2, 3]) if trade_type == 'EXIT' else 0
            
            sell_trade = {
                'timestamp': sell_time,
                'symbol': 'BTCUSDT',
                'side': 'SELL',
                'quantity': quantity,
                'price': sell_price,
                'total_value': quantity * sell_price,
                'order_id': f'test_sell_{i}',
                'trade_type': trade_type,
                'exit_stage': exit_stage,
                'test_mode': True,
                'notes': f'테스트 매도 - {trade_type}'
            }
            
            db.add_trade(sell_trade)
    
    # 더미 포지션 데이터
    position_data = {
        'timestamp': current_time,
        'symbol': 'BTCUSDT',
        'position': 1,  # 롱 포지션
        'entry_price': base_price,
        'position_size': 0.005,
        'stop_loss': base_price * 0.95,
        'secondary_stop_loss': base_price * 0.90,
        'unrealized_pnl': 250.0,
        'current_price': base_price + 1000
    }
    
    db.update_position(position_data)
    
    # 더미 계정 상태
    account_data = {
        'timestamp': current_time,
        'total_balance': 10000.0,
        'available_balance': 8000.0,
        'base_asset_balance': 0.005,
        'quote_asset_balance': 8000.0,
        'total_pnl': 1500.0,
        'win_rate': 65.5,
        'total_trades': 20
    }
    
    db.update_account_status(account_data)
    
    # 더미 시장 데이터 (차트용)
    for i in range(100):
        candle_time = current_time - timedelta(hours=i*4)
        open_price = base_price + random.uniform(-2000, 2000)
        close_price = open_price + random.uniform(-1000, 1000)
        high_price = max(open_price, close_price) + random.uniform(0, 500)
        low_price = min(open_price, close_price) - random.uniform(0, 500)
        
        market_data = {
            'timestamp': candle_time,
            'symbol': 'BTCUSDT',
            'timeframe': '4h',
            'open_price': open_price,
            'high_price': high_price,
            'low_price': low_price,
            'close_price': close_price,
            'volume': random.uniform(100, 1000),
            'ema10': close_price + random.uniform(-200, 200),
            'ema20': close_price + random.uniform(-400, 400),
            'ema50': close_price + random.uniform(-800, 800)
        }
        
        db.add_market_data(market_data)
    
    print("더미 데이터 생성 완료!")
    print("이제 대시보드를 실행할 수 있습니다.")
    print("python dashboard.py")

if __name__ == "__main__":
    create_dummy_data() 