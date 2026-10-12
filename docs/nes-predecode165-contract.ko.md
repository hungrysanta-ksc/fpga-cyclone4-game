# NES165 명령 사전 판별과 적재 완료 상태

같은 PR108의 FPGA 구현이다. **실제 같은 클록 setup 미달이 남음: 최저 setup -0.153ns, hold +0.155ns.** 전체 보드 IO·CDC 승인이나 실기판 완성을 뜻하지 않는다. [검증](../analysis/predecode165-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md).

## 목표와 변경

게임 영상 전송 회로가 FPGA에 배치된 뒤 남은 제어 지연을 줄이는 구현 작업이다. 진단 항목을 추가하는 작업이 아니다. 이전 retire165/map02 기준61개 입력 중 SPI·로더2개만 바꾸고59개를 보존했다.

SPI 프레임 종료를 잡는 기존 edge에서 카운터 초기화·증가 명령의 유효성을 두 비트로 저장한다. 헤더·본문을 다른 시점에 읽지 않는다. 실제 명령 실행 edge에서는 현재 하드 오류·응답 소유권·새 프레임 충돌을 계속 확인한다. 명령 완료 클록, 오류 우선순위, 응답식별6B와 직렬 응답은 유지된다.

첫 구현은 모든 명령의 본문 오류를 합친 식을 썼지만, ACK와 무관한 READ의 check_ready 경로까지 연결됐다. 최종 판별은 BEGIN/STOP/CHECK_BEGIN/ACK 각 명령에서 필요한 조건만 전개했다. 일반 오류코드 처리 자체는 변경하지 않는다.

로더는 `count_complete == (loaded_bytes == total)`을 바이트 수와 같은 edge에서 갱신한다. 마지막 바이트 증가 전의 total−1을 감지하며, reset·begin·stop·fault 정지 및19비트 wrap을 포함해 불변식을 검증했다. 주소 출력 조건에서 긴19비트 비교를 제거했고 외부 PSRAM 쓰기 펄스 길이는 유지한다. 카트리지 세이브 SRAM은 사용하지 않는다.

## 후보와 타이밍

|후보|전체 LE / LAB|기존 구현 SDC 최저 setup|실제 클록 최저 setup|
|---|---:|---:|---:|
|nes-predecode165-map01|15029 / 962|-0.436ns|-0.310ns|
|nes-predecode165-map02|15016 / 959|-1.178ns|-1.178ns|
|nes-predecode165-map04|15049 / 962|-1.243ns|-0.922ns|
|map03|15040 / 963|-0.605ns|-0.153ns|


선택은 **map03/reproduce03final**이다. map04의 비트별 XOR/clear 마스크는 기능 비교를 통과했지만 실제 클록 최저−0.922ns로 악화돼 제외했다. 35/56M9K, 8332레지스터,197104메모리비트,122실제핀·0가상핀·1PLL. 합성 추정 LE와 실제 FIT LE를 구분한다. LAB 잔여0개는 충분한 후속 여유를 보장하지 않는다.

실제 클록 조건에서 주요 목적지별 최저값도 따로 확인했다:

- nes-predecode165-map01: 카운터+0.016ns / 명령캡처-0.287ns / 로더주소-0.310ns
- nes-predecode165-map02: 카운터-0.172ns / 명령캡처-1.178ns / 로더주소+0.813ns
- nes-predecode165-map04: 카운터-0.791ns / 명령캡처-0.420ns / 로더주소+0.309ns
- nes-predecode165-map03: 카운터-0.153ns / 명령캡처+0.154ns / 로더주소+0.870ns

기존 구현 SDC와5.5/5.3ns 추가 배치 목표는 그대로다. 별도 분석은 고정된155의 순수 클록 SDC이며, 클록 주기·false path·multicycle을 바꾸지 않고 소스/설정/배선 DB를 보존했다. 추가 목표 결과(-0.605ns)와 실제 클록 결과(-0.153ns)는 서로 바꿔 부르지 않는다. 혼합 도메인 raw setup-15.504ns와 입력54·출력57미제약 포트는 여전히 IO/CDC 미완료다.

## 기능 검증

- 카운터 전체524288값과 오류·명령·리셋 우선순위262144조합, 합계786432상태가 이전 구현과 일치했다.
- 명령 수신393216사례에서 새 판별 비트와 이전 헤더/본문 오류·명령 인코딩 결과를 대조했다. 모든256명령,128조건,4인자,0/적재길이/다른주소3영역을 포함한다.
- 하드 오류 차단 누락과 헤더 차단 누락을 각각 검출했다. 정상 판정만 보는 시험이 아니다.
- 로더104448명령상태와524288개 모든 증가값, 합계628736비교에서 상태·데이터·핀과 완료 플래그가 일치했다. 잘못된 마지막 바이트 조건도 검출했다. 전체 ROM을 다시 쓰는 시험이 아니다.
- 실제SPI 상승 edge 시험98검사·8쓰기·6CHECK읽기·6실패조건·ACK경계·finish/START가 통과했다. 직접 바이트 수를 주입하던 옛 fixture의 두 위치에는 그 수에서 유도되는 완료 플래그만 같이 주입했다. 검사를 제거하거나 기대 성공으로 덮어쓰지 않았다.

초기 length01의 문자열 치환은 refdut에도 새 플래그를 넣어 참조 모듈 최적화가 실패했다. 수정한 length02는 같은RTL로 통과했다. path02/03은 옛fixture가 바이트 수만 주입해 완료 플래그와 어긋나55번째 검사에서 실패했다. 실패 기록과 이전 fixture는 보존하고 별도 adapter에서 두 주입 지점을 명시했다. 이들은 라이선스 문제가 아니다.

## 채택·재사용 기준과 다음 작업

기능 동등성과 새 배치의 타이밍은 따로 판정한다. 로더 RTL이 같은 후속 후보는 length02를 바이트 단위로 대조해 재사용했다. SPI 판별을 바꾼 후보는 캡처·실행 비교와 실제SPI를 다시 실행했다. 명령 판별의 등록으로 회로 경계가 바뀐 뒤 카운터 조건 선택식을 실험했으며, 이전 retire165의 등록 없는 긴 피드백과 같은 결과라고 가정하지 않는다. 완료 archive/record/audit와 이전 공개 pins는 수정하지 않는다.

다음 작업: Reuse selected map03: fix measured nominal -0.153ns path nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|check_next[0] -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|check_next[17] without moving retirement/fault edges or relaxing clocks. Routed path crosses response-address comparison -> counter_retire_ok -> final counter mux, not the carry increment itself; inspect comparator factoring/fanout or stable-tag capture contract before another fit. Inspect counter/capture/loader groups together, not only first worst row. Then necessary IO/video CDC and MCU RUN receive-convert-ACK/audio/input/STOP/time/full-link/stack, minimum SMB3(J) hardware. Keep save SRAM reserved/installed164/GBC. Do not repeat unchanged OAM/full writes/A-B/044 or rejected generic-body predecode/masked-XOR map04; preserve failed fixtures and completed archives.

**남은 완료 조건:** 외부IO·영상CDC/리셋 계약, MCU 수신·변환·ACK와 기존 사운드·입력·STOP·실제시간의 통합, 전체 링크·중첩스택, 최소 SMB3(J) 실기 시험. 설치164·GBC·세이브 SRAM 보존. 새SD나60fps 실기 성공은 이번 결과에 포함되지 않는다.
