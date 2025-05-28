#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from strategy import TrendFollowingStrategy
from database import TradingDatabase

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BinanceAutoTrader:
    """
    Binance 자동매매 클래스
    """
    def __init__(self, api_key, api_secret, symbol, timeframe='4h', initial_capital=None, max_trade_amount=None, test_mode=False):
        """
        초기화
        
        Args:
            api_key (str): Binance API 키
            api_secret (str): Binance API 시크릿
            symbol (str): 거래 심볼 (예: 'BTCUSDT')
            timeframe (str): 캔들 주기 (예: '1h', '4h', '1d')
            initial_capital (float): 초기 자본금 (None이면 계정에서 가져옴)
            max_trade_amount (float): 거래당 최대 금액 (USDT)
            test_mode (bool): 테스트 모드 여부 (True면 실제 주문 실행 안함)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.timeframe = timeframe
        self.test_mode = test_mode
        
        # 데이터베이스 초기화
        self.db = TradingDatabase()
        
        # 테스트 모드 안내
        if self.test_mode:
            logger.warning("테스트 모드로 실행 중입니다. 실제 주문은 실행되지 않습니다.")
        
        # Binance 클라이언트 초기화
        self.client = Client(api_key, api_secret)
        
        # 계정 정보 가져오기
        account_info = self.client.get_account()
        
        # 기본 설정
        self.quote_asset = self.symbol[-4:] if self.symbol.endswith('USDT') else self.symbol[-3:]
        self.base_asset = self.symbol.replace(self.quote_asset, '')
        
        # 초기 자본금 설정
        if initial_capital is None:
            if self.test_mode:
                # 테스트 모드에서는 설정 파일의 test_initial_capital 사용 또는 기본값
                self.initial_capital = 10000  # 기본값
            else:
                # 실제 계정 잔고 사용
                # USDT 잔고 확인
                for balance in account_info['balances']:
                    if balance['asset'] == self.quote_asset:
                        self.initial_capital = float(balance['free'])
                        break
        else:
            self.initial_capital = initial_capital
        
        # 최대 거래 금액 설정
        self.max_trade_amount = max_trade_amount
        if max_trade_amount:
            logger.info(f"거래당 최대 금액 설정: {max_trade_amount} {self.quote_asset}")
        
        logger.info(f"초기 자본금: {self.initial_capital} {self.quote_asset}")
        
        # 전략 초기화
        self.strategy = TrendFollowingStrategy(
            initial_capital=self.initial_capital,
            risk_percentage=0.01,  # 거래당 리스크 비율 (1%)
            leverage=1  # 레버리지 (현물 거래는 1)
        )
        
        # 거래 심볼 정보 가져오기
        self.symbol_info = self.client.get_symbol_info(self.symbol)
        
        # 수량 정밀도 (소수점 자릿수)
        self.quantity_precision = self._get_precision_from_step_size()
        
        # 가격 정밀도 (소수점 자릿수)
        self.price_precision = self._get_price_precision()
        
        # 최소 주문 금액
        self.min_notional = self._get_min_notional()
        
        # 마지막 체크 시간
        self.last_check_time = None
        
        # 마지막 거래 시간 (과도한 거래 방지)
        self.last_trade_time = None
        self.trade_cooldown = 4 * 3600  # 4시간 (초)
        
        # 현재 시장 상태
        self.current_market_state = {
            'position': 0,  # 0: 포지션 없음, 1: 롱, -1: 숏
            'entry_price': 0,
            'stop_loss': 0,
            'secondary_stop_loss': 0,
            'position_size': 0
        }
        
        # 안전 설정 확인
        self._check_security_settings()
        
        logger.info(f"BinanceAutoTrader 초기화 완료 - 심볼: {self.symbol}, 타임프레임: {self.timeframe}")
    
    def _check_security_settings(self):
        """API 키 권한 및 안전 설정 확인"""
        try:
            # API 키 권한 확인
            api_permissions = self.client.get_api_key_permission()
            
            # 필요한 권한 확인
            has_read = api_permissions.get('enableReading', False)
            has_spot = api_permissions.get('enableSpotAndMarginTrading', False)
            
            if not has_read:
                logger.warning("API 키에 읽기 권한이 없습니다!")
            
            if not has_spot:
                logger.warning("API 키에 현물 거래 권한이 없습니다!")
            
            # 인출 권한 확인 (보안을 위해 인출 권한이 없어야 함)
            has_withdraw = api_permissions.get('enableWithdrawals', False)
            if has_withdraw:
                logger.warning("API 키에 인출 권한이 있습니다. 보안을 위해 인출 권한을 제거하세요!")
            
            logger.info("API 키 권한 확인 완료")
            
        except Exception as e:
            logger.error(f"API 키 권한 확인 중 오류: {e}")
    
    def _get_price_precision(self):
        """가격 정밀도(소수점 자릿수) 가져오기"""
        for filter in self.symbol_info['filters']:
            if filter['filterType'] == 'PRICE_FILTER':
                tick_size = float(filter['tickSize'])
                precision = 0
                while tick_size < 1:
                    tick_size *= 10
                    precision += 1
                return precision
        return 2  # 기본값
    
    def _get_min_notional(self):
        """최소 주문 금액 가져오기"""
        for filter in self.symbol_info['filters']:
            if filter['filterType'] == 'MIN_NOTIONAL':
                return float(filter['minNotional'])
        return 10.0  # 기본값
    
    def _get_precision_from_step_size(self):
        """
        심볼 정보에서 수량 정밀도(소수점 자릿수) 가져오기
        """
        for filter in self.symbol_info['filters']:
            if filter['filterType'] == 'LOT_SIZE':
                step_size = float(filter['stepSize'])
                precision = 0
                while step_size < 1:
                    step_size *= 10
                    precision += 1
                return precision
        return 8  # 기본값
    
    def format_quantity(self, quantity):
        """
        수량을 심볼 정밀도에 맞게 포맷팅
        """
        return f"{quantity:.{self.quantity_precision}f}"
    
    def fetch_latest_data(self, limit=100):
        """
        최신 OHLCV 데이터 가져오기
        
        Args:
            limit (int): 가져올 캔들 수
            
        Returns:
            pandas.DataFrame: OHLCV 데이터
        """
        try:
            # Binance API에서 캔들 데이터 가져오기
            klines = self.client.get_klines(
                symbol=self.symbol,
                interval=self.timeframe,
                limit=limit
            )
            
            # 데이터프레임으로 변환
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 타입 변환
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # 타임스탬프를 인덱스로 설정
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"{limit}개의 {self.timeframe} 캔들 데이터를 가져왔습니다.")
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Binance API 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"데이터 가져오기 오류: {e}")
            return None
    
    def place_market_order(self, side, quantity):
        """
        시장가 주문 실행
        
        Args:
            side (str): 'BUY' 또는 'SELL'
            quantity (float): 주문 수량
            
        Returns:
            dict: 주문 결과
        """
        try:
            # 최소 수량 확인
            if quantity <= 0:
                logger.error(f"유효하지 않은 주문 수량: {quantity}")
                return None
            
            # 최소 주문 금액 확인
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            order_value = quantity * current_price
            
            if order_value < self.min_notional:
                logger.error(f"주문 금액({order_value:.2f})이 최소 주문 금액({self.min_notional:.2f})보다 작습니다.")
                return None
            
            # 최대 거래 금액 확인 (설정된 경우)
            if self.max_trade_amount and side == 'BUY' and order_value > self.max_trade_amount:
                logger.warning(f"주문 금액({order_value:.2f})이 최대 거래 금액({self.max_trade_amount:.2f})을 초과합니다. 수량을 조정합니다.")
                quantity = self.max_trade_amount / current_price
            
            # 과도한 거래 방지 (쿨다운 확인)
            current_time = time.time()
            if self.last_trade_time and side == 'BUY' and (current_time - self.last_trade_time) < self.trade_cooldown:
                remaining_time = self.trade_cooldown - (current_time - self.last_trade_time)
                logger.warning(f"거래 쿨다운 중입니다. {remaining_time/60:.1f}분 후에 다시 시도하세요.")
                return None
            
            formatted_quantity = self.format_quantity(quantity)
            logger.info(f"{side} 시장가 주문 - 수량: {formatted_quantity} {self.base_asset}")
            
            # 테스트 모드인 경우 실제 주문 실행 안함
            if self.test_mode:
                logger.info("테스트 모드: 실제 주문이 실행되지 않았습니다.")
                
                # 테스트 주문 응답 생성
                test_order = {
                    'symbol': self.symbol,
                    'orderId': 0,
                    'clientOrderId': 'test',
                    'transactTime': int(time.time() * 1000),
                    'price': '0.00',
                    'origQty': formatted_quantity,
                    'executedQty': formatted_quantity,
                    'status': 'FILLED',
                    'timeInForce': 'GTC',
                    'type': 'MARKET',
                    'side': side
                }
                
                if side == 'BUY':
                    self.last_trade_time = current_time
                
                # 테스트 모드에서도 데이터베이스에 매매 내역 저장
                self._save_trade_to_db(test_order, side, quantity, current_price)
                
                return test_order
            
            # 실제 주문 실행
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type='MARKET',
                quantity=formatted_quantity
            )
            
            logger.info(f"주문 성공 - ID: {order['orderId']}, 상태: {order['status']}")
            
            # 매수 주문인 경우 마지막 거래 시간 업데이트
            if side == 'BUY':
                self.last_trade_time = current_time
            
            # 데이터베이스에 매매 내역 저장
            self._save_trade_to_db(order, side, quantity, current_price)
            
            return order
            
        except BinanceAPIException as e:
            logger.error(f"주문 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"주문 실행 중 오류 발생: {e}")
            return None
    
    def _save_trade_to_db(self, order, side, quantity, price):
        """매매 내역을 데이터베이스에 저장"""
        try:
            # 거래 타입 결정
            trade_type = 'ENTRY'
            exit_stage = 0
            
            if side == 'SELL':
                if self.strategy.sl_triggered:
                    trade_type = 'STOP_LOSS'
                else:
                    trade_type = 'EXIT'
                    exit_stage = self.strategy.exit_stage
            
            trade_data = {
                'timestamp': datetime.now(),
                'symbol': self.symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'total_value': quantity * price,
                'order_id': order.get('orderId') if order else None,
                'trade_type': trade_type,
                'exit_stage': exit_stage,
                'stop_loss_price': self.current_market_state.get('stop_loss'),
                'secondary_stop_loss_price': self.current_market_state.get('secondary_stop_loss'),
                'test_mode': self.test_mode,
                'notes': f"자동매매 - {trade_type}"
            }
            
            self.db.add_trade(trade_data)
            logger.info(f"매매 내역이 데이터베이스에 저장되었습니다: {side} {quantity} {self.symbol}")
            
        except Exception as e:
            logger.error(f"매매 내역 저장 중 오류: {e}")
    
    def update_market_state(self):
        """
        현재 시장 상태 업데이트 (포지션, 잔고 등)
        """
        try:
            # 계정 정보 가져오기
            account_info = self.client.get_account()
            
            # 자산 잔고 확인
            base_balance = 0
            quote_balance = 0
            
            for balance in account_info['balances']:
                if balance['asset'] == self.base_asset:
                    base_balance = float(balance['free'])
                elif balance['asset'] == self.quote_asset:
                    quote_balance = float(balance['free'])
            
            # 현재 가격 확인
            ticker = self.client.get_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            
            # 포지션 상태 업데이트
            if base_balance > 0.0001:  # 최소 보유량 이상이면 롱 포지션으로 간주
                self.current_market_state['position'] = 1
                self.current_market_state['position_size'] = base_balance
                
                # 마지막 매수 주문 찾기
                orders = self.client.get_all_orders(symbol=self.symbol, limit=10)
                buy_orders = [order for order in orders if order['side'] == 'BUY' and order['status'] == 'FILLED']
                
                if buy_orders:
                    last_buy = buy_orders[-1]
                    # 평균 매수가 계산
                    self.current_market_state['entry_price'] = float(last_buy['price'])
                else:
                    self.current_market_state['entry_price'] = current_price
                
                logger.info(f"롱 포지션 감지 - 수량: {base_balance} {self.base_asset}, 평균가: {self.current_market_state['entry_price']}")
            else:
                self.current_market_state['position'] = 0
                self.current_market_state['position_size'] = 0
                self.current_market_state['entry_price'] = 0
                logger.info(f"포지션 없음 - 보유 {self.quote_asset}: {quote_balance}")
            
            # 전략 객체의 포지션 정보도 업데이트
            self.strategy.position = self.current_market_state['position']
            self.strategy.position_size = self.current_market_state['position_size']
            self.strategy.entry_price = self.current_market_state['entry_price']
            
            # 데이터베이스에 포지션 상태 저장
            self._save_position_to_db(current_price, base_balance, quote_balance)
            
            return True
            
        except BinanceAPIException as e:
            logger.error(f"시장 상태 업데이트 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"시장 상태 업데이트 중 오류 발생: {e}")
            return False
    
    def _save_position_to_db(self, current_price, base_balance, quote_balance):
        """포지션 상태를 데이터베이스에 저장"""
        try:
            # 미실현 손익 계산
            unrealized_pnl = 0
            if self.current_market_state['position'] == 1 and self.current_market_state['entry_price'] > 0:
                unrealized_pnl = (current_price - self.current_market_state['entry_price']) * self.current_market_state['position_size']
            
            position_data = {
                'timestamp': datetime.now(),
                'symbol': self.symbol,
                'position': self.current_market_state['position'],
                'entry_price': self.current_market_state['entry_price'],
                'position_size': self.current_market_state['position_size'],
                'stop_loss': self.current_market_state.get('stop_loss'),
                'secondary_stop_loss': self.current_market_state.get('secondary_stop_loss'),
                'unrealized_pnl': unrealized_pnl,
                'current_price': current_price
            }
            
            self.db.update_position(position_data)
            
            # 계정 상태도 저장
            total_balance = base_balance * current_price + quote_balance
            
            account_data = {
                'timestamp': datetime.now(),
                'total_balance': total_balance,
                'available_balance': quote_balance,
                'base_asset_balance': base_balance,
                'quote_asset_balance': quote_balance,
                'total_pnl': unrealized_pnl,
                'win_rate': 0,  # 나중에 계산
                'total_trades': 0  # 나중에 계산
            }
            
            self.db.update_account_status(account_data)
            
        except Exception as e:
            logger.error(f"포지션 상태 저장 중 오류: {e}")
    
    def execute_strategy(self):
        """
        전략 실행 및 매매 신호 처리
        """
        try:
            # 최신 데이터 가져오기
            df = self.fetch_latest_data(limit=100)
            if df is None or df.empty:
                logger.error("데이터를 가져올 수 없습니다.")
                return False
            
            # 현재 시장 상태 업데이트
            self.update_market_state()
            
            # 현재 캔들 정보
            current_candle = df.iloc[-1]
            previous_candle = df.iloc[-2]
            current_price = float(current_candle['close'])
            
            # 현재 시장 변동성 확인
            current_volatility = abs(current_candle['high'] - current_candle['low']) / current_candle['low']
            
            # 변동성이 매우 높은 경우 경고
            if current_volatility > 0.05:  # 5% 이상 변동성
                logger.warning(f"현재 시장 변동성이 높습니다 ({current_volatility:.2%}). 매매 신호에 주의하세요.")
            
            # EMA 값 계산
            df['ema10'] = self.strategy.calculate_ema(df, 10)
            df['ema20'] = self.strategy.calculate_ema(df, 20)
            df['ema50'] = self.strategy.calculate_ema(df, 50)
            
            ema10 = df['ema10'].iloc[-1]
            ema20 = df['ema20'].iloc[-1]
            ema50 = df['ema50'].iloc[-1]
            
            # 시장 데이터를 데이터베이스에 저장
            self._save_market_data_to_db(current_candle, ema10, ema20, ema50)
            
            # 현재 타임스탬프
            current_timestamp = datetime.now()
            
            # 1. 포지션이 있는 경우 손절/익절 확인
            if self.current_market_state['position'] != 0:
                # 손절 확인
                if self.strategy.sl_triggered:
                    # 1차 손절이 이미 발생한 경우 2차 손절 확인
                    if self.current_market_state['position'] == 1:  # 롱 포지션
                        if current_price <= self.current_market_state['secondary_stop_loss']:
                            logger.info(f"2차 손절 발생 - 가격: {current_price}")
                            order = self.place_market_order('SELL', self.current_market_state['position_size'])
                            if order:
                                self.current_market_state['position'] = 0
                                self.strategy.position = 0
                                return True
                    elif self.current_market_state['position'] == -1:  # 숏 포지션 (현물에서는 발생하지 않음)
                        pass
                else:
                    # 1차 손절 확인
                    if self.current_market_state['position'] == 1:  # 롱 포지션
                        if current_price <= self.current_market_state['stop_loss']:
                            logger.info(f"1차 손절 발생 - 가격: {current_price}")
                            # 포지션의 절반만 청산
                            sell_quantity = self.current_market_state['position_size'] / 2
                            order = self.place_market_order('SELL', sell_quantity)
                            if order:
                                self.strategy.sl_triggered = True
                                self.current_market_state['position_size'] -= sell_quantity
                                return True
                
                # 익절 확인
                if self.current_market_state['position'] == 1:  # 롱 포지션
                    # 첫 번째 익절: 양봉 후 음봉 발생
                    if self.strategy.exit_stage == 0 and previous_candle['close'] > previous_candle['open'] and current_candle['close'] < current_candle['open']:
                        logger.info(f"1차 익절 발생 (음봉) - 가격: {current_price}")
                        sell_quantity = self.current_market_state['position_size'] / 3
                        order = self.place_market_order('SELL', sell_quantity)
                        if order:
                            self.strategy.exit_stage = 1
                            self.current_market_state['position_size'] -= sell_quantity
                            return True
                    
                    # 두 번째 익절: 10일 EMA 아래로 이탈
                    elif self.strategy.exit_stage < 2 and current_price < ema10:
                        logger.info(f"2차 익절 발생 (10일 EMA 이탈) - 가격: {current_price}")
                        sell_quantity = self.current_market_state['position_size'] / 2  # 남은 포지션의 절반
                        order = self.place_market_order('SELL', sell_quantity)
                        if order:
                            self.strategy.exit_stage = 2
                            self.current_market_state['position_size'] -= sell_quantity
                            return True
                    
                    # 세 번째 익절: 20일 EMA 아래로 이탈
                    elif self.strategy.exit_stage == 2 and current_price < ema20:
                        logger.info(f"3차 익절 발생 (20일 EMA 이탈) - 가격: {current_price}")
                        order = self.place_market_order('SELL', self.current_market_state['position_size'])
                        if order:
                            self.strategy.exit_stage = 3
                            self.current_market_state['position'] = 0
                            self.current_market_state['position_size'] = 0
                            self.strategy.position = 0
                            return True
            
            # 2. 포지션이 없는 경우 새로운 진입 확인
            else:
                # EMA 정배열/역배열 확인
                ema_alignment = self.strategy.check_ema_alignment(ema10, ema20, ema50)
                
                # 롱 포지션 진입 조건 확인 (현물 거래이므로 롱 포지션만 고려)
                if ema_alignment == 1:  # 정배열
                    # 조정 구간 확인 (눌림목)
                    adjustment = self.strategy.check_adjustment(current_price, ema10, ema20, ema50, 1)
                    
                    # 횡보 구간 확인
                    sideways = self.strategy.detect_sideways(df.iloc[-6:-1], lookback=5, threshold=0.02)
                    
                    # 돌파 확인
                    breakout = self.strategy.identify_range_breakout(df.iloc[-11:], lookback=10)
                    
                    if adjustment and sideways and breakout == 1:
                        logger.info("매수 신호 발생 - 정배열 + 조정구간 + 횡보구간 + 상방돌파")
                        
                        # 캔들 패턴 확인 (신호 검증)
                        if current_candle['close'] < current_candle['open']:
                            logger.warning("현재 캔들이 음봉입니다. 매수 신호 무시.")
                            return False
                        
                        # 거래량 확인 (신호 검증)
                        avg_volume = df['volume'].iloc[-6:-1].mean()
                        if current_candle['volume'] < avg_volume * 1.2:
                            logger.warning("돌파 거래량이 부족합니다. 매수 신호 무시.")
                            return False
                        
                        # 1차 손절가 설정 (돌파 캔들의 저점)
                        stop_loss_price = min(current_candle['low'], previous_candle['low'])
                        
                        # 2차 손절가 설정 (횡보 구간의 하단)
                        range_data = df.iloc[-11:-1]
                        range_low = range_data['low'].min()
                        secondary_stop_loss = range_low
                        
                        # 손절 범위 계산
                        stop_loss_percentage = (current_price - stop_loss_price) / current_price
                        
                        # 손절 범위가 너무 크면 경고 및 조정
                        if stop_loss_percentage > 0.05:  # 5% 이상 손절
                            logger.warning(f"손절 범위가 너무 큽니다 ({stop_loss_percentage:.2%}). 손절가를 조정합니다.")
                            stop_loss_price = current_price * 0.95  # 5% 손절로 제한
                            stop_loss_percentage = 0.05
                        
                        # 투자 금액 계산 (리스크 1% 기준)
                        risk_amount = self.initial_capital * 0.01
                        position_value = risk_amount / stop_loss_percentage  # 투자 가능 금액
                        
                        # 계정 잔고 확인
                        account_info = self.client.get_account()
                        quote_balance = 0
                        for balance in account_info['balances']:
                            if balance['asset'] == self.quote_asset:
                                quote_balance = float(balance['free'])
                                break
                        
                        # 실제 투자 금액 (계정 잔고와 계산된 투자 금액 중 작은 값)
                        invest_amount = min(position_value, quote_balance)
                        
                        # 최대 거래 금액 확인
                        if self.max_trade_amount:
                            invest_amount = min(invest_amount, self.max_trade_amount)
                        
                        # 최소 주문 금액 확인
                        if invest_amount < self.min_notional:
                            logger.warning(f"계산된 투자 금액({invest_amount:.2f})이 최소 주문 금액({self.min_notional:.2f})보다 작습니다.")
                            
                            if quote_balance >= self.min_notional:
                                invest_amount = self.min_notional
                                logger.info(f"투자 금액을 최소 주문 금액으로 조정: {invest_amount:.2f}")
                            else:
                                logger.error(f"계정 잔고({quote_balance:.2f})가 최소 주문 금액보다 작습니다. 주문을 실행할 수 없습니다.")
                                return False
                        
                        # 수량 계산
                        quantity = invest_amount / current_price
                        
                        # 주문 실행
                        logger.info(f"매수 주문 - 금액: {invest_amount:.2f} {self.quote_asset}, 수량: {self.format_quantity(quantity)} {self.base_asset}")
                        logger.info(f"손절가 설정 - 1차: {stop_loss_price:.2f}, 2차: {secondary_stop_loss:.2f}")
                        
                        order = self.place_market_order('BUY', quantity)
                        if order:
                            # 포지션 정보 업데이트
                            self.current_market_state['position'] = 1
                            self.current_market_state['entry_price'] = current_price
                            self.current_market_state['position_size'] = quantity
                            self.current_market_state['stop_loss'] = stop_loss_price
                            self.current_market_state['secondary_stop_loss'] = secondary_stop_loss
                            
                            # 전략 객체 상태 업데이트
                            self.strategy.position = 1
                            self.strategy.entry_price = current_price
                            self.strategy.position_size = quantity
                            self.strategy.stop_loss = stop_loss_price
                            self.strategy.secondary_stop_loss = secondary_stop_loss
                            self.strategy.sl_triggered = False
                            self.strategy.exit_stage = 0
                            self.strategy.remaining_position_pct = 1.0
                            
                            return True
            
            logger.info(f"현재 상태 - 포지션: {'롱' if self.current_market_state['position'] == 1 else '없음'}, 가격: {current_price:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"전략 실행 중 오류 발생: {e}")
            return False
    
    def _save_market_data_to_db(self, candle, ema10, ema20, ema50):
        """시장 데이터를 데이터베이스에 저장"""
        try:
            # Timestamp를 datetime 문자열로 변환
            timestamp = candle.name
            if hasattr(timestamp, 'strftime'):
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                timestamp_str = str(timestamp)
            
            market_data = {
                'timestamp': timestamp_str,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'open_price': float(candle['open']),
                'high_price': float(candle['high']),
                'low_price': float(candle['low']),
                'close_price': float(candle['close']),
                'volume': float(candle['volume']),
                'ema10': float(ema10) if pd.notna(ema10) else None,
                'ema20': float(ema20) if pd.notna(ema20) else None,
                'ema50': float(ema50) if pd.notna(ema50) else None
            }
            
            self.db.add_market_data(market_data)
            
        except Exception as e:
            logger.error(f"시장 데이터 저장 중 오류: {e}")
    
    def run(self, check_interval=300):
        """
        자동 매매 시스템 실행
        
        Args:
            check_interval (int): 매매 신호 확인 주기 (초)
        """
        logger.info(f"자동 매매 시스템 시작 - 심볼: {self.symbol}, 타임프레임: {self.timeframe}")
        
        try:
            while True:
                current_time = datetime.now()
                
                # 주기적으로 매매 신호 확인
                if self.last_check_time is None or (current_time - self.last_check_time).total_seconds() >= check_interval:
                    logger.info(f"매매 신호 확인 중... ({current_time})")
                    self.execute_strategy()
                    self.last_check_time = current_time
                
                # 대기
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 프로그램이 중단되었습니다.")
        except Exception as e:
            logger.error(f"프로그램 실행 중 오류 발생: {e}")
        finally:
            logger.info("자동 매매 시스템 종료")


if __name__ == "__main__":
    # 설정 파일에서 API 키 읽기
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            api_key = config.get('api_key')
            api_secret = config.get('api_secret')
            test_mode = config.get('test_mode', True)  # 기본값은 테스트 모드
            max_trade_amount = config.get('max_trade_amount')  # 거래당 최대 금액
            symbol = config.get('symbol', 'BTCUSDT')  # 거래 심볼
            timeframe = config.get('timeframe', '4h')  # 캔들 주기
            test_initial_capital = config.get('test_initial_capital', 10000)
            
        if not api_key or not api_secret:
            raise ValueError("API 키가 설정되지 않았습니다.")
        
        # 테스트 모드일 때 초기 자본금 설정
        initial_capital = test_initial_capital if test_mode else None
            
        # 자동 매매 시스템 초기화
        trader = BinanceAutoTrader(
            api_key=api_key,
            api_secret=api_secret,
            symbol=symbol,
            timeframe=timeframe,
            initial_capital=initial_capital,
            max_trade_amount=max_trade_amount,
            test_mode=test_mode
        )
        
        # 자동 매매 시스템 실행
        trader.run(check_interval=300)  # 5분마다 매매 신호 확인
        
    except FileNotFoundError:
        logger.error("config.json 파일을 찾을 수 없습니다. API 키 설정이 필요합니다.")
    except json.JSONDecodeError:
        logger.error("config.json 파일 형식이 잘못되었습니다.")
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.error(f"프로그램 초기화 중 오류 발생: {e}") 