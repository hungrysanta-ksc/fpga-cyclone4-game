# NES213 생산 RUN과 변경 범위 출력 연결

PR120의211/212 후보를 실제 실행·전송·표시·반납 경로에 연결한다. 하드웨어 시험 전 로컬 검증과 배포 게이트는 `analysis/runtime213-verification.json`에 고정한다.

## 작업 의미

60fps를 위한 **반복 타일 생성·전송과 SNES 전수 비교 제거 구현을 실기 실행 경로에 적용**한다. 기존210의 재사용 가능량 모델은 실제 슬롯 유지 상태로 교체한다. 화면의 작은 변경을 매번 전체 화면 작업으로 처리하던 비용을 줄이는 단계다. 아직 지속 스크롤60fps를 달성했다는 의미는 아니다.

## 수명과 순서

- 실제 로더는 SMB3(J)의 헤더/길이/CRC `5a04eed7`과 FPGA 저장 내용 전체 비교를 통과하고 checked START 뒤에만 세션을 연다. CHR-ROM128KiB이며 RUN 중 loader write/state-load는 없다.
- ARM의 `content_epoch`는 이 검증된 불변 ROM **세션의 내용 식별자**다. FPGA201/207의 실제 loader epoch와 같은 값이라고 가정하지 않는다. 물리 소스 수명은 기존 FPGA lease가 독립적으로 검증한다. CRC 자체를 범용 내용 무결성/동시성 보장으로 사용하지 않는다.
- 매 세션 FPGA 재구성/COMMON reset과 SNES boot 후 resident를 비운다. 같은 ROM으로 재시작해도 두 bank가 모두 cold다. CHR-RAM은 RUN API에서 거절하며, 다른 매퍼/state-load 지원 시 내용 변경을 동반한 전체 세션 무효화 또는 별도 버전 설계가 필요하다.
- 순서: receiver COMMITTED → resident BEGIN →212 BEGIN →211 planner/200 batch →200 finish(모든193 chunk와 END drain) →212 SEAL →실제 최종 표시ACK 검증과 resident COMMIT →200 retire →receiver consumed.
- callback의 true는 **계획 큐 수락**이다. 타일 DMA 완료가 아니다. finish 전에 SEAL하지 않는다. 표시 후 retire에 실패하면 이미 표시한 프레임은 계수하되 세션을 fault로 닫는다.
- 모든 terminal에서 resident reuse를 무효화한다. 재시도 없이 기존 COMMON STOP/base/menu 경로를 거친다. stack의 resident/receiver/video 포인터를 RUN 반환 전에 철회한다.

## 검증 범위

선택: arm01/test05/check01/report01/budget01/join02/binding02/asm01/romcheck01/release01.

1. 실제213 RUN/200 batch/184 C queue, 보존된203 ingress trace:9연속 frame/361152참조 planar bytes/6오류 경로, mutable 거절·cold 재시작. receiver 경계9개 재사용. SPI peer/소비ACK는 모델이며 이것만으로 실제 하드웨어 승인을 하지 않는다.
2. 실제213 C→200 SPI→207 RTL epoch/lease/READ16/bulk→실제212 65816/PPU/DMA/ACK 연결:3연속 frame/183552RGB pixels가 이전208과 동일.65534→65535→0 generation,3표시와3retire. warm frame은1VBlank. partial E9는1표시/1retire만 허용하고 resident fault 및 공통 취소. loader/core arbitration/metadata와 E0/E1 queue는 fixture이며 전체 게임/물리 클록 동시 시뮬레이션은 아니다.
3. 그 실제 요청/응답115개를 변경 없는184 RTL queue에4credit로 재배열해 재생:80정상/35중간중단,43179checks. 원래 SPI 일정 재현은 아니다. 실제 top mux320truth cases와descriptor/aperture/saveSRAM 비점유 유지.
4.212의14frame/11표시전 오류/pressure/표시후ACK손상 증거는 그대로 재사용한다. 원본archive를 수정하지 않는다.
5. 전체 ARM206704B/static27812/RUN32088/IRQ508/보수적 여유5016B.1024B 기준 유지. resident3200B가 이전passive cache2560B를 대체하며 추가global cache 없음. 전체 메뉴/GBC 호출그래프의 새 전수증명은 아니다.
6. 실제 로그 최대4047/4096B, budget2415/4096B. post-STOP 안전 gate/IRQ 복원/동일 텍스트버퍼 저장 tail은210과 파일명 외 동일하다. budget schema213의 `slot_hits`는 실제 목적bank에서 재사용한 슬롯 수이며 bytes/FPS가 아니다. `reserved0/1`은0, mapdirty는 직전표시 대비 값이다. 실패한 미완료 프레임에는 표시된 hit 집계가 추가되지 않는다.
7. 검증된207 배선에서4KiB ROM만 CDB MIF/ASM/CPF로 교체. RTL/배치/배선/timing 보고 불변. default/slow85/fast0의3개 post-fit netlist에서 각각4096B 정확 대조. EDA 후QSF의 줄바꿈/edition/출력 메타데이터만 허용. 새 FIT/STA·전기적 검증이 아니다.207의 조건부 IO와 좁은 timing 여유를 재사용한다.

212 SNES code3552B/free384, 내부 WRAM metadata522B와명령9736B는 그대로다. 저장카트리지SRAM/GBC164/기존배포/사용자ROM bytes는 변경하지 않는다.

## 실기 판단과 다음 작업

213은 재사용·dirty 구현을 시험할 첫 배포판이다. [실기 안내](nes-game213-ready.ko.md)에 따라 첫 레벨의 스크롤·소리·조작·메뉴복귀를 확인한다. 로딩 종료 직전부터 영상과3TXT를 받는다. 같은210/044 반복은 요구하지 않는다. 사용자210 마지막약5초는 **첫레벨 내부**라는 정정을 유지한다.

좋은 결과도 고정 장면/전체평균으로60fps라고 판정하지 않는다. 실제 스크롤에서16.67ms 전체예산을 본다. 아직 geometry ingress, NES좌표 기반 순환 scroll-map, 생산·소비 겹침이 남아 있다. 성능이 부족하면 이번 타일 유지/직접DMA/표시ACK 기반을 보존하고 그 병목을 먼저 개선한다. AV60fps→긴플레이/오류·실기리셋로그→입력품질 순서다.

중간기록: test01 sandboxDLL623, test02 시험모델의RLE 누락, test03 부적절한 destination map 기대값, test04 Windows printf 형식오류. 최종test05선택. join01은 동작통과지만 소스출처key 오기; 수정 재현join02선택. binding01은한글Questa DB경로 실패, ASCII binding02선택. 이전기록은 삭제하지 않는다.
