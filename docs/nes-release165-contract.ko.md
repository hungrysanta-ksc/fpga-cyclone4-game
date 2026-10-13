# NES165 영상 mailbox 리셋 해제 분리

165 영상 경로 진척: 영상 mailbox 리셋 해제 레지스터4개의 병합을 방지해 지역별 분리를 확인했습니다. 이번 후보는 기존 기준보다 전체 타이밍이 나빠 채택하지 않았습니다. 선택 구현 predecode165/map03/reproduce03final. 후보 15073LE/963LAB/35M9K, 실제 클록 setup-0.583ns. RTL·클록·SDC는 이전 후보와 같으며 기능 시험은 재사용했습니다. 외부IO·CDC·MCU와 실기는 미완료, 설치164·세이브 SRAM 보존, 새SD 없음.

[검증 수치](../analysis/release165-verification.json) · [현재 인계](../cores/nes/HANDOFF.ko.md).

## 변경 근거

이전 eligibility165/map02에서는 합성기가 영상 mailbox와 입력의 리셋 해제 레지스터를 audio.dac_release와 병합했다. 공유 해제→영상 SPI held 저장 허용 경로는−1.994ns였고 데이터 지연의84%가 배선이었다. 사운드 데이터 오류는 아니었다.

이번에는 QSF에 DONT_MERGE_REGISTER ON을 정확히4개 추가했다: native_records.dr[0:1], native_prepared.sr[0:1]. 원래 있던 host 클록의2단 해제 체인을 각각 유지한다. RTL·상태·handshake·리셋 해제 클록 수·PSRAM 펄스·클록 주기·SDC는 바꾸지 않았다. 회로 전체에 병합 방지나 preserve를 적용하지 않았다.

공식 설정 설명은 [Quartus 설정 참조](https://www.intel.com/programmable/technical-pdfs/683296.pdf)의 DONT_MERGE_REGISTER 항목을 확인했다. 이 설정은 지정 레지스터와 다른 레지스터의 병합을 양방향으로 방지한다. 실제 적용 여부는 문서 설명에 의존하지 않고 QSF 읽기 결과와 배치된4개 독립 레지스터로 확인했다.

## 검증과 결과

- 전체61개 배치 입력에서 QSF만 변경했다. 나머지60개는 바이트 동일하며, 새로 생성한 소스와도 일치한다.
- 변경되지 않은 eligibility165의 SPI·boot·reader 기능 시험과 동일 mailbox RTL의 기존 검증을 재사용했다. 새 Questa 실행·전체 ROM 쓰기·게임 부팅·MCU/SNES 실기 시험은 하지 않았다. 이를 새로운 기능 시험 통과로 세지 않는다.
- 설정4개가 모두 ON으로 읽혔고, 각2단 체인의 첫 레지스터 fanout은 다음 레지스터1개다. 서로 다른4개의 배치 레지스터를 확인했다.
- 3개 동작 조건에서 두 체인의 setup/hold12경로를 확인했다. 최소 setup+8.701ns, hold+0.195ns다. 전체 reset pulse·CDC·MTBF 승인을 의미하지 않는다.
- 해제2단의 fanout은 records 177, prepared 20이다. records 해제→SPI held 경로 최소 setup은+6.750ns다.

|항목|결과|
|---|---:|
|전체 FIT/ROUTE|통과|
|LE / LAB / M9K|15073 / 963 / 35|
|실제 클록 최악 setup|-0.583ns|
|실제 클록 최소 hold|+0.134ns|
|추가 배치 목표 최악 setup|-0.583ns|

**이번 후보는 기존 기준보다 전체 타이밍이 나빠 채택하지 않았습니다.** 전체4클록·3조건의 결과로 판단한다. 추가 배치 목표와 실제 클록 분석을 구분하고, 외부IO54입력/57출력 미제약·혼합 클록 경로·전체 MCU 연결은 계속 미완료다. 완료된 이전 archive·도구·검증 해시를 수정하지 않았다.

이번 분리로 host 클록 전체 최소 setup은+1.215ns, 문제였던 해제→held 경로는+6.750ns가 됐다. 메모리 클록의 최악 경로는 load_begin→로더 fault~2→state~43/44/45/52/53/73→WRITE/HOLD이며 논리7단, 데이터 지연6.469ns(배선3.712ns,57%)다. 여전히−0.583ns이므로 기존 선택 기준−0.153ns보다 나쁘다. 정상 실기 설치164는 바꾸지 않는다.

현재 records의 해제2단 fanout177은 이전 공유 노드83보다 작지 않다. 이번 성공을 단순 fanout 수 감소로 설명할 수는 없다. 동일한 해제 기능의 **물리적 분리와 배치 변화에 따른 경로 개선**으로 기록한다. 입력과 오디오 해제 레지스터의 기존 병합은 남아 있으며 이번 변경 범위 밖이다.

## 다음 작업과 의미

SELECT predecode165/map03/reproduce03final;retain release165map01 as isolated-host experiment, not installable. QSF four-release-register isolation verified; nominal -0.583ns worst nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|load_begin -> nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_loader:loader|state.WRITE. This is a 7-level same-clock load_begin->fault~2->state~43/44/45/52/53/73->WRITE/HOLD path, not the old reader predicate or host release. Inspect independent state-transition equations versus shared fault/error task, preserving exact WRITE/HOLD pulse drain and command conflict/STOP priority. Do not repeat compare165.drain (already rejected), old phase/counter variants, blind refits or global dont_merge/preserve. Reuse four local-release assignments only with new hierarchy timing evidence. Then necessary native-video IO/CDC/reset and MCU receive-convert-ACK/audio/input/STOP/time/full-link/stack, minimum SMB3(J) hardware. No unchanged CHECK/OAM/full writes/A-B/044;saveSRAM reserved.

영상 전송 회로의 실제 배선 지연을 줄이는 구현 작업이다. 기능이 같은 회로를 불필요하게 다시 시험하지 않고, 이번 변경으로 달라지는 배치와 경로만 확인했다. 목표는 연속 화면·사운드·조작을 갖춘 SMB3 첫 레벨 실기이며, 일반 디버그 기능 확대가 아니다.
