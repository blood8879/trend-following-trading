#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import sys

def migrate_database():
    """데이터베이스를 선물 거래에 맞게 마이그레이션"""
    
    print("📊 데이터베이스 마이그레이션 시작...")
    
    try:
        conn = sqlite3.connect('trading_history.db')
        cursor = conn.cursor()
        
        # trades 테이블에 선물 거래 컬럼 추가
        print("🔧 trades 테이블 업데이트 중...")
        
        try:
            cursor.execute('ALTER TABLE trades ADD COLUMN position_side TEXT')
            print("   ✅ position_side 컬럼 추가됨")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⏭️ position_side 컬럼이 이미 존재함")
            else:
                print(f"   ❌ position_side 컬럼 추가 실패: {e}")
        
        try:
            cursor.execute('ALTER TABLE trades ADD COLUMN leverage INTEGER DEFAULT 1')
            print("   ✅ leverage 컬럼 추가됨")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("   ⏭️ leverage 컬럼이 이미 존재함")
            else:
                print(f"   ❌ leverage 컬럼 추가 실패: {e}")
        
        # positions 테이블에 선물 거래 컬럼들 추가
        print("🔧 positions 테이블 업데이트 중...")
        
        futures_columns = [
            ('long_position', 'REAL DEFAULT 0'),
            ('short_position', 'REAL DEFAULT 0'),
            ('long_entry_price', 'REAL DEFAULT 0'),
            ('short_entry_price', 'REAL DEFAULT 0'),
            ('long_stop_loss', 'REAL DEFAULT 0'),
            ('short_stop_loss', 'REAL DEFAULT 0'),
            ('long_secondary_stop_loss', 'REAL DEFAULT 0'),
            ('short_secondary_stop_loss', 'REAL DEFAULT 0'),
            ('leverage', 'INTEGER DEFAULT 1')
        ]
        
        for column_name, column_type in futures_columns:
            try:
                cursor.execute(f'ALTER TABLE positions ADD COLUMN {column_name} {column_type}')
                print(f"   ✅ {column_name} 컬럼 추가됨")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"   ⏭️ {column_name} 컬럼이 이미 존재함")
                else:
                    print(f"   ❌ {column_name} 컬럼 추가 실패: {e}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ 데이터베이스 마이그레이션 완료!")
        print("🚀 이제 선물 거래 모니터링을 사용할 수 있습니다.")
        
    except Exception as e:
        print(f"❌ 마이그레이션 중 오류 발생: {e}")
        return False
    
    return True

def check_database_schema():
    """현재 데이터베이스 스키마 확인"""
    
    print("\n📋 현재 데이터베이스 스키마:")
    
    try:
        conn = sqlite3.connect('trading_history.db')
        cursor = conn.cursor()
        
        # trades 테이블 스키마
        cursor.execute("PRAGMA table_info(trades)")
        trades_columns = cursor.fetchall()
        
        print("\n🏷️ trades 테이블:")
        for col in trades_columns:
            print(f"   {col[1]} ({col[2]})")
        
        # positions 테이블 스키마
        cursor.execute("PRAGMA table_info(positions)")
        positions_columns = cursor.fetchall()
        
        print("\n📍 positions 테이블:")
        for col in positions_columns:
            print(f"   {col[1]} ({col[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 스키마 확인 중 오류: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_database_schema()
    else:
        if migrate_database():
            check_database_schema() 