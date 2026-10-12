# NES165 로더 READY 직접 판정 검증

165 영상 경로 진척: 로더 READY 판정을 단순화하고 reader 마지막 사이클 판정을 미리 계산해 실제 SPI/boot/reader 동등성을 검증했습니다. 전체 타이밍 이득이 없어 새 후보를 채택하지 않았습니다. 선택 구현 predecode165/map03/reproduce03final. 후보 15017LE/963LAB/35M9K, 실제 클록 setup-1.994ns. 외부IO·CDC·MCU 연결과 실기 확인은 남아 있으며 설치164·세이브 SRAM을 보존합니다. 새SD 없음.

[수치와 재현 근거](../analysis/eligibility165-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md).

## 문제와 변경

직전 tag165/map02의 최악 경로는 로더 fault→run 판정→loaded 판정→CHECK 활성→명령 오류 캡처로 이어져−0.616ns였다. 조합 논리5단 중 배선 지연이67%였고, 같은 상태를 여러 번 조합하는 부분이 있었다.

새 후보는 로더가 `check_loaded = !active_reset && !fault && state==READY`를 직접 내보내게 한다. 기존 `loaded && !loader_run && !boot_fault`와 값이 같다. boot의 CHECK 활성 조건과 sticky CHECK 오류 조건에 이 출력을 연결해 중복 계산을 줄였다. 추가 클록 지연·fault 저장·READY 선행 추정은 없다. 원래 loaded/RUN 출력과 로더 쓰기 상태기계·펄스 길이도 그대로다.

SPI는 tag165/map02의 독립 요청 주소 저장 회로를 함께 시험했다. 이 코드는 이전에 미채택된 실험이므로 새 후보 전체의 타이밍으로 다시 판단한다. 실행문은 기존 시험과 같고 '검증된 READ만 저장한다'는 오래된 주석 한 줄만 실제 queued READ 저장 동작에 맞게 고쳤다. 이전 완료 archive는 수정하지 않았다.

첫 배치 map01에서는 로더 fault→명령 오류가+0.919ns로 개선됐으나 reader remaining[3]→data_hold[5]가−0.856ns가 되어 미채택했다. 후속 map02는 ACTIVE 상태의 `remaining==1` 판정을 `read_last` 레지스터로 대체했다. SETUP까지 READ_CYCLES==1을 준비하고, ACTIVE에서는 다음 사이클을 위해 remaining==2를 저장한다. ACTIVE 중 read_last==(remaining==1)이 유지된다. 데이터 샘플·ACK·HOLD/RELEASE 사이클과 CE/OE 유지 시간은 바꾸지 않았다.

## 검증 범위

- 실제 로더 RTL의16상태 값×4리셋 해제 비트×2fault와 enable/request/failed8조합, 총1024조합에서 기존 READY 판정과 오류 조건이 같았다. fault 차단을 누락한 대조 회로는 검출됐다.
- 실제 SPI·boot·READ16 연결에서 기존 SPI 레지스터 및 기존 boot 출력 전체를 매 클록 비교했다. PASS TAG165 edges=1271681 reads=124 acks=7 corruptions=19 cancels=72 overlaps=2.
- 추가26로더 오류: 읽기24위치, CHECK_BEGIN 이전, READ 프레임 전송 직후/SS 캡처 이전을 시험했다. 오류 코드9/6과 요청 차단·reader 중단이 유지됐다.
- READ/ACK7주소 경계, 응답 순간19주소 비트 오류, STOP·hard fault·reset72중단, 동시 오류2경우도 새 결선에서 확인했다. loader READY·길이·유휴 주소와 짧은 reader 단계용 queued STOP 일부는 시험용으로 심었다. 전체 ROM 쓰기·게임 부팅·새 SNES 실행이 아니다.
- 기존 SPI 조건부1409024상태/393216캡처와 대조 시험은 실행문이 정확히 같은 것을 확인해 재사용했다. 주석 한 줄 변경만 정규화했다. 모든 임의 상태의 무조건 동등성 또는 형식 증명으로 주장하지 않는다.
- 별도 reader 시험은 READ_CYCLES1/2/3/16과 보드 값16의 두 위상에서 CHECK/RUN 양쪽의 기존 레지스터·핀을 비교했다. 120읽기·126리셋 중단·5클록 정지 리셋과 잘못된 마지막 사이클 대조 시험이 통과했다. 짧은 주기는 상수 데이터 모델이며, 실제 READ16/70ns 모델은 위 연결 시험에서 검증했다. 출력 포트 미연결 경고170개는 계층 이름으로 직접 관측하는 출력들에서 발생했다.
- 총61개 배치 입력 중4개 RTL을 변경했고57개는 바이트가 같다. 재생성한 소스와 배치 소스를 비교했다. QSF·SDC·클록과 PSRAM 펄스를 바꾸지 않았다.

