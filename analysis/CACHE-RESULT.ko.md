# NES CHR 캐시 전송 결과 — NES-P1-CACHE-003

2026-10-05. SPDX-License-Identifier: MIT.

**8개 1KB CHR 창을 순서대로 교체하고 같은 물리 주소의 세대 갱신을 실제 SNES
PPU 출력으로 확인했다. 진단 OFF/ON 각각 128프레임에서 화소 차이, 전송 기한
초과, 소유권 위반이 없었다. 아직 합성 ROM 공급원 시험이며 MMC3/실기 통과는 아니다.**

[이전 동적 결과](STREAM-RESULT.ko.md), [캐시 계약·재현](../docs/nes-cache-contract.md),
[원시 재검사 요약](cache-verification.json), [소스·증거 해시](cache-artifacts.json).

## 변경과 검증 범위

이전 시험의 BG CHR는 고정 상주했다. 이번에는 8KB VRAM 캐시의 각 1KB 창을
매 프레임 하나씩 교체한다. 32개 상태를 반복하면서 각 창은
`bank w/gen1 → bank w+8/gen0 → bank w+8/gen1 → bank w/gen0 → bank w/gen1`을
거친다. bank는 합성 물리 CHR 주소의 1KB 단위 번호이며 MMC3 레지스터 자체가 아니다.

원본 2bpp 패턴 2,048개(16 banks × 2 generations × 64 tiles)는 모두 서로 다르다.
첫 6화소에 주소/세대 식별자를 넣고 나머지는 결정적 패턴으로 채웠다. 전체 atlas의
중복 없음과 planar 왕복 변환을 검사했다. 모든 2,048개 타일이 화면에 전부 나왔다고
주장하지 않는다. OBJ는 이전 시험의 고정 타일을 사용한다.

타일 캐시 키는 `(물리 bank, generation)`이다. 고정 창별로 저장한 이전 키와
패킷의 예상 이전 키가 일치해야 새 데이터를 받는다. 부분 패치 CHR/지도는 비표시
영역에 먼저 전송한다. 취소 검사를 통과한 뒤 phase 5 확정 구간에서 표시 캐시를
교체하고 CGRAM/OAM/스크롤/화면 선택을 갱신한다. 이 구간은 VBlank 안에서 끝나야
하며 도중 취소는 지원하지 않는다. 전송 후 되돌리는 이중 BG 캐시는 아니다.

## 실행 결과

| 시험 | 캡처 | 확인 결과 |
| --- | ---: | --- |
| 진단 OFF | 128 | 화소 차이 0, 128 commit |
| 진단 ON | 128 | 화소 차이 0, OFF와 전체 프레임 해시 동일 |
| 프레임 7 stage 후 reset 요청 | 64 | 63 commit/1 cancel; 이전 화면·캐시 키 유지, 동일 프레임 재시도 성공 |
| 프레임 8의 8페이지 요청 | 32 | E3, 해당 요청 DMA 0B, 이전 화면 유지 |
| 프레임 8의 예상 이전 세대 오류 | 32 | E4, 해당 요청 DMA 0B, 이전 화면 유지 |
| 새 키에 이전 세대 데이터 주입 | 64 | 16프레임에서 총 84,510화소 오류 검출 |
| bank 상위 주소 비트 누락 | 64 | 46프레임에서 총 1,326,616화소 오류 검출 |

마지막 네 시험은 의도대로 실패해야 감사가 통과한다. 오래된 **데이터 내용**과 주소
별칭은 호스트가 자체 CRC로 거부한 것이 아니라, 실제 RGB 대조로 검출했다. 캐시 키만
맞고 데이터가 잘못된 경우의 검출 필요성을 보여 준다. 런타임 payload CRC는 없다.

