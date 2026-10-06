# NES-P2-RTL-FETCH-007 — 주소 구분 CHR RTL 검증

2026-10-05. 기존 무료 Starter FLOAT 경로로 실제 Questa RTL 실행과 Mesen 참조 비교를 완료했다. RTL-006 driver/적응 규칙을 그대로 재사용했으며 코어 RTL 추가 수정은 없다.

| 관측 항목 | 결과 |
|---|---|
| 실제 RTL 실행 | 140.02ms PASS, simulator 실행 111초 |
| 완전한 화면 | 연속 4 × 256×240 = 245,760화소 |
| 좌표/CHR oracle 및 Mesen RGB 비교 | 차이 0 |
| 패턴 테이블 | 0 → 4096 → 0 → 4096 |
| 배경 CHR latch | 65,552건, 슬롯/물리 mapping/값 오류 0 |
| 화소에 쓰인 fetch | 61,440건, 독립 예상 주소 및 Mesen 주소·값 차이 0 |
| 각 프레임 참조 타일 | 256개, 두 테이블 합계 서로 다른 512개 |
| CPU 주기/미정 버스 | 250,430 CPU enable 관측, 12 master clocks 주기 오류 0, 미정값 0 |
| 프레임 간격 | 357,364 / 357,368 / 357,364 master ticks |
| 실패 검출 | 화소 변조·화면 절단·잘못된 테이블·주소 변조·latch 누락 5종 PASS |
| Questa | Errors 0, Warnings 42; 기존 경고 유지 |

RGB 해시는 table 0 `99af6acc30681dd5ccd00aab57babf1e6c4e6fad35e7d13d247b1e99498c913a`, table 1 `1fdf127ff07d2b55fef8e9187884f178a7dfa75951951912cd841236614a2c90`로 FETCH-005 Mesen과 같다. 고유 CHR 타일로 이전 checkerboard에서 놓칠 수 있는 타일 주소 alias를 이번 입력 범위에서 검사했다.

실행은 1회다. 첫 Python 검증은 Questa 파일명 공백 패딩을 0 패딩으로 예상해 파일을 찾지 못했다. 원본 검증기와 실패 설명은 `analysis/local-rtl-fetch-007/verifier-history/`에 보존했고 파일명 처리만 수정했다. RTL은 최초 실행에서 통과했다.

원시 HDL 적응 사본·컴파일/시뮬레이션 로그·frame/fetch/control 기록은 ignored `analysis/local-rtl-fetch-007/run-01/`, 이전 상태 문서는 `baseline-status/`에 있다. 라이선스 파일/서버 로그는 제외했다. 종료 뒤 서버 프로세스와 18000–18002 listener는 0이었다.

[검증 JSON](rtl-fetch-verification.json), [소스/증거 해시](rtl-fetch-artifacts.json), [관측 계약·재현](../docs/nes-rtl-fetch-contract.md).

자체 NROM, BG만 사용한 PPUCTRL 전환, CHR 사전 상주, 이상적 동기 메모리 범위다. Mesen과는 화면 및 화소에 쓰인 fetch 의미를 비교했으며 절대 CPU phi2/A12 타이밍 일치를 주장하지 않는다. MMC3 mapping/A12/IRQ, 실제 cache miss, sprite/scroll 복합 동작, NES→SNES 통합, 전체 P1/P2·fit/STA·SMB3·실기는 미완료다. 240→239줄 crop 승인은 없다.

다음은 자체 MMC3 진단의 bank register/물리 주소 관측과 A12/IRQ 비교다. Mapper4는 별도 소스 라이선스 검토 후 로컬 실험에 연결한다. 이전 P1/STREAM/CACHE/RESIDENT 소스 47개와 RTL-006 소스 9개·증거 278개를 해시 대조했다. GBC C44/0.9.0 소스 152개·Quartus 입력·부트 도달 2048바이트 검증도 통과했다.
