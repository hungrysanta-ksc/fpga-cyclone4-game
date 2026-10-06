# MMC3 매퍼 단독 검증 계약

SPDX-License-Identifier: MIT.

[Questa FLOAT 규칙](questa-execution.md)을 그대로 적용한다. NROM 실행기를 변경하지 않고 `tools/run_nes_mmc3.ps1`이 같은 검증된 임시 FLOAT 래퍼로 실제 작업을 실행한다.

```powershell
& ./tools/run_nes_mmc3.ps1 -Python $PY -FloatWrapper $FLOAT -QuestaBin $QUESTA -Upstream $UPSTREAM -Out "$env:TEMP/nes-mmc3-unit"
```

새 ASCII 출력 경로를 사용한다. 설치 경로는 전역 AGENTS.md 참조. 별도 라이선스 smoke, 유료 라이선스 또는 영구 환경 변경이 필요하지 않다.

고정 upstream `49a0a662e244469ca77b2155746a066df704ffae`의 `MMC3.sv` 해시를 확인하고 MMC3 module만 추출한다. 기존 선언 정리 함수와 명시적 savestate package import만 적용한다. register/IRQ 동작 수정은 없다. savestate VHDL helper는 원본을 컴파일한다. 원본 파일과 COPYING, 정확한 변환 diff는 ignored 출력에 보존한다. MMC3 및 savestate helper의 개별 파일 license hold는 유지한다.

- flags=4, submapper=0, CHR ROM, 2KB CIRAM인 표준 Mapper4 경로다. 다른 매퍼·MMC6·Acclaim·MMC3A 변종을 검증하지 않는다.
- master clock은 빠른 단독 시험용 10ns다. CE와 m2_inv는 각각 12 ticks에 한 번이며 6 ticks 떨어져 있다. 통합 NES의 cart/CPU 위상을 모델링한 것은 아니다.
- PRG는 두 mode × 256개 R6/R7 값 × 4개 8KB slot의 양 끝 주소를 검사한다. 상위 두 비트 무시, 고정 last/second-last bank, R6 교환을 포함한다. ROM write transaction은 이번 검사에 포함하지 않는다.
- CHR는 두 inversion mode × 256개 register 값 조합 × 8개 1KB slot의 양 끝 주소를 검사한다. R0/R1의 2KB 정렬과 모든 8bit bank 값을 포함한다. 각 레지스터 조합은 value+37×register로 구분한다.
- $A001 enable/protect 네 상태에서 $6000/$7FFF read/write 허용과 활성 RAM 물리 주소를 확인한다. $A000 양 모드의 네 nametable 선택을 확인한다. CHR ROM write 허용은 0이어야 한다.
- IRQ는 1/2 falling-M2 sample 동안 low였던 A12 거부, 3 samples 뒤 상승 수용, high 유지 중 중복 count 방지, latch 유지, E001 비승인 동작, E000 disable/ack, disabled count, reload 지연/중간 reload, latch=0 반복 IRQ, reset을 검사한다.
- A12 상승을 12개 master 위상에 배치한다. 각 19개 IRQ 관측을 12번 실시하고 핵심 5개 edge case의 실제 tick modulo 12가 모두 존재해야 한다.
- 출력 trace를 Python 주소 oracle로 검사한다. 원시 PRG/CHR 출력은 각각 PRG offset, CHR 0x200000 기반 bank address이고 RAM은 0x3c0000 기반이다. CPU RAM/외부 크기 mask/cart_top 전체 통합을 검증한 것은 아니다.
- PASS marker, Fatal/Error 부재, trace 수·IRQ case 수·위상 범위·주소/권한 oracle을 모두 요구한다. 실제 trace의 주소·권한·IRQ 변조 및 절단 5종이 같은 검사에서 거부돼야 한다.

Mesen MMC3 구현 소스를 독립 의미 비교에 참고했지만 이 시험에서 Mesen runtime 비교를 수행하지 않았다. 다음은 원본 Mapper4 진단 ROM과 CPU/PPU 통합 경로, 실제 PPU A12 및 CPU IRQ service 관측이다.
