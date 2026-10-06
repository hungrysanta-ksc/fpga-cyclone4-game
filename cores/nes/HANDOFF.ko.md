# NES 다음 작업 인계 — 058 이후

현재 후보는 **NES-READBACK-PORT-058**. [결과](../../analysis/ROM-READBACK-PORT-RESULT.ko.md)와 [포트 계약](../../docs/nes-rom-readback-port-contract.md)을 먼저 읽는다. 실기044·MCU056은 유지하며 새 SD 이미지는 없다.

## 완료한 경계

- 057 승인된 chr32 공유를 유지한다.058은 기존052 reader의 FSM/주소/chip/lane/data를 메모리 클록 CHECK와 RUN이 공유한다. 코어는 CHECK 동안 reset이다. FPGA CRC·두 번째 reader·새 CDC 왕복은 추가하지 않았다.
- 핀 모델1919161검사:835585핀 쓰기,80/96KiB 전체를 포함한180238CHECK 읽기,1024RUN 읽기.10취소/10거부/4데이터 손상,chip/lane/CHR 주소의 예상 실패3종이 확인됐다. 오류 중 기존 쓰기는 끝까지 유지한다.
- CHECK를 끈 reader와 원본052의 전체 출력은4096요청(4053응답+43취소),161207edge 비교에서 동일하다.058은 전체 NES CPU/PPU를 새로 실행하지 않았다. 마지막 실제 코어8프레임/491520픽셀은057이다.
- 새 공동 fit13946LE/949LAB/5160레지스터/26M9K. 외부 CHECK 포트를 포함한335가상핀 조건에서14LAB 여유다.057보다 패킹이 달라졌으며 SPI 확장의 여유를 보장하지 않는다. 물리 핀22개 미배치,PLL0,전체 보드/STA 미완료다.

## 다음 구현 순서

1. CHECK를 SPI 명령/응답에 연결한다.058 응답은 한 메모리 클록 pulse이며 다음 요청이 주소 tag를 바꾸므로 SPI용 완료 mailbox/ack가 필요하다. 수신 offset은 STATUS 중 덮어써질 수 있어 그대로 재사용하지 않는다. 단일 outstanding,실제 데이터·tag 보존,프로토콜 버전/CRC/CS절단/오류 취소를 먼저 정한다.
2. MCU가 SD 승인 입력과 실제 반환 바이트 전부를 비교하고 길이·중복·tag·timeout을 검증한다. 입력CRC/END/loaded를 무결성 완료로 표시하지 않는다. 검증 성공 뒤 CHECK 해제·reader 공통 reset·RUN/049 scrub으로 넘긴다. 아직058에는 성공을 요구하는 START gate가 없다.
3. 실제 C GPIO 파형을 RTL에 재생하고 전체 코어8프레임/전체 이벤트를 새 통합 경로로 회귀한다. 같은 구현으로 공동 fit를 다시 한다.14LAB은 현재 외부 CHECK 포트 시험의 수치다.
4. 보드 클록/소비자/프레임 마감/복구와 전체 핀·PLL fit·CDC·STA 이후 RUN/메뉴 진행/종료 표시와 복구 가능한 실기 쌍을 준비한다. SNES_SYSCLK/PIN_A9는 아직 미확인 후보며,056 true 반환은 메뉴 재로딩 안전성이다. 복구 실패에서 RESET/USB 보호를 풀지 않는다.

STOP과 CHECK 해제는 함께 수행한다. RUN 전에는 CHECK를 최소 한 mem_clk 내려 reader 양쪽을 공통 reset한다(058시험5클록). CHECK 잘못 사용 시 sticky fault는 common reset으로만 해제한다. 핀25ns 모델을 실제 메모리 규격으로 부르지 않는다.

044 실기와 과거 실패/원시 근거를 유지한다.058 초기 fit의 중첩 폴더 복사 실패,초기 diff의 미연결 출력 경고와 수정 후 통과도 보존한다. [과거 주의사항](history/AGENTS-053.md), [공개 재현](REPRODUCING.ko.md), [주요 진전 관리](../../docs/development/MILESTONE-WORKFLOW.ko.md)를 따른다.
