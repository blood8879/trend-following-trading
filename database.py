#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd

class TradingDatabase:
    """
    매매 내역을 저장하고 관리하는 데이터베이스 클래스
    """
    
    def __init__(self, db_path: str = "trading_history.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 매매 내역 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,  -- BUY, SELL
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    order_id TEXT,
                    trade_type TEXT,  -- ENTRY, EXIT, STOP_LOSS
                    exit_stage INTEGER DEFAULT 0,  -- 0: 진입, 1: 1차익절, 2: 2차익절, 3: 3차익절
                    stop_loss_price REAL,
                    secondary_stop_loss_price REAL,
                    test_mode BOOLEAN DEFAULT TRUE,
                    notes TEXT
                )
            ''')
            
            # 포지션 상태 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    position INTEGER NOT NULL,  -- 0: 없음, 1: 롱, -1: 숏
                    entry_price REAL,
                    position_size REAL,
                    stop_loss REAL,
                    secondary_stop_loss REAL,
                    unrealized_pnl REAL,
                    current_price REAL
                )
            ''')
            
            # 계정 상태 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    total_balance REAL NOT NULL,
                    available_balance REAL NOT NULL,
                    base_asset_balance REAL NOT NULL,
                    quote_asset_balance REAL NOT NULL,
                    total_pnl REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    total_trades INTEGER DEFAULT 0
                )
            ''')
            
            # 시장 데이터 테이블 (차트용)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    ema10 REAL,
                    ema20 REAL,
                    ema50 REAL
                )
            ''')
            
            conn.commit()
    
    def add_trade(self, trade_data: Dict) -> int:
        """매매 내역 추가"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (
                    timestamp, symbol, side, quantity, price, total_value,
                    order_id, trade_type, exit_stage, stop_loss_price,
                    secondary_stop_loss_price, test_mode, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('timestamp', datetime.now()),
                trade_data.get('symbol'),
                trade_data.get('side'),
                trade_data.get('quantity'),
                trade_data.get('price'),
                trade_data.get('total_value'),
                trade_data.get('order_id'),
                trade_data.get('trade_type'),
                trade_data.get('exit_stage', 0),
                trade_data.get('stop_loss_price'),
                trade_data.get('secondary_stop_loss_price'),
                trade_data.get('test_mode', True),
                trade_data.get('notes')
            ))
            
            trade_id = cursor.lastrowid
            conn.commit()
            return trade_id
    
    def update_position(self, position_data: Dict):
        """포지션 상태 업데이트"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO positions (
                    timestamp, symbol, position, entry_price, position_size,
                    stop_loss, secondary_stop_loss, unrealized_pnl, current_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                position_data.get('timestamp', datetime.now()),
                position_data.get('symbol'),
                position_data.get('position'),
                position_data.get('entry_price'),
                position_data.get('position_size'),
                position_data.get('stop_loss'),
                position_data.get('secondary_stop_loss'),
                position_data.get('unrealized_pnl'),
                position_data.get('current_price')
            ))
            
            conn.commit()
    
    def update_account_status(self, account_data: Dict):
        """계정 상태 업데이트"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO account_status (
                    timestamp, total_balance, available_balance,
                    base_asset_balance, quote_asset_balance,
                    total_pnl, win_rate, total_trades
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                account_data.get('timestamp', datetime.now()),
                account_data.get('total_balance'),
                account_data.get('available_balance'),
                account_data.get('base_asset_balance'),
                account_data.get('quote_asset_balance'),
                account_data.get('total_pnl', 0),
                account_data.get('win_rate', 0),
                account_data.get('total_trades', 0)
            ))
            
            conn.commit()
    
    def add_market_data(self, market_data: Dict):
        """시장 데이터 추가"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO market_data (
                    timestamp, symbol, timeframe, open_price, high_price,
                    low_price, close_price, volume, ema10, ema20, ema50
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                market_data.get('timestamp'),
                market_data.get('symbol'),
                market_data.get('timeframe'),
                market_data.get('open_price'),
                market_data.get('high_price'),
                market_data.get('low_price'),
                market_data.get('close_price'),
                market_data.get('volume'),
                market_data.get('ema10'),
                market_data.get('ema20'),
                market_data.get('ema50')
            ))
            
            conn.commit()
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict]:
        """최근 매매 내역 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM trades 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (limit,))
            
            columns = [description[0] for description in cursor.description]
            trades = []
            
            for row in cursor.fetchall():
                trade = dict(zip(columns, row))
                trades.append(trade)
            
            return trades
    
    def get_current_position(self, symbol: str) -> Optional[Dict]:
        """현재 포지션 상태 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM positions 
                WHERE symbol = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (symbol,))
            
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            
            return None
    
    def get_account_summary(self) -> Dict:
        """계정 요약 정보 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 최근 계정 상태
            cursor.execute('''
                SELECT * FROM account_status 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                account_status = dict(zip(columns, row))
            else:
                account_status = {}
            
            # 총 거래 수
            cursor.execute('SELECT COUNT(*) FROM trades')
            total_trades = cursor.fetchone()[0]
            
            # 승률 계산
            cursor.execute('''
                SELECT 
                    COUNT(CASE WHEN side = 'SELL' AND trade_type != 'STOP_LOSS' THEN 1 END) as wins,
                    COUNT(CASE WHEN side = 'SELL' AND trade_type = 'STOP_LOSS' THEN 1 END) as losses
                FROM trades
            ''')
            
            win_loss = cursor.fetchone()
            wins, losses = win_loss[0], win_loss[1]
            win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
            
            account_status.update({
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate
            })
            
            return account_status
    
    def get_market_data_for_chart(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """차트용 시장 데이터 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM market_data 
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (symbol, timeframe, limit))
            
            columns = [description[0] for description in cursor.description]
            data = []
            
            for row in cursor.fetchall():
                candle = dict(zip(columns, row))
                data.append(candle)
            
            return list(reversed(data))  # 시간순 정렬
    
    def get_pnl_history(self, days: int = 30) -> List[Dict]:
        """손익 히스토리 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    DATE(timestamp) as date,
                    SUM(CASE WHEN side = 'SELL' THEN total_value ELSE -total_value END) as daily_pnl
                FROM trades 
                WHERE timestamp >= datetime('now', '-{} days')
                GROUP BY DATE(timestamp)
                ORDER BY date
            '''.format(days))
            
            columns = [description[0] for description in cursor.description]
            pnl_data = []
            
            for row in cursor.fetchall():
                pnl = dict(zip(columns, row))
                pnl_data.append(pnl)
            
            return pnl_data 