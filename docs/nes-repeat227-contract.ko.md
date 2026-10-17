# NES227: 스프라이트 반복 꼬리 전송과 실제 SNES 복원

## 문제와 작업 의미

226은 계획 계산 시간을 줄였지만 실기에서 수신22.40초, SEAL21.11초가 남았다. 이 중 매번 전송하던 OAM544바이트는 실제 표시 객체 뒤에 같은4바이트 항목이 반복되는 경우가 많다. 227은 **이 반복 데이터의 전송량을 줄이는 실제 출력 경로 변경**이다. 새 디버그 체계나 FPS 제한이 아니다. 팔레트·geometry 수신 전체를 해결한 것으로 확대 해석하지 않는다.

새 후보는226 생산 C와 검증된224 FPGA 배선을 기준으로 한다. 새 FPGA 논리·FIT 없이 내부4KiB SNES 소비기 ROM과 ARM 송신기를 함께 바꾼다. 새bank/프레임RAM·저장SRAM은 쓰지 않는다.

## 정확한 계약

- op8은 section4(OAM)만 허용한다. 물리 payload4바이트, expanded8..512바이트, offset/expanded 모두4배수, offset+expanded<=512. 마지막32바이트 high attributes는 일반 DATA/RLE 경로다.
- ARM은 첫512바이트 끝에서 같은4바이트 항목의 연속 범위를 모든 바이트 비교로 구한다. 길이64이상이고 기존2바이트 RLE와 중복되지 않으며 기존 wire cost 모델보다 작을 때만 사용한다. 그렇지 않으면 원래 span을 사용한다. hash·이전 프레임 캐시·숨김Y값 가정은 없다.
- SNES는 기존 길이/순서/token/serial/generation/bank/범위를 모두 검사한 다음 candidate WRAM에 처음4바이트를 DMA한다. 앞으로 복사하는 MVN으로 같은 bank 안에서 나머지를 복원한다. DB를 저장/복구하고, 최대512바이트 복원 후 service/STOP을 확인한 다음 ACK한다.
- BEGIN/SEAL 버전은2271이다. 이전2121과 섞인 조합은 BEGIN에서 거부한다. 최종 실제 displayACK 전에는 resident bank commit을 허용하지 않는다.
- 미완료·실패 경로는 기존 공통 STOP/reset을 사용한다. active VRAM, displayed source lease, CHR epoch, row/alt/mask, saveSRAM은 유지한다.

## 검증과 실제 범위

선택: arm01, snes04(normal), snes03(9faults), runtime02, check02, asm02, romcheck01. snes01의 sandbox DLL오류, snes02의 존재하지 않는 stop모드 지정, runtime01의 시험 객체 이름 오류, asm01의 Lite/Standard DB 불일치, evidence01의 QSF 메타데이터 판정 실패는 별도 보존했다. 시험 코드·도구 선택 오류를 제품 실패로 집계하지 않는다.

- 실제 C→실제65816: 스크롤·wrap·반대 방향·raw rows·bank 전환을 포함한30프레임, 기준186 화면1835520픽셀 완전 일치. 544×30=16320바이트 candidate OAM도 모두 일치한다. 보이지 않는 꼬리까지 비교했다.
- 기존225 동등 입력과 비교해 OAM 표현·sequence·버전 외의 패킷은 모두 바이트 단위로 동일하다. planner226의225 동등성은 이전1939프레임 증거를 유지하며 이번에도 실제 기준 화면과 대조했다.
- 잘못된 반복 길이(짧음/홀수), section, period/payload, offset overflow와 wrong displayACK, wrong bank, wrong epoch, repeat 직후 STOP의9경계를 검사했다. 실패 시 기존 표시 화면을 유지한다. 잘못된 displayACK는 SNES 표시와 ARMcommit을 별도 판정한다.
- 실제 RUN9프레임/6실패경계, receiver9경계, OAM 복원 비교 통과. 이 RUN시험의 FPGA/SNES 응답은 모델이며 실제65816 검증은 위 별도 시험이다. fullboard/game cosimulation이라고 하지 않는다.
- ARM209828B/static28116/RUN35000/IRQ508/**여유1800B**. 기존1024B gate를 유지한다. 새영구상태0B, 로그 최대3521B/4096B, budget 형식226 유지.
- SNES body3712/3936B, 여유224B. boot copy/readback 포함4KiB. 이전 ROM과 같은 private WRAM만 사용한다.
- 기존224 route에서 ROM MIF만 CDB/ASM/CPF로 갱신. RTL·SDC·배선·timing 관련93파일 유지. QSF 차이는 LAST_QUARTUS_VERSION의 Lite→Standard 기록과 정확히3개 EDA export설정뿐이다. EDA3출력의 ROM4096바이트 모두 새 소비기와 일치한다. 새FIT/STA가 아니며 기존 conditional IO/full CDC 한계는 남는다.

## 성능 판단

같은30프레임의 메타데이터 packet bytes104753→88733(-15.29%), packet955→949. 스크롤16프레임은58768→50288(-14.43%)다. 타일 aperture5088바이트, 나머지 패킷 의미·픽셀은 같다. 이 수치는 E0 polling, CRC/framing, ingress, audio/service를 제외하며 실제 SMB3에서 수집한 스크롤 재생이 아니다.

MVN 복원은 기존 literal DMA보다 추가 SNES 연산을 사용한다. 따라서 전송 바이트 감소를 그대로 지연/FPS 개선율로 바꾸지 않는다. 실기에서226 대비 SEAL 시간·총 표시 완료·첫 레벨 스크롤을 함께 확인한다. 성공하더라도 전체16.67ms 목표의 일부이며, 수신·기타metadata·finish 병목은 그대로다. 이 작은 압축의 순효과가 없으면 codec 확장 반복을 중단하고 남은 큰 경로를 우선한다.

## 재현과 인계

생성: tools/nes_repeat227.py. 실제 SNES: tools/test_nes_repeat227_snes.py. RUN: tools/test_nes_repeat227_runtime.py. 링크: tools/check_nes_repeat227_arm.py. ROM 교체: tools/assemble_nes_paired227.py. 전체 gate: tools/nes_repeat227_evidence.py. 패키지: tools/release_nes_repeat227.py.

[검증 JSON](../analysis/repeat227-verification.json), [실기 안내](nes-game227-ready.ko.md). 로컬 probes/nes-repeat227에서 실패·선택 자료를 함께 보존한다. Mesen 입력은 ASCII 임시 경로에서 실행하고 종료 뒤 복사했다. 준비는 예외 승인/새 라이선스/새 FPGA FIT를 요구하지 않는다. 227 paired파일 설치 후 첫 레벨 숫자1+A, 오른쪽+B/A 스크롤과3TXT·영상·소리·조작·메뉴가 다음 gate다. 같은226/044 재시험은 하지 않는다.
