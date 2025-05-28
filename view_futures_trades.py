#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
import json

def get_db_connection():
    """데이터베이스 연결"""
    return sqlite3.connect('trading_history.db')

def view_futures_trades(limit=20):
    """선물 매매 내역 조회"""
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
        position_side as 포지션방향,
        leverage as 레버리지,
        exit_stage as 청산단계,
        CASE WHEN test_mode = 1 THEN '가상매매' ELSE '실거래' END as 모드,
        notes as 비고
    FROM trades 
    WHERE notes LIKE '%선물%' OR trade_type IN ('ENTRY_LONG', 'ENTRY_SHORT', 'EXIT_LONG', 'EXIT_SHORT')
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    df = pd.read_sql_query(query, conn, params=(limit,))
    conn.close()
    
    print(f"\n🚀 최근 {limit}개 선물 매매 내역")
    print("=" * 120)
    
    if df.empty:
        print("선물 매매 내역이 없습니다.")
        return
    
    # 테이블 형태로 출력 (더 보기 좋게)
    for idx, row in df.iterrows():
        # 포지션 방향에 따른 이모지
        if row['포지션방향'] == 'LONG':
            pos_emoji = "📈" if row['방향'] == 'BUY' else "📉"
        elif row['포지션방향'] == 'SHORT':
            pos_emoji = "📉" if row['방향'] == 'SELL' else "📈"
        else:
            pos_emoji = "💹"
        
        # 거래 타입에 따른 색상
        if 'ENTRY' in str(row['거래타입']):
            type_prefix = "🔵 진입"
        elif 'EXIT' in str(row['거래타입']):
            type_prefix = "🔴 청산"
        else:
            type_prefix = "⚪ 기타"
        
        print(f"{pos_emoji} {row['시간']} | {type_prefix}")
        print(f"   {row['심볼']} | {row['방향']} {row['수량']} @ ${row['가격']:,}")
        print(f"   총액: ${row['총액']:,} | 레버리지: {row['레버리지']}배 | {row['모드']}")
        if row['비고']:
            print(f"   비고: {row['비고']}")
        print("-" * 80)
    
    # 요약 정보
    long_entries = len(df[(df['거래타입'] == 'ENTRY_LONG')])
    short_entries = len(df[(df['거래타입'] == 'ENTRY_SHORT')])
    long_exits = len(df[(df['거래타입'] == 'EXIT_LONG')])
    short_exits = len(df[(df['거래타입'] == 'EXIT_SHORT')])
    
    print("\n" + "=" * 120)
    print(f"📊 거래 요약: 롱진입 {long_entries}회 | 숏진입 {short_entries}회 | 롱청산 {long_exits}회 | 숏청산 {short_exits}회")

def view_current_positions():
    """현재 선물 포지션 상태 조회"""
    conn = get_db_connection()
    
    # 최근 포지션 상태 (선물용 확장 쿼리)
    position_query = """
    SELECT 
        datetime(timestamp, 'localtime') as 시간,
        symbol as 심볼,
        long_position as 롱포지션,
        short_position as 숏포지션,
        ROUND(long_entry_price, 2) as 롱진입가,
        ROUND(short_entry_price, 2) as 숏진입가,
        ROUND(long_stop_loss, 2) as 롱손절가,
        ROUND(short_stop_loss, 2) as 숏손절가,
        ROUND(current_price, 2) as 현재가,
        ROUND(unrealized_pnl, 2) as 미실현손익,
        leverage as 레버리지
    FROM positions 
    ORDER BY timestamp DESC 
    LIMIT 1
    """
    
    position_df = pd.read_sql_query(position_query, conn)
    
    print(f"\n📍 현재 선물 포지션 상태")
    print("=" * 80)
    
    if not position_df.empty:
        pos = position_df.iloc[0]
        print(f"⏰ 업데이트 시간: {pos['시간']}")
        print(f"🎯 심볼: {pos['심볼']}")
        print(f"💰 현재 가격: ${pos['현재가']:,}")
        print(f"🔧 레버리지: {pos['레버리지']}배")
        print()
        
        # 롱 포지션 정보
        if pos['롱포지션'] > 0:
            pnl_color = "🟢" if pos['미실현손익'] > 0 else "🔴"
            print(f"📈 롱 포지션:")
            print(f"   수량: {pos['롱포지션']:.6f}")
            print(f"   진입가: ${pos['롱진입가']:,}")
            print(f"   손절가: ${pos['롱손절가']:,}")
            print(f"   {pnl_color} 미실현 손익: ${pos['미실현손익']:+,.2f}")
        else:
            print("📈 롱 포지션: 없음")
        
        print()
        
        # 숏 포지션 정보
        if pos['숏포지션'] > 0:
            pnl_color = "🟢" if pos['미실현손익'] > 0 else "🔴"
            print(f"📉 숏 포지션:")
            print(f"   수량: {pos['숏포지션']:.6f}")
            print(f"   진입가: ${pos['숏진입가']:,}")
            print(f"   손절가: ${pos['숏손절가']:,}")
            print(f"   {pnl_color} 미실현 손익: ${pos['미실현손익']:+,.2f}")
        else:
            print("📉 숏 포지션: 없음")
            
        if pos['롱포지션'] == 0 and pos['숏포지션'] == 0:
            print("📊 현재 보유 포지션 없음")
            
    else:
        print("포지션 정보가 없습니다.")
    
    conn.close()

