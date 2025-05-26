#!/usr/bin/env python
# -*- coding: utf-8 -*-

from strategy import TrendFollowingStrategy
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import os

def run_backtest():
    # 전략 객체 생성
    strategy = TrendFollowingStrategy(
        initial_capital=10000,  # 초기 자본금 (USDT)
        risk_percentage=0.01,   # 거래당 리스크 비율 (1%)
        leverage=3              # 레버리지 (최대 3배)
    )
    
    print("백테스팅 시작...")
    print("데이터 가져오는 중...")
    
    # 데이터 가져오기 (지난 90일 데이터)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    # 타임스탬프를 밀리초로 변환
    since = int(start_date.timestamp() * 1000)
    until = int(end_date.timestamp() * 1000)
    
    try:
        # Binance에서 BTC/USDT 4시간봉 데이터 가져오기
        data = strategy.fetch_data(
            exchange_id='binance',
            symbol='BTC/USDT',
            timeframe='4h',
            since=since,
            until=until
        )
        
        print(f"데이터 가져오기 완료: {len(data)}개 캔들")
        
        # 백테스팅 실행
        print("백테스팅 실행 중...")
        results = strategy.backtest(data)
        
        # 백테스팅 결과 저장
        save_results(results)
        
        # 결과 시각화
        strategy.plot_results(results)
        
    except Exception as e:
        print(f"백테스팅 오류: {e}")

def save_results(results):
    """백테스팅 결과를 CSV 파일로 저장"""
    # 결과 디렉토리 생성
    os.makedirs('backtest_results', exist_ok=True)
    
    # 현재 시간을 파일명에 포함
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 자본금 곡선 저장
    equity_curve_file = f'backtest_results/equity_curve_{timestamp}.csv'
    results['equity_curve'].to_csv(equity_curve_file)
    print(f"자본금 곡선 저장: {equity_curve_file}")
    
    # 거래 기록 저장
    trades_file = f'backtest_results/trades_{timestamp}.csv'
    results['trades'].to_csv(trades_file)
    print(f"거래 기록 저장: {trades_file}")
    
    # 요약 통계 저장
    summary_file = f'backtest_results/summary_{timestamp}.txt'
    with open(summary_file, 'w') as f:
        f.write(f"총 수익률: {results['total_return'] * 100:.2f}%\n")
        f.write(f"총 거래 횟수: {results['total_trades']}\n")
        f.write(f"승률: {results['win_rate'] * 100:.2f}%\n")
        f.write(f"손익비: {results['profit_factor']:.2f}\n")
        f.write(f"최대 낙폭: {results['max_drawdown'] * 100:.2f}%\n")
        f.write(f"최종 자본금: {results['final_capital']:.2f} USDT\n")
    print(f"요약 통계 저장: {summary_file}")

if __name__ == "__main__":
    run_backtest() 