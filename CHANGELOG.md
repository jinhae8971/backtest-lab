# Changelog

All notable changes to **backtest-lab** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- trendline-detector 통합 (JSON 입력으로 Elliott 정밀도 향상)
- chart-analyzer 연동 (백테스트 결과 기반 차트 생성 + Telegram)
- Walk-forward analysis (과최적화 방지)
- Parameter optimization (grid search + optuna)
- 한국 종목 지원 (FinanceDataReader 통합)

---

## [0.2.0] — 2026-04-18

### Added
- **BollingerBreakout 전략** (`src/strategies/bollinger_breakout.py`)
  - BB(20, 2σ) 상단 돌파 시 진입
  - **Squeeze 감지**: band_width가 과거 평균 대비 좁을 때 → 강한 돌파 신호
  - Volume confirmation: 거래량이 20MA의 1.2배 초과
  - 200MA trend filter
  - 밴드 중앙선 이탈 시 mean-reversion 청산
- **MACDDivergence 전략** (`src/strategies/macd_divergence.py`)
  - **강세 다이버전스 감지**: 가격 신저가 + MACD 히스토그램 상승 저점
  - 30-bar lookback, 2-bar rising confirmation
  - 최소 3% 하락 후 검증 (노이즈 제거)
  - MACD 하향 크로스 시 청산
- **Strategy registry 확장**: `STRATEGY_REGISTRY`에 `bollinger_breakout`, `macd_divergence` 추가
- **6 new pytest cases** (`tests/test_new_strategies.py`)

### Verified (NVDA 5년 실측 결과 비교)
| 전략 | 수익률 | Sharpe | MDD | 승률 | 거래 |
|---|---|---|---|---|---|
| ma_golden | +85.1% | 0.056 | -19.4% | 37.9% | 29 |
| **rsi_oversold** 🥇 | +40.2% | 0.068 | **-6.9%** | **87.5%** | 8 |
| elliott_w3 | +29.9% | 0.035 | -12.0% | 46.7% | 15 |
| bollinger_breakout | +34.7% | 0.043 | -10.5% | 57.1% | 14 |
| macd_divergence | +5.9% | 0.005 | -3.9% | 50.0% | 4 |

### Rollback
복원 명령: `git checkout v0.1.0`

---

## [0.1.0] — 2026-04-18

### Added
- **Data loader** (`src/data/`)
  - `loader.py`: yfinance 기반 OHLCV 로더
  - Backtrader `PandasData` feed 어댑터 (`load_backtrader_feed`)
  - 멀티레벨 컬럼 자동 평탄화
- **3 전략 템플릿** (`src/strategies/`)
  - `MAGoldenAlignment`: MA5 > MA20 > MA60 정배열 진입 + RSI14 필터 + 스탑로스
  - `RSIOversoldBounce`: RSI < 30 진입 + RSI > 70 청산 + 200MA 추세 필터
  - `ElliottWave3Entry`: 엘리엇 2파 완료(38.2%-78.6% 되돌림) + 1파 고점 돌파 시 진입
  - `STRATEGY_REGISTRY`로 CLI에서 이름으로 호출
  - 모두 risk_per_trade 기반 포지션 사이징
- **Report builder** (`src/reports/`)
  - `run_analyzers_metrics`: Sharpe/Drawdown/Returns/TradeAnalyzer 지표 추출
  - `build_json_summary`: 스키마 버전 기록된 JSON 요약
  - `build_html_report`: 한국어 전문가급 HTML (KPI 카드 + 상세 지표 + 거래 이력)
- **CLI** (`src/run.py`)
  - `python -m src.run --strategy <name> --ticker SPY,QQQ --years 5`
  - 멀티 티커 지원 (comma-separated)
  - 멀티 티커 `index.json` 자동 생성 (전략 비교용)
  - `--start/--end` 명시적 기간 지정 또는 `--years` 백 프로젝션
- **GitHub Actions 주간 워크플로우** (`.github/workflows/weekly_backtest.yml`)
  - 매주 일요일 23:00 UTC (월요일 08:00 KST) 자동 실행
  - Matrix strategy: 3전략 × 5티커 = 15개 백테스트 병렬
  - HTML + JSON 결과를 `docs/reports/` 로 자동 커밋
  - Rebase-on-push 재시도 로직 (commit 경합 내성)
- **Pytest 테스트 커버리지** (7개 테스트, 100% 통과)
  - Strategy registry + Backtrader 호환성
  - 실제 cerebro 실행 (MAGoldenAlignment, RSIOversoldBounce)
  - Report 빌더 (JSON + HTML)
  - yfinance 데이터 로더

### Verified (실측 동작 확인)
- **SPY 5년 MA Golden**: +8.61%, Sharpe 0.014, MDD -3.6%, 승률 46.4% (13W/15L)
- **QQQ 5년 RSI Oversold**: +4.97%, MDD -5.6%, **승률 66.7%** (4W/2L)
- **NVDA 5년 Elliott W3**: **+29.87%**, Sharpe 0.035, MDD -12.0%, 승률 46.7% (7W/8L)
- HTML 리포트: NVDA 6.2KB, SPY 8.8KB — 전문가급 시각화 확인

### Rollback
복원하려면: `git checkout v0.0.0`

---

## [0.0.0] — 2026-04-18

### Added
- 프로젝트 초기화
- README with Quick Start + Emergency Rollback SOP
- CHANGELOG.md (Keep a Changelog 표준)
- .gitignore (Python 표준)
- requirements.txt (의존성 정의)
- 프로젝트 스켈레톤 (src/ directory structure)

### Context
- 목적: TrendSpider "AI Strategy Lab" 기능의 무료 대체
- 기존 운영 시스템(global-market-orchestrator 등 10개 레포)와 **완전 독립**
- Rollback 전략: archive 처리만으로 격리 가능

### Baseline (작업 시작 시점 기존 시스템 상태)
기존 10개 운영 레포 commit SHA (2026-04-18 기준):

| Repo | SHA |
|------|-----|
| global-market-orchestrator | 4417984e |
| crypto-research-agent | 1a59604a |
| kospi-research-agent | 53dbfaca |
| sp500-research-agent | beaa678f |
| nasdaq-research-agent | 8402b032 |
| dow30-research-agent | f18bfc72 |
| github-actions-dashboard | 47b12d54 |
| kospi-strategy | 2e87972d |
| crypto-monitor | f7594646 |

이 상태는 backtest-lab 작업과 무관하게 보존됨.