관측 Lua는 읽기/기록만 수행한다. `verify_nes_cache.py`는 원시 RGB와 프레임 번호,
모든 캐시 키, 원시 DMA 레지스터/phase/clock을 다시 읽고 전송 순서·범위·기한과
오류 원인을 검증한다. 에뮬레이터 frame skipping은 비활성화했다. 정상 모드에서는
source frame을 생략하거나 forced blank를 반복하지 않았다.

## 전송 예산

지도에서 바뀌는 패치 행은 14번 한 행뿐이다. 기존의 5행 대신 64B만 전송한다.
OBJ 15개의 좌표/속성 60B만 매 프레임 쓰고, 미사용 OBJ와 high table은 startup에
한 번 초기화한다. 색·화소·스프라이트 수를 줄인 최적화가 아니다.

| 매 프레임 DMA | 바이트 |
| --- | ---: |
| BG CHR 캐시 한 창 | 1,024 |
| 부분 패치 CHR | 544 |
| 부분 패치 지도 한 행 | 64 |
| CGRAM | 384 |
| OAM 사용 항목 | 60 |
| **합계** | **2,076** |

startup DMA는 25,600B이며 초기 forced blank에서 별도로 수행한다.

| 실행 | 최장 begin→commit | 최소 deadline 여유 |
| --- | ---: | ---: |
| OFF | 21,282 master clocks | 8,610 clocks |
| ON | 22,050 master clocks | 7,858 clocks |
| reset 포함 | 21,392 master clocks | 8,522 clocks |

1페이지/패치 최대 544B에 대한 보수적 모델은 DMA + CPU/설정 4,096 + 진단 768 =
21,472 usable clocks다. 이전 모델의 80% 목표 23,299.2 이내다. 실측은 Mesen의
master clocks로 refresh를 포함하며, 이전과 같은 line 0 직전 경계를 사용한다.
이 여유에 FPGA/SRAM/MCU 공급 지연이 포함된 것은 아니다.

**8페이지가 모두 새 데이터라면 CHR DMA만 65,536 clocks가 필요해 239줄 표시의
22 blank lines(30,008 raw clocks) 안에 들어가지 않는다.** 이번 런타임은 그 요청을
조용히 생략하지 않고 E3로 정지한다. 이는 제품 해결책이 아니라 분명한 미통과 범위다.
실제 fetch working set에 맞춘 상주/사전 적재/타일 단위 갱신을 더 검증해야 한다.

## 남은 제한과 다음 단계

- 256×239 비교만 수행했다. 원본 240번째 줄 표시 정책은 아직 결정/승인되지 않았다.
- scanline/dot 중 bank switch, CHR RAM 개별 쓰기 타이밍, 일반 캐시 할당/eviction,
  실제 PPU fetch, mapper IRQ는 이 고정 창 교체 시험의 범위 밖이다.
- reset은 stage 후 협력적 요청 취소다. epoch를 올리고 동일 요청을 다시 처리한다.
  비동기 물리 reset, 확정 구간 중 reset, 실제 CDC/MCU ack는 검증하지 않았다.
- 세대는 시험용 0/1, frame counter는 8bit이며 wrap/장기 실행은 미검증이다.
- OBJ CHR 갱신, 일반 layer overlap, emphasis/left mask, 외부 메모리 지연은 미완료다.
- 원래 NES 기능 컴파일 문제, HDL 라이선스 보류, 전체 fit/STA, SMB3/실기는 그대로다.

다음 gate는 동시에 필요한 CHR 타일의 working set과 사전 적재 가능 시점이다.
새 bank가 예고 없이 도착해도 표시를 유지할 수 있는 경우와 실패하는 경우를 분리해
측정해야 한다. 게임 속도·프레임·색을 희생하는 정책을 채택하지 않았다.

기존 P1/STREAM-002 소스·결과와 실험 초안을 보존했다. GBC 기준 소스 해시 및
Quartus 입력/packed boot 검사는 통과했다. 공통 MCU/FPGA 코드 변경과 실기 배포는 없다.
