# PR127 회고와 다음 구현 인계

2026-10-18. 검토 대상은 PR127의 231–246, 기준 head `201d777fc7c59336d462e81b8bd845108fc8d69d`다. 이 문서는 그 뒤 사용자가 승인한 계획 재설정이며 **새 구현·시험·실기 성공 보고가 아니다.**

## 작업 의미와 PR 경계

60fps 목표의 판단 기준을 개별 압축기 면적에서 전체 화면 경로의 처리량·지연·자원으로 되돌린다. PR127은 C/SNES 증분 개선, FPGA 후보와 기각 근거, 이번 회고·인계까지 담아 종료한다. 사용자가 PR127을 머지한 뒤 원격 master에 포함됐는지 확인하고 새 `codex/` 브랜치·새 PR에서 구현을 시작한다. 이번 PR에서 자동 머지하거나 후속 RTL을 추가하지 않는다.

**이 문서와 [실행 계획](nes-pr127-next-plan.json)이 이전 HANDOFF 및 236–246 문서의 NEXT를 대체한다.** 과거 결과·해시·실패 자료는 수정하지 않는다. 단일 sequencer는 다음 구현으로 선정된 것이 아니라 비교 후보 중 하나다.

## 목표와 완료 기준

1. **최우선: SMB3(J) 첫 레벨 스크롤에서 정상 게임 속도와 약60Hz의 연속 표시를 함께 달성한다.** 게임 CPU 진행, 전송 완료, 최종 표시 완료를 분리한다. 정상 장면을 버리거나 게임을 느리게 해 통과시키지 않는다. NTSC 실제 표시 주기를 측정하고 16.67ms는 60Hz 설계 기준으로 사용한다.
2. 음성·방향키 유지·동시 입력·메뉴 복귀를 보존한다. 평균 표시 수뿐 아니라 실제 표시 간격의 분포·최대 간격·오래된 화면이 남는 시간을 평가한다. 같은 화면이 본래 유지되는 장면은 프레임 누락과 구별한다. 화면 전환과 지속 스크롤 결과를 따로 기록한다.
3. FPGA 전체 LE/LAB/M9K, ARM RUN/IRQ, SNES 코드·WRAM·VRAM 및 공유 버스에 확장 여유를 남긴다. MMC4/5가 같은 bitstream에 모두 들어간다고 약속하지 않는다. 매퍼별 구성도 비교할 수 있으나 fetch-time bank/latch/CHR-RAM 의미를 보존한다.
4. 화면·사운드 안정화 뒤 60초 제한 완화, 오류/본체 리셋 시 안전 정지와 로그 저장, 장시간 입력 품질을 진행한다. 향후 frame-skip/state-save/mute를 위한 상태 소유권을 고려하되 지금 구현하지 않는다. save SRAM은 작업 버퍼로 사용하지 않는다.

현재 생산/실기 기준은227, 기능 비교 기준은240이며 **240도 배치되지 않은 후보**다. 241/246은 기각 상태다. 새 계획으로 이 판정을 바꾸지 않는다.

## 확보한 결과와 미완료

| 범위 | 재사용할 결과 | 미완료·해석 제한 |
|---|---|---|
| 231 출력 증분 | 같은 스크롤에서 E1 평균5094.70→1483.83B, 약70.87% 감소 | 전체 입력/출력/표시 FPS가 아님 |
| 232 실제65816 소비 | warm69 중1VBlank51→64, 2VBlank18→5 | 952/954/955/963/968의 map/OBJ burst 잔존 |
| 233 전체 ARM RUN | 출력 증분 연결, RUN/IRQ 후 여유1616B | 입력은227. 새 입력까지 연결한 메모리·시간 승인값 아님 |
| 234–240 입력 생성 | 905..975의71관측 frame: 실제 collector/query/encoder/SPI/C 경계의 복원 비교 | 게임 CPU 전체/실제 ARM 시간/최종 SNES 표시를 모두 연결한 실기 아님 |
| 240 전체 보드 | FIT 요구15898LE/1003LAB/54M9K | 한도15408/963/56 대비490LE/40LAB 부족 |
| 241 control-only ROM | 기능 비교 통과, 자원 악화 기록 | FIT16218LE/1022LAB/55M9K로 기각 |
| 246 공유 연산기 전체 | 25정상+17경계, byte/CRC/base 및7출력 view stall 통과 | FIT16027LE/1011LAB/55M9K, 240보다129LE/8LAB/1M9K 증가. 기각 |

