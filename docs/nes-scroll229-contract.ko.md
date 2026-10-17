# NES229 — 실제 첫 레벨 스크롤 자료와 입력 delta 설계 조건

2026-10-18. 사용자의 재개 요청에 따라 [228 회고의 수정 계획](nes-video-retrospective228.ko.md)을 시작했다. **이번 결과는 실제 게임의 연속 프레임 자료를 얻고 다음 구현의 정확성 조건을 정한 단계다. 새 펌웨어 또는 60fps 성능 검증은 아니다.** 배포 기준은227이며, 픽셀 불일치가 남은228 후보는 계속 보류한다.

## 작업 의미

기존 실기 로그는 구간별 비용을 보여주지만, 같은 게임의 연속 NES 프레임에서 실제로 무엇이 바뀌었는지는 보여주지 않았다. 이를 합성 스크롤 장면으로 대신하면 변경량과 매퍼 효과를 잘못 추정할 수 있다. 이번 도구는 사용자가 지정한 SMB3(J)의 첫 레벨을 조작으로 재현하고, **입력부터 줄이는 후보를 기존 출력과 비교할 실제 자료**를 만든다. 구현 성능 개선 자체는 다음 단계다.

공개 결과는 [검증 요약 JSON](../analysis/scroll229-verification.json), 도구는 `run_nes_scroll229.py`, `capture_scroll229.lua`, `analyze_nes_scroll229.py`, `test_nes_scroll229_analysis.py`다. ROM·화면·메모리·fetch 원자료는 로컬 `probes/nes-scroll229`에만 보존한다.

## 확보한 실제 장면과 검증 범위

- ROM SHA256: `dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49`. 지역·리비전을 바꾸지 않는다. ROM 패치·RAM 쓰기·치트 없이 버튼 입력으로 진입했다.
- MesenCE2.2.1, 소스 기준 `20ba206cef5ba207c21203176d02cb9f43dda9fb`, 사용 EXE/Core 해시는 JSON에 고정한다. MesenDB가 적용한 HVC-TSROM/MMC3A 설정과 FPGA 구현이 같다고 가정하지 않는다.
- 총96프레임880~975. 카메라 정지880~905와 **연속 스크롤906~975의70프레임**을 분리했다. 후자는 행32의 fetch 좌표 변화와 화면을 확인했으며, 직전905부터174픽셀 이동했다. 측정 좌표에는 선택한 fetch 열의16픽셀 오프셋이 있으므로 절대 카메라 좌표로 쓰지 않는다.
- 전체1,935,763건의 CHR 읽기에서 물리 주소·값이 사용자 ROM과 일치했다. 이는 Mesen 관측값 검증이며 FPGA의 PSRAM 응답 검증이 아니다.
- 같은 입력으로 관측을 끈 대조 실행도 완료했다. 입력·master clock 기록이 같고, 공통900/930/960 화면3개가 RGB 바이트 단위로 일치했다. 모든 프레임의 무관측 대조까지 했다는 의미는 아니다.
- 잘린 fetch 기록, 틀린 CHR 값, 필요한 PPUMASK 변경 증거가 없는 기록의3가지 오염을 분석기가 거절했다. 원자료는 변하지 않았다.

70프레임은 약1초 남짓의 한 장면이다. 장기 플레이·첫 레벨 전체·장면 전환·다른 매퍼를 대표하지 않는다. 다만 현재 후보를 판단할 때 부족했던 **실제 연속 스크롤**의 기준점이다. 이 자료를 먼저 소비하고, 후보의 결론을 바꾸는 경우에만 추가 수집한다.

## 관측 결과

아래는906~975, 이전 프레임 대비다. CPU 쓰기 횟수와 메모리 최종 차이는 서로 다른 관측이며 합산하지 않는다.

| 항목 | 평균/프레임 | 최대 | 의미 |
|---|---:|---:|---|
| 물리 nametable RAM 변경 | 3.44B | 12B | 기존 배경 대부분은 남고 새 영역 일부만 바뀜 |
| OAM 최종 변경 | 21.44B | 36B | 매 프레임256B DMA를 하더라도 최종 차이는 작음 |
| palette 최종 변경 | 0B | 0B | 이번 짧은 장면에 한함 |
| 최종 CHR bank map 변경 | 0B | 0B | **프레임 도중 bank 변경이 없다는 뜻이 아님** |
| NT/OAM/palette 단순 span 모델 | 63.37B | 117B | offset16+length8+변경 바이트만. 프로토콜·행 상태·픽셀 검증 제외 |

