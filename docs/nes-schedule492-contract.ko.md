# NES492 — 실제 ARM·SPI·IRQ·ROM·65816 전체 일정 비교

[491 구현·모델](nes-consume491-contract.ko.md) · [492 연결 검증](../analysis/schedule492-verification.json) · [전달 manifest](../analysis/schedule492-package.json) · [설치/원복](nes-mmc492-trial.ko.md) · [PR138](progress/pr-138.md).

## 현재 결론

491의 ARM plan 조회 변경과65816 word 복원을 같은 보드/프로그램 쌍으로 묶고 **MMC492-SCHEDULE.zip**을 준비했다. 실제 전체 처리 시간 감소·492 실기 FPS·메뉴 복귀는 아직 확인 전이다. 현재 실기는489의60.08초577최종 표시/9.60fps,실행·메뉴 복귀 정상이다. 고정71개 CPU/전송 모델의7.25%와 ARM endpoint query 감소를 더해 물리 이득으로 계산하지 않는다.

물리 IRQ·ROM 경쟁을 포함하는 전체 시간은 현재 연결된 실기 DWT/elapsed/최종ACK 카운터로 확인한다. 현재 보드는 사용자가 ZIP을 SD에 설치하고 로그를 반환하는 방식이다. 새 모델을 실물 공통 시계의 증명으로 대체하지 않는다. 이번 전달본은 이미 기능·동일시작 CPU·whole Lite를 검증한491 변경의 실제 실행본이며 계측 코드만 바꾼 전달은 아니다.

## 연결된 소유권·일정

- actual receiver의 D0/D1/D2/D3와 planner221·E9/actual op7 DMA 공급을 기존 shared SPI 경로로 실행한다. 첫 BG는 즉시 flush,15개/240B 경계·finish/END는 계속 실제 E8/E0 진행·소비를 확인한다.
- actual nes_sink212_seal→독립 검사/coverage/manifest→65816 수신·DMA/VBlank→표시 generation/token에 맞는 최종ACK→native_frames/retire 흐름을 유지한다. 저장 credit을 실제 DMA 소비/최종ACK로 바꾸지 않는다.
- DWT 수신/계획·타일 공급/SEAL·최종ACK 세 단계가 그 실제 코드를 감싼다.84MHz DWT는 IRQ·guard·서비스·SPI 대기 중에도 진행한다. 최종 표시 완료 수와 DISPLAY_NEXT→DISPLAY_STOPPED의 elapsed를 함께 사용한다. 각 op·quiet 구간은 단계에 중첩돼 별도 시간처럼 더하지 않는다.
- NES/source/tile ROM의 기존 PSRAM 중재가 실물에서 함께 실행된다. 지연은 elapsed/DWT에 포함되지만 현재 로그에는 IRQ별 단독 시간·ROM grant별 카운터가 없어 원인을 완전히 분해할 수 없다. MCU_RDY는 external_memory_ready이며 source-ready IRQ로 재해석하지 않는다.
- STOP·deadline·stale DONE/ACK 차단·이전 표시 identity·base/menu 경로는 유지한다. 마지막 미완료 입력을 표시 수에 넣지 않는다. screen_frames는 기존의 untrusted 필드이며 native 최종ACK 완료 수를 사용한다.

## 동일 구성과 비용

492 ARM은491에서 marker/ROM/FPGA 파일명/로그/VERSION의 같은 길이 label만 변경했다. 최종 ELF의 **781개 함수 주소·크기·명령 byte가491과 모두 동일**하다. STM3 생성 header32B 뒤의 전체 payload도 label 치환 외에 byte가 모두 같아 vector/data까지 확인했다. runtime/planner/sink/window·DWT 계측·fpga programmer·실제 SysTick handler source도 byte/hash로 확인했다. labels는492,wire client ABI는 호환되는4891/profile7b/status3 그대로다.

| 비용 | 489 실기 | 491/492 비교본 |
|---|---:|---:|
| whole Lite LE/comb/FF | 15272/14078/8392 | **동일** |
| logical RAM bits/M9K | 264800/51 | **동일** |
| 남은 LE/M9K | 136/5 | **동일** |
| 관련 구현 setup/hold | +0.183/+0.168ns | **동일** |
| nominal setup/hold | +0.224/+0.168ns | **동일** |
| ARM firmware/남은 Flash | 212868/124B | **212844/148B** |
| BSS/RUN | 18572/31848B | **동일**,새global0B |
| SNES body/program | 4311/5120B | **4425/5120B**,새persistent/frame RAM0B |

491의 source-pinned SOF와 FIT/STA를 그대로 사용해 RBF를 추출하고 BI3를 가역 encode/decode했다. ROM 내용까지 동일하므로 바뀌지 않은 합성·Questa 실행은 반복하지 않았다. 실제227 FatFS/programmer로 선택 BI3/RBF의 CRC·스트림을 검사했다. GPIO/DONE은 모델이므로 실제 구성·메뉴는 반환 로그/사용자 확인이 필요하다. 전체 reset/CDC/IO/full stack·IRQ 승인은 미완료다.

## 판정·다음 순서

먼저492에서 기존처럼 대기와 첫 레벨 플레이를 구분해 로그3개/화면·입력·메뉴 결과를 확인한다. 가능하면489와 같은 장면·조작·경과 시간을 맞춘다. 다른 입력/장면의9.60fps와 비교한 차이를 전부 인과적 개선으로 귀속하지 않는다. 필요할 때 포함된489 원복으로 조건을 맞춘 기준 실행을 추가한다.

반환 뒤 전체 elapsed/최종ACK 완료,수신/계획·타일/SEAL·ACK,각 SPI op와 quiet,ROM/observer 오류·STOP/base 상태를 함께 비교한다. 조회 감소가 실제 DMA 공급 지연으로 상쇄됐는지 확인한 뒤 E8/E0 공급·소비 개선 유지/기각과 다음 D0/source/ROM 작업을 정한다.60fps·capture 무손실·레벨 전용FPS·MMC4/5 증명은 아직 없다.

파서는492를 엄격히 구분하고 기존489에 기반한 **label 변환 fixture**로12개 잘못된 실패 signature 거부를 확인했다. 이는492 실측 데이터가 아니다. deadline/video14도 정확한result/plan/commit/오류 조합에서만 분류하며14를 단독 허용하지 않는다. 이전485/489 판정은 유지한다. CLI `--trial 492 --baseline-raw <489로그폴더> --baseline-trial 489`를 지원한다.

## 보존·재현

원복은489/485/482/476/164/467 모두 byte/hash 동일하게 포함했다. 상용 ROM/save는 제외하고 자작 NROM 회귀2개만 기존 원복에 보존한다. base와m3nu도489와 같다. GBC/save 원본을 바꾸지 않는다.

로컬 선택은 `probes/nes-schedule492` candidate01/ARM01/assembly01/trial02/parser01,programmer01은 ASCII 실행 폴더에 보존했다. 공개 레시피는 nes_schedule492/assemble/package/test_analysis와 기존 strict hardware 분석기다. 정당한 ROM/491 원본·보드·도구 의존성은 [재현 범위](../cores/nes/REPRODUCING.ko.md)에 따른다. 누락 ELF Python import와 준비되지 않은 출력 경로의 초기 실패도 원시 출력으로 보존한다. 개인 라이선스·원시 로그·실행 파일·설치 ZIP은 Git에 넣지 않는다.
