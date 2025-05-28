#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys

def get_db_connection():
    """데이터베이스 연결"""
    return sqlite3.connect('trading_history.db')

def view_recent_trades(limit=20):
    """최근 매매 내역 조회"""
    conn = get_db_connection()
    
    query = """
    SELECT 
        datetime(timestamp, 'localtime') as 시간,
        symbol as 심볼,
        side as 방향,
        ROUND(quantity, 6) as 수량,
        ROUND(price, 2) as 가격,
        ROUND(total_value, 2) as 총액,
        trade_type as 거래타입,
        CASE WHEN test_mode = 1 THEN '테스트' ELSE '실거래' END as 모드
    FROM trades 
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    
    print(f"\n📊 최근 {limit}개 매매 내역")
    print("=" * 100)
    
    if df.empty:
        print("매매 내역이 없습니다.")
        return
    
    # 테이블 형태로 출력
    print(df.to_string(index=False))
    
    # 요약 정보
    buy_count = len(df[df['방향'] == 'BUY'])
    sell_count = len(df[df['방향'] == 'SELL'])
    
    print("\n" + "=" * 100)
    print(f"📈 매수: {buy_count}회 | 📉 매도: {sell_count}회")

def calculate_profit_loss():
    """손익 계산"""
    conn = get_db_connection()
    
    query = """
    SELECT 
        b.timestamp as buy_time,
        s.timestamp as sell_time,
        b.price as buy_price,
        s.price as sell_price,
        b.quantity,
        ROUND(((s.price - b.price) / b.price * 100), 2) as profit_rate,
        ROUND((s.total_value - b.total_value), 2) as profit_amount
    FROM trades b
    JOIN trades s ON b.timestamp < s.timestamp 
        AND b.side = 'BUY' 
        AND s.side = 'SELL'
        AND ABS(b.quantity - s.quantity) < 0.0001
    ORDER BY b.timestamp DESC
    LIMIT 10
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"\n💰 최근 10개 완성된 거래의 손익")
    print("=" * 80)
    
    if df.empty:
        print("완성된 거래가 없습니다.")
        return
    
    for _, row in df.iterrows():
        buy_time = datetime.fromisoformat(row['buy_time']).strftime('%m-%d %H:%M')
        sell_time = datetime.fromisoformat(row['sell_time']).strftime('%m-%d %H:%M')
        
        profit_emoji = "🟢" if row['profit_rate'] > 0 else "🔴"
        
        print(f"{profit_emoji} {buy_time} → {sell_time}")
        print(f"   매수: ${row['buy_price']:,} | 매도: ${row['sell_price']:,}")
        print(f"   수익률: {row['profit_rate']:+.2f}% | 손익: ${row['profit_amount']:+.2f}")
        print("-" * 50)
    
    # 전체 요약
    total_profit = df['profit_amount'].sum()
    avg_profit_rate = df['profit_rate'].mean()
    win_rate = len(df[df['profit_rate'] > 0]) / len(df) * 100
    
    print(f"\n📊 거래 요약:")
    print(f"   총 손익: ${total_profit:+.2f}")
    print(f"   평균 수익률: {avg_profit_rate:+.2f}%")
    print(f"   승률: {win_rate:.1f}%")

def view_current_status():
    """현재 상태 조회"""
    conn = get_db_connection()
    
    # 최근 포지션 상태
    position_query = """
    SELECT 
        datetime(timestamp, 'localtime') as 시간,
        CASE 
            WHEN position = 1 THEN '롱'
            WHEN position = -1 THEN '숏'
            ELSE '없음'
        END as 포지션타입,
        position_size as 포지션크기,
        ROUND(current_price, 2) as 현재가,
        ROUND(unrealized_pnl, 2) as 미실현손익
    FROM positions 
    ORDER BY timestamp DESC 
    LIMIT 1
    """
    
    position_df = pd.read_sql_query(position_query, conn)
    
    print(f"\n📍 현재 포지션 상태")
    print("=" * 60)
    
    if not position_df.empty:
        pos = position_df.iloc[0]
        print(f"업데이트 시간: {pos['시간']}")
        print(f"포지션 타입: {pos['포지션타입']}")
        print(f"포지션 크기: {pos['포지션크기']:.6f}")
        print(f"현재 가격: ${pos['현재가']:,}")
        print(f"미실현 손익: ${pos['미실현손익']:+.2f}")
    else:
        print("포지션 정보가 없습니다.")
    
    conn.close()

def export_to_csv():
    """CSV 파일로 내보내기"""
    conn = get_db_connection()
    
    query = """
    SELECT * FROM trades 
    ORDER BY timestamp DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"\n💾 매매 내역이 {filename} 파일로 저장되었습니다.")

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "trades":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            view_recent_trades(limit)
        elif command == "profit":
            calculate_profit_loss()
        elif command == "status":
            view_current_status()
        elif command == "export":
            export_to_csv()
        else:
            print("사용법: python3 view_trades.py [trades|profit|status|export] [숫자]")
    else:
        # 기본: 모든 정보 표시
        view_recent_trades(10)
        calculate_profit_loss()
        view_current_status()

if __name__ == "__main__":
    main() 