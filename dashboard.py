#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import json
from datetime import datetime, timedelta
import threading
import time
from database import TradingDatabase

app = Flask(__name__)
app.config['SECRET_KEY'] = 'trading_dashboard_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 데이터베이스 인스턴스
db = TradingDatabase()

class DashboardManager:
    """대시보드 관리 클래스"""
    
    def __init__(self):
        self.is_running = False
        self.update_thread = None
    
    def start_real_time_updates(self):
        """실시간 업데이트 시작"""
        if not self.is_running:
            self.is_running = True
            self.update_thread = threading.Thread(target=self._update_loop)
            self.update_thread.daemon = True
            self.update_thread.start()
    
    def stop_real_time_updates(self):
        """실시간 업데이트 중지"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join()
    
    def _update_loop(self):
        """실시간 업데이트 루프"""
        while self.is_running:
            try:
                # 최신 데이터 가져오기
                recent_trades = db.get_recent_trades(limit=10)
                account_summary = db.get_account_summary()
                
                # 클라이언트에 데이터 전송
                socketio.emit('trades_update', recent_trades)
                socketio.emit('account_update', account_summary)
                
                time.sleep(5)  # 5초마다 업데이트
                
            except Exception as e:
                print(f"실시간 업데이트 오류: {e}")
                time.sleep(10)

dashboard_manager = DashboardManager()

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('dashboard.html')

@app.route('/api/trades')
def get_trades():
    """매매 내역 API"""
    limit = request.args.get('limit', 50, type=int)
    trades = db.get_recent_trades(limit=limit)
    return jsonify(trades)

@app.route('/api/account')
def get_account():
    """계정 정보 API"""
    account_summary = db.get_account_summary()
    return jsonify(account_summary)

@app.route('/api/position/<symbol>')
def get_position(symbol):
    """포지션 정보 API"""
    position = db.get_current_position(symbol)
    return jsonify(position)

@app.route('/api/chart/<symbol>/<timeframe>')
def get_chart_data(symbol, timeframe):
    """차트 데이터 API"""
    limit = request.args.get('limit', 100, type=int)
    chart_data = db.get_market_data_for_chart(symbol, timeframe, limit)
    return jsonify(chart_data)

@app.route('/api/pnl')
def get_pnl_history():
    """손익 히스토리 API"""
    days = request.args.get('days', 30, type=int)
    pnl_data = db.get_pnl_history(days)
    return jsonify(pnl_data)

@socketio.on('connect')
def handle_connect():
    """클라이언트 연결 시"""
    print('클라이언트가 연결되었습니다.')
    dashboard_manager.start_real_time_updates()
    
    # 초기 데이터 전송
    recent_trades = db.get_recent_trades(limit=10)
    account_summary = db.get_account_summary()
    
    emit('trades_update', recent_trades)
    emit('account_update', account_summary)

@socketio.on('disconnect')
def handle_disconnect():
    """클라이언트 연결 해제 시"""
    print('클라이언트가 연결을 해제했습니다.')

if __name__ == '__main__':
    # 개발 서버 실행
    socketio.run(app, debug=True, host='0.0.0.0', port=8080) 