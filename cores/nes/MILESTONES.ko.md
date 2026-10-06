# NES 주요 진전

이 문서는 개발 단계의 색인이다. 진단 통과는 일반 게임 또는 제품 완료를 의미하지 않는다. 원시 로그는 공개하지 않고 후보별 요약·계약·해시를 제공한다.

| 단계 | 진전과 관측 | 근거 |
| --- | --- | --- |
| 001–018 | upstream/고지 조사, 자체 CPU·PPU·DMA·IRQ 진단, 자원 조사 | [source lock](../../analysis/source-lock.json), `analysis/*RESULT*` |
| 019–032 | 영상 부하·스크롤·CHR/뱅크·전송 큐·CDC·SNES 경계의 제한된 실현 가능성 | [누적 기록](history/README-053.md) |
| 033–036 | 가독성 있는 LINK SCREEN 진단, MCU GPIO 파형 재생. 이전 SPI 응답 비트 밀림을 보존·수정 | [SPI 결과](../../analysis/H1-SPI-RESULT.ko.md) |
| 037–043 | 자동 메뉴 복귀 실패. 종료 로그·일관된 오류 사건·입력 샘플링 조사. 원래 SDF 실패 보존 | [누적 기록](history/README-053.md) |
| 044 | 실기 화면 순환·RESET 복구, GBC 정상 플레이 보고 | [실기 기록](../../analysis/H1-HARDWARE-044-RESULT.ko.md) |
| 045–046 | 메모리 패킷 생산기와 제한된 NCR1 BG 인코더 | [045](../../analysis/PACKET-MEMORY-RESULT.ko.md), [046](../../analysis/NCR1-ENCODER-RESULT.ko.md) |
| 047 | 실제 코어 PPU→인코더→전송 연결, 8프레임/491520픽셀 비교 | [047](../../analysis/NCR1-LIVE-RESULT.ko.md) |
| 048 | OAM 쓰기 구조 최적화, 216362클록 비교. 870 LE 절감 | [048](../../analysis/OAM-BANKED-RESULT.ko.md) |
| 049 | 12 KiB 로컬 RAM·초기화 연결 | [049](../../analysis/LOCAL-MEMORY-RESULT.ko.md) |
| 050–051 | 공유 ROM 서비스 마감 오류 재현 및 조기 읽기, 2–4클록 모델 통과 | [050](../../analysis/ROM-SERVICE-RESULT.ko.md), [051](../../analysis/ROM-EARLY-RESULT.ko.md) |
| 052 | PSRAM 읽기 핀·서로 다른 클록 연결, 16위상 검사 | [052](../../analysis/ROM-PHYSICAL-RESULT.ko.md) |
| 053 | 핀으로 ROM 적재 후 코어 실행, 8프레임/491520픽셀. 공동 929 LAB | [053](../../analysis/ROM-BOOT-RESULT.ko.md) |

다음은 [MCU 적재·보드 통합](HANDOFF.ko.md)이다. 이번 공개 정리의 새 시험은 [공개 메모리 회귀](REPRODUCING.ko.md)이며 과거 실제 코어 실행을 다시 실행한 것으로 계산하지 않는다.
