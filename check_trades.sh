#!/bin/bash

# 트레이딩 봇 매매 내역 빠른 확인 스크립트

echo "🤖 선물 자동매매 로그 체크"
echo "=========================="

# 1. 최근 로그 확인
echo ""
echo "📊 최근 활동 (로그 파일):"
echo "-----------------------"
tail -10 futures_trading.log | grep -E "(매수|매도|신호|주문|INFO)" | tail -5

# 2. 현재 가격 확인
echo ""
echo "💰 현재 BTC 가격:"
echo "---------------"
curl -s "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
price = float(data['price'])
print(f'${price:,.2f}')
"

# 3. 데이터베이스 요약
echo ""
echo "📈 매매 내역 요약:"
echo "----------------"
sqlite3 trading_history.db "
SELECT 
    '총 거래: ' || COUNT(*) || '회' as summary
FROM trades;

SELECT 
    '매수: ' || COUNT(*) || '회' as buy_count
FROM trades WHERE side = 'BUY';

SELECT 
    '매도: ' || COUNT(*) || '회' as sell_count
FROM trades WHERE side = 'SELL';

SELECT 
    '최근 거래: ' || datetime(MAX(timestamp), 'localtime') as last_trade
FROM trades;
"

# 4. 옵션별 상세 정보
case "$1" in
    "detail"|"d")
        echo ""
        echo "📋 상세 매매 내역:"
        echo "----------------"
        source venv/bin/activate && python3 view_trades.py trades 10
        ;;
    "profit"|"p")
        echo ""
        echo "💵 손익 분석:"
        echo "------------"
        source venv/bin/activate && python3 view_trades.py profit
        ;;
    "export"|"e")
        echo ""
        echo "💾 CSV 내보내기:"
        echo "---------------"
        source venv/bin/activate && python3 view_trades.py export
        ;;
    *)
        echo ""
        echo "💡 사용법:"
        echo "  ./check_trades.sh        # 기본 요약"
        echo "  ./check_trades.sh detail # 상세 내역" 
        echo "  ./check_trades.sh profit # 손익 분석"
        echo "  ./check_trades.sh export # CSV 내보내기"
        ;;
esac

echo ""
echo "✅ 체크 완료!" 