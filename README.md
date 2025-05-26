# 트렌드 팔로잉 자동매매 시스템

비트코인 선물시장을 대상으로 하는 트렌드 팔로잉 전략 기반 자동매매 시스템입니다.
크리스티안 쿠리마기의 돌파 매매 전략을 구현하였습니다.

## 주요 기능

- EMA 정배열/역배열 감지
- 횡보 구간 식별 및 돌파 감지
- 3단계 부분 익절 전략
- 2단계 손절 전략
- 자동 주문 실행
- 백테스팅

## 설치 방법

1. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

2. Binance API 키 설정
`config.json` 파일에 Binance API 키와 시크릿을 입력하세요:
```json
{
    "api_key": "YOUR_BINANCE_API_KEY_HERE",
    "api_secret": "YOUR_BINANCE_API_SECRET_HERE"
}
```

## 자동매매 실행 방법

```bash
python auto_trader.py
```

## 백테스팅 실행 방법

백테스팅을 실행하려면 다음과 같이 Python 코드를 작성하여 실행하세요:

```python
from strategy import TrendFollowingStrategy
import pandas as pd

# 전략 객체 생성
strategy = TrendFollowingStrategy(initial_capital=10000, risk_percentage=0.01, leverage=3)

# 데이터 불러오기 (자체 데이터 또는 API에서 가져오기)
data = strategy.fetch_data(exchange_id='binance', symbol='BTC/USDT', timeframe='4h')

# 백테스팅 실행
results = strategy.backtest(data)

# 결과 시각화
strategy.plot_results(results)
```

## 주의사항

- 자동매매 시스템은 실제 자산을 거래하므로 신중하게 사용하세요.
- API 키는 안전하게 보관하고, 필요한 권한만 부여하세요 (읽기 권한, 거래 권한).
- 실제 운영 전에 충분한 백테스팅과 페이퍼 트레이딩을 권장합니다.

## 라이센스

MIT License
