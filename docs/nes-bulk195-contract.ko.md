# NES195: 4KiB 복귀와 실제 C 직접 DMA 명령 연결

PR117의 미배포 후보. 배포186, GBC164, 세이브 SRAM은 그대로 유지한다. SEAL1941·op7·descriptor 주소와 소유권 의미는 [194 계약](nes-bulk194-contract.ko.md)을 따른다.

## 작업 의미

194의 직접 DMA 수신 코드를 기존 4KiB ROM에 넣고, 실제 C sink 및 전송 큐에서 op7을 발행하도록 연결했다. 타일 payload를 MCU/SPI로 다시 보내지 않고 20B 명령만 전달하는 경로다. 새 진단 관측기를 추가한 작업이 아니다.

전체 생산 경로는 아직 미완성이다. 이번 결합 시험에서는 보관된 합성 장면의 타일을 시험용 읽기창에 공급했다. 실제 FPGA 생산기에서 descriptor를 취득하는 MCU 어댑터, plan CDC/content epoch/frame latch, 보드 mux/common STOP 연결은 남아 있다. 실기 스크롤 감소율이나 FPS를 확인한 것으로 해석하지 않는다.

## 4KiB 코드 배치

- 부팅 코드는 복사와 모든 byte의 WRAM readback 검증을 포함해 89B다. 기존 256B 예약을 96B로 줄여 본문 시작을 ROM `$8100`에서 `$8060`으로 옮겼다. WRAM 실행 주소 `$7E2000`은 유지한다.
- MVN 원본 주소와 readback 비교 원본 주소를 함께 옮겼다. 부팅 코드가 96B를 넘으면 생성이 실패한다.
- session/sequence/generation 대조와 응답 복사를 indexed loop로 공유했다. 초기화와 service의 A/flags가 이후 사용되지 않는 0 저장만 STZ로 바꿨다. 길이·정렬·token·STOP·SPC 검사는 제거하지 않았다.
- 본문 3999→3935B. 새 수용 범위는 3936B이므로 **본문 여유는 1B**다. 코드 수정 때 크기 검사는 계속 필요하다. 4096B image의 본문/빈 영역/header/vector projection을 검사했다.
- 8KiB ROM 증가분은 필요 없어졌다. 194의 `PROGRAM_BYTES` 기본값 4096과 기존 bus RTL을 그대로 사용할 수 있다. 새 FIT/보드 ROM 교체/배포 승인은 아니다. 193의 부분 회계 47/56 M9K는 여전히 합성 결과가 아니며, 계획 생산기·제어부와 LAB 전체 비용은 미확정이다.

## C 명령과 완료 경계

`nes_sink195_bulk(s, descriptor12)`는 ready=1, BG/OBJ kind, generation, 길이·정렬·범위, 순차 slot, token 소진 여부를 검사한다. token 0은 유효하고 FFFFFFFF는 소진으로 거부한다. 불변 descriptor의 token4B만 packet에 싣는다. 기존 `packet_wire`의 status/op/sequence/serial/generation/signature 대조를 공유한다.

op7은 비동기 enqueue 대상이 아니다. `nes_window184_barrier`가 앞선 packet을 drain하고 op7을 보낸 뒤, 실제 SNES ACK까지 기다린다. 성공한 뒤에만 `bg_next`/`obj_next`를 증가시킨다. 실패나 응답 불명확은 terminal fault이며 재시도하지 않는다. 다음 실행은 source/controller/SNES의 공통 취소 및 새 token 수명으로 시작해야 한다. SNES consume 이후 ACK가 소실될 수 있으므로 단순 재전송은 안전하지 않다.

이 완료는 staging chunk 수신이다. `displayed`, `last_generation`, frame 최종 ACK1은 모든 section을 검사한 SEAL에서만 갱신한다. 정상 SEAL의 map/raw/CGRAM/OAM/HDMA·기존 delta와 비활성 VRAM bank 전환은 유지했다. 기존 C runtime의 실제 호출부는 아직 이 API를 사용하지 않는다.

