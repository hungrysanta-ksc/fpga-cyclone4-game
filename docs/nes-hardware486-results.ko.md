# NES486 — MMC485 대기·레벨 플레이 실기 수신

486은485 전달본의 수신 분석 번호다. 새 firmware/FPGA/설치본은 만들지 않았다. [수치·해시](../analysis/hardware486-gameplay485.json)·[485 변경](nes-supply485-contract.ko.md)·[현재 순서](nes-game484-next-plan.json)를 따른다.

사용자는 두 실행 모두 게임 로드와 메뉴 복귀가 정상이라고 확인했다.1차는 스테이지에 들어가지 않고 둔 실행,2차는 월드맵에서1-1에 들어가 플레이한 실행이다. **장면이 다른 두 결과를 하나의 FPS로 합치지 않는다.**

## 실측

| 항목 | 1차: 스테이지 미진입 | 2차: 첫 레벨 플레이 포함 |
|---|---:|---:|
| 표시 실행 구간 | 60.07s | 60.07s |
| 최종 완료 표시 | 814 | 494 |
| 구간 평균 표시 FPS | **13.55** | **8.22** |
| 전체 평균/표시 | 73.80ms | 121.60ms |
| 수신 DWT 포함 | 17.13ms | 31.78ms |
| 계획·tile 공급 DWT 포함 | 30.19ms | 40.31ms |
| 출력·SEAL·최종 ACK DWT 포함 | 25.89ms | **48.33ms** |
| coarse planner−callback | 11.40ms | 10.93ms |
| coarse finish | 15.82ms | 25.32ms |

DWT는 실제 ARM·IRQ·guard·SPI/ROM 대기를 포함한다. coarse는10ms tick 집계이며 마지막 미완료 시도도 일부 포함한다. op/quiet는 단계 안에 중첩되므로 위 값에 더하거나 통째로 빼지 않는다.8.22fps는 타이틀·월드맵 구간도 포함한60초 평균이며 레벨만의 FPS가 아니다.

2차의 프레임 시작 기준5초 버킷은68/71/50/40/35/38/34/32/31/32/27/36회다. 후반은5초당27..40회로 줄며 해당 버킷의 SEAL은 약58..68ms/완료 표시다. 이는 정밀 장면 FPS/p95나 영상과의 정확한 시간 정렬을 뜻하지 않는다.

기존482는 다른 조작의60.06초/877회·14.60fps였다. 관측상485의1차 계획 단계는32.32→30.19ms지만 SEAL은18.44→25.89ms로 길어졌다. **485의 전체 가속은 입증되지 않았다.** 장면·입력이 달라 특정 변경의 회귀율이나484 계산 절감의 실기 효과를 이 숫자만으로 확정하지 않는다.

## 영상 확인

2차 MOV는67.03초이며5초 간격14개 실제 프레임을 추출해 살폈다. 타이틀→월드맵→1-1, Mario의 위치 변화·공중 동작·횡스크롤 장면을 확인했다. 촬영된29.96fps는 카메라 값이며 게임 표시 FPS가 아니다. 이 표본만으로 모든 프레임의 픽셀 정확도·매끄러움·음질을 증명하지 않는다.

끝 표본은 화면이 어두워지는 전환 중이다. **메뉴 복귀는 사용자 확인과 STOP/base 로그가 근거**이며, 영상 표본에서 메뉴 화면까지 확인했다고 쓰지 않는다. 원본 영상·추출 이미지·contact sheet는 로컬 `probes/nes-hardware486/video`에 보존하고 Git에는 hash/관측만 기록했다.

## 종료와 error13의 해석

두 번 모두 전체393216B 적재/readback·검사·START·STOP·base 복구·safe_to_reload를 통과했다. native_result=1은60초 deadline 종료다. CRC 오류·driver failed transfer·receiver 오류는0이다.

1차는 input COMMIT815/최종 표시814이며 마지막 시도는 완료하지 않았다. window sent11712/retired11711로 실제 ACK 대기1건이 남았으므로 이를 표시로 더하지 않는다.

