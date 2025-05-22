import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ccxt
import os
from datetime import datetime, timedelta
# 한글 폰트 설정을 위한 폰트 매니저 추가
import matplotlib.font_manager as fm
import time

class TrendFollowingStrategy:
    def __init__(self, initial_capital=10000, risk_percentage=0.01, leverage=3):
        """
        비트코인 선물시장 트렌드 팔로잉 전략 구현
        
        Args:
            initial_capital (float): 초기 자본금 (USDT)
            risk_percentage (float): 거래당 허용 리스크 비율 (0.01 = 1%)
            leverage (int): 사용할 레버리지 (최대 3배)
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.risk_percentage = risk_percentage
        self.leverage = min(leverage, 3)  # 최대 3배로 제한
        
        # 포지션 관련 정보
        self.position = 0  # 0: 포지션 없음, 1: 롱, -1: 숏
        self.entry_price = 0
        self.position_size = 0
        self.stop_loss = 0
        
        # 거래 기록
        self.trades = []
        
        # 백테스팅 결과 저장
        self.equity_curve = []
        self.drawdowns = []
        self.current_drawdown = 0
        self.max_drawdown = 0
        self.peak_capital = initial_capital
        
        # 동적 파라미터 조정을 위한 변수
        self.market_volatility = 0
        self.last_adjustment_time = None
        self.adjustment_period = 20  # 파라미터 조정 주기 (캔들 수)
        
    def calculate_ema(self, data, period):
        """지수이동평균(EMA) 계산"""
        return data['close'].ewm(span=period, adjust=False).mean()
    
    def calculate_atr(self, data, period=14):
        """평균 실제 범위(ATR) 계산"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        return true_range.rolling(period).mean()
    
    def adjust_parameters_based_on_market(self, data, current_idx):
        """
        시장 상황에 따라 파라미터 동적 조정
        
        Args:
            data (pandas.DataFrame): OHLCV 데이터
            current_idx (int): 현재 인덱스
            
        Returns:
            dict: 조정된 파라미터
        """
        # 정해진 주기마다 파라미터 조정
        if self.last_adjustment_time is None or current_idx - self.last_adjustment_time >= self.adjustment_period:
            self.last_adjustment_time = current_idx
            
            # 최근 데이터로 ATR 계산하여 변동성 측정
            recent_data = data.iloc[max(0, current_idx-30):current_idx+1]
            if len(recent_data) > 14:  # ATR 계산에 필요한 최소 데이터
                atr = self.calculate_atr(recent_data)
                self.market_volatility = atr.iloc[-1] / recent_data['close'].iloc[-1]
            
            # 변동성에 따라 파라미터 조정
            sideways_threshold = 0.02  # 기본값
            breakout_lookback = 10     # 기본값
            
            # 변동성이 높을 때 (빠르게 대응)
            if self.market_volatility > 0.03:
                sideways_threshold = 0.08  # 횡보 감지 임계값 증가
                breakout_lookback = 3      # 더 짧은 기간으로 돌파 감지
                risk_percentage = min(0.015, self.risk_percentage * 1.2)  # 리스크 소폭 증가
            # 변동성이 중간일 때
            elif self.market_volatility > 0.015:
                sideways_threshold = 0.05
                breakout_lookback = 5
                risk_percentage = self.risk_percentage  # 기본 리스크 유지
            # 변동성이 낮을 때 (보수적으로 대응)
            else:
                sideways_threshold = 0.03
                breakout_lookback = 8
                risk_percentage = max(0.007, self.risk_percentage * 0.8)  # 리스크 감소
            
            return {
                'sideways_threshold': sideways_threshold,
                'breakout_lookback': breakout_lookback,
                'risk_percentage': risk_percentage
            }
        
        return None
    
    def detect_sideways(self, data, lookback=5, threshold=0.02):
        """
        횡보 구간 식별
        
        Args:
            data (pandas.DataFrame): OHLCV 데이터
            lookback (int): 확인할 기간
            threshold (float): 횡보 구간으로 판단할 고가-저가 범위 비율
            
        Returns:
            bool: 횡보 구간 여부
        """
        if len(data) < lookback:
            return False
        
        recent_data = data.iloc[-lookback:]
        highest = recent_data['high'].max()
        lowest = recent_data['low'].min()
        
        # 고가와 저가의 차이가 threshold 이내면 횡보 구간으로 판단
        price_range = (highest - lowest) / lowest
        return price_range < threshold
    
    def identify_range_breakout(self, data, lookback=10):
        """
        횡보 구간 돌파 식별
        
        Args:
            data (pandas.DataFrame): OHLCV 데이터
            lookback (int): 확인할 기간
            
        Returns:
            int: 1 (상방 돌파), -1 (하방 돌파), 0 (돌파 없음)
        """
        if len(data) < lookback + 2:
            return 0
        
        # 횡보 구간의 고가와 저가 설정
        range_data = data.iloc[-lookback-1:-1]
        range_high = range_data['high'].max()
        range_low = range_data['low'].min()
        
        # 최신 캔들
        current_candle = data.iloc[-1]
        
        # 상방 돌파 확인
        if current_candle['close'] > range_high:
            return 1
        
        # 하방 돌파 확인
        elif current_candle['close'] < range_low:
            return -1
        
        return 0
    
    def check_ema_alignment(self, ema10, ema20, ema50):
        """
        EMA 정배열/역배열 확인
        
        Args:
            ema10 (float): 10일 EMA 값
            ema20 (float): 20일 EMA 값
            ema50 (float): 50일 EMA 값
            
        Returns:
            int: 1 (정배열), -1 (역배열), 0 (불명확)
        """
        # 정배열 확인 (10일 > 20일 > 50일)
        if ema10 > ema20 > ema50:
            return 1
        
        # 역배열 확인 (10일 < 20일 < 50일)
        elif ema10 < ema20 < ema50:
            return -1
        
        # 조건 완화: 10일과 20일 EMA만으로도 트렌드 판단
        elif ema10 > ema20:
            return 1
        elif ema10 < ema20:
            return -1
        
        # 불명확한 상태
        return 0
    
    def check_adjustment(self, current_price, ema10, ema20, ema50, trend):
        """
        조정 구간 확인
        
        Args:
            current_price (float): 현재 가격
            ema10 (float): 10일 EMA 값
            ema20 (float): 20일 EMA 값
            ema50 (float): 50일 EMA 값
            trend (int): 트렌드 방향 (1: 상승, -1: 하락)
            
        Returns:
            bool: 조정 구간 여부
        """
        # 조건 완화: 상승 트렌드에서는 50일 EMA 조건 제외
        if trend == 1:  # 상승 트렌드
            # 가격이 10일 또는 20일 EMA를 이탈했으면 조정 구간으로 판단
            return (current_price < ema10 or current_price < ema20)
        
        # 조건 완화: 하락 트렌드에서는 50일 EMA 조건 제외
        elif trend == -1:  # 하락 트렌드
            # 가격이 10일 또는 20일 EMA를 상향 돌파했으면 조정 구간으로 판단
            return (current_price > ema10 or current_price > ema20)
        
        return False
    
    def calculate_position_size(self, entry_price, stop_loss_price):
        """
        포지션 사이즈 계산 (리스크 기반)
        
        Args:
            entry_price (float): 진입 가격
            stop_loss_price (float): 손절 가격
            
        Returns:
            float: 포지션 사이즈 (계약 수량)
        """
        if entry_price == stop_loss_price:
            return 0
            
        # 손실 허용 금액 계산
        risk_amount = self.capital * self.risk_percentage
        
        # 손실 비율 계산
        loss_percentage = abs(entry_price - stop_loss_price) / entry_price
        
        # 레버리지를 고려한 포지션 사이즈 계산
        position_size = (risk_amount / loss_percentage) * self.leverage / entry_price
        
        return position_size
    
    def update_equity(self, current_price, timestamp):
        """
        자본금 업데이트 및 Drawdown 추적
        
        Args:
            current_price (float): 현재 가격
            timestamp (datetime): 현재 타임스탬프
        """
        unrealized_pnl = 0
        
        # 포지션이 있는 경우 미실현 손익 계산
        if self.position != 0:
            price_change = current_price - self.entry_price
            unrealized_pnl = price_change * self.position_size * self.position
        
        # 현재 자본금 계산
        current_equity = self.capital + unrealized_pnl
        
        # 최고 자본금 업데이트 및 Drawdown 계산
        if current_equity > self.peak_capital:
            self.peak_capital = current_equity
            self.current_drawdown = 0
        else:
            self.current_drawdown = (self.peak_capital - current_equity) / self.peak_capital
            self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        
        # 자본금 곡선에 기록
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': current_equity,
            'drawdown': self.current_drawdown
        })
        
        # Drawdown 기록
        self.drawdowns.append(self.current_drawdown)
    
    def enter_position(self, direction, price, timestamp, stop_loss_price):
        """
        포지션 진입
        
        Args:
            direction (int): 포지션 방향 (1: 롱, -1: 숏)
            price (float): 진입 가격
            timestamp (datetime): 진입 시간
            stop_loss_price (float): 손절 가격
        """
        # 이미 포지션이 있는 경우 무시
        if self.position != 0:
            return
        
        # 포지션 사이즈 계산
        size = self.calculate_position_size(price, stop_loss_price)
        
        # 포지션 정보 업데이트
        self.position = direction
        self.entry_price = price
        self.position_size = size
        self.stop_loss = stop_loss_price
        
        # 거래 기록 추가
        self.trades.append({
            'type': 'entry',
            'direction': 'long' if direction == 1 else 'short',
            'price': price,
            'size': size,
            'timestamp': timestamp,
            'stop_loss': stop_loss_price
        })
    
    def exit_position(self, price, timestamp, reason=""):
        """
        포지션 청산
        
        Args:
            price (float): 청산 가격
            timestamp (datetime): 청산 시간
            reason (str): 청산 이유
        """
        # 포지션이 없는 경우 무시
        if self.position == 0:
            return
        
        # 손익 계산
        price_change = (price - self.entry_price) * self.position
        pnl = price_change * self.position_size
        
        # 자본금 업데이트
        self.capital += pnl
        
        # 거래 기록 추가
        self.trades.append({
            'type': 'exit',
            'price': price,
            'pnl': pnl,
            'timestamp': timestamp,
            'reason': reason
        })
        
        # 포지션 정보 초기화
        self.position = 0
        self.entry_price = 0
        self.position_size = 0
        self.stop_loss = 0
    
    def check_stop_loss(self, current_price, timestamp):
        """
        손절 조건 확인
        
        Args:
            current_price (float): 현재 가격
            timestamp (datetime): 현재 시간
            
        Returns:
            bool: 손절 실행 여부
        """
        if self.position == 0:
            return False
        
        # 롱 포지션 손절
        if self.position == 1 and current_price <= self.stop_loss:
            self.exit_position(current_price, timestamp, "stop_loss")
            return True
        
        # 숏 포지션 손절
        elif self.position == -1 and current_price >= self.stop_loss:
            self.exit_position(current_price, timestamp, "stop_loss")
            return True
        
        return False
    
    def check_take_profit(self, current_price, timestamp, ema10, ema20):
        """
        익절 조건 확인
        
        Args:
            current_price (float): 현재 가격
            timestamp (datetime): 현재 시간
            ema10 (float): 10일 EMA 값
            ema20 (float): 20일 EMA 값
            
        Returns:
            bool: 익절 실행 여부
        """
        if self.position == 0:
            return False
        
        # 포지션 방향과 반대 방향으로 EMA 이탈 확인
        if self.position == 1:  # 롱 포지션
            # 10일 EMA 아래로 이탈
            if current_price < ema10:
                self.exit_position(current_price, timestamp, "tp_ema10")
                return True
            # 20일 EMA 아래로 이탈
            elif current_price < ema20:
                self.exit_position(current_price, timestamp, "tp_ema20")
                return True
                
        elif self.position == -1:  # 숏 포지션
            # 10일 EMA 위로 이탈
            if current_price > ema10:
                self.exit_position(current_price, timestamp, "tp_ema10")
                return True
            # 20일 EMA 위로 이탈
            elif current_price > ema20:
                self.exit_position(current_price, timestamp, "tp_ema20")
                return True
        
        return False
    
    def backtest(self, data):
        """
        백테스팅 실행
        
        Args:
            data (pandas.DataFrame): OHLCV 데이터 (timestamp, open, high, low, close, volume)
            
        Returns:
            dict: 백테스팅 결과
        """
        # EMA 계산
        data['ema10'] = self.calculate_ema(data, 10)
        data['ema20'] = self.calculate_ema(data, 20)
        data['ema50'] = self.calculate_ema(data, 50)
        
        # ATR 계산 (변동성 측정용)
        data['atr'] = self.calculate_atr(data)
        
        # 처음 50일은 스킵 (EMA 안정화)
        for i in range(50, len(data)):
            row = data.iloc[i]
            prev_row = data.iloc[i-1]
            
            timestamp = row.name if isinstance(row.name, datetime) else datetime.fromtimestamp(row.name / 1000)
            current_price = row['close']
            
            # 시장 상황에 따른 파라미터 동적 조정
            adjusted_params = self.adjust_parameters_based_on_market(data, i)
            if adjusted_params:
                sideways_threshold = adjusted_params['sideways_threshold']
                breakout_lookback = adjusted_params['breakout_lookback']
                self.risk_percentage = adjusted_params['risk_percentage']
            else:
                sideways_threshold = 0.1  # 기본값 더 완화
                breakout_lookback = 3     # 기본값 더 완화
            
            # EMA 값
            ema10 = row['ema10']
            ema20 = row['ema20']
            ema50 = row['ema50']
            
            # 손절 확인
            if self.check_stop_loss(current_price, timestamp):
                continue
            
            # 익절 확인
            if self.check_take_profit(current_price, timestamp, ema10, ema20):
                continue
            
            # EMA 정배열/역배열 확인 (더 약한 조건도 허용)
            ema_alignment = self.check_ema_alignment(ema10, ema20, ema50)
            
            # 포지션이 없는 경우 진입 조건 확인
            if self.position == 0:
                # 돌파 확인
                breakout = self.identify_range_breakout(data.iloc[i-10:i+1], lookback=breakout_lookback)
                
                # 롱 포지션 진입 조건 (매우 완화됨)
                if (ema10 > ema20 and breakout == 1):  # 단순히 10일 EMA가 20일 EMA보다 위에 있고 상방 돌파
                    # 손절가 설정 (돌파 캔들의 저점)
                    stop_loss_price = min(row['low'], prev_row['low'])
                    
                    # 진입
                    self.enter_position(1, current_price, timestamp, stop_loss_price)
                
                # 숏 포지션 진입 조건 (매우 완화됨)
                elif (ema10 < ema20 and breakout == -1):  # 단순히 10일 EMA가 20일 EMA보다 아래에 있고 하방 돌파
                    # 손절가 설정 (돌파 캔들의 고점)
                    stop_loss_price = max(row['high'], prev_row['high'])
                    
                    # 진입
                    self.enter_position(-1, current_price, timestamp, stop_loss_price)
            
            # 자본금 업데이트
            self.update_equity(current_price, timestamp)
        
        # 백테스팅 결과 계산
        return self.calculate_results()
    
    def calculate_results(self):
        """
        백테스팅 결과 계산
        
        Returns:
            dict: 백테스팅 결과
        """
        if not self.trades:
            return {
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'final_capital': self.capital,
                'equity_curve': pd.DataFrame(self.equity_curve),
                'trades': pd.DataFrame(self.trades)
            }
        
        # 거래 기록 DataFrame으로 변환
        trades_df = pd.DataFrame(self.trades)
        
        # 각 거래의 entry와 exit 매칭
        entry_trades = trades_df[trades_df['type'] == 'entry'].reset_index(drop=True)
        exit_trades = trades_df[trades_df['type'] == 'exit'].reset_index(drop=True)
        
        # 결과가 더 적은 쪽에 맞춤
        min_trades = min(len(entry_trades), len(exit_trades))
        entry_trades = entry_trades.iloc[:min_trades]
        exit_trades = exit_trades.iloc[:min_trades]
        
        # 승리/패배 거래 구분
        wins = exit_trades[exit_trades['pnl'] > 0]
        losses = exit_trades[exit_trades['pnl'] <= 0]
        
        # 승률 계산
        win_rate = len(wins) / len(exit_trades) if len(exit_trades) > 0 else 0
        
        # 손익비 계산
        total_profit = wins['pnl'].sum() if not wins.empty else 0
        total_loss = abs(losses['pnl'].sum()) if not losses.empty else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # 총 수익률
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        
        # 자본금 곡선 DataFrame으로 변환
        equity_curve_df = pd.DataFrame(self.equity_curve)
        
        return {
            'total_return': total_return,
            'total_trades': len(exit_trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown,
            'final_capital': self.capital,
            'equity_curve': equity_curve_df,
            'trades': trades_df
        }
    
    def plot_results(self, results):
        """
        백테스팅 결과 시각화
        
        Args:
            results (dict): 백테스팅 결과
        """
        if results['equity_curve'].empty:
            print("결과가 없습니다.")
            return
        
        # 한글 폰트 설정
        plt.rcParams['font.family'] = 'AppleGothic'  # MacOS용 기본 한글 폰트
        plt.rcParams['axes.unicode_minus'] = False   # 마이너스 기호 깨짐 방지
        
        # 플롯 설정
        plt.figure(figsize=(15, 10))
        
        # 자본금 곡선
        plt.subplot(2, 1, 1)
        plt.plot(results['equity_curve']['timestamp'], results['equity_curve']['equity'])
        plt.title('자본금 곡선', fontsize=16)
        plt.xlabel('시간')
        plt.ylabel('자본금 (USDT)')
        plt.grid(True)
        
        # Drawdown 곡선
        plt.subplot(2, 1, 2)
        plt.fill_between(results['equity_curve']['timestamp'], results['equity_curve']['drawdown'] * 100)
        plt.title('Drawdown', fontsize=16)
        plt.xlabel('시간')
        plt.ylabel('Drawdown (%)')
        plt.grid(True)
        
        plt.tight_layout()
        plt.show()
        
        # 결과 통계 출력
        print(f"총 수익률: {results['total_return'] * 100:.2f}%")
        print(f"총 거래 횟수: {results['total_trades']}")
        print(f"승률: {results['win_rate'] * 100:.2f}%")
        print(f"손익비: {results['profit_factor']:.2f}")
        print(f"최대 낙폭: {results['max_drawdown'] * 100:.2f}%")
        print(f"최종 자본금: {results['final_capital']:.2f} USDT")
    
    def fetch_data(self, exchange_id='binance', symbol='BTC/USDT', timeframe='4h', since=None, until=None, limit=1000):
        """
        거래소에서 OHLCV 데이터 가져오기
        
        Args:
            exchange_id (str): 거래소 ID (예: 'binance', 'bybit')
            symbol (str): 심볼 (예: 'BTC/USDT')
            timeframe (str): 시간프레임 (예: '1h', '4h', '1d')
            since (int): 시작 타임스탬프 (밀리초)
            until (int): 종료 타임스탬프 (밀리초)
            limit (int): 각 요청당 가져올 캔들 개수
            
        Returns:
            pandas.DataFrame: OHLCV 데이터
        """
        # 거래소 인스턴스 생성
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True,
        })
        
        # 기본 시작 시간 설정 (없는 경우 현재 시간부터 limit*timeframe 이전)
        if since is None:
            timeframe_in_seconds = exchange.parse_timeframe(timeframe)
            since = exchange.milliseconds() - (limit * timeframe_in_seconds * 1000)
        
        all_ohlcv = []
        now = exchange.milliseconds() if until is None else until
        
        # API 제한을 고려해 여러 번 나눠서 데이터 가져오기
        current_since = since
        timeframe_in_seconds = exchange.parse_timeframe(timeframe)
        
        # 예상되는 총 캔들 수 계산
        estimated_candles = (now - since) / (timeframe_in_seconds * 1000)
        estimated_requests = min(30, max(5, int(estimated_candles / limit) + 1))  # 최소 5회, 최대 30회 요청
        
        print(f"지정된 기간: {datetime.fromtimestamp(since/1000)} ~ {datetime.fromtimestamp(now/1000)}")
        print(f"예상 캔들 수: 약 {int(estimated_candles)}개")
        print(f"요청 계획: 최대 {estimated_requests}회 API 요청 (각 요청당 최대 {limit}개 캔들)")
        
        # 데이터를 여러 번 나눠서 가져오기 (최대 예상 요청 수 또는 현재 시간까지)
        for i in range(estimated_requests):
            if current_since >= now:
                print(f"지정된 종료 시간에 도달했습니다. 데이터 수집 완료.")
                break
                
            # 진행률 표시
            progress = min(100, int((current_since - since) / (now - since) * 100)) if now > since else 0
            print(f"데이터 요청 {i+1}/{estimated_requests} ({progress}% 진행): {datetime.fromtimestamp(current_since/1000).strftime('%Y-%m-%d %H:%M:%S')} 부터")
            
            try:
                # API 호출로 데이터 가져오기
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, current_since, limit)
                
                if len(ohlcv) == 0:
                    print("더 이상 가져올 데이터가 없습니다.")
                    break
                
                # 중복 제거를 위해 이미 가져온 타임스탬프 체크
                if all_ohlcv and ohlcv[0][0] == all_ohlcv[-1][0]:
                    ohlcv = ohlcv[1:]  # 첫 번째 캔들이 중복이면 제거
                
                all_ohlcv.extend(ohlcv)
                print(f"  - {len(ohlcv)}개 캔들 추가 (누적: {len(all_ohlcv)}개)")
                
                # 다음 시작 시간 설정 (마지막 캔들 이후)
                if ohlcv:
                    current_since = ohlcv[-1][0] + timeframe_in_seconds * 1000
                else:
                    break
                
                # API 속도 제한 방지를 위한 대기
                time.sleep(1.5)  # 좀 더 긴 대기 시간으로 조정
                
            except Exception as e:
                print(f"데이터 가져오기 오류: {e}")
                # 오류 발생 시 잠시 대기 후 재시도
                time.sleep(5)
                continue
        
        if not all_ohlcv:
            raise Exception("데이터를 가져올 수 없습니다.")
        
        # DataFrame으로 변환
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df.drop_duplicates()  # 중복 제거
        
        # 지정된 기간으로 필터링
        if since is not None:
            since_dt = pd.to_datetime(since, unit='ms')
            df = df[df.index >= since_dt]
        
        if until is not None:
            until_dt = pd.to_datetime(until, unit='ms')
            df = df[df.index <= until_dt]
        
        # 결과 요약
        if not df.empty:
            print(f"\n데이터 가져오기 완료:")
            print(f"가져온 총 캔들 수: {len(df)}개")
            print(f"기간: {df.index[0]} ~ {df.index[-1]}")
            print(f"시간프레임: {timeframe}")
        else:
            print("가져온 데이터가 없습니다.")
        
        return df 