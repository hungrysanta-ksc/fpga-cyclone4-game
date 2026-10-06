# NES-P2-MMC3-UNIT-008 — 매퍼 단독 RTL 검증

2026-10-05. 고정 MiSTer MMC3 module을 실제 Questa에서 실행해 **12,540개 관측을 통과**했다. 기존 무료 FLOAT 경로를 사용했고, 매퍼 동작 코드는 수정하지 않았다.

| 검사 | 관측 수 / 결과 |
|---|---|
| PRG banking 및 RAM 접근 | 4,112건, 주소·허용 오류 0 |
| CHR banking 및 미러링 | 8,200건, 주소·선택 오류 0 |
| IRQ | 19종 × 12회 = 228건, 오류 0 |
| A12 위상 | 핵심 5종 각각 실제 master tick 0..11 모두 관측 |
| 잘못된 증거 거부 | PRG 주소·권한, CHR 주소, IRQ 레벨 변조, trace 절단 5종 통과 |
| 최종 반복 실행 | run-02와 run-03 원시 trace byte 동일 |
| 컴파일/시뮬레이션 | Errors 0, Warnings 0 |

PRG mode 교환과 고정 bank, CHR inversion/2KB 정렬, RAM enable/protect, 수평·수직 미러링을 확인했다. IRQ는 짧은 A12 low 거부, 3 falling-M2 sample 후 상승 수용, 반복 high 거부, reload/count/ack/disable/zero-latch 및 reset을 포함한다. **이번 단독 매퍼 경고 0은 이전 전체 NROM 코어 경고 42개를 해결했다는 뜻이 아니다.**

최초 run-01은 task 호출 중에만 CE/M2 phase가 움직였고, low 구간 종료가 고정 위상으로 정렬돼 12개 초기 phase 반복이 실제 12개 상승 phase를 보장하지 않았다. 검토에서 발견해 연속 CE/M2 구동과 상승 직전 phase 지연으로 testbench를 수정했다. run-02 통과 후 run-03은 실제 trace 위상 커버리지를 필수 검사로 추가했고 trace는 같았다. 최종 검사기는 run-01을 phase coverage 부족으로 거부한다. 약한 최초 결과를 최종 성공 근거로 쓰지 않는다.

실험 원본/변환 diff/로그/trace는 ignored `analysis/local-mmc3-unit-008/run-01..03/`, 이전 runner는 baseline/, 이전 상태 문서는 baseline-status/에 보존했다. 라이선스/서버 로그는 제외했다. 실행 뒤 라이선스 서버 프로세스와 포트 listener는 0이었다.

[검증 JSON](mmc3-unit-verification.json), [해시 목록](mmc3-unit-artifacts.json), [관측 계약·재현](../docs/nes-mmc3-unit-contract.md).

범위는 표준 Mapper4 submapper0 단독 RTL에 합성 버스 입력을 공급한 것이다. Mesen 소스 의미를 검토했지만 Mesen runtime 비교, CPU/PPU 통합 ROM 실행, 모든 MMC3 revision, 실제 게임 cache miss, NES→SNES 통합, full-fit/STA, SMB3·실기를 완료하지 않았다. MMC3/savestate 개별 파일 license hold는 유지하며 raw HDL을 공개 허용 목록에 넣지 않았다.

다음 구현: 자체 Mapper4 ROM 생성 → 최소 cart adapter 연결 → PRG/CHR 물리 주소와 PPU A12/CPU IRQ service 기록 → Mesen 참조 비교. 기존 NROM 시험은 유지한다. GBC 152개 소스·Quartus 입력·부트 도달 2048바이트 검증도 통과했다.
