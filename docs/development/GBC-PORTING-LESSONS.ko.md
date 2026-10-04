# GBC 이식 회고와 다음 코어에 전달할 교훈

기준: 2026-10-04 공개한 [sd2snesHST 0.9.0](https://github.com/hungrysanta-ksc/sd2snesHST/releases/tag/v0.9.0). 개발 후보는 G13C44다. 이 문서는 당시 실패·수정·실기 보고와 최종 소스를 대조한 회고이며, 새 NES 코어의 실행 성공을 뜻하지 않는다.

## 1. 먼저 읽을 기준선

- 게임 실행 로직은 **Gameboy_MiSTer 기반 FPGA 코어**를 이식했다. **SameBoy는 공개 CGB 부트 코드의 출처**다. SameBoy 소프트웨어 에뮬레이터 전체를 포팅한 것이 아니다. [의존성 등록부](../DEPENDENCY-REGISTER.ko.md), [원본 부트 고지](../../licenses/SameBoy/README.md).
- 실행 구현 기준: `35ef4aef14fc6abef6495a980b7f00f257e5174f`; 배포 대응 소스 기준: `a2b1fb59390a96f70bbc8588a63e465831e7e247`. 문서·소스 묶음 커밋과 실행 코드 변경을 구분한다.
- [제품 버전·공개 자산 대응표](../../release/product-version-map.json), [C44 실행 파일](../../release/c44-artifacts.json), [검증](../../release/c44-verification.json), [재현 빌드](../BUILD-C44.ko.md)를 함께 읽는다.
- 사용자 실기 결과는 [호환성 기록](../COMPATIBILITY.ko.md)의 범위만 인정한다. 특정 장면 통과를 전체 게임·장시간·모든 지역판 통과로 확대하지 않는다.
- 아래 과거 단계의 원본 로컬 기록은 [근거 색인](../../release/gbc-porting-evidence.json)에 파일명과 SHA256으로 식별했다. 원본 ROM·세이브·덤프·영상은 공개하지 않았다. 로컬 기록 해시가 공개 저장소에서 그 시험을 재실행할 수 있다는 뜻은 아니다.

## 2. 성공한 시스템의 경계

```text
SD/게임 선택 → STM32 로더·저장·설정 → 코어별 FPGA 이미지
                                      ├ 게임 CPU/영상/음향/매퍼
                                      ├ PSRAM·SRAM 중재·프레임 소유권
                                      ├ SNES 표시 프로그램 → SNES PPU
                                      └ 입력 전달·오디오 출력
```

코어 계산만 합성되면 완료되는 구조가 아니다. 카트리지 버스에서 SNES가 코드를 읽는 시간, 화면을 전송하는 시간, FPGA가 메모리를 쓰는 시간이 경쟁한다. SPI 명령·부트·RUN·메뉴·리셋도 하나의 수명 주기로 검증해야 한다. 공통화할 경계는 [개발 구조](ARCHITECTURE.ko.md)를 따른다.

최종 FPGA는 15,155/15,408 LE, M9K 56개를 사용했다. 메모리 비트 사용은 424,896/516,096이지만 블록 여유와 같지 않다. 최소 constrained setup +0.056ns, hold +0.072ns는 [C43 검증 기록](../../release/c43-verification.json)의 수치이며 C44는 같은 FPGA 바이트를 쓴다. 이것만으로 모든 보드 I/O·CDC가 signoff됐다고 할 수 없다. **NES에는 별도 FPGA 이미지를 사용**하며 이 GBC 자원 점유를 NES에 합산하거나 그대로 예상치로 쓰지 않는다.

## 3. 증상에서 일반 원인을 찾은 사례

| 사례 | 확인한 내용과 수정 | 다음 코어에서 처음부터 확인할 것 |
| --- | --- | --- |
| C11/C14 진단 OFF 뒤 폴리오 점멸, C15 정상 | C15는 반복 VRAM 전송을 프레임 경계에서 분리하고 길이 설정을 수정했다. 실제 VBlank/V카운터 조건과 유한 대기를 사용했다. 단순 대기 증가였던 C14는 실패했다. | 진단의 실행 시간도 스케줄을 바꾼다. 첫 설치/반복 설치, 프레임 0번 줄, IRQ/DMA/HDMA 중첩을 각각 시험한다. 물리 경합의 세부 원인은 확정하지 않았다. |
| C10 입력 밀림 | 입력 처리 중 다른 메모리 작업을 보류하는 여유 확보가 필요했다. | 평균 대역폭만 보지 말고 최장 버스 점유, FIFO peak, pending 작업과 누적 backlog를 측정한다. FIFO를 키우기 전에 장기 처리율을 확인한다. |
| C18 약 20초 → C19/C20 약 5초지만 검은 화면 | 빠른 전송 성공과 게임 시작 성공이 달랐다. C21에서 로딩 반환 뒤 기존 `snes_set_mcu_cmd(0)` 경로의 D0/D2 명령과 새 로더의 충돌을 바로잡았다. 이후 실행·저장 로드·소리·폴리오가 확인됐다. | 로더 함수 단위 시험에 그치지 말고 실제 호출자, 로딩 후 cleanup, 버스 소유권과 RUN 유지까지 포함한다. 약 5초는 당시 게임의 관측값이지 모든 ROM의 상한이 아니다. |
| 에스트폴리스가 로딩에서 정지 | 초기 저장 RAM 범위에서 헤더 기반 용량·뱅크 처리로 확장했고 32KiB 저장을 확인했다. | 게임명 예외보다 헤더·지원 매퍼·ROM/RAM 크기·주소 배치를 검증한다. 헤더 인식은 하드웨어 매퍼 지원의 증거가 아니다. |
| Street Fighter 아케이드 그래픽 깨짐, C25 정상 | `cart_ready`에 따라 카트리지 ROM 읽기 동안 CPU enable을 대기시켰다. 실기 수정 효과와 기존 게임 회귀를 확인했다. | 빠른 CPU·캐시 miss·외부 RAM 지연에서 응답 전 데이터를 소비하지 않는지 검사한다. 시각적 증상을 곧바로 팔레트 결함으로 단정하지 않는다. 물리 원인 전체를 실기로 입증한 것은 아니다. |
| 메뉴에서 B/RESUME 시 영상 정지, C30 정상 | 메뉴 helper를 카트리지 SRAM에서 SNES WRAM으로 옮기고 메뉴·응답 대기에도 페이지 교환을 처리했다. | CPU 정지/출력 drain/페이지 소유권/메뉴 표시/복귀 순서를 나눠 검증한다. 음악이 들린다는 이유로 CPU·영상 전체 정상이라고 판단하지 않는다. |
| C35 SAVE STATE 실패, 리셋 검정·0KB 로그 | SPI read-ahead가 유효 영역 뒤를 읽는 문제를 재현했다. C36은 마지막 바이트를 증가 없는 읽기로 분리하고 완료 대기·READY timeout·짧은 읽기 처리를 추가했다. | 1바이트/끝 주소/정지한 코어/응답 없음/부분 SD 쓰기를 시험한다. 진단도 고장난 전송에 무한 대기하면 증거를 잃는다. |
| 봄버맨 시작 전 정지·마리오 타일 문제, C41 개선 | MBC1/MBC1M 뱅킹 경로를 수정했다. 봄버맨·기존 MBC5 게임과 마리오 타일이 정상화됐다. | 서로 다른 게임의 증상도 같은 매퍼 경계에서 생길 수 있다. 타이틀만 아닌 뱅크 전환·모드·상태 복원까지 검증한다. |
| 마리오 캐릭터 미표시, C42 정상 | SRAM DMA는 read를 유지하고 주소만 바꿨는데 기존 client가 첫 바이트만 요청했다. 주소 변화도 새 접근으로 처리했다. | read strobe 상승 에지만 거래라고 가정하지 않는다. 주소 연속 변화, 같은 주소 유지, 응답 시점, backpressure를 구분한다. |

### 현재 소스에서 읽을 위치

- 로딩과 실행 전환: [memory.c](../../src/firmware-overlay/src/memory.c), [main.c](../../src/firmware-overlay/src/main.c), [gbc_load_duplex.sv](../../src/fpga/gbc_load_duplex.sv), [gbc_load_bus_mux.sv](../../src/fpga/gbc_load_bus_mux.sv), [host start guard](../../src/fpga/gbc_host_start_guard.sv).
- 카트리지 wait·매퍼: [gb.v](../../src/fpga/gb.v)의 `cart_cpu_wait`, [full_core_link.sv](../../src/fpga/full_core_link.sv)의 `selected_rom_bank`/`selected_ram_bank`.
- 연속 DMA: [gbc_save_client.sv](../../src/fpga/gbc_save_client.sv)의 `access_changed`와 응답 forwarding. 현 버스 계약을 이해한 뒤 NES 전용 계약으로 재설계한다.
- 전송 마지막 바이트·timeout: [gbc_memio.c](../../src/firmware-overlay/src/gbc_memio.c). 테스트 mock에도 실제 SPI read-ahead 부작용을 넣는다.
- 표시·메뉴: [renderer 생성기](../../src/renderer/build_gbc_product_renderer.py), [C40 메뉴 생성기](../../src/renderer/build_g13c40_renderer.py), [display pages](../../src/fpga/display_pages.sv). 생성된 기계어만 수정해 재현 경로를 끊지 않는다.

## 4. 저장·RTC·리셋을 뒤늦게 붙일 때의 비용

배터리 저장과 실행 상태 저장은 별개다. `WRITE SRAM`은 게임 저장 RAM을 SD에 기록한다. `SAVE STATE`는 CPU·RAM·영상·디지털 음향·매퍼·진행 중 latch까지 복원해야 한다. 레지스터 이름 목록만 저장하면 timer/PPU pipeline 같은 숨은 상태가 빠진다.

[상태 세션](../../src/fpga/gbc_state_session.sv), [상태 전송](../../src/firmware-overlay/src/gbc_state_transfer.c), [파일 형식](../../src/firmware-overlay/src/gbc_state_format.c), [슬롯](../../src/firmware-overlay/src/gbc_state_slots.c)에서 safe capture, 세션 잠금, 두 세대 파일, readback 검증, 부분 복원 실패 시 저장 억제를 읽는다. 게임 상태뿐 아니라 출력 drain/reset/rearm과 음향 재개도 복원 계약에 포함한다. GBC schema `00350002`를 NES 상태 파일에 그대로 사용하지 않는다.

자동 저장은 SRAM 변경 감지 후 지연 기록한다. 즉시 전원을 끄기 전에 WRITE SRAM의 완료를 확인하는 경로를 남긴다. SD 오류를 단순 성공처럼 표시하지 않고 유효한 이전 저장을 보존한다. 새 코어의 파일명·core ID·ROM identity·상태 버전을 구분하여 GBC 저장을 잘못 읽지 않게 한다.

MBC3 RTC는 보드 시계·UTC 시차와 게임 시계 상태를 분리했다. 전원 OFF 경과 보정, 44/48바이트 footer 읽기와 48바이트 쓰기, LOAD STATE와 현실 시간의 관계를 명시했다. 초 미만 위상은 파일에 보존하지 않는다. [RTC codec](../../src/firmware-overlay/src/gbc_rtc_codec.h), [RTC 테스트](../../tools/test_rtc.py)는 파일 경계와 오류 주입의 참고 사례이며 NES에 RTC가 필요하다는 뜻은 아니다.

## 5. 자원·타이밍·화질에서 피할 우회

1. 코어만이 아니라 로더·메모리 중재·CDC FIFO·영상 변환·음향·저장·진단을 포함해 물리 fit한다. 비트 수 대신 M9K 블록 수, LE뿐 아니라 LAB 배치 제약도 본다. C25에서 여러 fit 실패를 보존한 이유다.
2. 고정 upstream/QSF/SDC/도구/seed와 성공·실패 결과를 함께 남긴다. 양수 slack을 얻기 위해 false path나 clock 요구를 근거 없이 완화하지 않는다. [타이밍 한계](../TIMING-EXCEPTIONS.ko.md)와 [경로 감사](../P0-STA-COVERAGE.ko.md)를 함께 읽는다.
3. SNES로의 지속 전송은 첫 프레임과 반복 프레임이 다르다. source → complete → publish → display의 frame ID, 최대 age, 버스 blackout을 측정한다. 고정 이미지 endpoint의 픽셀 일치는 실제 producer/consumer 공동 처리량 증거가 아니다.
4. GBC의 해상도·팔레트 변환·64슬롯·전송량·클록·메모리 주소를 NES에 복사하지 않는다. NES의 영상 전체를 먼저 예산화하고 NTSC/PAL, crop/overscan, 색·음향·프레임 정책을 명시한다. 품질 저하가 필요하면 근거를 제시하고 사용자와 결정한다.
5. R 빨리감기는 사용자가 선택한 별도 모드다. C38은 정상 캡처 1프레임과 가속 중 캡처를 생략한 8프레임으로 약 3배를 목표로 했고 실기 동작을 확인했다. 내부 최대 배속과 체감 배속은 같지 않다. 이 예외를 정상 모드 프레임 손실 허용으로 확대하지 않는다.

## 6. 진단과 검증 설계

진단 레지스터·타이밍 관측·파일 출력 정책을 분리한다. C44는 `GBC_FILE_LOGS=0`으로 load/cap/state 파일 기록을 끄되 기존 실행·저장·통신 선택 플래그는 유지했다. `DIAGNOSTIC`이라는 이름만 보고 컴파일 옵션을 제거하면 기능까지 빠질 수 있다. [로그 정책](../../src/firmware-overlay/src/gbc_log_policy.h), [ON/OFF 검사](../../tools/test_log_policy.py), [검증 결과](../../release/c44-verification.json).

검사 순서는 작은 합성 fixture/오류 주입 → 실제 함수 호출자·RTL 통합 → full-fit·STA/CDC 검토 → 사용자 실기다. 각 결과에 소스/제약 해시, 도구, 입력, 포함하지 않은 경계와 timeout/fail을 기록한다. 실기에 필요한 시점에는 수정이 들어간 설치 패키지와 한정된 검사 순서를 제공한다. 사용자 성공 보고 뒤 같은 범위의 로그를 반복 요구하지 않는다.

게임별 디버그는 일반 원인을 발견하기 위한 표본으로 사용한다. ROM/RAM 규모, 매퍼, 연속 DMA, 일반/배속, 메뉴·저장 전환 등 동작 범주로 회귀 표본을 고른다. 처음 해리포터 한 게임이 성공한 것이 범용 호환성을 보장하지 않았으며, 이후 RAM·ROM wait·MBC1·DMA 수정을 통해 범위를 넓혔다.

## 7. 빌드와 공개의 재현성

- 독립 출력 폴더, 원본 보존, 소스/SDC/산출물 해시를 기본으로 한다. FPGA 빌드는 ASCII 경로와 고정 도구로 재현한다. 구체 명령은 [빌드 가이드](../BUILD-C44.ko.md).
- MCU 헤더의 빌드 시각 ID 4바이트만 가변이었다. 그 외 전체 바이트가 동일할 때만 성공본 ID를 고정한다. 다른 코드 차이를 normalize로 숨기지 않는다.
- MCU·FPGA·SNES renderer의 혼합 설치를 검사한다. UI 버전 문자열만 일치한다고 정상 세트로 보지 않는다.
- 소스 ZIP에는 고정 upstream 빌드 입력과 고지를 동봉하고 오프라인 준비·손상 거부를 확인했다. 사용자 저장소의 GitHub 자동 Source code ZIP은 실행 코어의 대응 소스가 아니다.
- 공개 0.9.0의 자산은 고정한다. 제품 문서에는 제품 버전만, 내부 C44 대응은 개발 저장소에 남긴다. 첨부는 **01 업데이트 → 02 소스 → 03 매니페스트 → 04 SHA256SUMS**이며 파일명·본문·매니페스트·업로드 순서를 맞춘다.
- 배포 초안을 사용자가 수정했다면 서버 본문을 먼저 읽고 반영한다. 최종 태그가 임시 `untagged-…`가 아닌 제품 버전인지, 머지된 커밋·서버 해시·문서가 일치하는지 공개 전에 확인한다.

## 8. NES 작업의 첫 완료 조건

[NES 인계 계획](../../cores/nes/HANDOFF.ko.md)에 따라 후보 출처·라이선스와 자원/영상 경로를 먼저 검증한다. 가능한 후보는 실제 독립 합성과 최소 진단 ROM 통합으로 이어간다. 제안서만 작성하고 작업을 끝내지 않되, 아직 측정하지 않은 성능·호환성·완료 일정을 약속하지 않는다.
