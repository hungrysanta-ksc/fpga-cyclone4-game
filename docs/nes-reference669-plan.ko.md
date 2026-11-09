# NES 669 · sd2snes+ 재검토와 다음 실행 순서

**참고할 구현이 남아 있다. MMC666을 유지하고, 다음 작업을 직접 공급 경계의 비용 비교부터 시작한다.** 658에서 핵심 구조를 조사했지만 후속 실행은 CHR 사전 변환·PSRAM 공급에 집중했다. FPGA→SNES 변경 스트림은 별도 검토로 남았고 668 이후 계획에도 구체적인 실행 단계가 없었다. 이를 다시 명시한다. [658 원래 조사](nes-reference658-results.ko.md) · [668 기각 근거](nes-output668-results.ko.md)

## 확인한 소스와 적용 상태

사용자가 제공한 Downloads/sd2snes는 배포본이다. 보존된 소스는 제공된 v1.11.2-br-v2.19 태그의 commit `6867510aba14693543577a87fa161595e1422b42`다. bridge·transport·renderer·loader·CHR 변환 5파일의 Git blob SHA를 고정값과 대조하고, 배포본 6파일을 658의 공식 배포본 hash와 다시 대조했다. 선택 MMC666의 ARM·65816·보드 입력과 기존 STA 보고서도 확인했다. 새 기능 시험·합성·sd2snes+ 실기 FPS 측정은 하지 않았다. [재검증 JSON](../analysis/reference669-review.json) · [재현 도구](../tools/check_nes_reference669.py)

| 공개 구현의 아이디어 | 현재 구현과 판정 | 다음에 확인할 차이 |
|---|---|---|
| CHR-ROM 사전 변환 | **반영됨.** 660은 추가 사본 대신 적재 주소 배치를 바꿔 두 plane을 한 word로 읽고 staging·묶음 DMA 유지. 661 이후 MMC666에 포함 | 같은 작업을 신규 최적화로 반복하지 않음 |
| PSRAM→VRAM 작은 타일 직접 DMA | **659에서 연결 후 기각.** ROM 경쟁에서 첫 16B 중 4B만 공급, DMA 설정 증가·배치 실패 | 원래 버스 공급 보장을 바꾸는 새 근거 없이는 재시도하지 않음 |
| FPGA가 PPU 변경을 연속 범위 명령으로 만들어 SNES에 직접 공급 | **map 경로에 미반영.** 현재 ARM이 생성한 `p->map`을 `map527`→`packet_wire`→E1으로 보냄. 타일은 이미 FPGA staging 직접 공급 | ARM 계획을 유지한 일부 데이터 우회와 SNES 변환 경로를 각각 계산. NES 원본과 SNES 목적 map은 다른 데이터이므로 단순 복사로 간주하지 않음 |
| 표시 중 mailbox→WRAM DMA, VBlank에 PPU DMA | **원칙은 이미 있음.** 현재 패킷·bulk의 WRAM DMA와 선행 map DMA를 사용 | 새로운 DMA 도입이 아니라 준비된 범위의 소유권·발행·수신 일정을 비교 |
| 남은 주사선 시간에 따라 변환 작업량 제한 | **참고할 부분이 남음.** 현재 beam 검사·STOP·246선과 선행 DMA는 유지 | 수신/검사/설정의 최악 비용을 포함한 작업 예산으로, 큐를 일부러 비우는 대기 없이 DMA 기회 확보 가능한지 비교 |
| 해석 뒤 ACK, 같은 seq 재실패 시에도 ACK | **그대로 도입하지 않음.** 저장/소비 credit과 표시 후 최종 ACK는 별개 | WRAM 수신 완료로 저장을 반환해도 표시 이력·최종 ACK는 독립 검사 및 표시 뒤에만 확정 |

