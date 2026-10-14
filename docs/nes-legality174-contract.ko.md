# NES174 — 명령 허용 상태 분리와 타이밍 회복

174의 비트평면·묶음 전송 후보를 실기에 올리기 위해 ROM 적재기의 공유 오류 경로를 줄였다. **최악 setup은 -0.807ns에서 -0.098ns로 개선했지만 아직 실패다.** map01을 다음 개발 기준으로 보존한다. map02는 -1.344ns로 악화되어 채택하지 않는다. 새 설치 ZIP은 없으며 기존173과174 MCU를 섞어 설치하지 않는다.

## 변경 계약

map01은 `nes_rom_loader.sv`만 변경한다. BEGIN·START·END·DATA를 상태상 거부하는 네 비트를 다음 onehot 상태와 같은 에지에서 갱신한다. 현재 상태를 한 에지 늦게 복사하는 방식이 아니다. RECEIVE의 길이 비교는 현재 값을 그대로 사용한다. sticky fault를 상세 error code 우선순위 mux와 분리하되 명령 수락·응답 에지, 상태 전이, 카운터, 오류 우선순위, WRITE/HOLD 중단 후 drain은 유지한다.

과거165의 조합식 평탄화와 달리 상태 조건을 레지스터에 미리 갖추는 변경이다. `reject_state[3:0]` 네 레지스터가 실제 배치에 존재함을 확인했다. reset과 active_reset은 IDLE 거부값1110으로 초기화한다. DATA와 STOP 동시 입력, 명령 충돌, commands_blocked 및 길이 경계의 기존 의미도 유지한다.

map02는 map01에서 SPI `error_code[3:0]`의 AUTO_CLOCK_ENABLE_RECOGNITION·ALLOW_SYNCH_CTRL_USAGE만 OFF로 지정했다. 기능 RTL 차이는 이 합성 속성뿐이다. 대상 `check_busy → error_code` 경로는 +2.005ns로 좋아졌으나 loader `phase[8] → loaded_bytes`가 -1.344ns, 새 legality 레지스터 경로도 -0.113ns가 되어 전체 후보를 거부한다. 이 설정만 반복하거나 seed를 순회하지 않는다.

## 검증 결과

| 후보 | 전체 실제 클록 setup 최솟값 | load_valid → fault | legality 입력 | 배치 자원 | 판단 |
| --- | --- | --- | --- | --- | --- |
| 기존 cross174 | -0.807ns | -0.807ns | 없음 | 15,076LE / 963LAB / 36M9K | 이전 실패 기준 |
| legality174 map01 | -0.098ns | +1.968ns | +0.113ns | 15,056LE / 961LAB / 36M9K | 개발 기준, 배포 불가 |
| legality174 map02 | -1.344ns | +2.117ns | -0.113ns | 15,065LE / 963LAB / 36M9K | 미채택 |

map01의 실제 클록 hold 최솟값은 +0.148ns다. 기존의 더 엄격한 구현 예산 결과(-0.438ns)도 보존한다. 실제 클록·SDC·false path·multicycle은 변경하지 않았다. FIT 성공과 타이밍 통과는 구분한다. 외부 IO·CDC·실기 FPS를 통과했다고 주장하지 않는다.

- 실제 기준·후보 loader 비교: 294,912개 조건과 1,056개 명령/reset 순서 통과. 매 에지에서 legality가 현재 상태와 일치하는지 확인했다.
- 잘못된 한 에지 지연, commands_blocked 무시, DATA/STOP 우선순위 손상 세 변이를 모두 검출했다.
- 실제 SPI→boot→READ16 연결: 100회 읽기, 7ACK, 19잘못된 응답, 72취소, 2겹침, 1,126,009에지 통과. 219 wire frame, SCK2.625MHz·SS 간격2µs다. READY·loaded count를 설정한 연결 시험이며 새 전체 ROM 쓰기·게임 부팅 시험은 아니다.
- map02는 합성 속성만 다름을 바이트 변환으로 확인하고 map01의 기능 증명을 재사용했다. 별도 map02 시뮬레이션을 실행했다고 기록하지 않는다.
- 픽셀 수집기·SNES172 코드·MCU는 바뀌지 않아 이전 cross174·batch174 검증을 재사용한다. 새 전체 부팅·A/B·044 반복은 없다.

## 다음 작업

1. **map01에서 시작한다.** 남은 `control.check_busy → control.error_code[0..3]`의 enable 경로는 5논리 단계다. 비정상 응답 조건과 error code 유지/갱신 조건이 공유되는 지점을 분리할 수 있는지 검토한다. map02의 설정 변경이나 과거 오류 단일-owner 변경을 그대로 반복하지 않는다. 실제 응답 에지와 오류 우선순위가 바뀌면 계약과 MCU 간격을 함께 수정해야 한다.
2. 수정한 경계만 검증하고 전체 실제 클록 setup/hold를 확인한다. 그다음 외부 PSRAM·SNES·SPI와 reset/CDC의 필요한 검사를 실시한다. 내부 타이밍 실패 상태에서 배포 준비 검사를 반복하지 않는다.
3. 통과하면 기존 `probes/nes-batch174/arm01`(여유1,040바이트)과 **새 FPGA를 쌍으로** 묶는다. ROM·로그 형식과 source pin을 연결하고 실제 SMB3에서 화면 지속·갱신 속도·사운드·입력·메뉴 복귀를 확인한다. 모델 성공만으로60fps를 선언하지 않는다.

세이브 SRAM·GBC·164 복원본을 보존하고 RUN 중 SD 쓰기·두 번째 MCU 프레임 버퍼를 추가하지 않는다. 연속 영상·사운드 → 장기 플레이/오류·리셋 로그 → 입력 유지 순서다. 전체 테이블 재전송 비용은 여전히 남아 있으며 SNES의 기존 변경분 DMA를 중복 구현하지 않는다.

[검증·소스 해시](../analysis/legality174-verification.json) · [묶음 전송](nes-batch174-contract.ko.md) · [현재 인계](../cores/nes/HANDOFF.ko.md)
