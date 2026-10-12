# NES165 CHECK 카운터의 명령 완료 경로

같은 PR108의 후속 작업이다. [secondary OAM 배치](nes-oam-secondary165-contract.ko.md)에서 실제 배치·배선은 성공했지만 CHECK 응답 주소에서 다음 주소 갱신까지 −1.218ns의 setup 부족이 남았다. 원시 배선 경로를 기준으로 그 부분만 수정했다.

## 변경 계약

기존 low8/high11 카운터 증가에서 carry-chain의 입력까지 오류 판정이 들어가 긴 경로를 만들었다. 각 비트의 증가를 XOR와 하위 비트 carry 조건으로 표현해 명령 완료 조건이 긴 덧셈 앞단에 들어가지 않도록 했다. high11의 기존 `next_carry8`는 그대로 사용한다. 다음 주소 값, 오류·중지 우선순위, SPI 프레임 처리와 명령 완료 클록은 바꾸지 않는다.

첫 후보는 전체 배치 후 최악 경로가 `load_data` 레지스터의 enable 입력으로 이동했다. 두 번째 후보는 해당8비트에만 `AUTO_CLOCK_ENABLE_RECOGNITION OFF`를 적용해 데이터 피드백 mux로 구현하도록 했다. 다른 레지스터나 전체 프로젝트의 enable 인식 설정은 변경하지 않았다. 두 번째 후보와 첫 후보의 기능 RTL은 이 합성 속성 하나를 제거하면 바이트 단위로 같다.

카트리지 세이브 SRAM, 기존 사운드·입력·STOP, native 영상 경로, OAM, CPU/PPU/MMC3/APU는 변경하지 않았다. SDC의5.5ns/5.3ns 목표나 클록 주기를 완화하지 않았다. 새로운 파이프라인이나 대기 클록도 없다.

## 검증 범위

- 실제 기존 decoder와 카운터 값524,288개 전수 비교. 19비트 범위와 low8/high11 경계를 모두 포함한다.
- 오류·응답 일치 여부·리셋·SPI 중첩·명령16종·carry 패턴 조합262,144개 비교. 총786,432개 상태에서 모든 decoder 레지스터의 다음 값이 일치했다. 계층 주입을 사용한 한 클록 상태 비교이므로 실제 SPI 실행과 구분한다.
- 잘못된 high carry를 넣은 대조군은 `check_next` 불일치로 검출했다.
- 실제 SPI master 상승 edge 샘플 시점의 기존 경계 시험을 적용했다. 검사98회, 실제 쓰기8회, CHECK 읽기6회, 실패 조건6회, ACK 경계·완료·START가 통과했다. 전체384KiB 적재나 새 SMB3 게임 부팅을 반복한 것은 아니다.
- SPI 시험의 첫 실행은 옛149의 응답 ID `5F` 기대값에서 실패했다. 변경 전 회로도 정확히 같은78번째 검사에서 실패했고 실제 현재 decoder는 이미 `6B`다. 원래 시험 파일은 보존하고 기대값 두 곳만 현재 계약으로 바꾼 별도 실행본이 통과했다. DUT의 ID나 오류 검사를 완화하지 않았다.
- 두 번째 후보의 기능 검증은 합성 속성 하나만 제거한 실행 RTL과의 정확한 대조로 재사용한다. 재배치에 따른 타이밍 결과는 별도로 새 배치에서 측정한다.

최종 수치와 선택 여부는 [검증 기록](../analysis/check165-verification.json), 다음 작업은 [인계](../cores/nes/HANDOFF.ko.md)에 기록한다. 합성 추정 LE와 실제 배치 LE를 구분하며, 같은 클록 setup/hold 결과가 외부 IO·CDC·실기 승인이라는 뜻은 아니다.

## 재현과 후속 기준

[생성기](../tools/nes_check165.py)는 보존된 secondary map03의 해시를 확인해 새로운 ASCII 작업 폴더에 복사하고 `nes_rom_spi.sv`만 바꾼다. [상태 비교](../tools/test_nes_check165.py), [SPI 경계 시험](../tools/test_nes_check_path165.py), [결과 검사](../tools/check_nes_check165.py)를 사용한다. Questa는 기존 FLOAT wrapper로 실행한다.

무변경 OAM·부팅·A/B·044 시험을 반복하지 않는다. 다음에는 실제 선택 배치의 남은 경로와 필요한 PSRAM/SPI/SNES IO·CDC 조건만 확인하고 MCU RUN 수신·변환·ACK, 사운드·입력·STOP·경과시간, 전체 link/stack을 연결해 SMB3(J) 첫 레벨 실기로 간다. 완료된 원시 evidence와 record/audit는 수정하거나 다시 실행하지 않는다.

## 이번 선택 배치의 결과

선택 map03/reproduce03: 전체 배치·배선 **15,015LE, 961/963LAB, 35/56M9K**. 같은 클록 최저 setup **-0.488ns**, hold **+0.158ns**. 같은 클록 setup 부족이 남았습니다. 기존 SDC 그대로이며 3 corner198행을 확인했다. 혼합 도메인 raw setup -12.665ns, 미제약 입력54/출력57포트는 별도 미완료다.

map01은 카운터 표현 변경만으로−0.552ns/15023LE/962LAB, map02는 load_data의enable제어 변경으로−0.536ns/14968LE/962LAB였다. map02의 최악 경로가 check_next의동기clear 입력으로 옮겨가 map03에서 해당19비트의 ALLOW_SYNCH_CTRL_USAGE만 OFF로 바꿨다. 세 후보 모두 추가 레지스터·클록 지연 없이8316레지스터와197104메모리비트를 유지한다. 기능 비교는 두 합성 속성만 제거하면 실제 실행한 후보와 동일함을 확인해 재사용했다.

다음 경로: Use selected CHECK map03: repair measured boot check_failed -> loader state.RECEIVE (-0.488ns at nominal5.952ns), byte_count -> miso_hold (-0.332ns at5.3ns target), and check_next -> check_busy (-0.174ns at5.5ns target); no uncontrolled latency/SDC relaxation or repeated attribute-only fits. Then necessary external IO/video CDC and MCU RUN receive/convert/ACK with existing audio/input/STOP/elapsed time, whole firmware link/stack, SMB3 first-level hardware. Preserve save SRAM and164; no unchanged OAM/boot/A-B/044 repeat.
