# CF85: 독립 입력 클록을 이용한 제한 진단 차단 계약

이 후보는 CPU/PPU 없는 CF68 셸에 클록 감시를 추가한 **디지털 검증용 CF85**다. 정상044/GBC, CF68 RTL·fit·071 파일 쌍, 성공한 SDREPORT084를 바꾸지 않는다. 새 ARM·FPGA 설치 파일은 없다. `installable=false`이며 다음 조건을 충족하기 전 실기에 설치하지 않는다.

## 해결하려는 경계

CF68의 CLKIN과 내부84MHz PLL은 같은 입력에 의존한다. 고정 MCU 소스도 HSE를 FPGA MCO1과 CPU PLL에 공급한다. 이 입력이 멈추고 `locked`가 HIGH로 남으면 같은 클록의 카운터는 CE를 해제할 수 없다. 기존068의 CE LOW 9µs 반례는 유효하다.

CF85는 기존 물리 포트 `SNES_SYSCLK`를 두 번째 클록으로 연결한다. 기존 `src/fpga/pin.qsf`의 핀은 A9다. 이것은 **포트·핀 지정 근거**이며 사용자 기기에서 RESET 중에도 계속 동작한다는 관측이 아니다. 시험은 CLKIN 8MHz, 별도 기준 클록20MHz·약21.477MHz·22MHz를 공급한다. 새 기준 클록의 실제 가용성·배선·전압은 미확인이다.

## 동작

| 조건 | CF85 동작 |
| --- | --- |
| 기동 | 두 영역이 각각 상대 클록의 변화8회를 관측하기 전 접근 금지. 이어 기존1600 CLKIN 주기의 초기 대기와 reset 해제 FF를 거침 |
| CLKIN 정지, 기준 클록 계속 | 기준 영역의2단 동기화·64주기 무변화 검출 후 기존 메모리 비동기 reset을 올림 |
| 기준 클록 정지, CLKIN 계속 | 기준 클록 분주 비트의2단 동기화·32 CLKIN 주기 무변화 검출 후 같은 reset을 올림 |
| 단일 고장 뒤 클록 재개 | fault가 유지되며 자동 재무장 금지. 적재 상태 무효화. raw PLL lock loss 또는 재구성으로 초기화한 뒤 새 준비·적재·비교 필요 |
| 두 클록 동시 정지, locked HIGH | 검출 불가능. CE LOW 9µs 반례를 의도적으로 유지. 전체 클록 정지 안전성을 주장하지 않음 |
| raw locked LOW | 기존 비동기 reset/핀 해제 유지. 이때 중단된 쓰기는 유효한 메모리 쓰기로 취급하지 않음 |

기준 영역은 CLKIN마다 반전하는 heartbeat를 본다. 메모리 영역은 기준 클록4비트 카운터의 bit3을 본다. 분주하여8MHz 수신 쪽에서20–22MHz 원신호를 직접 샘플링할 때의 alias를 피한다. 이것은 해당 시험 주파수 범위의 liveness 검사이며 임의 주파수·듀티·지터·메타안정성 승인이나 주파수 측정기가 아니다.

새 fault는 자기 자신의 reset 입력으로 되먹임하지 않는다. 그렇게 연결하면 fault가 즉시 지워져 재시작 루프를 만들 수 있다. `clock_allowed`는 기존 메모리 reset에만 연결한다. H1 전체나 SPI MISO의 독립 정지까지 이 변경의 보장으로 확대하지 않는다. 저장용 SRAM OE/WE는 기존대로 비활성이고 RUN의 parser 거부·시작선 분리도 유지한다.

## 검증 범위

실제 생성된 top→boundary→loader/reader→PSRAM 핀에서 시험한다. 과거060 C의 적재256바이트·CHECK256바이트 GPIO 기록을 그대로 재생한다. CHECK의96KiB 준비는 TB의 loader 입력을 통한 핀 쓰기이며, 전체96KiB C SPI 적재로 부르지 않는다.

그 뒤 실제 loader/reader 입력에 직접 트래픽을 주어 읽기/쓰기 × 멈추는 클록2종 × 정지 위상8종을 검사한다. 한쪽 정지는5µs 안에 fault를 내고 핀/MCU_RDY를 비활성화해야 한다. 정상 및 단일 고장 중 CE LOW는8µs를 넘으면 실패한다. 두 클록 동시 정지 반례만 별도 표식으로 이 성공 집계에서 제외한다. 메모리 모형은 guard reset 이후 중단된 쓰기를 저장하지 않는다. 이는 데이터 무효화 정책이며 정전 중 데이터 보존을 검증한 것이 아니다.

실행 로그의 최종 `pin_bytes`에는 후속 고장 트래픽도 포함된다. C 재생 구간은 앞의 `PASS C_PREFIX085`와 결과 JSON의 `prefix_pin_bytes`/`checked_response_bits`로 구분한다. 준비도는 기존4완료/7부분/1미완료를 유지한다.

```powershell
& ./tools/run_nes_clock_guard085.ps1 -Python $Python -FloatWrapper $FloatWrapper -QuestaBin $QuestaBin -Out $FreshASCIIPath -HostRun $Frozen060Host
# 같은 호출을 각각 새 폴더에서 -Mutation bypass-guard / same-clock / nonsticky 로 실행
```

기존 Starter FLOAT 한 seat를 순차 사용한다. `HostRun`은 공개 저장소에 없는 기존060 C GPIO 증거이므로 public clone만으로 위 통합 시험을 재현할 수 있다고 주장하지 않는다. 공개 `nes_clock_guard085.py`는 새 디렉터리에 CF85 RTL을 생성한다. 이전068 도구·archive는 수정하지 않는다.

## 후속 승인 순서

1. RESET-held 구간의 SNES_SYSCLK 가용성과 독립성, 실제 클록 범위를 확인한다. 기존 MCU `get_snes_sysclk()`/명령FE 경로를 먼저 검토한다. 옛 `clk_test.v`는96000000주기 창을 쓰므로 현재 base의 실제 구동 주파수·명령 지원·측정창 완료를 확인하지 않고 반환값을 Hz로 보고하지 않는다. CF85에는 명령FE 측정기를 추가하지 않았다. 추가 사용자 분해·LED·PC USB 연결을 요구하지 않는다.
2. CF85 동일 소스로 새 fit/STA를 실행하고 A9 클록 라우팅·CDC 동기화·비동기 assert 경로·reset 해제와 외부 지연을 검토한다. 변경된 셸에068 내부 slack이나3168경로 예산을 그대로 붙이지 않는다. 두 클록 동시 고장/전원 상실은 별도 정책의 근거와 제한을 남긴다. 정상 클록 가정만으로 P2를 완료 처리하지 않는다.
3. 위 판단을 반영한 후보 ID와 최신 MCU의 승인·전체80/96KiB 적재/비교/STOP·복구 회귀를 연결한다. 구형 MCU는 CF85를 승인하지 않아야 한다. 자동 ID 우회나071과의 임의 혼합 금지.
4. 같은 최종 RTL fit의 ASM/압축/ARM/base/menu manifest와 정상044 복원을 묶어 P3를 만들고, 외부에서 실행하여 TXT/영상으로 회수하는 P4를 진행한다. 084의 저장·화면·정상044 복원 성공은 유지하며 같은 시험을 반복하지 않는다.
