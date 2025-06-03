#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
선물 거래 통계 조회 스크립트
롱/숏별 상세 통계를 확인할 수 있습니다.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys

def get_db_connection():
    """데이터베이스 연결"""
    return sqlite3.connect('trading_history.db')

def calculate_long_short_stats():
    """롱/숏별 상세 통계 계산"""
    conn = get_db_connection()
    
    # 롱 포지션 통계
    long_query = """
    SELECT 
        COUNT(CASE WHEN trade_type = 'ENTRY_LONG' THEN 1 END) as long_entries,
        COUNT(CASE WHEN trade_type = 'EXIT_LONG' THEN 1 END) as long_exits,
        SUM(CASE WHEN trade_type = 'ENTRY_LONG' THEN -total_value ELSE total_value END) as long_pnl
    FROM trades 
    WHERE trade_type IN ('ENTRY_LONG', 'EXIT_LONG')
    """
    
    # 숏 포지션 통계  
    short_query = """
    SELECT 
        COUNT(CASE WHEN trade_type = 'ENTRY_SHORT' THEN 1 END) as short_entries,
        COUNT(CASE WHEN trade_type = 'EXIT_SHORT' THEN 1 END) as short_exits,
        SUM(CASE WHEN trade_type = 'ENTRY_SHORT' THEN -total_value ELSE total_value END) as short_pnl
    FROM trades 
    WHERE trade_type IN ('ENTRY_SHORT', 'EXIT_SHORT')
    """
    
    # 완성된 롱 거래 분석
    long_complete_query = """
    WITH long_pairs AS (
        SELECT 
            e.timestamp as entry_time,
            x.timestamp as exit_time,
            e.price as entry_price,
            x.price as exit_price,
            e.quantity,
            e.leverage,
            ((x.price - e.price) / e.price * 100 * e.leverage) as profit_rate,
            (x.total_value - e.total_value) as profit_amount
        FROM trades e
        JOIN trades x ON e.timestamp < x.timestamp 
            AND e.trade_type = 'ENTRY_LONG'
            AND x.trade_type = 'EXIT_LONG'
            AND ABS(e.quantity - x.quantity) < 0.001
    )
    SELECT 
        COUNT(*) as total_long_trades,
        COUNT(CASE WHEN profit_amount > 0 THEN 1 END) as long_wins,
        COUNT(CASE WHEN profit_amount <= 0 THEN 1 END) as long_losses,
        AVG(profit_rate) as avg_long_profit_rate,
        SUM(profit_amount) as total_long_profit,
        AVG(profit_amount) as avg_long_profit
    FROM long_pairs
    """
    
    # 완성된 숏 거래 분석
    short_complete_query = """
    WITH short_pairs AS (
        SELECT 
            e.timestamp as entry_time,
            x.timestamp as exit_time,
            e.price as entry_price,
            x.price as exit_price,
            e.quantity,
            e.leverage,
            ((e.price - x.price) / e.price * 100 * e.leverage) as profit_rate,
            (e.total_value - x.total_value) as profit_amount
        FROM trades e
        JOIN trades x ON e.timestamp < x.timestamp 
            AND e.trade_type = 'ENTRY_SHORT'
            AND x.trade_type = 'EXIT_SHORT'
            AND ABS(e.quantity - x.quantity) < 0.001
    )
    SELECT 
        COUNT(*) as total_short_trades,
        COUNT(CASE WHEN profit_amount > 0 THEN 1 END) as short_wins,
        COUNT(CASE WHEN profit_amount <= 0 THEN 1 END) as short_losses,
        AVG(profit_rate) as avg_short_profit_rate,
        SUM(profit_amount) as total_short_profit,
        AVG(profit_amount) as avg_short_profit
    FROM short_pairs
    """
    
    try:
        # 데이터 조회
        long_df = pd.read_sql_query(long_query, conn)
        short_df = pd.read_sql_query(short_query, conn)
        long_complete_df = pd.read_sql_query(long_complete_query, conn)
        short_complete_df = pd.read_sql_query(short_complete_query, conn)
        
        conn.close()
        
        # 결과 출력
        print("\n" + "="*80)
        print("🔸 선물 거래 롱/숏별 상세 통계")
        print("="*80)
        
        # 롱 포지션 통계
        long_data = long_complete_df.iloc[0] if not long_complete_df.empty else {}
        long_entries = long_data.get('total_long_trades', 0)
        long_wins = long_data.get('long_wins', 0)
        long_losses = long_data.get('long_losses', 0)
        long_win_rate = (long_wins / long_entries * 100) if long_entries > 0 else 0
        long_profit = long_data.get('total_long_profit', 0) or 0
        avg_long_profit = long_data.get('avg_long_profit', 0) or 0
        avg_long_rate = long_data.get('avg_long_profit_rate', 0) or 0
        
        print(f"\n🟢 롱 포지션 통계")
        print(f"   진입 횟수: {long_entries}회")
        print(f"   승리 횟수: {long_wins}회")
        print(f"   패배 횟수: {long_losses}회")
        print(f"   승률: {long_win_rate:.1f}%")
        print(f"   총 손익: {long_profit:+,.2f} USDT")
        print(f"   평균 손익: {avg_long_profit:+,.2f} USDT")
        print(f"   평균 수익률: {avg_long_rate:+.2f}%")
        
        # 숏 포지션 통계
        short_data = short_complete_df.iloc[0] if not short_complete_df.empty else {}
        short_entries = short_data.get('total_short_trades', 0)
        short_wins = short_data.get('short_wins', 0)
        short_losses = short_data.get('short_losses', 0)
        short_win_rate = (short_wins / short_entries * 100) if short_entries > 0 else 0
        short_profit = short_data.get('total_short_profit', 0) or 0
        avg_short_profit = short_data.get('avg_short_profit', 0) or 0
        avg_short_rate = short_data.get('avg_short_profit_rate', 0) or 0
        
        print(f"\n🔴 숏 포지션 통계")
        print(f"   진입 횟수: {short_entries}회")
        print(f"   승리 횟수: {short_wins}회")
        print(f"   패배 횟수: {short_losses}회")
        print(f"   승률: {short_win_rate:.1f}%")
        print(f"   총 손익: {short_profit:+,.2f} USDT")
        print(f"   평균 손익: {avg_short_profit:+,.2f} USDT")
        print(f"   평균 수익률: {avg_short_rate:+.2f}%")
        
        # 전체 통계
        total_entries = long_entries + short_entries
        total_wins = long_wins + short_wins
        total_losses = long_losses + short_losses
        total_win_rate = (total_wins / total_entries * 100) if total_entries > 0 else 0
        total_profit = long_profit + short_profit
        
        print(f"\n💰 전체 통계")
        print(f"   총 거래 횟수: {total_entries}회")
        print(f"   총 승리 횟수: {total_wins}회")
        print(f"   총 패배 횟수: {total_losses}회")
        print(f"   전체 승률: {total_win_rate:.1f}%")
        print(f"   총 손익: {total_profit:+,.2f} USDT")
        
        if total_entries > 0:
            avg_total_profit = total_profit / total_entries
            print(f"   평균 거래당 손익: {avg_total_profit:+,.2f} USDT")
        
        # 손익비 계산
        if total_wins > 0 and total_losses > 0:
            avg_win = (long_profit if long_profit > 0 else 0) + (short_profit if short_profit > 0 else 0)
            avg_win = avg_win / total_wins if total_wins > 0 else 0
            
            avg_loss = abs((long_profit if long_profit < 0 else 0) + (short_profit if short_profit < 0 else 0))
            avg_loss = avg_loss / total_losses if total_losses > 0 else 0
            
            profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
            print(f"   손익비: {profit_loss_ratio:.2f}")
        
        print("="*80)
        
    except Exception as e:
        print(f"통계 계산 중 오류: {e}")
        conn.close()