참조 위치는 [bridge의 두 8KiB mailbox](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/verilog/sd2snes_nes/nes_bridge.v#L727), [연속 nametable 범위 발행](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/verilog/sd2snes_nes/nes_bridge.v#L2343), [WRAM 수신·512B 분할·채널 분리](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_transport_device.a65#L263), [주사선 예산](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_render.a65#L3775), [ACK 의미](https://github.com/ludufre/sd2snes/blob/6867510aba14693543577a87fa161595e1422b42/snes/nes/nes_transport_device.a65#L150)다. 512B 크기와 주사선 상수는 공개 구현의 조건이며 우리 코드에 그대로 적용할 안전 근거가 아니다. NMI와 main이 동시에 DMA 설정을 변경하는 구조로 바꾼다면 채널 소유권도 분리해야 한다. 현재 코드의 채널 충돌이 발견됐다는 뜻은 아니다.

## 복사보다 먼저 해결할 경계

선택 보드는 **15,324/15,408 LE, 962/963 LAB, 56/56 M9K**다. ARM Flash 여유496B, 물리 65816 ROM 여유11B다. 공개 mailbox 16KiB를 추가하는 안은 시작부터 제외한다. 실제 선택 RTL의 bulk 저장은 2×2KiB, ordinary 큐는 4×256B이며 둘 다 현재 사용 중이다. 이 5KiB를 빈 공간으로 계산하거나 과거 실험의 슬롯 수를 현재 보드에 대입하지 않는다. 각 값은 `nes_bulk_aperture188.sv`, `nes_sink_spi165.sv`와 실제 인스턴스·QSF에서 확인했다.

현재 ARM의 map에는 tile slot 배정·속성·대상 뱅크 이력이 반영된다. 공개 bridge의 nametable run은 NES 원본이다. SPI를 우회하려면 **그 변환을 누가, 어느 RAM에서 수행하는지** 비용에 포함해야 한다. 원본을 직접 보낸 뒤 65816의 64열 변환·gather가 되살아나거나 FPGA에 별도 범용 실행기를 붙이면 과거 회귀를 반복할 수 있다. 공개 구현의 ACK/변경 합치기 정책과 우리 최종 표시 검사는 같은 완료 기준이 아니다. 사용자 체감 속도나 화면 깨짐의 원인을 이 차이만으로 확정하지 않는다.

## 보완한 작업 순서

1. **다음 한 단계: 직접 공급·변환·삭제 예산표.** 같은 MMC666의 905/906 cold, 911 마감, 951–957 밀집 입력으로 다음 세 경우를 비교한다. 기존 ARM 계획+E1을 대조군으로, (A) ARM이 확정한 주소/slot/속성 descriptor만 발행하고 기존 FPGA 저장에서 가능한 payload를 공급, (B) NES 변경 run을 SNES WRAM으로 공급하고 필요한 변환을 SNES에서 실행하는 경우다. map·palette·OAM은 표현이 다르므로 바이트별 생산자를 따로 표시한다. 변환을 다시 구현해야 하는 범위, 실제 생략 가능한 D1/E1·상태조회·credit 거래, 추가 descriptor·CRC·cold 재전송을 계산한다. A가 모든 map을 공급할 수 있다고 가정하지 않는다.
2. **같은 표에서 저장과 검사를 확정한다.** 기존 큐/serializer/복원/주소 선택 중 실제 삭제할 코드와 RTL, 대체 RAM의 수명·read/write 포트·CDC·최대 backlog를 기록한다. ARM 계획/새 캡처/ROM 읽기와 충돌을 포함한다. `입력 캡처 identity → 고정 payload → WRAM 수신 credit → 독립 검사 → DMA → 표시 ACK → 이력 확정`을 분리하고 부분 전송·STOP·늦은 응답·cold 전체 복구를 정한다. 원본과 expected가 같은 손상 데이터를 공유해 검사가 무력해지는 안은 제외한다. 84LE/1LAB/0M9K 여유는 배치 성공 보장이 아니며, 전체 대체 예산을 먼저 통과시킨다.
3. **일정 후보는 분리 평가한다.** 위 구조와 별개로 954·957의 수락 범위/병합/빈 큐 시점에 주사선 기반 작업 예산을 적용할 수 있는지 계산한다. 입력/출력 거래 제거의 이득과 선행 DMA의 이득을 먼저 각각 평가한 뒤 결합한다. 668의 단독 탐색·일괄 drain, 위상별 고정 지연은 보류한다. 단순히 남은 시간을 모두 DMA 예산으로 쓰지 않고 STOP·새 패킷 처리·검사·설정·ROM 경쟁을 차감한다.
4. **가능한 후보 하나만 실제 연결한다.** 원본·공통 코드 대조군·기능 적용본을 같은 ARM/SPI/IRQ/ROM 시작 시각으로 비교한다. 두 위상에서 밀집 평균 표시 간격과 957 마지막 ACK가 모두 개선되고, 911 기존 마감(SEAL189/검사 완료214선), 951의246선, 952의3 VBlank 이하, 957 최종 대기0회를 유지해야 한다. 954/955는 선택본 대비 VBlank 회귀를 허용하지 않는다. 원본 바이트·변경 map/OBJ 작업량, 독립 검사·STOP·캡처 회복·최종 ACK·메뉴 복귀를 함께 검증한다. RTL 변경 시 같은 소스의 Quartus Lite 전체 FIT·STA, ARM 전체 링크·stack/RAM과 65816 ROM/WRAM 비용을 판정한다.
5. **실기 전달은 통과 뒤.** MMC666과 같은 첫 레벨 동선, 5–40초·40–55초 집계, 새 파일명·RESTORE 제외 정책을 유지한다. 두 후보가 예산을 통과하지 못하면 불가능한 비용과 남은 대안을 기록하고 기존 수락 범위·병합 계획으로 돌아간다. sd2snes+ 구조를 무조건 채택하거나 또 다른 작은 FSM 조정으로 넘어가지 않는다.

이 재검토는 새 속도 개선의 검증이 아니다. 668 재생의 SEAL 발행15.69ms와 업로드 VBlank 대기9.26ms는 서로 관련된 경로이며, 이를 전부 없앨 수 있는 절약량으로 합산하지 않는다. 실기 출력26.84ms를 이 비율로 분할하지도 않는다. **즉시 작업은 1–2의 경계·순삭제·전체 비용표이며 구현 선택은 그 결과 뒤**다. 실행 순서의 기준은 [579 계획](nes-retrospective579-plan.json)의 `current_followup`에 동일하게 반영한다.

## 재현

`tools/check_nes_reference669.py`에 `--reference`(해당 commit의 소스 root 또는 보존된658 subset), `--distribution`(제공된 sd2snes 폴더), `--arm`(MMC666 arm01/src), `--client`(665 client02), `--board`(665 board01), `--out`을 전달한다. 소스 파일은 위 고정 commit에서 다시 받을 수 있으며 Git blob과 SHA256으로 확인한다. 로컬 probes/Temp가 Git clone에 포함된다고 가정하지 않는다. 선택 보드 재생성 경로는 [665 검증](nes-entry665-results.ko.md), 배포 산출물은 [666 패키지](../analysis/trial666-package.json), 과거 직접 DMA 실패와 word 공급 선택은 [659](nes-bg659-results.ko.md)·[660](nes-word660-results.ko.md)을 따른다.
