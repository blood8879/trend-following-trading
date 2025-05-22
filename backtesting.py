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

def get_user_input():
    """대화형으로 사용자 입력을 받습니다."""
    print("\n==== 비트코인 선물시장 트렌드 팔로잉 전략 백테스팅 ====\n")
    
    # 시간프레임 설정
    valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
    timeframe = ""
    while timeframe not in valid_timeframes:
        timeframe = input("백테스팅할 시간봉을 설정해주세요(1m, 5m, 15m, 30m, 1h, 4h, 1d): ")
        if timeframe not in valid_timeframes:
            print(f"올바른 시간프레임을 입력해주세요. 가능한 값: {', '.join(valid_timeframes)}")
    
    # 시작일 설정
    start_date_str = ""
    while True:
        start_date_str = input("백테스트 시작일을 설정해주세요(YYYYMMDD): ")
        try:
            start_date = datetime.strptime(start_date_str, "%Y%m%d")
            break
        except ValueError:
            print("올바른 날짜 형식(YYYYMMDD)으로 입력해주세요.")
    
    # 종료일 설정
    end_date_str = ""
    while True:
        end_date_str = input("백테스트 종료일을 설정해주세요(YYYYMMDD): ")
        try:
            end_date = datetime.strptime(end_date_str, "%Y%m%d")
            if end_date < start_date:
                print("종료일은 시작일보다 이후여야 합니다.")
                continue
            break
        except ValueError:
            print("올바른 날짜 형식(YYYYMMDD)으로 입력해주세요.")
    
    # 레버리지 설정
    leverage = 0
    while leverage <= 0 or leverage > 10:
        try:
            leverage = int(input("레버리지를 설정해주세요(1~10): "))
            if leverage <= 0 or leverage > 10:
                print("레버리지는 1에서 10 사이의 값이어야 합니다.")
        except ValueError:
            print("숫자를 입력해주세요.")
    
    # 리스크 비율 설정
    risk_percentage = 0
    while risk_percentage <= 0 or risk_percentage > 0.1:
        try:
            risk_percentage = float(input("거래당 리스크 비율을 설정해주세요(0.01~0.1, 0.01은 1%): "))
            if risk_percentage <= 0 or risk_percentage > 0.1:
                print("리스크 비율은 0.01에서 0.1 사이의 값이어야 합니다.")
        except ValueError:
            print("숫자를 입력해주세요.")
    
    # 초기 자본금 설정
    initial_capital = 0
    while initial_capital <= 0:
        try:
            initial_capital = float(input("초기 자본금을 설정해주세요(USDT): "))
            if initial_capital <= 0:
                print("초기 자본금은 0보다 커야 합니다.")
        except ValueError:
            print("숫자를 입력해주세요.")
    
    # 저장된 데이터 사용 여부
    use_saved_data = ""
    while use_saved_data.lower() not in ["y", "n"]:
        use_saved_data = input("저장된 데이터가 있다면 사용하시겠습니까? (y/n): ")
    
    # 데이터 저장 여부
    save_data = ""
    while save_data.lower() not in ["y", "n"]:
        save_data = input("백테스트 후 데이터를 저장하시겠습니까? (y/n): ")
    
    # 거래소 설정
    exchange = input("사용할 거래소를 입력해주세요(기본값: binance): ") or "binance"
    
    # 심볼 설정
    symbol = input("거래할 심볼을 입력해주세요(기본값: BTC/USDT): ") or "BTC/USDT"
    
    return {
        "timeframe": timeframe,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "leverage": leverage,
        "risk_percentage": risk_percentage,
        "initial_capital": initial_capital,
        "use_saved_data": use_saved_data.lower() == "y",
        "save_data": save_data.lower() == "y",
        "exchange": exchange,
        "symbol": symbol,
        "data_dir": "data",
        "sideways_lookback": 5,
        "sideways_threshold": 0.1,
        "breakout_lookback": 3,
        "limit": 1000
    }

