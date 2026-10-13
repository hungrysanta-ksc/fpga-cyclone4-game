# NES165 CHECK 요청 주소 분리 검증

165 영상 경로 진척: CHECK 요청 주소를 별도 저장하는 구조와 실제 SPI/reader 중단 경계를 검증했습니다. 전체 타이밍이 기존보다 나빠 새 후보를 채택하지 않았다. 선택 구현 predecode165/map03/reproduce03final. 새 후보 15068LE/962LAB/35M9K, 실제 클록 setup-0.616ns. 외부IO·CDC·MCU 실행 연결은 미완료이며 설치164·세이브 SRAM 보존, 새SD 없음.

[검증 수치](../analysis/tag165-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md). 실제 게임 영상 전달 목표는 아직 미완료다. 같은 클록의 수치와 외부IO/CDC·게임 동작 승인을 구분한다.

## 구조와 불변조건

기존 `check_next`는 다음 CHECK 주소인 동시에 응답 주소 검사 기준이었다. 응답 비교 결과가 같은 카운터 갱신을 허용하므로 비교→허용→카운터의 긴 경로가 생겼다. 후보는19비트 `check_request_tag`를 별도로 보관하고 **응답이 들어온 바로 그 edge에서** 응답 주소를 검사한다. 응답 주소가 한 클록 먼저 안정되어 있다는 전제나 오류 검사 생략을 도입하지 않았다.

검토한 계약은 `check_busy -> check_request_tag == check_next`다. reset에서는 busy가0이다. 유효 READ 실행은 태그를 현재 카운터로 잡으며 busy를1로 만든다. 진행 중에는 ACK가 허용되지 않는다. STOP은 busy와카운터를 함께 해제하고, 오류는 busy를 해제한다. BEGIN/CHECK_BEGIN의 적법 조건은 진행 중 상태와 양립하지 않는다. SS 캡처와 바로 다음 실행 사이에 별도 READ가 끼어들 수 없다는 기존 pending 규칙도 유지한다.

map01은 태그 저장까지 기존 오류 우선순위 블록에 넣었다. 카운터 경로는+0.056ns로 개선됐지만 **태그 자체의 갱신 경로가−0.335ns**, 로더가−0.678ns가 되어 미채택했다. map02는 queued READ일 때 태그를 독립 블록에서 저장한다. 거부될 READ도 내부 태그를 바꿀 수 있지만 실제 요청은 발행하지 않고 busy를 유지하지 않으므로 진행 중 요청의 계약을 깨지 않는다. map02의 독립 캡처 블록 주석이 이 동작의 기준이며 앞선 map01의 'validated READ만 저장' 설명을 그대로 적용하면 안 된다. 실제 READ·응답·ACK·STOP·오류의 외부 동작 edge는 같다.

## 실행 검증

- 두 후보 각각 조건부 한 단계 비교1409024상태, 명령 캡처393216사례가 기존 구현과 같았다. 이 시험은 태그 불변조건을 전제로 한다. 강제 주입된 임의 상태 전체의 무조건 동등성 또는 형식검증 도달성 증명으로 부르지 않는다.
- 별도 순차 시험은 실제 SPI decoder + boot + READ16 reader를 연결했다. 매 클록 기존 SPI 레지스터 전체를 비교하며 태그 불변조건을 검사했다. PASS TAG165 edges=1026691 reads=100 acks=7 corruptions=19 cancels=72 overlaps=2.
- 실제 SPI READ/ACK와7주소 경계, 응답 순간19개 주소 비트 오류, 각24위치의 STOP·hard fault·reset 총72중단, 잘못된 응답과 STOP 및 hard fault 우선순위2경우가 통과했다. 잘못된 태그 저장과 비교 비트 누락을 넣은 대조 회로는 각각 검출됐다.
- 적재 READY/길이와 유휴 CHECK 카운터만 시험용으로 심었다. 중간 단계 STOP은 유효 STOP의 queued 필드를 심어 reader의 짧은 단계별 중단을 검사했다. 정상 STOP은 실제 SPI 프레임으로 보냈다. 전체 ROM 쓰기나 새 게임 부팅으로 주장하지 않는다.
- 총61입력 중 SPI RTL1개만 변경했고60개는 바이트가 같다. 소스 재생성도 비교했다. 기존 로더·GBC·설치164·오디오·입력·세이브 SRAM을 바꾸지 않았다.

## 배치 결과

|구현|LE / LAB / M9K|실제 클록 최악 setup|태그 저장 / 응답→카운터|
|---|---:|---:|---:|
|기존 predecode165/map03|15040 / 963 / 35|-0.153ns|해당 없음|
|map01 오류 판정 안에서 저장|14983 / 962 / 35|-0.678ns|-0.335 / +0.056ns|
|map02 독립 저장|15068 / 962 / 35|-0.616ns|+1.340 / +0.330ns|

추가 배치 목표의 setup은-0.616ns, 실제 클록 최소 hold는+0.150ns다. 네 클록과 세 동작 조건을 모두 확인했고 SDC·주기·false path·multicycle을 완화하지 않았다. 첫 전체 FIT 이후 태그 자체의 경로가 실패한 근거에 따라 독립 저장 후보를 추가했다. 무변경 재배치가 아니다. 전체 판단: **전체 타이밍이 기존보다 나빠 새 후보를 채택하지 않았다**.

외부 입력54개/출력57개 미제약과 혼합 클록 경로는 별도 미완료다. 성공적인 FIT나 특정 양수 경로만으로 설치 가능한 상태라고 주장하지 않는다. 초기 시험 실행기의 괄호/문자열 위치 오류와 추가 STA의 작업 디렉터리 오류는 원본 기록을 남겼고 수정했다. RTL 실패나 새 라이선스 요구가 아니다.

## 다음 작업과 의미

SELECT predecode165/map03/reproduce03final. Tag trial map02 nominal -0.616ns: nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|fault -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|pending_causes[2]. Preserve the established CHECK request-tag invariant and same-edge response rejection. Inspect this actual worst path and all-clock minima before another structural change; do not repeat compare165 local equations/SPEED or tag165 map01 guarded capture. Keep request-tag capture separate from dynamic response errors. Existing129/130/131 rejected phase-counter variants are not a new rationale. Only changed-boundary tests and justified fit, then minimum native-video IO/CDC + MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack and SMB3(J). No repeated CHECK/OAM/full writes/A-B/044 or save SRAM.

이번 작업은 실제 영상 전송 회로를 FPGA에 배치하고 타이밍을 맞추기 위한 구현 검증이다. 새로운 일반 디버그 기능 추가가 아니다. 최소 안정성이 확보되면 실제 SMB3 첫 레벨의 화면·사운드·입력으로 확인한다. 기존에 통과한 동일 CHECK·전체 쓰기·OAM·A/B·044 복원은 반복하지 않는다.