동일 화면 위치의 BG 물리 패턴 태그·plane row는75.74%가 이전 프레임과 같았다. PPU nametable 주소와 plane row로 대응시키면98.14%가 같았다. **속성·팔레트·OBJ·은행 소유권을 제외한 태그 대응 실험**이다. 기존 캐시의 hit rate, 전체 데이터의98% 절감, 실제 packet 크기 또는 FPS로 쓰지 않는다. 프레임 안에서 같은 키가 다른 태그에 대응하는 경우는 재사용 후보에서 제외했다.

더 중요한 것은70프레임 모두에서 다음 두 현상이 확인됐다는 점이다.

1. 같은 논리 CHR 페이지가 프레임 도중 서로 다른 물리 은행으로 매핑된다. 예를 들어906의 논리1KiB 페이지0은 물리 페이지8과92에서 실제로 읽혔다. 최종 bank map만 저장하면 이 차이가 사라진다. mapper 쓰기는 평균74.97회지만 IRQ 관련 쓰기도 있으므로 그 수 자체를 bank 전환 횟수로 부르지 않는다.
2. scanline193 부근에 PPUMASK로 렌더링을 잠시 끈다. 표준 BG plane fetch14784개를 기대했을 때61~65개가 빠지는 현상이 이 변경과 대응한다. missing fetch를0으로 채우거나 일반 행으로 억지 복구하지 않는다.

따라서 **“최종 NT/OAM이 조금 바뀌었으니 몇십 바이트만 보내면 화면 전체를 재현한다”는 설계는 탈락**이다. 상태줄 경계·행별 mask·fetch 시점의 물리 CHR 식별을 보존해야 한다. 이는 처음부터 현재 row/alt/mask 경로를 남겨야 하는 구체적 근거다.

기록의 프레임 경계도 구분했다. Mesen의 frameCount 증가와 startFrame 관측 gate 사이에 VBlank가 있어 첫880 쓰기 기록은 부분적이고976의 뒤쪽 VBlank가 포함된다. 쓰기 통계는 완전한881~975만 사용하며976은 별도로 세고 제외한다. fetch와 원자료의 번호를 임의로 다시 붙이지 않는다. CPU `$2004` 쓰기에는 OAM DMA가 포함되고 `$2007`과 PPU memory callback도 중복 관측이므로 각각의 횟수를 전송 비용으로 더하지 않는다.

## 후보 비교와 이번 결정

227의 실제 공유 SPI 비용은 평균16960B/완료, wire만51.69ms다. 60Hz 용량5468.75B에 CPU·간격·다른 서비스 여유도 남겨야 한다. 이번70프레임은 그 비용을 대체할 가능성을 조사하는 자료이며,227 실기의 다른 장면과 직접 속도를 비교하지 않는다.

| 후보 | 이번 자료가 지지하는 부분 | 아직 없는 증거·중단 조건 |
|---|---|---|
| A. 입력과 출력 공동 delta | 화면 위치보다 안정된 PPU/물리 식별로 대응할 여지가 큼. NT/OAM 변화도 작음 | 실제 collector geometry→기존 ARM planner→SNES 출력까지 같다는 증거, 입력+출력 전체 바이트와 CPU 비용, 기준 상태 메모리 |
| B. 병렬 aperture 확장·계산 재배치 | SPI의 대량 입력/metadata 경유를 제거할 구조적 가능성 | 현재 aperture는 SNES가 읽는 포트다. geometry를 여기에 놓는 것만으로 ARM 수신·계산이 없어지지 않음. SNES/FPGA로 옮길 계산과 제거할 기존 논리까지 정해야 함 |
| C. CHR 사전 준비 | ROM 물리 내용은 불변이므로 반복 읽기 일부를 줄일 가능성 |227의 생성 타일은 평균249B/완료, E9은0.52%. 입력·metadata 병목을 그대로 두면 우선 해결책이 아님 |

**A를 다음 제한된 구현 후보로 우선 검증한다. 최종 구조 채택이나 FIT 승인은 아직 하지 않는다.** 단순 snapshot 전송은 제외하고, 현재 생산 collector가 출력하는 의미를 유지한 기준 상태/변경 표현을 설계한다. B는 A가 전체 예산 또는 메모리 조건을 넘으면 전환할 대안으로 남긴다. C만 별도로 최적화하거나228의8B 맵 후보부터 수리하지 않는다.

현재 자원 여유는 FPGA159LE·2LAB·9M9K, ARM margin1800B, SNES body224B다. ARM 최소 gate1024B를 남기면 순증 여유는776B뿐이다. NT+OAM+palette만 복제해도2336B이므로 **새로운 전체 기준 snapshot을 ARM에 추가하는 안은 기존 저장공간 대체 없이 성립하지 않는다.** 현재 geometry15912B를 하나 더 복제하는 방식도 제외한다. FPGA RAM이 남아도 제어 논리·포트·배치 예산을 먼저 계산한다. 게임 세이브 SRAM은 사용하지 않는다.

