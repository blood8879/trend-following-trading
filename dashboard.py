#!/usr/bin/env python
# -*- coding: utf-8 -*-

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import json

# 데이터베이스 연결
def get_db_connection():
    return sqlite3.connect('trading.db')

# 매매 내역 조회
def get_trades_data():
    conn = get_db_connection()
    query = """
    SELECT timestamp, symbol, side, quantity, price, total_value, 
           trade_type, position_side, leverage, test_mode
    FROM trades 
    ORDER BY timestamp DESC 
    LIMIT 100
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# 포지션 내역 조회
def get_positions_data():
    conn = get_db_connection()
    query = """
    SELECT timestamp, symbol, long_position, short_position, 
           long_entry_price, short_entry_price, unrealized_pnl, current_price
    FROM positions 
    ORDER BY timestamp DESC 
    LIMIT 100
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# 계정 상태 조회
def get_account_data():
    conn = get_db_connection()
    query = """
    SELECT timestamp, total_balance, available_balance, total_pnl
    FROM account_status 
    ORDER BY timestamp DESC 
    LIMIT 100
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# 시장 데이터 조회
def get_market_data():
    conn = get_db_connection()
    query = """
    SELECT timestamp, close_price, ema10, ema20, ema50, volume
    FROM market_data 
    ORDER BY timestamp DESC 
    LIMIT 200
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# Dash 앱 초기화
app = dash.Dash(__name__)
app.title = "선물 자동매매 대시보드"

# 레이아웃 정의
app.layout = html.Div([
    html.H1("🚀 선물 자동매매 대시보드", style={'textAlign': 'center', 'color': '#2c3e50'}),
    
    # 새로고침 간격 설정
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # 30초마다 업데이트
        n_intervals=0
    ),
    
    # 상단 요약 카드
    html.Div([
        html.Div([
            html.H3("총 잔고", style={'color': '#3498db'}),
            html.H2(id='total-balance', style={'color': '#2c3e50'})
        ], className='summary-card', style={'width': '23%', 'display': 'inline-block', 'margin': '1%', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px'}),
        
        html.Div([
            html.H3("미실현 손익", style={'color': '#e74c3c'}),
            html.H2(id='unrealized-pnl', style={'color': '#2c3e50'})
        ], className='summary-card', style={'width': '23%', 'display': 'inline-block', 'margin': '1%', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px'}),
        
        html.Div([
            html.H3("롱 포지션", style={'color': '#27ae60'}),
            html.H2(id='long-position', style={'color': '#2c3e50'})
        ], className='summary-card', style={'width': '23%', 'display': 'inline-block', 'margin': '1%', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px'}),
        
        html.Div([
            html.H3("숏 포지션", style={'color': '#e67e22'}),
            html.H2(id='short-position', style={'color': '#2c3e50'})
        ], className='summary-card', style={'width': '23%', 'display': 'inline-block', 'margin': '1%', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '10px'})
    ]),
    
    # 차트 섹션
    html.Div([
        html.Div([
            html.H3("가격 차트 & EMA", style={'textAlign': 'center'}),
            dcc.Graph(id='price-chart')
        ], style={'width': '50%', 'display': 'inline-block'}),
        
        html.Div([
            html.H3("손익 추이", style={'textAlign': 'center'}),
            dcc.Graph(id='pnl-chart')
        ], style={'width': '50%', 'display': 'inline-block'})
    ]),
    
    # 매매 내역 테이블
    html.Div([
        html.H3("최근 매매 내역", style={'textAlign': 'center', 'marginTop': '30px'}),
        dash_table.DataTable(
            id='trades-table',
            columns=[
                {'name': '시간', 'id': 'timestamp'},
                {'name': '심볼', 'id': 'symbol'},
                {'name': '방향', 'id': 'side'},
                {'name': '수량', 'id': 'quantity', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                {'name': '가격', 'id': 'price', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                {'name': '총액', 'id': 'total_value', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                {'name': '타입', 'id': 'trade_type'},
                {'name': '포지션', 'id': 'position_side'},
                {'name': '테스트', 'id': 'test_mode'}
            ],
            style_cell={'textAlign': 'center'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{side} = BUY'},
                    'backgroundColor': '#d5f4e6',
                    'color': 'black',
                },
                {
                    'if': {'filter_query': '{side} = SELL'},
                    'backgroundColor': '#ffeaa7',
                    'color': 'black',
                }
            ],
            page_size=10
        )
    ], style={'margin': '20px'})
])

# 콜백 함수들
@app.callback(
    [Output('total-balance', 'children'),
     Output('unrealized-pnl', 'children'),
     Output('long-position', 'children'),
     Output('short-position', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_summary_cards(n):
    try:
        # 계정 데이터
        account_df = get_account_data()
        if not account_df.empty:
            total_balance = f"{account_df.iloc[0]['total_balance']:.2f} USDT"
        else:
            total_balance = "0.00 USDT"
        
        # 포지션 데이터
        positions_df = get_positions_data()
        if not positions_df.empty:
            latest_position = positions_df.iloc[0]
            unrealized_pnl = f"{latest_position['unrealized_pnl']:.2f} USDT"
            long_pos = f"{latest_position['long_position']:.4f}"
            short_pos = f"{latest_position['short_position']:.4f}"
        else:
            unrealized_pnl = "0.00 USDT"
            long_pos = "0.0000"
            short_pos = "0.0000"
        
        return total_balance, unrealized_pnl, long_pos, short_pos
    except:
        return "N/A", "N/A", "N/A", "N/A"

@app.callback(
    Output('price-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_price_chart(n):
    try:
        df = get_market_data()
        if df.empty:
            return go.Figure()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        fig = go.Figure()
        
        # 가격 라인
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['close_price'],
            mode='lines',
            name='가격',
            line=dict(color='#3498db', width=2)
        ))
        
        # EMA 라인들
        if 'ema10' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['ema10'],
                mode='lines',
                name='EMA10',
                line=dict(color='#e74c3c', width=1)
            ))
        
        if 'ema20' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['ema20'],
                mode='lines',
                name='EMA20',
                line=dict(color='#f39c12', width=1)
            ))
        
        if 'ema50' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['ema50'],
                mode='lines',
                name='EMA50',
                line=dict(color='#27ae60', width=1)
            ))
        
        fig.update_layout(
            title="가격 & EMA 차트",
            xaxis_title="시간",
            yaxis_title="가격 (USDT)",
            hovermode='x unified'
        )
        
        return fig
    except:
        return go.Figure()

@app.callback(
    Output('pnl-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_pnl_chart(n):
    try:
        df = get_account_data()
        if df.empty:
            return go.Figure()
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['total_pnl'],
            mode='lines+markers',
            name='총 손익',
            line=dict(color='#9b59b6', width=2),
            fill='tonexty'
        ))
        
        fig.update_layout(
            title="손익 추이",
            xaxis_title="시간",
            yaxis_title="손익 (USDT)",
            hovermode='x unified'
        )
        
        return fig
    except:
        return go.Figure()

@app.callback(
    Output('trades-table', 'data'),
    [Input('interval-component', 'n_intervals')]
)
def update_trades_table(n):
    try:
        df = get_trades_data()
        if df.empty:
            return []
        
        # 시간 포맷팅
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%m-%d %H:%M')
        
        return df.to_dict('records')
    except:
        return []

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8050, debug=False) 