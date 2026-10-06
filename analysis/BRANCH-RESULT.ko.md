# NES-P2-BRANCH-011 — 분기 discarded-read 주소 수정

2026-10-05. **T65 분기의 버려지는 읽기 주소 차이를 재현하고 로컬 시험용 코어 사본에서 수정했다.** 8개 opcode × 7개 조건의 자체 ROM 56개 검사가 모두 통과했다. 이 변경은 CPU 버스 주소 출력에 한정되며 제품 FPGA 이미지의 완성을 의미하지 않는다.

| 검사 | 수정 전 | 수정 후 |
|---|---:|---:|
| 조건 불성립 8개 | 주소/사이클 일치 | 일치 |
| 같은 페이지 분기 16개 | discarded-read 주소 불일치 | 일치 |
| 페이지 경계 분기 32개(+127/-128 포함) | discarded-read 주소 순서 불일치 | 일치 |
| 다음 opcode 및 2/3/4-cycle 수 | 56개 일치 | 56개 일치 |
| 주소·tick·R/W·data 변조 및 절단 검출 | 기준본 자체가 주소 실패 | 통과본에서 5종 거부 |

수정 전에는 branch Cycle_2에서 offset이 더해진 주소를 버스로 내보냈다. 같은 페이지에서는 목적지 주소를 너무 일찍 읽었고, page-cross에서는 sequential 주소 읽기를 건너뛴 뒤 page 보정 주소와 최종 목적지를 읽었다. 수정본은 sequential 주소, 필요할 때 이전 high byte/target low 주소, 최종 opcode 순서를 유지한다. 총 192 branch cycles 중 80 discarded reads를 oracle 및 Mesen 관측과 확인했다. 내부 PC 갱신·명령 cycle 수·IRQ detection 로직은 수정하지 않았다.

## 통합 회귀

- 수정본으로 Mapper4 CPU/PPU/APU 진단 140.02ms 실제 RTL 실행. 오류 0, 기존 경고 42개.
- 4프레임 245,760화소 exact, BG latch 65,552건 및 화소 사용 CHR fetch 61,440건 검사, PRG 오류 0, CPU period/미정 bus 오류 0, IRQ service 총 6회.
- 010 최종본과 frame/fetch/control/edges 8개 파일이 SHA256으로 동일하다. 수정된 CPU discarded-read 주소 외 기존 관측 결과를 보존했다.
- 공통 counter3..6의 IRQ bus landmark 10개 상대 사이클 유지. 첫 stack write→ack는 두 구현 모두 18 CPU cycles다. IRQ 전부터 있던 4-dot offset은 그대로이며 절대 IRQ timing 완료로 해석하지 않는다.
- 기존 polling loop에서 9개 discarded read가 `$E186`으로 수정되어 Mesen 주소/값과 일치한다. 이전 `$E182` 차이의 재현 및 수정 확인이다.

## 증거 및 보존

자체 ROM SHA256: `b3c2fedd4115648110cd2416636433fe753982631c075fd9db7ca9de2eba7c50`. NROM 32KB PRG + 8KB CHR, reset `$8000`, 자체 코드만 포함한다. 생성기와 [재현·관측 계약](../docs/nes-branch-contract.md), [검증 JSON](branch-verification.json), [해시 목록](branch-artifacts.json)을 함께 사용한다.

ignored `analysis/local-branch-011/`에 rom-01, mesen-01, rtl-01..04, integrated-01과 baseline/baseline-status를 보존했다. rtl-01은 reset 해제 직후의 미정 bus 1건을 정상 실행에 포함하여 종료 검사 실패했다. 첫 reset-vector 이후 opcode부터 관측하도록 고친 rtl-02가 수정 전 CPU 기준이다. 이 기준에서 주소 오류 48개를 검출했고 다른 분기 검사 오류는 없었다. rtl-03은 upstream CRLF 해시와 생성 사본 LF 해시를 혼동한 assertion으로 컴파일 전 중지됐다. 두 해시를 각각 고정한 rtl-04가 최종 수정본이다. 실패 기록은 최종 통과로 세지 않았다.

이전 010 source/status/evidence 131개와 각 이전 단계 소스, 원래 실험 draft 해시를 검증했다. GBC C44의 152 source hashes·Quartus 입력·2,048 boot bytes PASS. pinned upstream clean, 기존 driver 및 제품 MCU/FPGA 변경 없음. 무료 FLOAT 실행을 재사용했고 종료 후 관련 simulation/license process 및 18000–18002 listener는 0개다. 원본 라이선스와 서버 로그는 Git 및 증거 사본에서 제외했다.

다음은 taken/not-taken/page-cross 분기 각 cycle의 IRQ sampling을 독립적으로 검사하는 작업이다. 현재 분기 진단에서는 IRQ를 비활성화했으며 통합 회귀는 기존 MMC3 시나리오에 한정된다. RDY/DMA, MMIO, 전체 CPU/PPU/APU, NES→SNES 통합, full fit/STA, 일본판 SMB3, 실기 및 240→239/224줄 정책은 미완료다. upstream 개별 license hold도 유지한다.