def calculate_futures_pnl():
    """선물 거래 손익 계산"""
    conn = get_db_connection()
    
    # 완성된 거래 페어 찾기 (진입 → 청산)
    query = """
    WITH entry_trades AS (
        SELECT * FROM trades 
        WHERE trade_type IN ('ENTRY_LONG', 'ENTRY_SHORT')
        AND notes LIKE '%선물%'
        ORDER BY timestamp
    ),
    exit_trades AS (
        SELECT * FROM trades 
        WHERE trade_type IN ('EXIT_LONG', 'EXIT_SHORT')
        AND notes LIKE '%선물%'
        ORDER BY timestamp
    )
    SELECT 
        e.timestamp as entry_time,
        x.timestamp as exit_time,
        e.trade_type as entry_type,
        x.trade_type as exit_type,
        e.price as entry_price,
        x.price as exit_price,
        e.quantity,
        e.leverage,
        CASE 
            WHEN e.trade_type = 'ENTRY_LONG' THEN 
                ROUND(((x.price - e.price) / e.price * 100 * e.leverage), 2)
            WHEN e.trade_type = 'ENTRY_SHORT' THEN 
                ROUND(((e.price - x.price) / e.price * 100 * e.leverage), 2)
        END as profit_rate,
        CASE 
            WHEN e.trade_type = 'ENTRY_LONG' THEN 
                ROUND((x.total_value - e.total_value), 2)
            WHEN e.trade_type = 'ENTRY_SHORT' THEN 
                ROUND((e.total_value - x.total_value), 2)
        END as profit_amount
    FROM entry_trades e
    JOIN exit_trades x ON (
        (e.trade_type = 'ENTRY_LONG' AND x.trade_type = 'EXIT_LONG') OR
        (e.trade_type = 'ENTRY_SHORT' AND x.trade_type = 'EXIT_SHORT')
    )
    AND e.timestamp < x.timestamp
    AND ABS(e.quantity - x.quantity) < 0.001
    ORDER BY e.timestamp DESC
    LIMIT 15
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    print(f"\n💰 최근 15개 완성된 선물 거래의 손익")
    print("=" * 100)
    
    if df.empty:
        print("완성된 선물 거래가 없습니다.")
        return
    
    total_profit = 0
    win_count = 0
    
    for idx, row in df.iterrows():
        entry_time = datetime.fromisoformat(row['entry_time']).strftime('%m-%d %H:%M')
        exit_time = datetime.fromisoformat(row['exit_time']).strftime('%m-%d %H:%M')
        
        profit_emoji = "🟢" if row['profit_rate'] > 0 else "🔴"
        position_emoji = "📈" if 'LONG' in row['entry_type'] else "📉"
        
        if row['profit_rate'] > 0:
            win_count += 1
        
        total_profit += row['profit_amount']
        
        print(f"{profit_emoji} {position_emoji} {entry_time} → {exit_time}")
        print(f"   진입: ${row['entry_price']:,} | 청산: ${row['exit_price']:,} | {row['leverage']}배")
        print(f"   수익률: {row['profit_rate']:+.2f}% | 손익: ${row['profit_amount']:+.2f}")
        print("-" * 70)
    
    # 전체 요약
    win_rate = (win_count / len(df)) * 100 if len(df) > 0 else 0
    avg_profit_rate = df['profit_rate'].mean() if not df.empty else 0
    
    print(f"\n📊 선물 거래 요약:")
    print(f"   총 거래: {len(df)}회")
    print(f"   총 손익: ${total_profit:+.2f}")
    print(f"   평균 수익률: {avg_profit_rate:+.2f}%")
    print(f"   승률: {win_rate:.1f}% ({win_count}/{len(df)})")

def view_trading_log():
    """거래 로그 확인"""
    try:
        print(f"\n📋 최근 선물 거래 로그")
        print("=" * 80)
        
        with open('futures_trading.log', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 최근 20줄만 표시
            recent_lines = lines[-20:] if len(lines) > 20 else lines
            
            for line in recent_lines:
                line = line.strip()
                if any(keyword in line for keyword in ['주문', '포지션', '진입', '청산', '손절', '익절']):
                    # 로그 레벨에 따른 이모지
                    if 'ERROR' in line:
                        emoji = "❌"
                    elif 'WARNING' in line:
                        emoji = "⚠️"
                    elif 'INFO' in line:
                        emoji = "ℹ️"
                    else:
                        emoji = "📝"
                    
                    print(f"{emoji} {line}")
                    
    except FileNotFoundError:
        print("거래 로그 파일을 찾을 수 없습니다.")
    except Exception as e:
        print(f"로그 읽기 오류: {e}")

def view_config():
    """현재 설정 확인"""
    try:
        print(f"\n⚙️ 현재 선물 거래 설정")
        print("=" * 60)
        
        with open('config_futures.json', 'r') as f:
            config = json.load(f)
            
        print(f"📊 심볼: {config.get('symbol', 'N/A')}")
        print(f"⏰ 타임프레임: {config.get('timeframe', 'N/A')}")
        print(f"🔧 레버리지: {config.get('leverage', 'N/A')}배")
        print(f"💰 최대 거래 금액: ${config.get('max_trade_amount', 'N/A'):,}")
        print(f"🧪 테스트 모드: {'켜짐' if config.get('test_mode', True) else '꺼짐'}")
        
    except FileNotFoundError:
        print("설정 파일(config_futures.json)을 찾을 수 없습니다.")
    except Exception as e:
        print(f"설정 읽기 오류: {e}")

def export_futures_trades():
    """선물 매매 내역을 CSV로 내보내기"""
    conn = get_db_connection()
    
    query = """
    SELECT 
        timestamp,
        symbol,
        side,
        quantity,
        price,
        total_value,
        trade_type,
        position_side,
        leverage,
        exit_stage,
        test_mode,
        notes
    FROM trades 
    WHERE notes LIKE '%선물%' OR trade_type IN ('ENTRY_LONG', 'ENTRY_SHORT', 'EXIT_LONG', 'EXIT_SHORT')
    ORDER BY timestamp DESC
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        print("내보낼 선물 거래 내역이 없습니다.")
        return
    
    filename = f"futures_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    
    print(f"\n💾 선물 매매 내역이 {filename} 파일로 저장되었습니다.")
    print(f"📊 총 {len(df)}개의 거래 내역을 저장했습니다.")

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "trades":
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            view_futures_trades(limit)
        elif command == "positions":
            view_current_positions()
        elif command == "pnl":
            calculate_futures_pnl()
        elif command == "log":
            view_trading_log()
        elif command == "config":
            view_config()
        elif command == "export":
            export_futures_trades()
        elif command == "all":
            # 모든 정보 표시
            view_config()
            view_current_positions()
            view_futures_trades(10)
            calculate_futures_pnl()
            view_trading_log()
        else:
            print("\n사용법:")
            print("  python3 view_futures_trades.py [명령어] [옵션]")
            print("\n명령어:")
            print("  trades [숫자]  - 최근 매매 내역 보기 (기본값: 20)")
            print("  positions      - 현재 포지션 상태 보기")
            print("  pnl           - 손익 계산 및 통계")
            print("  log           - 최근 거래 로그 보기")
            print("  config        - 현재 설정 확인")
            print("  export        - CSV 파일로 내보내기")
            print("  all           - 모든 정보 한번에 보기")
    else:
        # 기본: 핵심 정보만 표시
        view_current_positions()
        view_futures_trades(10)
        calculate_futures_pnl()

if __name__ == "__main__":
    main() 