## 다음 구현의 구체적 순서

1. 선택한70프레임의 fetch 시점 정보와 production collector의 row/group/alt/mask 표현을 연결한다. 관측 자료에 없는 nametable/attribute fetch 정보가 필요하면 정확히 그 부분만 보충한다. end-frame snapshot으로 만들어낸 값을 실제 관측이라고 취급하지 않는다.
2. source에서 안정된 identity와 변경을 판정하고, ARM의 기존 geometry 저장공간에 증분 적용하는 후보를 만든다. source base는 마지막으로 **수신 완료·검증된 상태**여야 하며 단순 직전 캡처가 아니다. 표시 ACK/슬롯 commit은 별도 수명이다. drop·STOP·epoch 변경·실패 때 기준을 명확히 무효화하고 새 기준을 받는다.
3. 같은 실제 자료로 원래227 경로와 후보의 geometry/계획/최종 픽셀을 비교한다. 일반 스크롤과193 부근 예외를 모두 포함한다. mapper를 논리 tile 번호로 치환하지 않고 CHR-RAM은 versioned fetch 시점 보존 또는 명시적 미지원 처리한다.
4. 공유 SPI 전체, source 허용창, ARM 작업, SNES CPU/VRAM/명령 수, 저장공간을 한 장부로 만든다. 입력 절감만 보고 성공이라 부르지 않는다. 수신 이후 계획/출력 재사용까지 연결하지 못하면60fps 후보로 채택하지 않는다.
5. 자원·정확성·전체 처리량 조건이 성립하는 후보 하나에 한해 최소 경계 검증과 FIT/paired build를 거쳐 실기 첫 레벨로 간다. 실패하면 작은 codec/FIT 변형을 반복하지 않고 B의 계산 위치 재배치를 평가한다.

60Hz 처리량과 입력 지연/화면 나이를 함께 본다. stage 중첩으로 지연이16.67ms를 넘더라도 지속60/s가 가능할 수 있지만, 같은 SPI의 바이트를 겹쳐 계산하거나 큐가 계속 늘어나는 설계는 허용하지 않는다. cold/장면 전환과 warm 지속 스크롤은 별도다. 이번에는 그 전체 장부와 출력 동일성까지 완성하지 않았으며 다음 첫 작업으로 명시한다.

## 재현과 보존

실행기에는 Mesen의 Lua IO 허용 옵션이 필요하다. 처음 두 preview는 이 옵션 없이 timeout으로 실패했고, 뒤 preview에서는 world map 진입 입력을 조정했다. 최종 capture01/control01의 스크립트는 동일하고 ROM을 수정하지 않았다. 임시 출력 이름은 ASCII 디렉터리여야 하며, 실행기는 새 디렉터리만 만든다.

```powershell
python -B tools/run_nes_scroll229.py --rom <user-ROM> --mesen <pinned-Mesen.exe> --out C:/temp/scroll-capture --frames 1020 --capture-first 880 --capture-last 975
python -B tools/run_nes_scroll229.py --rom <user-ROM> --mesen <same-Mesen.exe> --out C:/temp/scroll-control --frames 1020
python -B tools/analyze_nes_scroll229.py --capture C:/temp/scroll-capture --control C:/temp/scroll-control --rom <user-ROM> --out <result.json>
python -B tools/test_nes_scroll229_analysis.py --capture C:/temp/scroll-capture --control C:/temp/scroll-control --rom <user-ROM> --out <new-fault-directory>
```

선택 분석은analysis04, 오염 거절은negative01이다. analysis01/02의 프레임 경계·fetch 개수 가정 오류를 발견한 뒤 원자료를 수정하지 않고 분석을 고쳤으며 analysis03도 보존한다. 공개 JSON은 통계·해시만, 로컬 manifest는 전체 선택 증거를 해시한다. 기존227 생산 소스13개도 회고 pin과 다시 대조했다. 기존 실기 로그·GBC164·세이브 공간·봉인 증거는 유지한다.

Mesen API는 해당 버전의 [Lua 문서](https://github.com/nesdev-org/MesenCE/blob/20ba206cef5ba207c21203176d02cb9f43dda9fb/UI/Debugger/Documentation/LuaDocumentation.json)를 기준으로 했다. 이 호스트 관측은 실제 FPGA collector·C/65816 통합시험 또는 실기 성능 측정을 대신하지 않는다.
