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
        logging.FileHandler("futures_trading.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BinanceFuturesAutoTrader:
    """
    Binance 선물 자동매매 클래스
    """
    def __init__(self, api_key, api_secret, symbol, timeframe='4h', initial_capital=None, 
                 max_trade_amount=None, leverage=3, test_mode=False):
        """
        초기화
        
        Args:
            api_key (str): Binance API 키
            api_secret (str): Binance API 시크릿
            symbol (str): 거래 심볼 (예: 'BTCUSDT')
            timeframe (str): 캔들 주기 (예: '1h', '4h', '1d')
            initial_capital (float): 초기 자본금 (None이면 계정에서 가져옴)
            max_trade_amount (float): 거래당 최대 금액 (USDT)
            leverage (int): 레버리지 (1-125배)
            test_mode (bool): 테스트 모드 여부 (True면 실제 주문 실행 안함)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.timeframe = timeframe
        self.leverage = min(max(leverage, 1), 125)  # 1-125배 제한
        self.test_mode = test_mode
        
        # 데이터베이스 초기화
        self.db = TradingDatabase()
        
        # 테스트 모드 안내
        if self.test_mode:
            logger.warning("테스트 모드로 실행 중입니다. 실제 주문은 실행되지 않습니다.")
        
        # Binance 클라이언트 초기화
        self.client = Client(api_key, api_secret)
        
        # 선물 계정 정보 가져오기
        try:
            futures_account = self.client.futures_account()
            logger.info("선물 계정 연결 성공")
        except Exception as e:
            logger.error(f"선물 계정 연결 실패: {e}")
            raise
        
        # 기본 설정
        self.quote_asset = 'USDT'  # 선물은 USDT 마진
        self.base_asset = self.symbol.replace('USDT', '')
        
        # 초기 자본금 설정 (선물 계정 잔고)
        if initial_capital is None:
            if self.test_mode:
                # 테스트 모드에서는 설정 파일의 test_initial_capital 사용 또는 기본값
                self.initial_capital = 10000  # 기본값
            else:
                # 실제 계정 잔고 사용
                for balance in futures_account['assets']:
                    if balance['asset'] == 'USDT':
                        self.initial_capital = float(balance['walletBalance'])
                        break
        else:
            self.initial_capital = initial_capital
        
        # 최대 거래 금액 설정
        self.max_trade_amount = max_trade_amount
        if max_trade_amount:
            logger.info(f"거래당 최대 금액 설정: {max_trade_amount} {self.quote_asset}")
        
        logger.info(f"초기 자본금: {self.initial_capital} {self.quote_asset}")
        logger.info(f"레버리지: {self.leverage}배")
        
        # 전략 초기화
        self.strategy = TrendFollowingStrategy(
            initial_capital=self.initial_capital,
            risk_percentage=0.01,  # 거래당 리스크 비율 (1%)
            leverage=self.leverage
        )
        
        # 선물 거래 설정
        self._setup_futures_trading()
        
        # 거래 심볼 정보 가져오기
        self.symbol_info = self._get_futures_symbol_info()
        
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
            'long_position': 0,      # 롱 포지션 크기
            'short_position': 0,     # 숏 포지션 크기
            'long_entry_price': 0,   # 롱 진입가
            'short_entry_price': 0,  # 숏 진입가
            'long_stop_loss': 0,     # 롱 손절가
            'short_stop_loss': 0,    # 숏 손절가
            'long_secondary_stop_loss': 0,   # 롱 2차 손절가
            'short_secondary_stop_loss': 0   # 숏 2차 손절가
        }
        
        # 안전 설정 확인
        self._check_security_settings()
        
        logger.info(f"BinanceFuturesAutoTrader 초기화 완료 - 심볼: {self.symbol}, 타임프레임: {self.timeframe}")
    
    def _setup_futures_trading(self):
        """선물 거래 초기 설정"""
        try:
            # 레버리지 설정
            self.client.futures_change_leverage(symbol=self.symbol, leverage=self.leverage)
            logger.info(f"레버리지 {self.leverage}배로 설정 완료")
            
            # 양방향 포지션 모드 설정 (롱/숏 동시 가능)
            try:
                self.client.futures_change_position_mode(dualSidePosition=True)
                logger.info("양방향 포지션 모드 설정 완료")
            except BinanceAPIException as e:
                if "No need to change position side" in str(e):
                    logger.info("이미 양방향 포지션 모드로 설정되어 있습니다")
                else:
                    logger.warning(f"포지션 모드 설정 실패: {e}")
            
            # 마진 타입을 격리 마진으로 설정 (선택사항)
            try:
                self.client.futures_change_margin_type(symbol=self.symbol, marginType='ISOLATED')
                logger.info("격리 마진 모드 설정 완료")
            except BinanceAPIException as e:
                if "No need to change margin type" in str(e):
                    logger.info("이미 격리 마진 모드로 설정되어 있습니다")
                else:
                    logger.warning(f"마진 타입 설정 실패: {e}")
                    
        except Exception as e:
            logger.error(f"선물 거래 설정 중 오류: {e}")
    
    def _get_futures_symbol_info(self):
        """선물 심볼 정보 가져오기"""
        try:
            exchange_info = self.client.futures_exchange_info()
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == self.symbol:
                    return symbol_info
            raise ValueError(f"심볼 {self.symbol}을 찾을 수 없습니다")
        except Exception as e:
            logger.error(f"선물 심볼 정보 가져오기 실패: {e}")
            raise
    
    def _check_security_settings(self):
        """API 키 권한 및 안전 설정 확인"""
        try:
            # 선물 계정 정보로 권한 확인
            account_info = self.client.futures_account()
            logger.info("선물 API 키 권한 확인 완료")
            
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
                return float(filter['notional'])
        return 5.0  # 기본값 (선물은 보통 5 USDT)
    
    def _get_precision_from_step_size(self):
        """수량 정밀도(소수점 자릿수) 가져오기"""
        for filter in self.symbol_info['filters']:
            if filter['filterType'] == 'LOT_SIZE':
                step_size = float(filter['stepSize'])
                precision = 0
                while step_size < 1:
                    step_size *= 10
                    precision += 1
                return precision
        return 3  # 기본값
    
    def format_quantity(self, quantity):
        """수량을 심볼 정밀도에 맞게 포맷팅"""
        return f"{quantity:.{self.quantity_precision}f}"
    
    def fetch_latest_data(self, limit=100):
        """최신 OHLCV 데이터 가져오기 (선물)"""
        try:
            # 선물 API에서 캔들 데이터 가져오기
            klines = self.client.futures_klines(
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
            
            logger.info(f"{limit}개의 {self.timeframe} 선물 캔들 데이터를 가져왔습니다.")
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Binance 선물 API 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"선물 데이터 가져오기 오류: {e}")
            return None
    
    def place_futures_order(self, side, quantity, position_side='BOTH'):
        """선물 시장가 주문 실행"""
        try:
            # 최소 수량 확인
            if quantity <= 0:
                logger.error(f"유효하지 않은 주문 수량: {quantity}")
                return None
            
            # 현재 가격 확인
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            order_value = quantity * current_price
            
            # 최소 주문 금액 확인
            if order_value < self.min_notional:
                logger.error(f"주문 금액({order_value:.2f})이 최소 주문 금액({self.min_notional:.2f})보다 작습니다.")
                return None
            
            # 최대 거래 금액 확인
            if self.max_trade_amount and order_value > self.max_trade_amount:
                logger.warning(f"주문 금액({order_value:.2f})이 최대 거래 금액({self.max_trade_amount:.2f})을 초과합니다. 수량을 조정합니다.")
                quantity = self.max_trade_amount / current_price
            
            # 과도한 거래 방지 (쿨다운 확인)
            current_time = time.time()
            if self.last_trade_time and (current_time - self.last_trade_time) < self.trade_cooldown:
                remaining_time = self.trade_cooldown - (current_time - self.last_trade_time)
                logger.warning(f"거래 쿨다운 중입니다. {remaining_time/60:.1f}분 후에 다시 시도하세요.")
                return None
            
            formatted_quantity = self.format_quantity(quantity)
            logger.info(f"{side} 선물 시장가 주문 - 수량: {formatted_quantity} {self.base_asset}, 포지션: {position_side}")
            
            # 테스트 모드인 경우 실제 주문 실행 안함
            if self.test_mode:
                logger.info("테스트 모드: 실제 선물 주문이 실행되지 않았습니다.")
                
                # 테스트 주문 응답 생성
                test_order = {
                    'symbol': self.symbol,
                    'orderId': 0,
                    'clientOrderId': 'test_futures',
                    'transactTime': int(time.time() * 1000),
                    'price': '0.00',
                    'origQty': formatted_quantity,
                    'executedQty': formatted_quantity,
                    'status': 'FILLED',
                    'timeInForce': 'GTC',
                    'type': 'MARKET',
                    'side': side,
                    'positionSide': position_side
                }
                
                self.last_trade_time = current_time
                
                # 테스트 모드에서도 데이터베이스에 매매 내역 저장
                self._save_trade_to_db(test_order, side, quantity, current_price, position_side)
                
                return test_order
            
            # 실제 선물 주문 실행
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=side,
                type='MARKET',
                quantity=formatted_quantity,
                positionSide=position_side
            )
            
            logger.info(f"선물 주문 성공 - ID: {order['orderId']}, 상태: {order['status']}")
            
            self.last_trade_time = current_time
            
            # 데이터베이스에 매매 내역 저장
            self._save_trade_to_db(order, side, quantity, current_price, position_side)
            
            return order
            
        except BinanceAPIException as e:
            logger.error(f"선물 주문 오류: {e}")
            return None
        except Exception as e:
            logger.error(f"선물 주문 실행 중 오류 발생: {e}")
            return None
    
    def _save_trade_to_db(self, order, side, quantity, price, position_side):
        """매매 내역을 데이터베이스에 저장"""
        try:
            # 거래 타입 결정
            trade_type = 'ENTRY'
            exit_stage = 0
            
            if side == 'SELL' and position_side == 'LONG':
                trade_type = 'EXIT_LONG'
            elif side == 'BUY' and position_side == 'SHORT':
                trade_type = 'EXIT_SHORT'
            elif side == 'BUY' and position_side == 'LONG':
                trade_type = 'ENTRY_LONG'
            elif side == 'SELL' and position_side == 'SHORT':
                trade_type = 'ENTRY_SHORT'
            
            trade_data = {
                'timestamp': datetime.now(),
                'symbol': self.symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'total_value': quantity * price,
                'order_id': order.get('orderId') if order else None,
                'trade_type': trade_type,
                'position_side': position_side,
                'leverage': self.leverage,
                'exit_stage': exit_stage,
                'test_mode': self.test_mode,
                'notes': f"선물 자동매매 - {trade_type}"
            }
            
            self.db.add_trade(trade_data)
            logger.info(f"선물 매매 내역이 데이터베이스에 저장되었습니다: {side} {quantity} {self.symbol} ({position_side})")
            
        except Exception as e:
            logger.error(f"선물 매매 내역 저장 중 오류: {e}")
    
    def update_market_state(self):
        """현재 선물 포지션 상태 업데이트"""
        try:
            # 선물 포지션 정보 가져오기
            positions = self.client.futures_position_information(symbol=self.symbol)
            
            # 현재 가격 확인
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            current_price = float(ticker['price'])
            
            # 포지션 상태 초기화
            self.current_market_state = {
                'long_position': 0,
                'short_position': 0,
                'long_entry_price': 0,
                'short_entry_price': 0,
                'long_stop_loss': 0,
                'short_stop_loss': 0,
                'long_secondary_stop_loss': 0,
                'short_secondary_stop_loss': 0
            }
            
            # 포지션 정보 업데이트
            for position in positions:
                position_amt = float(position['positionAmt'])
                entry_price = float(position['entryPrice'])
                
                if position['positionSide'] == 'LONG' and position_amt > 0:
                    self.current_market_state['long_position'] = position_amt
                    self.current_market_state['long_entry_price'] = entry_price
                    logger.info(f"롱 포지션: {position_amt} {self.base_asset}, 진입가: {entry_price}")
                    
                elif position['positionSide'] == 'SHORT' and position_amt < 0:
                    self.current_market_state['short_position'] = abs(position_amt)
                    self.current_market_state['short_entry_price'] = entry_price
                    logger.info(f"숏 포지션: {abs(position_amt)} {self.base_asset}, 진입가: {entry_price}")
            
            # 포지션이 없는 경우
            if (self.current_market_state['long_position'] == 0 and 
                self.current_market_state['short_position'] == 0):
                logger.info("포지션 없음")
            
            # 데이터베이스에 포지션 상태 저장
            self._save_position_to_db(current_price)
            
            return True
            
        except BinanceAPIException as e:
            logger.error(f"선물 포지션 상태 업데이트 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"선물 포지션 상태 업데이트 중 오류 발생: {e}")
            return False
    
    def _save_position_to_db(self, current_price):
        """포지션 상태를 데이터베이스에 저장"""
        try:
            # 미실현 손익 계산
            long_unrealized_pnl = 0
            short_unrealized_pnl = 0
            
            if self.current_market_state['long_position'] > 0:
                long_unrealized_pnl = ((current_price - self.current_market_state['long_entry_price']) * 
                                     self.current_market_state['long_position'])
            
            if self.current_market_state['short_position'] > 0:
                short_unrealized_pnl = ((self.current_market_state['short_entry_price'] - current_price) * 
                                      self.current_market_state['short_position'])
            
            total_unrealized_pnl = long_unrealized_pnl + short_unrealized_pnl
            
            # 레거시 position 필드 값 계산 (호환성용)
            position = 0  # 기본값: 포지션 없음
            if self.current_market_state['long_position'] > 0:
                position = 1  # 롱 포지션
            elif self.current_market_state['short_position'] > 0:
                position = -1  # 숏 포지션
            
            position_data = {
                'timestamp': datetime.now(),
                'symbol': self.symbol,
                'position': position,  # 호환성을 위한 레거시 필드
                'long_position': self.current_market_state['long_position'],
                'short_position': self.current_market_state['short_position'],
                'long_entry_price': self.current_market_state['long_entry_price'],
                'short_entry_price': self.current_market_state['short_entry_price'],
                'long_stop_loss': self.current_market_state.get('long_stop_loss', 0),
                'short_stop_loss': self.current_market_state.get('short_stop_loss', 0),
                'unrealized_pnl': total_unrealized_pnl,
                'current_price': current_price,
                'leverage': self.leverage
            }
            
            self.db.update_position(position_data)
            
        except Exception as e:
            logger.error(f"선물 포지션 상태 저장 중 오류: {e}")
    
    def execute_strategy(self):
        """선물 전략 실행 및 매매 신호 처리"""
        try:
            # 최신 데이터 가져오기
            df = self.fetch_latest_data(limit=100)
            if df is None or df.empty:
                logger.error("데이터를 가져올 수 없습니다.")
                return False
            
            # 현재 포지션 상태 업데이트
            self.update_market_state()
            
            # 현재 캔들 정보
            current_candle = df.iloc[-1]
            previous_candle = df.iloc[-2]
            current_price = float(current_candle['close'])
            
            # EMA 값 계산
            df['ema10'] = self.strategy.calculate_ema(df, 10)
            df['ema20'] = self.strategy.calculate_ema(df, 20)
            df['ema50'] = self.strategy.calculate_ema(df, 50)
            
            ema10 = df['ema10'].iloc[-1]
            ema20 = df['ema20'].iloc[-1]
            ema50 = df['ema50'].iloc[-1]
            
            # 시장 데이터를 데이터베이스에 저장
            self._save_market_data_to_db(current_candle, ema10, ema20, ema50)
            
            # 1. 포지션이 있는 경우 손절/익절 확인
            self._check_exit_conditions(current_price, ema10, ema20, current_candle, previous_candle)
            
            # 2. 포지션이 없거나 부분 포지션인 경우 새로운 진입 확인
            self._check_entry_conditions(df, current_price, ema10, ema20, ema50, current_candle, previous_candle)
            
            logger.info(f"현재 상태 - 롱: {self.current_market_state['long_position']:.3f}, "
                       f"숏: {self.current_market_state['short_position']:.3f}, 가격: {current_price:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"선물 전략 실행 중 오류 발생: {e}")
            return False
    
    def _check_exit_conditions(self, current_price, ema10, ema20, current_candle, previous_candle):
        """손절/익절 조건 확인"""
        # 롱 포지션 청산 조건
        if self.current_market_state['long_position'] > 0:
            # 손절 확인
            if (self.current_market_state['long_stop_loss'] > 0 and 
                current_price <= self.current_market_state['long_stop_loss']):
                logger.info(f"롱 포지션 손절 발생 - 가격: {current_price}")
                self.place_futures_order('SELL', self.current_market_state['long_position'], 'LONG')
                return
            
            # 익절 확인 (양봉 후 음봉)
            if (previous_candle['close'] > previous_candle['open'] and 
                current_candle['close'] < current_candle['open']):
                logger.info(f"롱 포지션 1차 익절 발생 (음봉) - 가격: {current_price}")
                sell_quantity = self.current_market_state['long_position'] / 3
                self.place_futures_order('SELL', sell_quantity, 'LONG')
                return
            
            # EMA 이탈 익절
            if current_price < ema20:
                logger.info(f"롱 포지션 EMA 익절 발생 - 가격: {current_price}")
                self.place_futures_order('SELL', self.current_market_state['long_position'], 'LONG')
                return
        
        # 숏 포지션 청산 조건
        if self.current_market_state['short_position'] > 0:
            # 손절 확인
            if (self.current_market_state['short_stop_loss'] > 0 and 
                current_price >= self.current_market_state['short_stop_loss']):
                logger.info(f"숏 포지션 손절 발생 - 가격: {current_price}")
                self.place_futures_order('BUY', self.current_market_state['short_position'], 'SHORT')
                return
            
            # 익절 확인 (음봉 후 양봉)
            if (previous_candle['close'] < previous_candle['open'] and 
                current_candle['close'] > current_candle['open']):
                logger.info(f"숏 포지션 1차 익절 발생 (양봉) - 가격: {current_price}")
                buy_quantity = self.current_market_state['short_position'] / 3
                self.place_futures_order('BUY', buy_quantity, 'SHORT')
                return
            
            # EMA 이탈 익절
            if current_price > ema20:
                logger.info(f"숏 포지션 EMA 익절 발생 - 가격: {current_price}")
                self.place_futures_order('BUY', self.current_market_state['short_position'], 'SHORT')
                return
    
    def _check_entry_conditions(self, df, current_price, ema10, ema20, ema50, current_candle, previous_candle):
        """진입 조건 확인"""
        # EMA 정배열/역배열 확인
        ema_alignment = self.strategy.check_ema_alignment(ema10, ema20, ema50)
        
        # 롱 포지션 진입 조건 (정배열)
        if ema_alignment == 1 and self.current_market_state['long_position'] == 0:
            if self._check_long_entry_signal(df, current_price, ema10, ema20, ema50, current_candle):
                self._enter_long_position(current_price, current_candle, previous_candle)
        
        # 숏 포지션 진입 조건 (역배열)
        elif ema_alignment == -1 and self.current_market_state['short_position'] == 0:
            if self._check_short_entry_signal(df, current_price, ema10, ema20, ema50, current_candle):
                self._enter_short_position(current_price, current_candle, previous_candle)
    
    def _check_long_entry_signal(self, df, current_price, ema10, ema20, ema50, current_candle):
        """롱 진입 신호 확인"""
        # 조정 구간 확인 (눌림목)
        adjustment = self.strategy.check_adjustment(current_price, ema10, ema20, ema50, 1)
        
        # 횡보 구간 확인
        sideways = self.strategy.detect_sideways(df.iloc[-6:-1], lookback=5, threshold=0.02)
        
        # 돌파 확인
        breakout = self.strategy.identify_range_breakout(df.iloc[-11:], lookback=10)
        
        if adjustment and sideways and breakout == 1:
            # 캔들 패턴 확인
            if current_candle['close'] < current_candle['open']:
                logger.warning("현재 캔들이 음봉입니다. 롱 진입 신호 무시.")
                return False
            
            # 거래량 확인
            avg_volume = df['volume'].iloc[-6:-1].mean()
            if current_candle['volume'] < avg_volume * 1.2:
                logger.warning("돌파 거래량이 부족합니다. 롱 진입 신호 무시.")
                return False
            
            return True
        
        return False
    
    def _check_short_entry_signal(self, df, current_price, ema10, ema20, ema50, current_candle):
        """숏 진입 신호 확인"""
        # 조정 구간 확인 (반등)
        adjustment = self.strategy.check_adjustment(current_price, ema10, ema20, ema50, -1)
        
        # 횡보 구간 확인
        sideways = self.strategy.detect_sideways(df.iloc[-6:-1], lookback=5, threshold=0.02)
        
        # 돌파 확인
        breakout = self.strategy.identify_range_breakout(df.iloc[-11:], lookback=10)
        
        if adjustment and sideways and breakout == -1:
            # 캔들 패턴 확인
            if current_candle['close'] > current_candle['open']:
                logger.warning("현재 캔들이 양봉입니다. 숏 진입 신호 무시.")
                return False
            
            # 거래량 확인
            avg_volume = df['volume'].iloc[-6:-1].mean()
            if current_candle['volume'] < avg_volume * 1.2:
                logger.warning("돌파 거래량이 부족합니다. 숏 진입 신호 무시.")
                return False
            
            return True
        
        return False
    
    def _enter_long_position(self, current_price, current_candle, previous_candle):
        """롱 포지션 진입"""
        # 손절가 설정
        stop_loss_price = min(current_candle['low'], previous_candle['low'])
        
        # 손절 범위 계산
        stop_loss_percentage = (current_price - stop_loss_price) / current_price
        
        # 손절 범위 제한
        if stop_loss_percentage > 0.05:
            stop_loss_price = current_price * 0.95
            stop_loss_percentage = 0.05
        
        # 투자 금액 계산 (레버리지 고려)
        risk_amount = self.initial_capital * 0.01
        position_value = (risk_amount / stop_loss_percentage) * self.leverage
        
        # 계정 잔고 확인
        account_info = self.client.futures_account()
        available_balance = float(account_info['availableBalance'])
        
        # 실제 투자 금액
        invest_amount = min(position_value, available_balance * 0.9)  # 90%만 사용
        
        if self.max_trade_amount:
            invest_amount = min(invest_amount, self.max_trade_amount)
        
        # 수량 계산
        quantity = invest_amount / current_price
        
        if invest_amount >= self.min_notional:
            logger.info(f"롱 포지션 진입 - 금액: {invest_amount:.2f} USDT, 수량: {quantity:.3f}")
            logger.info(f"손절가: {stop_loss_price:.2f}")
            
            order = self.place_futures_order('BUY', quantity, 'LONG')
            if order:
                self.current_market_state['long_stop_loss'] = stop_loss_price
        else:
            logger.warning(f"투자 금액({invest_amount:.2f})이 최소 주문 금액보다 작습니다.")
    
    def _enter_short_position(self, current_price, current_candle, previous_candle):
        """숏 포지션 진입"""
        # 손절가 설정
        stop_loss_price = max(current_candle['high'], previous_candle['high'])
        
        # 손절 범위 계산
        stop_loss_percentage = (stop_loss_price - current_price) / current_price
        
        # 손절 범위 제한
        if stop_loss_percentage > 0.05:
            stop_loss_price = current_price * 1.05
            stop_loss_percentage = 0.05
        
        # 투자 금액 계산 (레버리지 고려)
        risk_amount = self.initial_capital * 0.01
        position_value = (risk_amount / stop_loss_percentage) * self.leverage
        
        # 계정 잔고 확인
        account_info = self.client.futures_account()
        available_balance = float(account_info['availableBalance'])
        
        # 실제 투자 금액
        invest_amount = min(position_value, available_balance * 0.9)  # 90%만 사용
        
        if self.max_trade_amount:
            invest_amount = min(invest_amount, self.max_trade_amount)
        
        # 수량 계산
        quantity = invest_amount / current_price
        
        if invest_amount >= self.min_notional:
            logger.info(f"숏 포지션 진입 - 금액: {invest_amount:.2f} USDT, 수량: {quantity:.3f}")
            logger.info(f"손절가: {stop_loss_price:.2f}")
            
            order = self.place_futures_order('SELL', quantity, 'SHORT')
            if order:
                self.current_market_state['short_stop_loss'] = stop_loss_price
        else:
            logger.warning(f"투자 금액({invest_amount:.2f})이 최소 주문 금액보다 작습니다.")
    
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
        """선물 자동 매매 시스템 실행"""
        logger.info(f"선물 자동 매매 시스템 시작 - 심볼: {self.symbol}, 레버리지: {self.leverage}배")
        
        try:
            while True:
                current_time = datetime.now()
                
                # 주기적으로 매매 신호 확인
                if self.last_check_time is None or (current_time - self.last_check_time).total_seconds() >= check_interval:
                    logger.info(f"선물 매매 신호 확인 중... ({current_time})")
                    self.execute_strategy()
                    self.last_check_time = current_time
                
                # 대기
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 선물 매매 프로그램이 중단되었습니다.")
        except Exception as e:
            logger.error(f"선물 매매 프로그램 실행 중 오류 발생: {e}")
        finally:
            logger.info("선물 자동 매매 시스템 종료")


if __name__ == "__main__":
    # 설정 파일에서 API 키 읽기
    try:
        with open('config_futures.json', 'r') as f:
            config = json.load(f)
            api_key = config.get('api_key')
            api_secret = config.get('api_secret')
            test_mode = config.get('test_mode', True)
            max_trade_amount = config.get('max_trade_amount')
            symbol = config.get('symbol', 'BTCUSDT')
            timeframe = config.get('timeframe', '4h')
            leverage = config.get('leverage', 3)
            test_initial_capital = config.get('test_initial_capital', 10000)
            
        if not api_key or not api_secret:
            raise ValueError("API 키가 설정되지 않았습니다.")
        
        # 테스트 모드일 때 초기 자본금 설정
        initial_capital = test_initial_capital if test_mode else None
            
        # 선물 자동 매매 시스템 초기화
        trader = BinanceFuturesAutoTrader(
            api_key=api_key,
            api_secret=api_secret,
            symbol=symbol,
            timeframe=timeframe,
            initial_capital=initial_capital,
            max_trade_amount=max_trade_amount,
            leverage=leverage,
            test_mode=test_mode
        )
        
        # 선물 자동 매매 시스템 실행
        trader.run(check_interval=300)
        
    except FileNotFoundError:
        logger.error("config_futures.json 파일을 찾을 수 없습니다. API 키 설정이 필요합니다.")
    except json.JSONDecodeError:
        logger.error("config_futures.json 파일 형식이 잘못되었습니다.")
    except ValueError as e:
        logger.error(str(e))
    except Exception as e:
        logger.error(f"선물 매매 프로그램 초기화 중 오류 발생: {e}") 