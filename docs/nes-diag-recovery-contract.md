# NES064 진단 하위 읽기·설정·관측 계약

이번 경계는 수동 적재/비교 진단에서 **실제 SD 읽기와 FPGA 설정 함수의 오류를 반환하고, 실패한 SD를 다시 사용하지 않는 것**이다. 063의 전체 SPI 기록과061 적재 전용 RTL을 유지한다. CPU/PPU RUN·설치 이미지·물리 STM32 실행은 포함하지 않는다.

## 소유권과 오류

- 수동 진단은 USB OTG IRQ를 저장/차단하고 SNES RESET을 유지한 뒤 runtime을 시작한다. 044/056 함수와 원래 프로그래머는 그대로 남는다.
- 진단의 SD 읽기는 버퍼가 있는 CMD17 단일 블록만 사용한다. 기존 다중 블록 상태가 있으면 CMD12로 종료하고 응답을 확인한다. 응답 길이·명령 번호·CRC7·R1 오류와 실제512바이트의 네 DAT lane CRC16을 확인한다. 카드 없음/상태 불량/오프로딩은 실패한다. 실패한 DATA/ACK/SD 명령을 재전송하지 않는다.
- `wait_busy`에는100tick/2,000,000poll 상한이 있다. 기존 명령 응답200,000회·데이터 시작2,000,000회 상한의 실패를 전달한다. native 오류는 sticky이며 `DRESULT` 오류가 FatFS `FR_DISK_ERR`로 전달된다. 부분 읽기 바이트가 있어도 오류를 성공으로 취급하지 않는다.
- active 상태에서 자동 SD 초기화와 쓰기를 거부한다. CTRL_SYNC는 카드 오류/잔여 전송이 없는 읽기 경계에서만 성공한다. 이전 offload의 `sd_offload_partial` 잔여 값과 실제 `sd_offload`/`ff_sd_offload` 소유권은 구별한다.
- SD 오류가 발생하면 GPIO를 복원하고 RESET/USB 보호를 유지한다. base 파일을 같은 실패한 SD에서 다시 읽거나 메뉴로 돌아가지 않는다. FPGA 설정 오류만 있고 SD가 정상일 때는 별도 checked programmer로 base 복구를 시도한다.
- checked programmer는 독립 FIL·256바이트 버퍼·검사한 RLE를 사용한다. 파일1MiB, 출력2MiB/3000tick, PROGB/INITB/DONE 각100tick/50,000,000poll 상한을 둔다. open/read/close·잘린 RLE·0길이 run·길이 초과·핀 대기 실패를 반환한다. `panic`, CLI와 설정 재시도는 없다.
- 보류 상태는 write LED를 켜고 ready LED를 점멸한다. RESET/USB를 차단한 의도적인 보호 루프에서 외부 전원/RESET 조치를 기다린다. 패드 취소를 구현한 것으로 보지 않는다.

상한의 tick은100Hz SysTick 기준 정책값이다. tick wrap과 멈춘 tick의 poll 종료는 host로 검사했으며 실기 경과 시간을 측정한 값은 아니다. TIM2 기반 기존 SPI `delay_us`, CPU 정지, 물리 watchdog과 모든 호출의 전체 시간 보장은 포함하지 않는다.

## 진행 관측

| 단계 | ready | read | write |
| --- | --- | --- | --- |
| VALIDATE / CHECK | 켜짐 | 250ms 간격 반전 | 꺼짐 |
| CONFIG / LOAD | 켜짐 | 꺼짐 | 250ms 간격 반전 |
| RECOVER | 켜짐 | 켜짐 | 켜짐 |
| BLOCKED | 250ms 간격 반전 | 꺼짐 | 켜짐 |

진단 시작 시 밝기 설정에 관계없이 GPIO LED 모드로 전환하고, 안전한 종료에서 원래 PWM/GPIO 모드와 세 논리 상태를 복원한다. SysTick은 정렬된 phase/ownership scalar만 읽으며 여러 필드의 report는 foreground가 소유한다. native activity/error LED는 active 진단 동안 양보한다. UART는 phase/error/25% 경계를 기록한다. active UART 송신/flush 대기는1tick/100,000poll로 제한하고 전달하지 못한 문자는 RAM counter에 남긴다. LED 가시성은 실제 기기에서 확인해야 한다.

064 생성 표식은 `NES VERIFY 064 80.nh1` / `NES VERIFY 064 96.nh1`, 로그 이름은 `nes-verify-last-064.txt`다. **아직 SD에 복사하거나 실행할 배포물이 아니다.** FPGA CF61/protocol59는 유지하며 파일 동일성은 별도 쌍 manifest가 필요하다.

## 재현과 근거 구분

```text
python tools/nes_diag_recovery_host.py --out <fresh-host> --gcc <gcc>
python tools/nes_diag_recovery_host.py --out <fresh-session> --gcc <gcc> --session --reference <frozen063-host>
python tools/nes_diag_recovery_checks.py --platform <pinned062-src> --out <fresh-unit> --gcc <gcc>
python tools/nes_diag_recovery_checks.py --platform <pinned062-src> --out <fresh-mutation> --gcc <gcc> --mutation sd-success
python tools/nes_diag_recovery_checks.py --platform <pinned062-src> --out <fresh-mutation> --gcc <gcc> --mutation fpga-done
python tools/nes_diag_recovery.py --baseline <private062-arm> --out <fresh-arm>
python tools/verify_nes_diag_recovery.py --evidence <frozen064>
```

상위 host는 공개 생성 진단 ROM을 사용하고 SD/FPGA 설정/GPIO를 모형으로 제공한다. 하위 host는 해시가 고정된 비공개 플랫폼에서 실제 command/CRC/wait/read/UART 함수 및 FatFS `f_read`/`validate`/`clust2sect`를 원문 추출한다. FAT chain·카드·핀·tick은 모형이다. ARM 준비는062 manifest와 플랫폼 해시를 확인한 입력이 필요하며 공개 clone만으로 원시 근거 audit/ARM 재현을 주장하지 않는다. ARM 빌드는 `tools/build_nes_diag_recovery_arm.ps1`을 사용한다.

063 보드 재생은 기록/생산 RTL이 같다는 검사 범위에서 재사용한다. UART 출력·SD 호출·CPU 실행에 따른 실제 지연은 SPI 기록의2µs mock 시간에 포함하지 않는다. 새 fit/Questa 실행을 한 것으로 기록하지 않는다.

## 다음 완료 조건

메뉴 재적재의 FPGA SD offload와 늦은 SD 로그 쓰기·active 밖 UART 대기는 아직 legacy 경로다. H08/H09 전체 복구는 부분 완료다. 다음에는 이 호출들을 실제 하위 함수까지 종료 가능하게 연결하고, 메뉴 준비 실패/재진입/로그 실패를 검증한다. 외부 PSRAM 정확한 부품·min/max 제약, 최종 FPGA ASM/ARM 쌍·압축 roundtrip·백업/rollback·실기 관측은 별도 gate다. 전체 NES959LAB/4LAB 여유·소비자·CDC·STA와 구분한다.
