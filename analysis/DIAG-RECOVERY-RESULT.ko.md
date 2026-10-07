# NES064 진단 하위 종료·오류 전달 결과

**이번 단계의 SD 읽기/FPGA 설정 오류 반환·진행 관측 목표는 달성했다. 전체 메뉴 복구와 실기 진입 준비는 부분 완료다.** PR #17 병합(`76bfe89dddbae7aa57fdf6eafff9167fbe19237b`,2026-10-07T03:02:30Z)을 확인하고 새 브랜치에서 진행했다. 실제 STM32·SD 실행이나 배포 쌍은 없다.

기존 `fpga_pgm`의 panic과 SD `wait_busy` 무한 대기, `sdn_read`의 무조건 성공 반환을 진단 전용 경로에서 처리했다. 플랫폼 원문과044/056/060/062 공개 기준을 보존하는 생성 overlay다. active 동안 버퍼 CMD17·실제 네 lane CRC16·응답 CRC7/R1 검사를 사용하며 재시도/오프로딩/쓰기/자동 재초기화를 막는다. native SD 오류 뒤에는 초기 검증 실패든 적재 중 실패든 GPIO를 복원하고 RESET/USB를 보호한 채 base SD 읽기·메뉴 재진입을 중단한다.

새 checked FPGA 설정은 독립 FIL·검사한 RLE·tick/poll/파일/출력 상한으로 실패를 반환한다. SD가 정상인 설정 실패는 base 복구를 시도하고, 실패한 base는 보호 상태로 남긴다. LED/UART로 검증·설정·적재·비교·복구·보류 단계를 구별하고 안전한 종료에서 LED 상태를 복원한다. UART 자체의 송신 대기도 active 중에는 제한한다. 보호 루프는 CLI를 호출하지 않는다.

| 새로 수행한 검사 | 결과 | 실제 경계 |
| --- | --- | --- |
| FPGA helper |22경우 통과 |실제 checked C + FatFS/핀/tick 모형. RLE·파일·핀·출력 상한/멈춘 tick/wrap |
| SD helper |24경우 통과 |실제 추출 command/CRC/wait/read. 비영 데이터 네 lane CRC, 응답 중/후 data, busy/response/data/CRC 오류, sticky/retry 방어 |
| LED / UART |16복원 조합 /5경우 통과 |실제 플랫폼 C + GPIO/UART/tick 모형. 원래 LED 모드/상태 복원, UART 대기 종료 |
| FatFS |6경우 통과 |실제 `f_read`/`validate`/`clust2sect`와064 `sdn_read`. 직접/캐시 읽기, 첫/부분 오류와 재접근 거부. FAT chain/카드는 모형 |
| 상위 SD/메뉴 |41회귀·18입력 거부·16메뉴 세션 + native 오류 보호2경우 통과 |실제064 C + SD/설정/GPIO 모형. early/적재 중 SD 오류 후 base 읽기/USB/메뉴 금지 |
| 실패 대조2개 |예상 assertion에서 실패 |SD 오류를 RES_OK로 바꾸거나 DONE 확인을 생략한 변형 |
| 전체 SPI |80/96KiB,180224바이트/901152프레임 |실제 새 C의 트랜잭션 기록이063 원본 두 trace와 SHA256 동일. 마지막 ACK/FINISH/STOP, START 없음 |
| STM32F401 ARM 전체 링크 |통과 |최종 ELF의3개 marker·1개 공유 run call·그 call로 합쳐지는2분기, checked 설정2호출·runtime/SD-fault 호출 확인. compile-only |

063의50,464,224응답 비트 보드 핀 재생과061 fit/STA는 동일 trace·생산 RTL에 한정해 재사용한다. 새 Questa/fit을 실행하지 않았다. 064에서 플랫폼 SD/설정/관측 C가 바뀌었으므로063을 실제 SD/설정/CPU 지연이나 물리 실행 증명으로 확장하지 않는다. SPI 기록은 명시적인2µs mock delay를 유지하며 UART/SD/CPU 실행 시간은 포함하지 않는다. 전체 NES059959LAB/4여유·마지막8프레임은 별도 근거다.

ARM 첫 빌드의 Make3.81 dependency 실패와 재시도, LED 상태 extern 누락, 정확히3개 run `bl`을 요구했던 검사 실패를 보존했다. 마지막 오류는 컴파일 실패가 아니라 GCC가 세 수동 경로를 한 call block으로 합친 결과였으며 실제 분기 목적지를 검사하도록 수정했다. host 첫 unused mock·macro의 local/global 이름 충돌·FatFS mock 선언/링크 오류도 원시 로그에 남겼다. 성공만 골라 이전 로그를 덮지 않았다.

근거는 로컬 `probes/nes-diag-recovery-064/` manifest에 동결한다. 공개 저장소에는 계약·시험 driver·집계만 포함하고 원시 로그/ROM/ELF/STM/라이선스를 넣지 않는다. [계약과 재현](../docs/nes-diag-recovery-contract.md), [기계 판독 집계](diag-recovery-verification.json).

H08은 미완료에서 **부분 완료**로 바뀌어 점검표는 완료5/부분6/미완료1이다. 공수·제품 완성률이 아니다. H09도 계속 부분 완료다. 메뉴 재적재의 FPGA SD offload, 늦은 SD 로그 쓰기와 active 밖 UART, 기존 SPI TIM2 대기까지 전체 호출 종료를 보장하지 않는다. 패드 취소·물리 watchdog·실제 LED 관측은 미구현/미검증이다.

다음 목표는 메뉴 준비/로그까지 하위 대기 오류가 반환되도록 연결하고 실패·재진입·RESET/USB/SD 보호를 검증하는 것이다. 이후 정확한 PSRAM 외부 min/max·보드 대응·최종 FPGA ASM/ARM 쌍·압축 roundtrip·백업/rollback을 닫아 제한된 실기 적재/비교/STOP·메뉴/GBC 복귀에 진입한다. 아직 새 설치 파일을 요청하지 않는다.