def main():
    # 명령줄 인자가 있으면 argparse로 처리, 없으면 대화형으로 입력 받기
    if len(os.sys.argv) > 1:
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
        args_dict = vars(args)
    else:
        args_dict = get_user_input()
    
    # 시작 날짜와 종료 날짜 설정
    start_date = datetime.strptime(args_dict["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(args_dict["end_date"], "%Y-%m-%d")
    print(f"\n백테스트 시작 날짜: {start_date.strftime('%Y-%m-%d')}")
    print(f"백테스트 종료 날짜: {end_date.strftime('%Y-%m-%d')}")
    print(f"선택한 시간프레임: {args_dict['timeframe']}")
    print(f"레버리지: {args_dict['leverage']}배")
    print(f"리스크 비율: {args_dict['risk_percentage'] * 100:.1f}%")
    print(f"초기 자본금: {args_dict['initial_capital']} USDT")
    
    # 데이터 디렉토리 생성
    data_dir = args_dict["data_dir"]
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # 전략 인스턴스 생성
    strategy = TrendFollowingStrategy(
        initial_capital=args_dict["initial_capital"],
        risk_percentage=args_dict["risk_percentage"],
        leverage=args_dict["leverage"]
    )
    
    # 파일명 생성
    exchange = args_dict["exchange"]
    symbol = args_dict["symbol"]
    timeframe = args_dict["timeframe"]
    filename_suffix = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    data_file = os.path.join(data_dir, f"{exchange}_{symbol.replace('/', '_')}_{timeframe}_{filename_suffix}.csv")
    
    use_saved_data = args_dict["use_saved_data"]
    if use_saved_data and os.path.exists(data_file):
        print(f"저장된 데이터를 불러옵니다: {data_file}")
        data = pd.read_csv(data_file)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
    else:
        print(f"{exchange}에서 {symbol} {timeframe} 데이터를 가져옵니다 ({args_dict['start_date']} ~ {args_dict['end_date']})...")
        
        # 시작 시간 계산
        start_time = int(start_date.timestamp() * 1000)
        end_time = int(end_date.timestamp() * 1000)
        
        # CCXT를 통해 데이터 가져오기
        data = strategy.fetch_data(
            exchange_id=exchange,
            symbol=symbol,
            timeframe=timeframe,
            since=start_time,
            until=end_time,
            limit=args_dict["limit"]
        )
        
        # 데이터 저장
        if args_dict["save_data"]:
            print(f"데이터를 저장합니다: {data_file}")
            data.reset_index().to_csv(data_file, index=False)
    
    print(f"데이터 로드 완료: {len(data)} 캔들")
    print(f"기간: {data.index[0]} ~ {data.index[-1]}")
    
    # 전략 파라미터 수정
    sideways_lookback = args_dict["sideways_lookback"]
    sideways_threshold = args_dict["sideways_threshold"]
    breakout_lookback = args_dict["breakout_lookback"]
    
    strategy.detect_sideways = lambda data, lookback=sideways_lookback, threshold=sideways_threshold: \
        TrendFollowingStrategy.detect_sideways(strategy, data, lookback, threshold)
    
    strategy.identify_range_breakout = lambda data, lookback=breakout_lookback: \
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
                long_returns = long_exits_df['pnl'].values / args_dict["initial_capital"]
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
                short_returns = short_exits_df['pnl'].values / args_dict["initial_capital"]
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
    trades_file = os.path.join(data_dir, f"trades_{exchange}_{symbol.replace('/', '_')}_{timeframe}_{filename_suffix}.csv")
    results['trades'].to_csv(trades_file)
    print(f"매매 내역이 저장되었습니다: {trades_file}")

if __name__ == "__main__":
    main() 

## 백테스팅 실행 방법
# python backtesting.py --start_date 2023-01-01 --end_date 2025-05-21 --limit 1000 --sideways_lookback 5 --sideways_threshold 0.1 --breakout_lookback 3 --use_saved_data --save_data --data_dir data