246의 FF42개 감소는 LE 절감이 아니었다. 제어·선택·RAM 접근 회로 비용이 절감분을 상쇄한 것으로 해석하되 개별 mux의 면적을 확정하지 않는다. RAM은 M9K로 정상 추론됐다. 유효 bit 사용량62%를 물리 M9K 여유38%로 읽지 않는다. 실제 요구량은55/56이다. 배치 실패를 배선/전기 문제로 확정하지 않는다.

246 합성 정상 case의130097..1043674cycle(22MHz 환산5.91..47.44ms)은 ready stall을 포함하며 실제 SMB3 71frame 시간 비교가 아니다. 자원만 맞추면 속도도 통과한다는 근거로 사용할 수 없다. 246에서71frame 통합은 실행하지 않았다.

## 전체 경로의 남은 병목

- **공유 SPI:** 현재2.625MHz에서60Hz 기준5468.75clock-B/frame. 236 ready4 모델 최대5341B=16.277ms로97.7%를 점유한다. 약0.389ms의 wire 여유를 CPU 여유나 실제 완료 여유로 바꾸지 않는다. 간격/poll/stall/다른 명령이 추가되고 ready1에서는5941B,69개 중2개 초과다.
- **SNES:** 232의5개 burst는 현4192 charge 기준을48..560 초과한다. charge는 DMA bytes와 설정 비용의 모델이며 CPU cycle 자체가 아니다. 주원인은 map/OBJ이며 raw만 더 압축해 해결된다고 가정하지 않는다. 비활성 VRAM 사전 업로드는 유효 범위·목적 bank·token·최종 완전성 조건과 실제 VBlank 작업 시간을 입증해야 한다.
- **ARM·동시성:** 새 입력 decoder를 실제 RUN/IRQ에 연결한 비용, source 생성/전송/ARM/SNES 간 겹침과 같은 SPI 경합이 미검증이다. 각 단계의 시간을 무조건 더하거나 가장 큰 값 하나로 끝내지 않는다. 큐는 일시적 burst를 흡수할 뿐 평균 대역폭을 늘리지 못한다. 처리량과 capture-to-display 지연을 구별한다.
- **자료 범위:**71frame는60fps 기준 약1.2초 분량의 좁은 관측 자료다. 이를 장시간/모든 mapper 보장으로 확대하지 않는다. 기존 다른 scroll/transition/raw-heavy 자료가 있는지 먼저 확인하고, 없는 장면을 이미 검증한 것으로 채우지 않는다.

## 기존 구현을 다시 만들지 않을 것

- 225 가로 원형 맵, 211 상주 physical pattern slot, 231 dirty 누적, 232 팔레트/raw/업로드 개선은 이미 있다. 231 생성 planner에도225 column 배치가 사용된다.
- 맵 갱신 원인을 실제 새 타일, slot 교체, group/row 배치 변화, alternate destination의 오래된 내용으로 나눠 본다. group ordinal 배치가 churn을 만들 가능성은 조사 가설이지 확정 원인이 아니다.
- 236의 단순화 비교는 **출력 경로를 고정한** 입력 코덱 비교다. shift-only 최대6922B/8초과, literal-only7616B/22초과라는 결과는 그대로 보존하되 출력도 함께 바꾼 모든 설계를 기각한 것으로 확대하지 않는다.
- 236 병렬 B의 기각 범위는 **227 입력을 유지하고 출력만 우회하는 안**이다. 입력 payload만19.078..19.785ms였다. 전체 변환 위치 재배치는 별도 미검증이다. ARM→SPI→FPGA→SNES 재공급은 SPI 우회가 아니다.

## 다음 PR의 단계와 중단 기준

### P0 — 같은 스크롤의 전체 예산표와 변경 원인

먼저 기존71frame와 기존 무거운 장면 자료로 한 행당 source generation/조회 비용, 입력·출력·제어 SPI bytes와 gap, ARM 변환, SNES upload/명령/commit을 연결한다. 값마다 실제 실행/모델/미측정을 표시한다. frame ID, cold/warm, 화면 전환 여부, 겹침 가능한 작업과 같은 자원에서 직렬인 작업을 명시한다. 전체 연결의 시간 상한이 없는 항목은 UNKNOWN으로 남긴다.