def view_recent_long_short_trades(limit=10):
    """최근 롱/숏 거래 내역 조회"""
    conn = get_db_connection()
    
    query = """
    SELECT 
        datetime(timestamp, 'localtime') as 시간,
        symbol as 심볼,
        trade_type as 거래타입,
        ROUND(quantity, 6) as 수량,
        ROUND(price, 2) as 가격,
        ROUND(total_value, 2) as 총액,
        leverage as 레버리지,
        CASE WHEN test_mode = 1 THEN '테스트' ELSE '실거래' END as 모드
    FROM trades 
    WHERE trade_type IN ('ENTRY_LONG', 'EXIT_LONG', 'ENTRY_SHORT', 'EXIT_SHORT')
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    
    print(f"\n📊 최근 {limit}개 롱/숏 거래 내역")
    print("=" * 120)
    
    if df.empty:
        print("거래 내역이 없습니다.")
        return
    
    print(df.to_string(index=False))
    
    # 요약
    long_entries = len(df[df['거래타입'] == 'ENTRY_LONG'])
    long_exits = len(df[df['거래타입'] == 'EXIT_LONG'])
    short_entries = len(df[df['거래타입'] == 'ENTRY_SHORT'])
    short_exits = len(df[df['거래타입'] == 'EXIT_SHORT'])
    
    print("\n" + "=" * 120)
    print(f"📈 롱 진입: {long_entries}회 | 롱 청산: {long_exits}회 | 📉 숏 진입: {short_entries}회 | 숏 청산: {short_exits}회")

def export_trading_stats_csv():
    """거래 통계를 CSV로 내보내기"""
    conn = get_db_connection()
    
    query = """
    SELECT 
        datetime(timestamp, 'localtime') as 거래시간,
        symbol as 심볼,
        trade_type as 거래타입,
        side as 방향,
        quantity as 수량,
        price as 가격,
        total_value as 총액,
        leverage as 레버리지,
        CASE WHEN test_mode = 1 THEN '테스트' ELSE '실거래' END as 모드,
        notes as 메모
    FROM trades 
    ORDER BY timestamp DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("내보낼 거래 데이터가 없습니다.")
        return
    
    filename = f"futures_trading_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"📁 거래 통계가 {filename}에 저장되었습니다.")
    print(f"📊 총 {len(df)}개의 거래 내역이 포함되었습니다.")

def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("\n💡 사용법:")
        print("  python view_trade_stats.py stats    # 롱/숏별 상세 통계")
        print("  python view_trade_stats.py recent   # 최근 거래 내역")
        print("  python view_trade_stats.py export   # CSV 내보내기")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'stats':
        calculate_long_short_stats()
    elif command == 'recent':
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        view_recent_long_short_trades(limit)
    elif command == 'export':
        export_trading_stats_csv()
    else:
        print("❌ 알 수 없는 명령어입니다.")
        print("사용 가능한 명령어: stats, recent, export")

if __name__ == "__main__":
    main() 