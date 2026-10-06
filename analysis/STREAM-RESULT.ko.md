# NES 동적 영상 전송 결과 — NES-P1-STREAM-002

2026-10-05. SPDX-License-Identifier: MIT.

**고정 장면에서 연속 프레임 갱신으로 진행했다. 진단 OFF/ON 각각 128프레임에서
SNES PPU 표시 화소 차이 0, VBlank 기한 초과 0, 표시 중 패치 영역 덮어쓰기 0을
확인했다. 아직 ROM 공급원을 쓰는 SNES 호스트 시험이며 FPGA/실기/SMB3 통과가 아니다.**

[이전 고정 장면 결과](P1-RESULT.ko.md), [동적 계약](../docs/nes-stream-contract.md),
[검증 요약](stream-verification.json), [소스·증거 해시](stream-artifacts.json).

## 실제로 실행한 변경

16개 서로 다른 원본 합성 상태를 순서대로 반복했다. 상태별로 1픽셀 스크롤,
움직이는 스프라이트, y=119/x=123의 팔레트 변경을 재생한다. 8×16 스프라이트는
두 SNES 8×8 OBJ로 나누고 NES의 scanline별 첫 8개 선택 결과를 타일 행 마스크에
반영한다. 스프라이트의 BG 앞/뒤 우선순위를 실제 SNES에서 비교했다.

Mode1 BG3는 2bpp 배경, BG1은 4bpp 부분 패치, OBJ는 스프라이트다. BG3 타일의
우선순위 비트를 설정해 뒤쪽 OBJ가 불투명 BG를 뚫고 나오는 오류를 수정했다.
소스 선택 결과는 합성 renderer가 계산한다. NES PPU의 실제 sprite evaluation
회로나 mapper fetch를 검증한 것은 아니다.

패치 CHR와 지도를 두 VRAM 영역에 번갈아 쓴다. 이전 영역을 유지한 채 새 영역을
먼저 전송하고, VBlank 안에서 CGRAM/OAM/스크롤/표시 map과 frame_id를 확정한다.
리셋 취소 후에는 frame_id의 홀짝이 아니라 현재 표시 영역의 반대쪽을 사용한다.

이번 진단 LUT는 64개 색 번호가 모두 서로 다른 RGB555 값이 되도록 고정했다.
기존 정적 시험의 LUT는 일부 색 번호가 동일 RGB가 되는 한계가 있었다. 이번 LUT도
실제 NES 아날로그 색·emphasis 변환 정책은 아니다. 색 수를 줄여 통과하지 않았다.

## 결과

| 시험 | 실제 캡처 | 결과 |
| --- | ---: | --- |
| 진단 OFF | 128 연속 프레임 | 화소 차이 0; 128 commit |
| 진단 ON | 128 연속 프레임 | 화소 차이 0; OFF와 모든 프레임 SHA256 동일 |
| 전송 후/commit 전 리셋 요청 | 64 연속 프레임 | 63 commit, 1 cancel; 이전 프레임 보존; 전체 화소 차이 0 |
| DMA 길이 0 주입 | 32 연속 프레임 | 프레임 7에서 E2 오류, 해당 거래 DMA 0B, 이전 화면 유지 |
| 길이 검사 뒤 강제 과다 전송 | 32 연속 프레임 | E1, deadline/영역 위반 검출; 한 프레임 52,735화소 차이 |
| NES 첫 8개 마스크 생략 | 32 연속 프레임 | 매 프레임 55화소 차이 검출; DMA 기한은 통과 |

정상 상태와 부정 시험을 합쳐 성공이라고 세지 않는다. 마지막 세 행은 의도대로
실패해야 통과하는 감사 항목이다. `verify_nes_stream.py`가 정상 결과뿐 아니라
실패 원인, 원시 RGB와 ROM 해시, 연속 emulator frame 번호를 다시 검사했다.

진단 ON은 매 프레임 WRAM 표식 16회 쓰기를 추가한다. FPGA 로깅 자원·대역폭을
모사하지는 않는다. OFF/ON 합계 256프레임은 약 수 초 범위로, 장기 플레이가 아니다.

## 전송량과 기한

모든 표시 프레임에서 필요한 데이터를 실제 DMA로 갱신했다. 관측 최댓값:

| 항목 | 바이트 |
| --- | ---: |
| 부분 패치 CHR | 544 |
| 패치 지도 5행 | 320 |
| CGRAM | 384 |
| OAM | 544 |
| **합계** | **1,792** |

BG CHR와 두 배경 지도, OBJ CHR 480B는 startup forced blank 중 사전 적재한다.
초기 적재는 총 25,056B이며, 게임 중 매 프레임 전송량과 분리한다. 정상 반복 중
forced blank를 켜거나 source frame을 생략하지 않았다.

| 시험 | 최장 begin→commit | 최저 deadline 여유 |
| --- | ---: | ---: |
| 진단 OFF | 17,586 master clocks | 12,328 clocks |
| 진단 ON | 18,394 master clocks | 11,508 clocks |
| 리셋 시험 | 17,656 master clocks | 12,240 clocks |

