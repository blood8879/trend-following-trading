import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from strategy import TrendFollowingStrategy
import argparse
import os
from datetime import datetime, timedelta
import time

def calculate_sharpe_ratio(returns, risk_free_rate=0.0):
    """
    샤프 지수 계산
    Args:
        returns: 수익률 시리즈
        risk_free_rate: 무위험 수익률
    Returns:
        샤프 지수
    """
    excess_return = returns - risk_free_rate
    return (np.mean(excess_return) / np.std(excess_return)) * np.sqrt(365) if np.std(excess_return) > 0 else 0

def calculate_profit_factor(profits, losses):
    """
    손익비 계산
    Args:
        profits: 수익 거래 합계
        losses: 손실 거래 합계 (양수값)
    Returns:
        손익비
    """
    return profits / losses if losses > 0 else float('inf')

def main():
    parser = argparse.ArgumentParser(description='비트코인 선물시장 트렌드 팔로잉 전략 백테스팅')
    
    # 백테스팅 관련 인자
    parser.add_argument('--initial_capital', type=float, default=10000, help='초기 자본금 (USDT)')
    parser.add_argument('--risk_percentage', type=float, default=0.02, help='거래당 허용 리스크 비율 (0.02 = 2%)')
    parser.add_argument('--leverage', type=int, default=3, help='사용할 레버리지 (최대 3배)')
    
    # 데이터 관련 인자
    parser.add_argument('--exchange', type=str, default='binance', help='거래소 (binance, bybit 등)')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='심볼 (BTC/USDT, ETH/USDT 등)')
    parser.add_argument('--timeframe', type=str, default='4h', help='시간프레임 (1h, 4h, 1d 등)')
    parser.add_argument('--start_date', type=str, default='2023-01-01', help='백테스팅 시작 날짜 (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2025-05-21', help='백테스팅 종료 날짜 (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=1000, help='각 요청당 가져올 캔들 개수')
    
    # 전략 파라미터
    parser.add_argument('--sideways_lookback', type=int, default=5, help='횡보 구간 감지 기간')
    parser.add_argument('--sideways_threshold', type=float, default=0.1, help='횡보 구간 감지 임계값 (높을수록 완화)')
    parser.add_argument('--breakout_lookback', type=int, default=3, help='돌파 감지 기간')
    
    # 기타 인자
    parser.add_argument('--use_saved_data', action='store_true', help='저장된 데이터 사용 여부')
    parser.add_argument('--save_data', action='store_true', help='데이터 저장 여부')
    parser.add_argument('--data_dir', type=str, default='data', help='데이터 저장 디렉토리')
    
    args = parser.parse_args()
    
    # 시작 날짜와 종료 날짜 설정
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    print(f"백테스트 시작 날짜: {start_date.strftime('%Y-%m-%d')}")
    print(f"백테스트 종료 날짜: {end_date.strftime('%Y-%m-%d')}")
    
    # 데이터 디렉토리 생성
    if not os.path.exists(args.data_dir):
        os.makedirs(args.data_dir)
    
    # 전략 인스턴스 생성
    strategy = TrendFollowingStrategy(
        initial_capital=args.initial_capital,
        risk_percentage=args.risk_percentage,
        leverage=args.leverage
    )
    
    # 파일명 생성
    filename_suffix = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    data_file = os.path.join(args.data_dir, f"{args.exchange}_{args.symbol.replace('/', '_')}_{args.timeframe}_{filename_suffix}.csv")
    
    if args.use_saved_data and os.path.exists(data_file):
        print(f"저장된 데이터를 불러옵니다: {data_file}")
        data = pd.read_csv(data_file)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
    else:
        print(f"{args.exchange}에서 {args.symbol} {args.timeframe} 데이터를 가져옵니다 ({args.start_date} ~ {args.end_date})...")
        
        # 시작 시간 계산
        start_time = int(start_date.timestamp() * 1000)
        end_time = int(end_date.timestamp() * 1000)
        
        # CCXT를 통해 데이터 가져오기
        data = strategy.fetch_data(
            exchange_id=args.exchange,
            symbol=args.symbol,
            timeframe=args.timeframe,
            since=start_time,
            until=end_time,
            limit=args.limit
        )
        
        # 데이터 저장
        if args.save_data:
            print(f"데이터를 저장합니다: {data_file}")
            data.reset_index().to_csv(data_file, index=False)
    
    print(f"데이터 로드 완료: {len(data)} 캔들")
    print(f"기간: {data.index[0]} ~ {data.index[-1]}")
    
    # 전략 파라미터 수정
    strategy.detect_sideways = lambda data, lookback=args.sideways_lookback, threshold=args.sideways_threshold: \
        TrendFollowingStrategy.detect_sideways(strategy, data, lookback, threshold)
    
    strategy.identify_range_breakout = lambda data, lookback=args.breakout_lookback: \
        TrendFollowingStrategy.identify_range_breakout(strategy, data, lookback)
    
    # 백테스팅 실행
    print("백테스팅을 시작합니다...")
    results = strategy.backtest(data)
    
    # 결과 출력
    print("\n===== 백테스팅 결과 =====")
    print(f"총 수익률: {results['total_return'] * 100:.2f}%")
    print(f"총 거래 횟수: {results['total_trades']}")
    print(f"승률: {results['win_rate'] * 100:.2f}%")
    print(f"손익비: {results['profit_factor']:.2f}")
    print(f"최대 낙폭: {results['max_drawdown'] * 100:.2f}%")
    print(f"최종 자본금: {results['final_capital']:.2f} USDT")
    
    # 거래 내역이 있는 경우만 상세 정보 출력
    if results['total_trades'] > 0:
        print("\n===== 거래 분석 =====")
        trades = results['trades']
        
        # 롱/숏 포지션 비율
        entry_trades = trades[trades['type'] == 'entry']
        long_trades = entry_trades[entry_trades['direction'] == 'long']
        short_trades = entry_trades[entry_trades['direction'] == 'short']
        print(f"롱 포지션: {len(long_trades)}개 ({len(long_trades)/len(entry_trades)*100:.1f}%)")
        print(f"숏 포지션: {len(short_trades)}개 ({len(short_trades)/len(entry_trades)*100:.1f}%)")
        
        # 포지션별 승률 계산
        exit_trades = trades[trades['type'] == 'exit']
        
        # 롱 포지션 승률 계산
        long_exits = []
        short_exits = []
        
        # 각 포지션에 대한 출구 거래 매칭
        for i in range(min(len(entry_trades), len(exit_trades))):
            if i < len(entry_trades) and i < len(exit_trades):
                if entry_trades.iloc[i]['direction'] == 'long':
                    long_exits.append(exit_trades.iloc[i])
                else:
                    short_exits.append(exit_trades.iloc[i])
        
        # 전체 수익률 시리즈 계산
        equity_curve = results['equity_curve']
        if 'equity' in equity_curve.columns:
            equity_values = equity_curve['equity'].values
            daily_returns = np.diff(equity_values) / equity_values[:-1]
            overall_sharpe = calculate_sharpe_ratio(daily_returns)
            print(f"\n전체 전략 샤프 지수: {overall_sharpe:.2f}")
        
        # 롱 포지션 승률
        if long_exits:
            long_exits_df = pd.DataFrame(long_exits)
            long_wins = long_exits_df[long_exits_df['pnl'] > 0]
            long_losses = long_exits_df[long_exits_df['pnl'] <= 0]
            long_win_rate = len(long_wins) / len(long_exits_df) if len(long_exits_df) > 0 else 0
            
            # 롱 포지션 손익비
            long_profit = long_wins['pnl'].sum() if not long_wins.empty else 0
            long_loss = abs(long_losses['pnl'].sum()) if not long_losses.empty else 0
            long_profit_factor = calculate_profit_factor(long_profit, long_loss)
            
            # 롱 포지션 샤프 지수
            if not long_exits_df.empty:
                long_returns = long_exits_df['pnl'].values / args.initial_capital
                long_sharpe = calculate_sharpe_ratio(long_returns)
            else:
                long_sharpe = 0
                
            print(f"\n롱 포지션 승률: {long_win_rate * 100:.2f}% ({len(long_wins)}/{len(long_exits_df)})")
            print(f"롱 포지션 총 수익: {long_profit:.2f} USDT")
            print(f"롱 포지션 손익비: {long_profit_factor:.2f}")
            print(f"롱 포지션 샤프 지수: {long_sharpe:.2f}")
        
        # 숏 포지션 승률
        if short_exits:
            short_exits_df = pd.DataFrame(short_exits)
            short_wins = short_exits_df[short_exits_df['pnl'] > 0]
            short_losses = short_exits_df[short_exits_df['pnl'] <= 0]
            short_win_rate = len(short_wins) / len(short_exits_df) if len(short_exits_df) > 0 else 0
            
            # 숏 포지션 손익비
            short_profit = short_wins['pnl'].sum() if not short_wins.empty else 0
            short_loss = abs(short_losses['pnl'].sum()) if not short_losses.empty else 0
            short_profit_factor = calculate_profit_factor(short_profit, short_loss)
            
            # 숏 포지션 샤프 지수
            if not short_exits_df.empty:
                short_returns = short_exits_df['pnl'].values / args.initial_capital
                short_sharpe = calculate_sharpe_ratio(short_returns)
            else:
                short_sharpe = 0
                
            print(f"\n숏 포지션 승률: {short_win_rate * 100:.2f}% ({len(short_wins)}/{len(short_exits_df)})")
            print(f"숏 포지션 총 수익: {short_profit:.2f} USDT")
            print(f"숏 포지션 손익비: {short_profit_factor:.2f}")
            print(f"숏 포지션 샤프 지수: {short_sharpe:.2f}")
        
        # 청산 이유 분석
        exit_reasons = exit_trades['reason'].value_counts()
        print("\n청산 이유 분석:")
        for reason, count in exit_reasons.items():
            print(f"- {reason}: {count}개 ({count/len(exit_trades)*100:.1f}%)")
    
    # 결과 시각화
    strategy.plot_results(results)
    
    # 매매 내역 저장
    trades_file = os.path.join(args.data_dir, f"trades_{args.exchange}_{args.symbol.replace('/', '_')}_{args.timeframe}_{filename_suffix}.csv")
    results['trades'].to_csv(trades_file)
    print(f"매매 내역이 저장되었습니다: {trades_file}")

if __name__ == "__main__":
    main() 