## 배치·타이밍 결과

|항목|결과|
|---|---:|
|전체 FIT/ROUTE|통과|
|LE / LAB / M9K|15017 / 963 / 35|
|실제 클록 최악 setup|-1.994ns|
|실제 클록 최소 hold|+0.154ns|
|로더 fault→명령 오류 캡처|+0.384ns|
|요청 태그 저장 / 응답→카운터|+2.070 / +0.420ns|
|reader 마지막 판정 저장 / 샘플 제어|+2.251 / +0.993ns|
|추가 배치 목표 최악 setup|-1.994ns|

네 클록과 세 동작 조건의 setup/hold를 함께 판정했다. 클록 주기·false path·multicycle을 완화하지 않았다. **전체 타이밍 이득이 없어 새 후보를 채택하지 않았습니다.** 외부 입력54개/출력57개 미제약과 혼합 클록 경로는 별도 미완료이며, 이 결과를 전체 보드 타이밍 또는 설치 승인으로 확대하지 않는다.

최종 map02의 reader 마지막 판정과 샘플 제어는 각각+2.251/+0.993ns로 통과했다. 그러나 host 클록에서 `audio.dac_release[1] → native_spi.held[13].ena`가−1.994ns로 실패했고, 메모리 클록도−0.203ns로 실패했다. 합성 보고서에서 native_records.dr[1], native_prepared.sr[1], pad.host_release[1]이 audio.dac_release[1]과 병합된 것을 확인했다. 따라서 사운드 데이터 처리 오류라는 뜻이 아니라 **여러 모듈이 공유하게 된 리셋 해제·수신 허용 경로**다. 해당 경로는 논리3단, 데이터 지연13.793ns 중 배선11.598ns(84%), 해제 신호 fanout83·held enable fanout88이다. 오디오를 끄는 식으로 우회하지 않는다.

현재 LAB963/963으로 배치 여유가 없다. 특정 경로 개선만 보고 채택하거나 같은 소스로 배치를 반복하지 않는다. 다음에는 이 공유 해제 신호의 지역별 보존과 held 저장 허용 신호의 fanout 분리를 검토하되, 리셋 해제 순서·동일 사이클 handshake·중단 조건이 유지되는 범위로 제한한다. 이는 후보 제안이며 아직 구현·검증한 결과가 아니다.

## 다음 작업과 의미

SELECT predecode165/map03/reproduce03final. Rejected eligibility165 map02 nominal -1.994ns, worst nes_dac162:audio|dac_release[1] -> nes_live_joint:core|nes_native_spi165:native_spi|held[13]. Mapping explicitly merges native_records.dr[1],native_prepared.sr[1],pad.host_release[1] into audio.dac_release[1]; this is shared reset-release fanout, NOT an audio sample defect. Inspect split/local preserved release and SPI held enable fanout with same-edge handshake/reset/cancel semantics, then check all clocks including memory -.203ns. Reuse READY/reader-terminal/CHECK tests; do not repeat compare165 equations/SPEED, tag165 guarded capture, or unmodified fits. Then necessary native-video IO/CDC/reset + MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack and minimum SMB3(J) hardware. No unchanged CHECK/OAM/full writes/A-B/044 or cartridge save SRAM.

이번 작업은 실기 영상 전송 회로의 동작 속도를 맞추기 위한 배선·상태 판정 구현이다. 일반 디버그 항목을 늘리는 작업이 아니다. 최소 안정성 확보 후 실제 SMB3 첫 레벨로 진행한다. 원본 GBC·설치164 사운드·입력·STOP·메뉴 및 사용자 세이브는 보존한다.
