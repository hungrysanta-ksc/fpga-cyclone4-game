# NES 다음 작업 인계 — 060 이후

현재 후보 **NES-SD-READBACK-060**. [결과](../../analysis/SD-READBACK-RESULT.ko.md)와 [계약](../../docs/nes-sd-readback-contract.md)을 읽는다.044 실기와 GBC를 보존하며 새 SD 이미지는 없다.

## 완료한 경계

- 새 `nes_sd_readback_probe`는 변경 없는044+056 C 뒤에 붙으며59 load/query와059 verify를 연결한다. 두 번째 입력의CRC·close 후 END,세 번째 입력의헤더·크기·전체CRC·close 후에만 FINISH한다.256바이트 버퍼 사용,START/SD 쓰기 없음.
- true는 안전한 메뉴 재로딩 가능성이다. `verified`,load 결과,verify 오류,STOP,base 복구를 각각 검사한다. 검증 성공 뒤 STOP 실패라도 base 복구가 필수다. 복구 실패에서는 RESET/USB 보호를 해제하지 않는다. 불확실한 DATA/ACK는 재전송하지 않는다.
-41실행·복구/18입력 거부와CRC·close 제거 예상 실패2종이 확인됐다. 실제 C GPIO 적재29024응답 비트/256핀 바이트,비교43288비트/256ACK/SD 오류STOP이044+059 RTL에서 통과했다. 비교용96KiB 준비는 loader stimulus와핀 쓰기이며 전체 C 적재 파형이 아니다.
- ARM 전체 링크에 새1068B 진입점이 남지만 메뉴는 미호출이다. 실제 STM32/SD 실행이 아니다. 컴파일 이미지를 설치하지 않는다.
- SPI/메모리5개 RTL은059와동일하다.959LAB/4여유와8프레임 근거는059 재사용,060 새 합성·전체코어실행 아님. 이전044–059 근거를 고정한다.

## 다음 구현 순서

1. CPU/PPU RUN 없는 load/verify/STOP 진단의 실제 보드 top을 만든다.044 경계와59 SPI/PSRAM을 승인된 핀·클록·reset에 연결하고,실제 메모리 규격·IO 타이밍·핀 소유권·PLL loss와전체 physical fit/STA를 확인한다. 동작하는 GBC의 조건을 NES 사실로 복사하지 않는다. SNES_SYSCLK/PIN_A9는 미확인 후보다.
2.060 함수를 동기 메뉴 흐름에 연결한다. 성공/오류/복구를 읽을 수 있는 후보 표식·대기 시간·로그로 남기고 취소·복귀를 검증한다. 현재59 byte별 추가 비교68.3/82.0초는 wire 계산이며 실기 측정이 아니다. RESET 유지 중 가능한 진행 표시 방식을 먼저 확인한다. 본래 fpga_pgm panic은 아직 별도 timeout으로 감싸지 않았다.
3. 같은 후보 MCU/FPGA 쌍,해시·백업·rollback·관측 절차를 준비해 제한된 실기 검증으로 간다. 전체 NES 소비자를 기다릴 필요는 없지만 해당 진단의 보드/복구 gate는 닫아야 한다. 일반 게임 실행 성공으로 확대하지 않는다.
4. 전체 코어 경로는4LAB 여유 아래 보드/소비자/프레임 마감/CDC/STA를 별도 진행한다. 필요 면적 개선은 차등 검증하고 NES를 늦추거나 프레임을 버려 통과시키지 않는다.

060 실패 기록: 초기host가 sticky SPI 오류 후 명령을 무시하는 동작을 잘못 가정했다. task 안의 참조도 선언 뒤에 놓아야 하며 preflight가 이를 검사한다. 실행 도중 driver가 편집될 수 있으므로 기록 해시는 저장한 실행 snapshot에서 구한다. wave02와최종wave03,Make 최초 dependency 실패를 보존한다. 한 FLOAT seat를 순차 사용하고 기존 wrapper가 서버를 종료하도록 한다.