2차는 input COMMIT495/최종 표시494, native_result1·plan_error2·video_error13·sink/window 오류0·trace abort0이다. 실제 코드는 deadline guard 실패→OBJ writer false→resident slot 반환 UINT16_MAX→planner error13으로 이어질 수 있다. **13만으로128 OBJ slot 부족이라고 해석하면 잘못이다.**

같은485 링크 M4를 기존905 입력으로 실행해 정상 전체 상태/계획을 대조한 뒤 OBJ writer만 실패시켰다. slot을1개 사용한 상태에서도 error13이 발생했다. 이 전파 검증과 위 로그 조합으로2차는 `deadline_during_OBJ_emit`로 분류한다. 물리 종료 순간의 RAM을 재생한 것은 아니며, native_result5/plan_error0 등 다른 실패 조합은 정상으로 허용하지 않는다.5개의 변조 로그를 거부하는 검증도 통과했다. 원래 엄격 parser의 거부와 원시 로그는 보존했다.

## 60Hz 예산에서 드러난 문제

2차의 현재 형식 command-body는 완료 표시당 약 **6728.50B**다. D1에서3B/회, E1에서19B/회, E9에서8B/회를 뺀 총량으로, input body3493.99B·output command body3147.42B·plan body87.09B다. full-duplex를 양방향으로 두 번 세지 않았다.

현재 SPI2.625Mbit/s에서 이 body만 전송해도 약 **20.51ms/표시**다. polling/framing까지 포함한 실제 wire byte 투영은38.98ms다.60Hz wire-only budget은5468.75B/표시이므로, 관측한 body량을 유지한다면 polling과 CPU 비용을0으로 해도16.67ms 예산을 넘는다. body를약18.72% 줄이는 것조차 wire-only 임계치일 뿐 전체60Hz 달성을 보장하지 않는다. 마지막 미완료 capture가 포함된 유한 구간 투영이며, 새 encoding/새 workload까지 불가능하다는 주장이 아니다.

2차의 D0/E0/E8은 표시당 약121.01/128.12/85.73회다.1차 D0는18.72회여서 입력 공급 대기가 크게 달라졌다. 또한 변경 map granule은1차1.67→2차12.67/표시로 늘었다. 이 값은 현재 map_dirty이며 destination bank의 stale union/실제 전송량과 같다고 가정하지 않는다. E1 body도 section별 구분이 없어 map/HDMA/OAM 각각의 원인까지 이 로그로 확정할 수는 없다.

현재 production FPGA에서 MCU_RDY는 `external_memory_ready`다. source packet-ready나 plan progress IRQ가 아니다. 옛367 연구의 source-ready IRQ를 현재485에 연결돼 있는 기능으로 계산하거나, 이 핀을 확인 없이 input-ready 대기로 바꾸지 않는다.

## 다음 순서

1. 고정 입력에서 실제 serializer의 map/HDMA/OAM/manifest body와 두 bank stale 확장을 구분한다. 이미 있는 압축·차분·재사용이 레벨 스크롤에서 어디서 효과를 잃는지 확인한다. 추가 계측만 넣은 실기 전달은 하지 않는다.
2. 가장 큰 출력·SEAL48.33ms를 ARM 발행/SPI·SNES 수신/독립 검사·DMA·VBlank까지 함께 비교한다. 단순 최종 ACK polling48ms라고 보거나 검사를 제거하지 않는다.
3. 현재 data량을 줄이는 방식과 검증 가능한 SPI 속도 여유를 전체 비용으로 비교한다. 속도 변경은 sampling/CDC/CRC·ROM 경쟁·STOP 검증 전 채택하지 않는다. Flash232B·FPGA154LE 여유를 무료로 쓰지 않는다.
4. D0 공급 대기와 ready 핀/IRQ 소유권을 추적한다. 다음 후보 또는 기존482/485의 같은 입력 비교에서만 속도 변경의 원인을 판정한다.

현재 플레이 포함 평균은121.60ms로60Hz까지 **104.93ms**가 남는다. 이번 실제 플레이 데이터는 기능 범위를 넓혔지만60fps 성과는 아니다. GBC 공개본·save·정상482/476/164/467 원복을 그대로 보존한다.