## 검증

선택: `build02`, `snes01`, `coupled03/candidate`, `coupled03`, `objects03`. `build02`와 `coupled03/candidate/client`의 ROM bytes는 같다.

- 축소 ROM, 실제65816: 7개 합성 장면 428288픽셀이 기존186과 동일. descriptor 오류6개·명령 오류4개·DMA 직후 STOP1개에서도 이전 화면과 잘못된 chunk의 소유권을 유지했다.
- 실제 C sink+실제 C window+실제65816: 정상 7장면/260 ACK/15 tile chunk, token 오류와 DMA 직후 STOP의 terminal fault 확인. WRAM·PPU·ACK를 시험 도구가 대신 작성하지 않는다. 최대 DMA2048B 및 첫 BG section4096B 경계를 검사했다. 타일4512B 중 사용하지 않는 BG를 0으로 확장한 시험이므로 실제 게임 전송량 자료가 아니다.
- C 단위 경계225개: BG/OBJ의 모든 유효 chunk 길이와 마지막 section 경계, 잘못된 descriptor, ACK 각 byte 변조 및 I/O 실패, sequence 소진, 중복 slot, 상태 거부. 실패 시 다음 slot 진행과 enqueue가 없고 표시 완료로 처리되지 않는다.
- ARM object: video15912B/sink32B 구조 크기와 기존 함수 스택 동일. 신규 `nes_sink195_bulk` 자체 stack40B, `packet_wire`320B 유지. sink text +264B, window +4B, 추가 data/bss 없음. **최종 RUN+IRQ 전체 링크 스택 승인은 아니다.** 실제 descriptor 취득/호출부 연결 후 전체 예산을 계산해야 한다.
- 194의 RTL/control/aperture 검증은 변경 없이 재사용한다. 이번 C→65816은 file bus이며 RTL과 동시에 실행한 시험은 아니다. ACK 수·시험 시간·부팅 시간으로 실기 FPS를 계산하지 않는다.

실패 기록은 보존한다. build01은 본문3937B로 1B 초과했고, service의 동등한 0 저장을 STZ로 바꿔 build02가 통과했다. coupled01은 시험 도우미의 컴파일 경고, coupled02는 실제 C window가 op7을 허용하지 않아 첫 BEGIN 다음에 거부한 기록이다. 동기 barrier에 op7을 연결한 coupled03이 선택본이다. objects01은 컴파일러 경로, objects02는 sandbox DLL623, objects03은 호스트 실행으로 완료했다.

## 다음 작업과 스크롤 기준

1. 이미 구현한 191 plan/192 source/193 tile chunk를 실제 생산 측 controller에 연결한다. descriptor 취득·generation/epoch 고정·frame 시작/종료·backpressure·공통 STOP과 새 token을 실제 경로에서 결합한다. MCU가 타일 payload를 읽어 다시 쓰는 우회는 하지 않는다.
2. 실제 생산기→C op7/barrier→SNES consume/SEAL/최종 ACK의 최소 경계를 확인하고 전체 ARM/FIT/IO·16.67ms 예산을 점검한다. 현재 4KiB 해결을 이유로 불필요한 독립 FIT/boot 반복을 하지 않는다.
3. 짝패키지가 준비되면 [스크롤 계획](../analysis/scroll193-measurement-plan.json)에 따라 SMB3 숫자1 타일+A→첫 레벨 확인→RIGHT+B 유지+A press/release 반복을 측정한다. 같은 generation의 source/변환/전송/고유 표시 간격을 연결한다. cold/static/warm scroll/전환을 나눠 비교한다. 현재 collected_runs는 비어 있다.

새 FW/ZIP/실기판 없음. AV 약60fps→장기플레이/오류·reset 로그→입력 유지 품질의 순서를 유지한다. MMC4/5·CHR-RAM snapshot·state/mute/frameskip 확장을 위해 content epoch와 표시 완료 경계를 유지한다.
