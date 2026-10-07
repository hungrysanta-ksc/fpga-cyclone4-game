# NES063 전체 수동 진단 C → 보드 메모리 핀 검증

**두 형상의 전체 적재·읽기 비교·순서 ACK·FINISH·STOP가 디지털 보드 핀 모형까지 통과했다.** 총180,224바이트 쓰기/읽기/ACK와50,464,224응답 비트가 일치했다. 생산061 RTL과062 C를 변경하지 않았으며044 실기/GBC 기준을 보존한다. 실제 STM32/SD 실행,메뉴 화면 복귀,외부 IO 사인오프와 설치 파일 쌍은 아직 없다.

PR16 병합 커밋 `b8e22a3c1df168708a071c0ce29b909c73cf6bdb`에서 진행했다. [기계 판독 근거](board-session-verification.json), [계약·재현](../docs/nes-board-session-contract.md), [현재 공정 가이드](../docs/development/NES-HARDWARE-READINESS-REVIEW.ko.md)를 함께 본다.

## 실제 연결 범위

062 실제 수동 메뉴 함수와 SD 검증/SPI C를 host GPIO/파일 플랫폼에서 실행해 승인된80/96KiB 두 파일을 완전히 처리했다. 헤더·크기·전체 CRC·close를 검사하고 전 바이트를 비교했다. BEGIN/END/FINISH/STOP 각1회,파일 close2회와 IRQ/GPIO 복원을 검사했으며 START는 보내지 않았다. PREPARED/RELEASE host 호출 후 verified/STOP/base 결과도 확인했다.

활성 SPI 프레임 안의 MOSI 전환·SCK 상승·C 샘플·CS 경계 시점을2µs 템플릿과 대조한 뒤 트랜잭션 기록을 만들었다. SCK 하강은 샘플 이후 순서를 검사하고 동일 C 템플릿으로 시점을 재구성한다. 이 기록을061 진단 top의 물리 SPI/PSRAM 핀에 재생했다. RAM은 초기화하지 않고 SPI DATA의 실제 WE 펄스로만 채웠다. 모든 쓰기/읽기 주소·chip·쓰기 byte lane·읽기 word enable을 검사했고,command byte 뒤 C가 사용하는 모든 응답 비트와 마지막 RAM 전체 바이트를 비교했다. END 적재 완료,마지막 ACK,FINISH verified,STOP 뒤 loaded/count/verified 해제와 주변 핀 소유권을 확인했다. CPU/PPU RUN은 끝까지 금지했다.

프레임 바깥 GPIO mode/latch 복원과 base FPGA 설정/메뉴 준비는 host 모형이다. 보드 재생은 STOP 뒤 진단 top에서 끝나며 실제 재설정·AF 전환·메뉴 화면을 재생하지 않는다.

## 최종 전체 시험

| 입력 | 쓰기/읽기/ACK 각각 | SPI 프레임 | C 응답 비트 | 시뮬레이션 경과 시간 |
| --- | --- | --- | --- | --- |
| fine_x | 81,920 | 409,616 | 22,938,352 | 1321.172초 |
| banks32 | 98,304 | 491,536 | 27,525,872 | 1580.703초 |

표의 시간은 호스트 시뮬레이션 소요 시간이다. C 명시적 지연 합은80KiB113.872638초/96KiB136.646398초이며 SD/CRC/실행/설정/메뉴 비용이나 실제 기기 시간·timeout 상한을 포함하지 않는다. 명목 위상1개로 재생했고 비동기 위상 스윕·인터럽트 지터·SD/CPU 처리 지연은 모형화하지 않았다. fixture와trace SHA256은 JSON 근거에 보존했다.

SPI decoder/PSRAM8MHz 클록은 모든 idle을 포함해 계속 구동했다. 긴 실행의 비용을 줄이기 위해 reset-held H1 포트만 별도 테스트 클록 표현식으로 분리하고 초기 CF61/F0A5/F144 뒤 디지털84MHz legacy 영역을 정지했다. 이후 모든 명령이 loader6x이고 모든 응답 샘플이8MHz loader 경로를 선택함을 검사했다. C2µs 지연과 메모리 클록은 단축하지 않았다. 이 변경은 테스트 전용이며 전체 보드 클록/아날로그 PLL 검증으로 확대하지 않는다.

