# NES181 — 호스트 RUN 수명과 통합 FPGA 자원 검사

## 작업 의미

RUN 허용 신호가 memory→host 클럭을 가로질러 ACK 저장 조건으로 직접 전달되던 구조를 호스트 내부 준비 상태로 바꿨다. 실기 영상 경로의 배선·응답 소유권 구현이다. 같은 후보에 검증된1813 압축 exporter/SPI와1815 SNES ROM을 통합했다.

**경계 기능 시험은 통과했지만 전체 FIT는977/963 LAB로 실패했다. 실제 타이밍 개선 여부는 측정하지 못했고 설치 패키지는 없다.** 이전 replyjoin의−1.408ns를 해결했다고 주장하지 않는다.

## 시작·종료 계약

`tools/nes_hostlease181.py`는 replyjoin181의69개 입력을 해시 검사해 격리 복사한다. bridge, exporter, native SPI, SNES ROM의4개 입력만 바꾼다. 클럭·핀·QSF·SDC·시드는 그대로다. 전체 보드 내 top의 연결도 그대로다.

- `raw_cancel = raw_reset || !active`. RUN 해제만으로도 이전 전송 수명이 끝나며 미완료 packet, ACK mask, ACK valid를 폐기한다.
- 기존 두 클럭 reset 해제 회로를 유지하고 SPI SS와 SNES `/WR`를 각각 두 FF로 관측한다. reset 해제 및 유휴 확인 후 `host_ready`가 올라간다. 이미 진행 중인 SPI transaction이나 SNES 쓰기에 중간 합류하지 않는다. 이전 즉시 활성화와 같은 지연이라고 주장하지 않는다.
- 내부 endpoint와 bus는 같은 `session_reset`과 호스트 `host_ready`를 사용한다. 정상 transaction 중에는 준비 상태를 철회하지 않는다.
- raw 취소는 외부 SNES OE/DIR도 직접 차단한다. 호스트 클럭이 멈춰도 reset assertion과 출력 해제는 RTL에서 작동하며, 클럭이 재개돼 준비 과정을 통과하기 전에는 다시 출력하지 않는다. 실제 전기적 취소 지연·메타안정성·reset pulse 폭 보장은 별도다.
- **graceful STOP과 수명 취소를 구분한다.** 기존 bridge의 `stop` 입력은 ROM/native transport fault를 SNES의 `$6001`에 전달하는 요청이다. 이 신호만으로 버스를 없애면 SNES가 요청을 읽지 못하므로 그대로 유지한다. endpoint 자체 fault도 기존대로 latch한다. MCU가 RUN을 해제하거나 공통 reset을 걸 때 소유권 전체를 폐기한다. 오류 검출 자체가 모두 즉시 raw 취소로 바뀐 것은 아니다.

## 최소 결합 검사

SELECT `map01/test01`. 실제 `nes_sink_spi165`와 `nes_sink_bus165`, reset/bridge를 연결했다. CPU·SPI master·clock-stop은 fixture이며 전체 NES 게임이나 실제65816 실행은 아니다.

16개 시작 오프셋 스케줄에서 정상 ACK 완료128회, 취소128회,912개 확인을 통과했다. 다음 경계를 포함한다.

- SPI와 SNES 쓰기가 이미 낮은 상태에서 RUN 시작, 두 버스가 유휴가 될 때까지 미승인.
- 정상 packet byte 읽기, 전체 ACK byte와 status CRC, 재시작 후 빈 상태.
- sealed packet, 일부 ACK, 전체 ACK 직후 취소.
- bus의 ACK-byte pulse 및 ACK-publish pulse가 endpoint에 전달되기 직전 취소.
- SPI status snapshot 전송 중 취소, 다음 수명에 이전 ACK가 남지 않음.
- 호스트 클럭 정지 중 reset, 클럭 정지 상태에서 reset 해제, 클럭 복귀 후 정상 재사용.
- graceful STOP 레지스터 유지와 partial ACK publish 거부.

아직 모든 임의 클럭 위상/아날로그 reset pulse/전체 loader→게임 동작을 증명한 것은 아니다. 테스트에서 reset은 raw 취소와 같은 경계지만 stopped-clock RUN-loss 자체를 별도 경우로 집계하지 않는다.