완료 산출물은 재사용 가능한 작은 분석과 비교표다. 새 광범위 관측 체계나 게임 실기 재시험부터 만들지 않는다. 어떤 map/slot/row 변경이 비용을 만드는지 확인해 P1의 후보를 좁힌다.

### P1 — 표현·처리 위치를 포함한 후보 비교

1. **A:240 전용 회로의 제한적 단순화.** query/encoder 중복과 실제 필요한 연산을 비교한다. 단일sequencer는 이 안의 하위 후보이며 자동 선택하지 않는다.
2. **B:수집 정보의 의미를 보존하는 필드/행 변경 전달.** 고정5741B 배열을 만든 뒤 다시 byte-diff하는 비용을 줄일 수 있는지 본다. 단순 PPU write 이벤트만으로 rendering을 복원할 수 있다고 가정하지 않는다. MMC4 latch/MMC5/CHR-RAM 등 fetch-time 관측과 순서·overflow 처리가 필요하다.
3. **C:입력·출력·일부 변환 위치의 공동 변경.** 기존 parallel aperture를 쓸 때 실제로 사라지는 SPI bytes와 추가65816/FPGA 계산, RAM·ROM 접근 비용을 함께 센다. 소프트웨어 처리 전체를65816으로 옮긴다고 미리 결정하지 않는다.

현재 SPI 설정은 영구적인 전기 한계라고 확정하지 않는다. 속도 변경은 양쪽 endpoint·실제 clock/edge·CDC·IO·보드 여유를 확인한 별도 조건부 후보로만 다룬다. clock/SDC/timeout 완화로 기존 실패를 통과시켰다고 보고하지 않는다.

후보별 전체 LE/LAB/M9K와 ARM/SNES 메모리, wire+control 비용, source/ARM/SNES 실행 비용, throughput/최대 화면 나이, 새 의미 제약과 구현 위험을 나란히 적는다. 기존 byte stream 동일성은 구현을 유지할 때만 기준이다. **새 형식은 복원한 의미·최종 pixel·오류/취소 계약의 동등성으로 평가한다.**

완료 기준은 근거 있는 이득 범위와 남은 여유를 갖춘 한 후보의 선택이다. 단순히 칩 한도 또는 wire16.67ms에 간신히 맞추는 안은 승인하지 않는다. 모든 후보가 실패하면 어떤 하한/누락 때문에 실패했는지 기록하고 표현·처리 위치를 다시 판단한다. 작은 counter/opcode/seed 수정으로 자동 후퇴하지 않는다.

### P2 — 선정 후보만 최소 구현·전체 보드 검증

변경된 의미와 소유권 경계의 최소 reference/cancel/STOP/partial 검증을 하고 전체 보드 자원·타이밍 검증으로 간다. 독립 kernel FF 수를 전체 절감으로 대신하지 않는다. 동일 실패 후보의 변경 없는 FIT는 반복하지 않는다. 실패하면 P1의 가정을 수정하고 구조적 근거 없이 연산기를 확장하지 않는다.

전체 새 입력 ARM RUN/IRQ, host/NES 최초 오류 전달, 실제 final displayACK→commit→lease/retire, 필요한 CDC/IO/STA를 선택 소스 쌍에서 확인한다. 기존 동일 소스의 검증은 재사용한다. 처음부터 전체 게임/매퍼 전수 cosim을 실기 진입 조건으로 만들지 않는다.

### P3 — 실제 첫 레벨 스크롤

최소 진입 조건이 갖춰지면 새 파일 쌍과 관측 방법을 갖춘 시험판을 제공한다. 대상은 `Super Mario Bros 3 (J).nes`; 선택 화면을 지나 월드맵 숫자1에서A, 첫 레벨에서 RIGHT+B 유지/A 반복으로 달리기·스크롤을 확인한다. 오프닝·정지 화면의 개선을 대체 지표로 삼지 않는다. 기존227/044 복원 반복이나 부품 재확인을 요청하지 않는다.