원래 클록 대조64프레임/29핀바이트와 legacy를 계속 구동한8,192프레임/4,093핀바이트를 통과했다. 최종 빠른 prefix도8,192프레임/458,608응답 비트를 통과했고 첫64프레임 경계가 두 전체 시험과 일치했다. prefix에는 CHECK 읽기가 없으므로 전체 성공으로 집계하지 않았다. 같은 생산 소스의062 bounded CHECK/STOP 및 오류·START/lock-loss 회귀를 별도 근거로 재사용했다.

## 보존한 실패와 수정 근거

- 최초 H1 input net force는 공유 PLL net에도 영향을 줘 첫 CF 응답이 high-Z로 실패했다. 제품 클록을 바꾸지 않고 테스트 포트 연결을 분리했다. DATA 전 실패 원본을 보존했다.
- 첫 전체80KiB 시험은 모든81,920바이트 쓰기와 END 뒤 첫 CHECK에서 실패했다. 새 monitor가 byte-write lane을 읽기에도 요구한 것이 원인이었다. 기존 reader는 두 word lane을 모두 열고 내부에서 byte를 고른다. monitor만 기존 계약대로 수정하고 새 폴더에서 전체를 다시 실행했다. 생산 RTL은 같다.
- 원래 클록/빠른 prefix는 읽기 monitor 수정 전 실행이다. 해당 prefix에서 실행하지 않은 read assertion과 설명2줄만 다름을 정확한 소스 비교로 감사했다. 수정된 assertion은 최종 두 전체 읽기에서 실행됐다.
- ARM 재사용 사전 검사에서 overlay-only archive에 없는 기준 헤더3개를 찾던 오류는063 archive 생성 전에 수정했다. ARM overlay10개와 공개 기준 헤더3개를 구분해 각각 동일 해시를 확인했다.

## 재사용과 증거 보관

생산 SV14개는061fit03과 동일하다. 따라서2386LE/186LAB/1458registers/44M9K/135물리핀/PLL1과 내부 최소slack0.131ns를 재사용했고 새 fit/STA를 돌리지 않았다. 외부54입력/49출력 포트는 여전히 미제약이다. 지연 RAM 모형70ns read/35ns disable/350ns minimum WE는 시험 가정이며 실제 PSRAM의 min/max 데이터시트가 아니다.

생산 C도062 ARM과 동일해 호출되는 기존 ARM 링크를 재사용했다. 이번에는 실제 ARM 실행이나 새 설치 이미지가 없다. 전체 NES059의959/963LAB와4LAB여유,마지막2ROM/8프레임 근거는 별도이며 이번에 일반 코어를 다시 실행하지 않았다.

로컬 `probes/nes-board-session-063/`에 실행 소스·로그·입력·결과와431파일 manifest를 동결했다. 중복 replay trace는 host02 원본trace와 명시적 해시 link로 보관했다. `verify_nes_board_session.py`는 이 로컬 근거의 해시·정확한 PASS 수치·생산 소스 재사용·테스트 변경 범위를 감사한다. 공개 clone만으로 새 시험을 실행했다는 뜻이 아니다. 라이선스·서버 정보·ROM·로그·바이너리는 공개 대상에서 제외한다.

## 다음 경계

현재 점검표는 완료5/부분5/미완료2이며 H10은 현재 소스의 디지털 적재 전용 전체 통합 범위에서 완료다. 최종 소스/타이밍 변경은 영향 검사를 다시 한다. 이 집계는 일정·공수·제품 완성률이 아니다.

다음은 RESET 중 읽을 수 있는 단계/진행 표시와 실제 하위 SD 대기·FPGA 설정 실패의 종료/오류 전달을 연결하는 H08/H09 작업이다. 함수 밖 timeout으로 panic이나 무한 대기가 종료된다고 가정하지 않는다. 알려진 FXPAK Pro/Mk.III·STM32·EP4CE15F17C8을 다시 질문하지 않으며 정확한 PSRAM 부품·timing/BOM 대응과 외부 IO H05/H06를 계속 검토한다. 이어 최종 FPGA/ARM 쌍·압축·manifest·SD 백업/rollback을 준비하고 제한된 실기 적재/비교/메뉴 복귀/재진입/GBC 복귀를 확인한다.
