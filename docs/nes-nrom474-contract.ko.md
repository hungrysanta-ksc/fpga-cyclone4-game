# NROM474: 같은 프레임 BG 계획 재사용과 진행 기반 E0 간격

2026-10-29. 선택 ARM은 `arm474-02`, materialized patch03, FPGA는 **471-04의 byte 동일 bitstream**, ROM은 실기471과 같은 NMI 이동 scene02다. 기존 실기473의19.610454fps/50.993209ms를 다음 동일 장면 비교 기준으로 고정한다. 새 실기 FPS는 아직 없다. 설치·원복은 [시험 안내](nes-nrom474-trial.ko.md)에 있다.

## 실제 바꾼 경계

1. **ARM planner의 같은 프레임 그룹 재사용.** COMMITTED 프레임의 정상 그룹에 대해33개 source word가 앞선 정상 그룹과 완전히 같으면, 이미 검증·배정한33개 slot을 현재 column·palette 위치에 다시 기록한다. 앞선 group slot은 used라 이후 evict되지 않는다. 새 map word마다 기존 dirty 비교를 수행한다. 예외 fine-row/alternate-tag 그룹은 대상에서 제외하며 기존 tile·범위·palette·raster 검사는 유지한다. hash 동등성을 신뢰하거나 이전 프레임 이력을 추가하지 않는다.
2. **재사용이 없는 장면의 비교 상한.** 첫4그룹에서 재사용이 없으면 나머지는 기존 allocator를 쓴다. 최초 구현의 서로 다른 row 장면에서 약3.9% 추가 명령이 나와 이 상한을 추가했다. 선택본의 추가 비용은 해당 case 약0.44%다. 전체 삭제나 changed-group cross-frame reuse를 구현했다고 부르지 않는다.
3. **E0 조회 사이의 quiet 구간.** 기존4credit·drain·최종ACK loop에서 첫 status는 즉시 조회하고 CRC/identity/counter를 독립 검사한다. 완료 또는 소비 진행이 있으면 바로 진행한다. 진행 없는 유효 응답 뒤 nominal128us 동안 기존 runtime guard를 반복 호출하고 다음 E0를 보낸다. guard는 deadline·CF86·observer/screen service를 계속 처리하며 SPI 진행 중 재진입하지 않는다. 완료 ACK의 뜻과 bank/token/retire 순서는 유지한다.
4. **계측 수정·추가.** E1/E9의 in-place 응답이 opcode를 덮기 전에 snapshot을 저장한다. credit/drain/finalACK의 유효 응답·진행/완료·quiet 대기·누계/최대 cycle과 BG 그룹 재사용 수를 cost schema474에 기록한다. DWT unavailable은 기존 즉시 조회+guard로 fallback한다. quiet 시간은 phase·opcode와 겹칠 수 있으므로 합산하지 않는다. IRQ/service가128us 예산을 넘길 수 있어 hard WCET라고 하지 않는다.

수신 압축2232·ARM 단일 복원·독립 coverage/CRC·출력client2271·loader profile78은 그대로다. FPGA(source/host/queue/plan/receipt/lease), NES/SNES clock·CDC·SNES client ROM은 바꾸지 않았다. input→display→EA ownership도 기존 경로를 유지했다.

## 실제 링크된 ARM 비교

Unicorn M4에서 최종 firmware의 해당 함수 bytes를 ELF와 대조해 실행했다. 실제 RTL static 입력과 live moving RPC의 D1 payload/CRC를 읽어 동일 canonical 입력을 만들었다. cold/warm bank0→1→0, coarseX/NT-X 경계, 두 palette epoch, 서로 다른 row를 포함한 각15case에서 old/new의 슬롯 계획·video15912B·resident 상태가 같았다.

| M4 planner case | 471 명령 | 474 명령 | 해석 |
|---|---:|---:|---|
| 정적 warm | 612,061 | 190,688 | 68.85% 감소 |
| 이동 입력 warm | 621,520 | 172,546 | 72.24% 감소 |
| 서로 다른 row, 정적 파생 | 618,911 | 621,611 | 0.44% 증가 |
| 서로 다른 row, 이동 파생 | 629,477 | 632,177 | 0.43% 증가 |

이는 packet 해석이 아니라 **계획 함수의 명령 수**다. 실제 IRQ/SPI/MMIO/전체 ARM RUN의 cycle이나 전체 FPS로 환산하지 않는다. 기존 계획13.63ms를72% 줄였다고 선언하지 않는다. 실제 결과는 다음474 로그에서 판정한다.

native renderer/reference129장면은96 scrolling frame, raw/예외 mapping, generation wrap, epoch 변경, 양 bank·활성 bank 보존·abort 등11경계와4,234,944B 참조를 통과했다. old/new M4 상태 비교는 이 독립 pixel/reference 검증을 대체하지 않는다.

## 조회·취소 검증