1813 exporter/SPI는 packed181의 실제 fill/SPI→C 검증 후보와 byte가 같다. 1815 ROM은 stream181에서 실제65816/PPU 검사를 통과한 파일과 같다. paired181 전체 ARM의1,384바이트 여유 결과도 유지한다. 변경 없는 경로는 재실행하지 않았고 새 검증 수에 더하지 않는다.

## 전체 합성·FIT 결과

| 항목 | 이전 replyjoin181 | 이번 압축·host 통합 후보 |
|---|---:|---:|
| MAP 추정 LE |19,565|19,895|
| MAP exporter 조합/FF |468/210|714/230|
| MAP sink 계층 조합/FF |534/544|558/578|
| FIT 단계 LE |15,048, 배선 완료|15,079, 미완료 준비 수치|
| LAB |963/963|977 필요/963 한도|
| M9K |38/56|38/56, 배치 미완료|
| 실제 setup/hold |−1.408/+0.147ns, 실패|측정 안 함|

MAP 추정 LE와 FIT 압축·준비 이후 LE를 섞지 않는다. 이번 LE15,079는 최종 배치·배선 결과가 아니다. 압축과 호스트 구조를 함께 넣었으므로14 LAB 초과를 host 변경 하나의 비용으로 분리해 주장할 수 없다. MAP는 성공했고 FIT는 자원 부족으로 종료됐다. STA/IO/ASM/ZIP을 이어 실행하지 않았다. 동일 설정 FIT 재시도도 하지 않았다.

## 다음 구조 변경 후보: ACK 저장 기간 합치기

현재 endpoint는96비트 `ack_work`,96비트 `ack_held`, status용 snapshot을 동시에 둔다. 실제 C 수신기는 F6/CRC/flags를 먼저 검사하고 **ACK valid가 있을 때만**12바이트 ACK를 소비한다. `src/nes/firmware/nes_sink_spi170.c`의 poll 분기가 근거다.

다음은 `ack_work`를 작성 중/완료 상태에서 이어 사용하는 구조를 검증한다. 아직 구현하거나 자원 절감을 측정하지 않았다.

1. sealed packet 동안 ACK byte를 work에 작성하고, publish는 mask 완성 여부를 검사해 valid만 설정한다. 별도 held96 복사를 제거한다.
2. E0 snapshot은 valid일 때만 work를 복사하고 invalid일 때는 ACK payload를0으로 보낸다. flags와 payload를 같은 edge의 이전 상태에서 샘플링해야 한다. invalid ACK bytes의 의미를 문서화한다.
3. status snapshot 자체는 유지해 SPI 전송·CRC 중 값이 변하지 않게 한다. publish와 E0 시작이 같은 edge인 경우, E1 후 부분 ACK, STOP·재시작·CRC 오류를 실제 endpoint와 C 소비자에 연결해 검사한다.
4. 이 공유가 가능한 이유는 E0/E1이 같은 SPI transaction을 동시에 소유할 수 없고, 새 E1이 sealed가 되면 이전 ACK valid가 내려가기 때문이다. 무효 ACK bytes를 예전 값과 항상 동일하다고 주장하면 안 된다.
5. reset/enable 중복 제어도 수명 증명에 따라 정리할 수 있으나, 작은 gate 변경만으로 반복 FIT하지 않는다. 줄어든 실제 FF/제어 자원을 MAP에서 확인한 뒤 통합 FIT를 판단한다.96FF 제거가14 LAB 해결을 보장하지 않는다. 부족하면 큰 OAM 저장/포트 구조를 검토한다.

압축을 빼고 느린 경로로 돌아가거나 클럭/예외를 완화해서 맞추지 않는다. raw7의 송신 하한 모델 약22ms와 단일 capture lease는 계속 미완료다. 이 변경은 FPGA 자원·안전한 응답 경계의 기반이며 직접적인 FPS 증가 측정이 아니다. 최소 안전 조건을 충족하면 SMB3 숫자1 타일→A 실기에서 지속 출력과 실제 표시 간격을 확인한다. 배포180/GBC164/세이브 SRAM/이전 archive는 보존한다.
