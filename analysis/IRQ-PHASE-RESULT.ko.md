# NES-P2-IRQ-PHASE-010 — IRQ 경로의 상대 사이클 확인

2026-10-05. **이번 자체 Mapper4 진단에서는 IRQ 처리 중 추가 CPU 사이클 차이가 발견되지 않았다.** 이전 009의 IRQ acknowledge 4 PPU-dot 차이는 IRQ 전 polling read에서도 이미 존재하고, 비교한 IRQ 버스 동작 10개까지 그대로 유지된다. 절대 IRQ 시점이나 전체 CPU 호환성의 완료 선언은 아니다.

| ROM counter | IRQ 전 RAM8 read의 RTL/Mesen dot | E000 ack RTL/Mesen dot | 첫 stack write→ack CPU cycles |
|---|---|---|---|
| 3 | 211/215, 229/233, 247/251 | 328/332 | 18/18 |
| 4 | 213/217, 231/235, 249/253 | 330/334 | 18/18 |
| 5 | 214/218, 232/236, 250/254 | 331/335 | 18/18 |
| 6 | 216/220, 234/238, 252/256 | 333/337 | 18/18 |

스택 저장·vector 읽기·PHA·RAM3 read/modify/write·ack의 주소, R/W, 값 및 상대 사이클을 검사했다. 첫 stack write 기준 두 구현 모두 `0,1,2,3,4,7,10,11,12,18` CPU cycles다. RTL cart_ce/cpu_ce 365쌍은 2 master ticks 차이로 같은 bus 값을 보인다. E000 ack를 1 CPU cycle 늦춘 변조 기록은 검증기가 거부했다.

## 기존 기능 유지와 기록

- 같은 ROM·코어로 RTL 140.02ms 실행 두 번, 최종 오류 0/기존 경고 42개. 관측 코드 외 core/adapter/ROM 변경 없음.
- 기존 통합 검증 통과: 4프레임 245,760화소 exact, BG latch 65,552건 검사 및 화소 사용 fetch 61,440건 exact, PRG 오류 0, CPU period 오류 0, IRQ service 총 6회.
- 최종 RTL의 frame/fetch/control/edges 8개 파일과 Mesen의 RGB/frame/trace 6개 파일이 009 최종 기록과 각각 SHA256 일치한다. 계측이 기존 관측 결과를 바꾸지 않았다.
- 처음 추가한 독립 posedge 관측 block에 master_ticks 갱신 순서 race가 있어 기존 control 기록과 1 tick 어긋났다. 기존 tick 증가 뒤로 계측을 옮긴 rtl-02가 최종 기준이다. rtl-01 및 최초 testbench를 삭제하지 않았다. 이것은 관측 timestamp 수정이며 core timing 수정이 아니다.
- 기존 009 source/status/evidence 215개 해시 검증, 이전 각 단계 source 및 원래 실험 draft 보존. GBC 152개 source hash·Quartus inputs·2,048 boot bytes 검증 통과. 원본 upstream clean.
- 기존 무료 Starter FLOAT 경로로 실행했고 종료 후 관련 simulation/license process와 18000–18002 listener가 없음을 확인했다. 신규 라이선스나 별도 smoke 시험은 필요하지 않았다.

원시 증거는 ignored `analysis/local-mmc3-irq-phase-010/{rtl-01,rtl-02,mesen-01,baseline,baseline-status}`에 보존했다. 공개 가능한 요약은 [검증 JSON](irq-phase-verification.json), [해시 목록](irq-phase-artifacts.json), [재현·관측 계약](../docs/nes-irq-phase-contract.md)을 따른다. ROM은 기존 009의 최종 원본과 동일하다.

## 남은 차이와 다음 작업

4-dot offset의 절대 기원은 아직 특정하지 않았다. 두 구현의 boot/alignment 및 callback 위상이 공통 외부 시간 기준으로 보정되지 않았고 Mesen IRQ 입력 상태도 이 getState에 노출되지 않는다. 현재 증거로 IRQ 입력 assertion→서비스 latency 전체를 동등하다고 선언할 수 없다.

분기에서 버려지는 읽기 주소가 RTL은 branch target `$E182`, Mesen은 sequential `$E186`으로 다르다. 현재 진단은 ROM 읽기라 부작용이 없지만 전체 bus conformance는 미완료다. 다음 우선 작업은 taken/not-taken/page-cross branch의 bus cycle 및 IRQ sampling을 자체 짧은 진단으로 분리하는 것이다. 관측 위치 차이인지 실제 T65 bus 동작 차이인지 확인한 뒤 수정 여부를 결정한다.

제품 목표인 Rev.D/NTSC 일본판 SMB3 Mapper4 정상 플레이, 메모리 stall, 전체 PPU/APU/CPU 호환성, NES→SNES 통합, full fit/STA, 실기는 미완료다. 240→239/224줄 정책과 개별 upstream license hold를 그대로 유지한다. GBC C44 / sd2snesHST 0.9.0과 공통 제품 코드는 변경하지 않았다.
