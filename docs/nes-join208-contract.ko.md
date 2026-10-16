# NES208 C·RTL·65816 표시 완료 결합

## 작업 의미

직접 타일 전송 경로의 마지막 소비와 표시 완료를 실제 SNES 코드로 검증했다. 기존에 각각 통과했던 C203 RUN, 보드207의 선택된 RTL, 65816 client195를 동시에 실행하고, 실제 표시 ACK 이후에만 C가 FPGA의 프레임을 반환하는지 확인한다. 실기판을 준비하기 위한 결합 검증이며 새로운 전송 최적화나 60fps 달성 결과는 아니다.

SELECT **test08/evidence01**. 생산 C/RTL/ROM은 변경하지 않았다. 새 FIT/ARM/ASM/ZIP은 없고 배포186/GBC164/세이브 SRAM과 이전23개 archive를 보존한다.

## 실행 경계

- C203의 실제 receiver/planner/sink/window/RUN을 사용한다. 입력은203에서 보존한 실제 exporter의 합성 장면 trace이며 BG/OBJ와 행 예외가 포함된다. 세대 번호만65534/65535/0으로 바꾼다.
- E8/E9/EA는 실제 SPI 핀을 통해206 endpoint로 전달한다. SPI2.625MHz, 기존 setup/hold/gap을 유지한다. epoch207, lease201, direct206, tile205, source192/cache, physical READ16, bulk/control/aperture가 실제 RTL이다. PSRAM은70ns 메모리 fixture다.
- 실제65816 client195가 descriptor와 aperture를 읽고 WRAM/PPU를 갱신하며 consume와 최종 표시 ACK를 작성한다. C는 이 ACK를 확인한 뒤 EA retire를 보낸다. ACK나 화면 메모리를 시험 코드에서 대신 작성하지 않는다. ROM195의 compact4096B projection이 보드207 sink-program.hex와 같다.
- 파일 RPC는 C/Questa/Mesen의 트랜잭션을 연결한다. aperture의 불변 payload는 실제 RTL에서 한 번 읽어 CPU에 순서대로 제공한다. 공통 시뮬레이터 클록으로 모든 버스 edge를 묶은 시험이 아니다.
- E0/E1의4slot held queue와 D0~D3 ingress는 fixture다. capture/load-ready/commit 발생 시점은 fixture가 구동하고 qualified_slot은 항상1, core_request는0이다. 전체 보드 mux/실제 NES 코어 경쟁/게임·사운드·컨트롤/물리 타이밍 증명으로 확대 해석하지 않는다. 기존207 FIT/IO 및203 ARM 결과는 변경 없음으로 재사용한다.

## 결과

정상 경로에서 동일 장면3프레임을 global/core reset 없이 처리했다. 실제 표시 ACK3회, RTL retire3회, 세대65534→65535→0, chunk token1~6이 일치한다. 실제 reference186 타일과672B가 같고,6개 descriptor72B를 포함한 raw SNES read는744B, consume write는30B다. C packet86개와 각각의 실제65816 ACK가 대응한다. 각 RGB 화면은256×239이며3장 모두 동일하고19색으로 구성되어 빈 화면 통과가 아니다.

부분 취소 경로는 첫 표시 완료 후 두 번째 E9 전송을 payload 중간에서 끊는다. 실제 endpoint가 거부하고 C의 첫 오류 IO를 유지한 채 common STOP/reset으로 끝난다. 두 번째 SEAL/retire는 발생하지 않는다. 실제 표시 ACK/retire는 각각1회, chunk2개224B와 descriptor24B가 reference와 같으며 이전 표시 화면을 끝까지 보존한다. C packet31개/consume write10B다. 정상+취소 합계896B/8chunks/4표시ACK이며 서로 다른 두 세션이다.

`test_nes_join208.py`는 실행 입력과 source hash를 기록하고 `nes_join208_evidence.py`가 실제 요청/응답 파일에서 descriptor·타일·consume·ACK·retire의 연결과 원본 불변성을 다시 검사한다. 단순 PASS 문자열만 집계하지 않는다. 최종 결과는 `analysis/join208-verification.json`이다. RPC 대기 시간, autopad 횟수, 에뮬레이터 frame count는 성능 수치로 사용하지 않는다.

## 중간 시도 보존

test01은 fixture header 누락,02/03은 Questa의 Windows 경로 인자 해석 문제였다.04는 실제 C가 EA 이전에 frame count를 올리는 순서를 assertion이 잘못 가정했다.05는 작은 장면에 적용되지 않는 기존 대형 SEAL-copy 횟수 조건이었다.06은 부분 전송의 실제 첫 오류 IO를 DISPLAY로 기대했고,07은 reset 중 false가 정의된 arbiter drained를 true로 기대했다. 모두 시험 장치의 조건을 바로잡았으며 생산 코드를 바꾸어 통과시키지 않았다. 최종08에서 정상/부분 취소를 함께 통과했고 원본 로그를 보존한다.

## 다음 작업

남은 결합 경계인 변경 없는 E0/E1 queue와 최상위 mux 연결을 기존 증거 재사용 또는 제한된 trace replay로 확인한다. 전체 게임 cosimulation이나 독립 codec/FIT 반복으로 범위를 늘리지 않는다. 이어 정확한 ARM identity·ROM 짝 검증과 패키징을 거쳐 FIRSTLEVELSCROLL 실기로 간다.

SMB3 숫자1+A 진입 후 RIGHT+B 유지/A press-release로 스크롤할 때 실제 부하와16.67ms 목표를 측정한다. collected_runs는 아직 비어 있고199의17.944ms 합성 모델도60fps 증명이 아니다.207의148LE/1LAB 여유가 작으므로 변경 없는 RTL을 다시 배치하지 않고, 추가 논리가 필요하면 MMC4/5·CHR-RAM·상태저장·뮤트·프레임스킵 예산을 함께 판단한다. AV약60fps→장기 플레이/오류·reset 로그→입력 유지의 우선순위를 유지한다.