측정은 Mesen의 실제 SNES masterClock/scanline/hClock과 DMA 레지스터 쓰기
callback에서 얻었다. line 0 전체를 남기는 경계를 deadline으로 잡고 odd-frame
short line 4 clocks를 보수적으로 차감했다. startup 첫 VBlank는 overscan 설정이
래치되기 전 225줄에서 시작할 수 있어 정상 반복의 240줄 시작과 구분한다.

실행 호스트는 CHR 길이를 1..1,024B, 32B 정렬로 제한한다. 길이 0은 SNES DMA에서
대량 전송이 되는 특수값이므로 시작 전에 거부한다. 현재의 고정 전송 묶음에 대해
DMA 2,272B 상한과 CPU/설정 4,096 clocks, 진단 768 clocks를 예약하면 23,040
usable clocks다. 모델의 80% 목표 23,299.2 clocks 이내지만 **1,024B 상한 자체를
실측 스트레스 실행한 것은 아니다**. 현재 실측은 CHR 최대 544B에 한정한다.

강제 과다 전송 시험은 길이 검사를 고의로 우회하는 테스트 변형이다. 정상 경로가
그런 payload를 허용한다는 뜻이 아니며, 단 한 프레임의 깨짐도 검출됨을 확인했다.

## 리셋과 소유권

프레임 7의 CHR+지도 864B를 비표시 영역에 쓴 뒤 reset 요청을 처리한다. CGRAM/OAM
commit 전에 취소하므로 새 팔레트와 이전 타일이 섞이지 않는다. 표시 frame_id 6을
한 번 더 유지하고 epoch를 증가시킨 뒤 8번으로 이어간다. 이 반복은 명시적으로
주입한 reset 취소 결과이며 정상 모드의 프레임 삭제 정책이 아니다.

이것은 **생산자 리셋 요청의 협력적 취소**다. CPU/PPU/FPGA의 비동기 물리 reset,
전원 차단, commit 중간 reset, 실제 MCU/CDC ack는 아직 검증하지 않았다. 공유
CGRAM/OAM commit이 시작된 뒤의 reset 요청은 해당 유한 구간이 끝날 때까지
보류해야 한다는 계약만 있다.

## 발견한 실패와 수정

- headless 최대속도에서 Mesen의 자동 frame skipping이 켜져 격프레임 캡처가
  이전 화소를 보였다. `--snes.disableFrameSkipping=true`를 필수 옵션으로 고정했다.
  비교 좌표나 예상 frame_id를 옮겨 결과를 맞추지 않았다.
- 스프라이트까지 모두 BG 화소 패치로 합친 최초 팔레트 배치는 6개 제한을 넘었다.
  색을 줄이지 않고 스프라이트를 OBJ로 분리했다. 이를 모든 화소 패치 방식의
  불가능 증명으로 확대하지 않는다.
- BG3 low priority에서는 뒤쪽 스프라이트가 BG 앞에 나왔다. BG3 high priority와
  OBJ priority 0/1의 관계를 적용한 뒤 실제 PPU 화소가 일치했다.

실패 ROM·캡처·로그는 로컬에 남아 있다. 최종 여섯 실행은 사용 소스 사본과 원시
RGB/trace/ROM을 묶어 보존했고, 공개 목록에는 자체 소스와 비식별 요약만 등록했다.

## 남은 범위

- 출력은 여전히 256×239다. 원본 240번째 줄 256화소는 미표시이며 제품 crop 승인 없음.
- 이번 C 시험은 고정 상주 BG/OBJ CHR를 사용한다. 8개 CHR 창의 실제 뱅크 교체,
  CHR RAM generation, 캐시 miss burst를 이 전송 시험으로 통과시킬 수 없다.
- 강조색/emphasis, left mask, 임의 dot 효과, 다양한 sprite 크기/overlap 조합,
  palette allocation의 전체 게임 범위는 미완료다.
- 입력은 ROM에 컴파일한 합성 상태다. FPGA가 실시간 생성하는 compact event 패킷,
  외부 SRAM 주소 변화/DMA 응답/MCU 경쟁/지연·drift·queue는 미구현이다.
- 8bit 실험 frame counter의 wrap과 장기 재생은 이번 128프레임 시험 범위 밖이다.
- Questa 기능 컴파일 실패, 파일별 HDL 고지 보류, 전체 board fit/STA, SMB3/실기 상태는 이전과 같다.

다음 실험은 **상주하지 않은 CHR 세대를 포함한 전송**이다. 첫째로 주소가 달라도
같아 보이지 않는 CHR 패턴을 만들고, 새 뱅크와 부분 패치가 함께 도착할 때의 실제
전송량을 측정한다. admission 초과는 cache preload/배치를 검토하며 감속·프레임
삭제·색 감소로 처리하지 않는다. 이 gate와 표시 정책을 해결한 뒤 CPU/MMC3 통합으로 간다.
