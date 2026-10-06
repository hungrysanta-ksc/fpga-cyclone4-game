# NES-H1-SPI-036 결과

2026-10-06. **실기 진입을 막을 SPI 비트 밀림을 재현·수정하고, 동일 수정본의 FPGA 이미지를 생성했다.**

035의 STM32는 SCK 상승2us 뒤 읽지만034 FPGA는 상승 뒤 응답 비트를 변경했다.
기존 시험이 상승 순간에 읽어 놓쳤던 차이다. 실제 RTL에서 F0 ID가 A5 대신4B로 읽히는 것을 확인했다.
응답을 SCK 하강에서만 갱신해 high 구간에 유지하도록 수정했다.

- 생산 C에서 얻은942행 파형:읽기224회 중 실제 응답88비트 일치.
- 기존 보드6조건,ROM65,536바이트·패턴8,192바이트 exact 회귀 통과.
- 물리 map/fit/STA/ASM 통과:1,302LE/104LAB/44M9K,135핀,PLL1.
- 내부 최소 slack:setup+2.224ns,hold+0.179ns,recovery+6.736ns,removal+0.592ns.
- RBF209,988 bytes와 BI3 생성.실제 MCU RLE 해제 C로 전체 바이트 및 EOF 일치.
- 이전035 산출물122개를 보존했다.035 MCU와034 ROM/프로토콜은 그대로다.

원본 압축기는 RBF 끝에 FF 1바이트를 중복 출력했다.
원본 압축을 보존하고 증명된 마지막 리터럴만 제거해 H1의 exact roundtrip을 맞췄다.
GBC 압축기·재현 도구와 원본 라이선스는 변경하지 않았다.

| 산출물 | SHA-256 |
|---|---|
| RBF | 59b60594789fb0ca0fe74e9f2fbd6ba81e1a3686493d14387e00552edeb6bb31 |
| fpga_nh1.bi3 | 6de44eeea2c8692f303bc8aa66a572cec076710bb7ab6b034310f5abd63ad913 |
| 함께 사용할035 MCU | 76ce009ce667878fd6da0577025eed8a1725b12ec5b8007fe81d6de7074a0470 |

**실기 준비 완료는 아니다.** 외부38입력/11출력은 아직 미제약이며, SNES/DMA/보드 방향전환 요구의 검토가 남았다.
기존 async_reg/ROM writeport/상수출력/무효 synchronizer assignment 경고도 기록에 유지한다.
STA/ASM 경고0과 내부 slack 양수만으로 외부 I/O를 통과 처리하지 않는다.

처음 dummy 응답 비교 오류, 압축 끝 패딩 검사 실패, Quartus 비ASCII Tcl 경로 실패와 검증기의
CRLF/QSF 버전 메타데이터 처리 수정도 원시 증거에 보존했다.
Questa의 기존 무료 FLOAT 경로를 사용했으며 이번에 새 Mesen/실물 MCU 실행은 하지 않았다.
H0의 기존 기본 육안 통과 범위는 그대로다.

[재현·한계·다음 관문](../docs/nes-h1-spi-contract.md), [기계 검증](h1-spi-verification.json), [파일 해시](h1-spi-artifacts.json).
원시 증거는 ignored local-h1-spi-036/에 있다.
