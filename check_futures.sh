#!/bin/bash

# 선물 거래 모니터링 스크립트
# 사용법: ./check_futures.sh [명령어]

# 가상환경 활성화
source venv/bin/activate

echo "🚀 바이낸스 선물 거래 모니터링"
echo "=========================================="

case "$1" in
    "trades" | "t")
        echo "📈 최근 매매 내역 확인"
        python3 view_futures_trades.py trades ${2:-10}
        ;;
    "positions" | "pos" | "p")
        echo "📍 현재 포지션 상태"
        python3 view_futures_trades.py positions
        ;;
    "profit" | "pnl")
        echo "💰 손익 계산"
        python3 view_futures_trades.py pnl
        ;;
    "log" | "l")
        echo "📋 거래 로그"
        python3 view_futures_trades.py log
        ;;
    "config" | "cfg" | "c")
        echo "⚙️ 현재 설정"
        python3 view_futures_trades.py config
        ;;
    "all" | "a")
        echo "📊 전체 정보"
        python3 view_futures_trades.py all
        ;;
    "export" | "e")
        echo "💾 CSV 내보내기"
        python3 view_futures_trades.py export
        ;;
    "watch" | "w")
        echo "🔄 실시간 모니터링 (5초마다 갱신, Ctrl+C로 종료)"
        while true; do
            clear
            echo "🚀 바이낸스 선물 거래 실시간 모니터링 $(date)"
            echo "=========================================="
            python3 view_futures_trades.py positions
            echo ""
            python3 view_futures_trades.py trades 5
            echo ""
            echo "🔄 5초 후 갱신... (Ctrl+C로 종료)"
            sleep 5
        done
        ;;
    "help" | "h" | "")
        echo "사용법: ./check_futures.sh [명령어]"
        echo ""
        echo "📋 명령어 목록:"
        echo "  trades, t [숫자]     - 최근 매매 내역 (기본값: 10)"
        echo "  positions, pos, p    - 현재 포지션 상태"
        echo "  profit, pnl          - 손익 계산 및 통계"
        echo "  log, l               - 최근 거래 로그"
        echo "  config, cfg, c       - 현재 설정 확인"
        echo "  all, a               - 모든 정보"
        echo "  export, e            - CSV 파일로 내보내기"
        echo "  watch, w             - 실시간 모니터링"
        echo "  help, h              - 이 도움말"
        echo ""
        echo "📌 예시:"
        echo "  ./check_futures.sh pos           # 포지션 확인"
        echo "  ./check_futures.sh trades 20     # 최근 20개 거래"
        echo "  ./check_futures.sh watch         # 실시간 모니터링"
        ;;
    *)
        echo "❌ 알 수 없는 명령어: $1"
        echo "사용법: ./check_futures.sh help"
        ;;
esac 