가능한 실제 표시 시각/완료 기록과 영상을 대응시켜 sustained scroll의 frame 간격·최대 gap·latency를 판단한다. CRT 촬영 대각선/색 변화는 사용자 설명대로 패널 불량이나 렌더링 오류로 취급하지 않는다. 실제 플레이가 가능하고 사운드·입력·메뉴 복귀가 유지되는지 확인한 뒤 장시간 테스트로 넘어간다. 현재 자료만으로 모든 게임/매퍼60fps를 보장하지 않는다.

## 다음 작업자가 반드시 보존할 경계

- GBC164, 생산227 및 독립 복원 자료, 사용자 save SRAM, 기존 봉인 probe·실패·원본 제약은 보존한다.
- physical CHR identity/epoch, active/inactive bank, partial failure 시 기준 무효화, ACK별 소유권을 유지한다. record 수신/PREPARED/transport consume를 실제 표시 완료로 취급하지 않는다.
- 새 형식은 생산자·수신자 버전과 CRC/길이/범위 검사, STOP 후 drain/새 세션 기준을 함께 바꾼다. ACK 제거·확인 없는 덮어쓰기만으로 속도를 얻지 않는다.
- ROM/trace/binary/라이선스/raw log는 private. 공개 clone만으로 모든 private 재현이 가능하다고 쓰지 않는다. Questa가 필요해질 때는 기존1seat FLOAT 절차를 사용하며 이 문서 작업에서 시뮬레이션을 재실행하지 않는다.
- GitHub는 지정된 개인 계정만 사용하며 대화형 회사 계정 선택으로 대체하지 않는다. PR 제목/본문은 한국어, `작업 목표 → 작업 내용 → 작업 결과 → 작업 의미` 순서다.

## 근거와 재개 위치

| 읽을 자료 | 용도 |
|---|---|
| [실행 계획 JSON](nes-pr127-next-plan.json) | 현재 목표·P0–P3·머지 후 새 PR 경계 |
| [227 실기](nes-game227-hardware01.ko.md) | 실제 구동/소리/메뉴 성공, 스크롤60fps 미완료 |
| [231](nes-delta231-contract.ko.md), [232](nes-sparse232-contract.ko.md), [233](nes-runtime233-contract.ko.md) | 증분 출력·실제 SNES·ARM 및5개 burst |
| [236](nes-path236-contract.ko.md) | 동일 자료 비용과 대안 기각의 정확한 범위 |
| [240](nes-source240-contract.ko.md), [246](nes-source246-contract.ko.md) | 기능 기준과 전체 공유 후보 기각 |
| `analysis/source240-verification.json`, `analysis/source246-verification.json` | 기존 검증 근거. 새 회고 검증으로 재분류하지 않음 |
| 작업공간 private `probes/nes-path236/analysis02/result.json` | 후보별 same-frame 비용. ROM/trace를 Git에 복사하지 않음 |
| 작업공간 private `probes/nes-source240/progress.json`, `probes/nes-source246/progress.json` | 선택 소스·실패/중간 결과 위치. 완료 finalizer 재실행 금지 |

외부 참고는 설계 비교 근거이지 우리 보드 성능 증명이나 upstream 코드 도입 승인이 아니다.

- [REHLS, ICCD2017](https://mesl.ucsd.edu/pubs/Lotfi_ICCD2017.pdf): 연산 공유 시 선택 회로·순차 실행 비용을 함께 고려한다. 논문의 다른 디바이스 절감률을 Cyclone IV 예상값으로 사용하지 않는다.
- [PocketNES ppu.s](https://github.com/Dwedit/PocketNES/blob/main/src/ppu.s): 쓰기 시점의 dirty tile/row 관리. GBA 처리량을 SNES에 대입하지 않는다.
- [Project Nested Gfx_Interrupt.asm](https://github.com/Myself086/Project-Nested/blob/master/Assembly/Project/Gfx_Interrupt.asm): 의미별 graphics queue와 표시 처리 참고. JIT/ROM 변환 체계를 이식한다는 계획이 아니다.
- [SNESdev Timing](https://snes.nesdev.org/wiki/Timing): VBlank/DMA 이론 용량. CPU/설정 비용을 빼지 않은 최대치를 현4192 charge의 대체 승인값으로 쓰지 않는다.

다음 세션은 **PR127 머지 확인 → 최신 master 기준 새 브랜치 → P0 예산/변경 원인 분석 → P1 후보 선택**으로 시작한다. 이 문서 작성만으로 새 설치물·FPS·회로 기능이 완성됐다고 보고하지 않는다.