동일한 외부 완료 시각을 둔 deterministic window model에서 E0는18→10회, 완료 시각2050→2194us였다. 조회44.4% 감소와 detection 지연144us가 함께 발생했다. 따라서 조회 감소를 표시 시간 감소로 보고하지 않는다. 이 모델의 추가 구간 한계는1회 status110us+quiet128us이며 실제 IRQ/service 전기적 WCET가 아니다.

credit 최대4, 정확한 final ACK, 잘못된 CRC/ACK identity, quiet 중 STOP/guard 실패 후 추가 SPI 차단, DWT32bit wrap, unavailable fallback을 통과했다. 실제 wrapper body와 in-place E1/E9/70·별도 E0 buffer 시험에서 분류를 확인했다. report의 모든32/64bit counter를 최대값으로 채운 출력은5184/6144B였다.

최종 `live474-02`는 실제 NES/source/SPI→474 native ARM C→FPGA queue/tile→Mesen65816 DMA/VBlank→최종ACK→EA→run136 STOP을 통과했다. 실제 source 입력을 사용하며 기존 geometry text는 host에 공급하지 않는다. 30ACK/4144VRAM bytes/2VRAM commands/1표시 commit과 독립 막대 mask를 확인했다. observer는42→350758→351002 후 정지했다. 관련66개 QSF input과 선택 ARM의 compiled C/header를 hash로 묶었다. 기존 초기 경고84개/RTL errors0도 보존한다.

live C host는 DWT clock이 없어서 quiet fallback이 동작하며, quiet 시간은 별도 deterministic model이 검증한다. PLL/PSRAM·초기 적재는 모델, ARM은 native C, SNES CPU는 emulator이며 한 live frame의 기능 증거다. 전체60초 실기 일정·capture 누락 없음·MMC4/5·60Hz 증거가 아니다. 실제 최종 M4 menu cleanup의 정상 및 program/DONE/busy/token4fault도 기존 외부 응답 모델로 통과했다.

## 전체 비용과 전달 조건

| 항목 | 471 | 474 | 차이 |
|---|---:|---:|---:|
| ARM text | 201641B | 202569B | +928B |
| ARM data | 10040B | 10040B | 0 |
| ARM bss | 18468B | 18552B | +84B |
| RUN workspace stack | 31848B | 31848B | 0 |
| planner static stack | 272B | 280B | +8B |
| quiet callback static stack | — | 32B | 신규 |
| cost formatter static stack | 72B | 72B | 0 |
| FPGA LE/comb/FF/RAM bits | 14740/13672/8063/185824 | 동일 | 0 |

ARM stack 표는 각 함수의 compiler stack-usage이며 전체 callchain 크기가 아니다. 전체 프레임 이력/RAM을 새로 추가하지 않았다. FPGA는471 byte를 그대로 쓰므로 Quartus를 다시 실행하지 않고 이전 Lite 전체 FIT/관련 timing 결과를 유지한다. nominal setup+0.081ns/hold+0.143ns, 강화 배치 예산−0.036ns와 raw reset/CDC/미제약IO의 한계도 남아 있다.

실제 target 설정은 Flash256KiB/RAM64KiB다. firmware212612B를0x0800c000부터 배치한 파일 후미와 설정된 Flash 끝 사이에는380B가 남는다. BSS 끝0x20007020/stack top0x20010000에서 RUN workspace31848B를 뺀 산술 간격은4984B이며 중첩 호출·IRQ stack을 아직 빼지 않은 값이다. 선택본은 링크 범위에 들어가지만 다음 기능 추가 전에는 코드 크기와 전체 stack 예산을 다시 확인해야 한다.

전달본은 **NROM474-PLANNER-POLL.zip / NES NROM 474.nh1 / nes-progress-nrom474.txt / nes-budget-nrom474.txt / nes-game-last-nrom474.txt**다. 동일 이동 장면CRC0fddf31c·정적428 비교·직전471/이전467/164 복원물을 포함한다. 기존471 전달본과 실기473 raw는 변경하지 않는다.

다음은 사용자의 동일 이동 장면 로그로 FPS·수신/계획/SEAL·credit/drain/finalACK·group 재사용·CRC/STOP/메뉴를 비교한다. 30fps는 중간 목표다. 60Hz를 위해 capture/display 시각·miss/repeat/p95·VBlank 소유권, 남은 ARM 작업과 외부 실행도 계속 검증해야 한다. 이후 필요하면 cross-frame changed-group/raster 재사용과 capture 중첩을 검토하며 이번 구현 범위로 계산하지 않는다.

선택 증거는 `analysis/nrom474-verification.json`, 구성은 `analysis/nrom474-package.json`, raw는 `probes/nes-nrom474/validation01`, 최종 구성·예산 메타데이터는validation02다. 처음의 sandbox GCC 기동 실패, ACK 모델의 section 생략 오류, formatter header 부족, 비교 상한이 없던 후보도 보존했다. 새 라이선스가 필요한 실패는 아니며 Questa는 기존 Starter FLOAT1좌석으로 순차 실행했다.
