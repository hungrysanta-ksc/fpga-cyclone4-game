# H1 040 정상 읽기 종료 오검출 수정

039 실기 로그를 보존·해석하고, 정상적인 payload 읽기 종료를 오류로 기록하는 RTL 결함을 재현해 수정했다.
040 FPGA 단일 교체 묶음은 준비 완료이며 **040 실기 결과는 아직 없다**.
[실기 안내](../docs/nes-h1-release-test.ko.md), [검증 기록](h1-release-verification.json).

## 실제039 증거

사용자는 화면1 뒤 자동 메뉴 복귀가 동일하다고 보고했다. candidate=NES-H1-FAULT-039,
F2_STATUS/07, start/stop=0, base_restored=1, polls=33, elapsed450ms다.
스냅샷 a539078710100018014e4d2e0002: frontend mask1, stage bus0, producer0,
flags87(valid/ready/RD높음/WR높음), ROMSEL높음, 주소011800, publish2.
캡처는 ARM 뒤3,034,446 host cycles(명목84MHz에서 약36.124ms)다.
450ms에는 FPGA 설정 시간이 포함되며 polls는 정확한 시간 단위가 아니다.
스냅샷은 오류 레지스터 갱신 다음 클록에 기록되므로011800을 오류 발생 트랜잭션 주소라고 단정하지 않는다.

## 결함과 최소 수정

031 frontend의 output_valid는 동기화된 RD 해제를 기다리는 동안 남는다.
그 사이 정상적으로 raw RD가 높아지고 ROMSEL도 높아지면 기존 마지막 조건이 frontend_error[0]를 설정한다.
즉 완료된 읽기까지 활성 읽기로 취급한다. 기존 보드 테스트는 RD만 해제하고 ROMSEL을 낮게 유지해 이 결함을 놓쳤다.

[파생 수정](../tools/nes_h1_release.py)은 ROMSEL 검사에 !read_n 조건 하나를 추가한다.
원본031 파일 해시를 고정해 보존하고, 새 RTL 시험과 물리 빌드에 동일한 파생 frontend를 넣는다.
응답 pending 중 조기 RD 해제, 활성 읽기의 ROMSEL 해제·주소 변경, RD/WR 충돌은 계속 오류다.
오류 무시·상태 강제 정상화·대기시간 연장은 하지 않았다.
039 snapshot boundary/SPI, MCU, ROM, 핀과 SDC는 그대로다. 프로토콜0x39와 로그 파일명039도 유지된다.

## 실제 실행 검증

- 기존 무료 Starter FLOAT 경로의 Questa 실행. 정상 읽기156조건(12위상,120/180ns pulse,해제 skew0/1/6/12/24/36ns와 레지스터 읽기): 수정본156통과, 기존본120개 오검출.
- 실제 비정상 종료72조건: 활성ROMSEL 해제, 응답 전 RD 해제, 활성주소 변경, RD/WR충돌, 순서위반, 응답부재 검출 유지.
- 전체 boundary/queue/stage/producer에서 정상 읽기 종료만으로 기존본 F2=07, flags87, frontend1/bus0/producer0, ROMSEL/RD/WR높음,011800 재현. 수정본 F2=03, snapshot0, frontend0.
- 이 시험은 합법적인 합성 버스 자극이다. 실기에서 측정한 핀 파형의 재생이 아니므로 같은 상태 재현만으로 실기 원인을 확정하지 않는다.
- 전체 보드9조건 통과:64KiB ROM,8192 payload bytes,3페이지와 대기 중 poll,STOP/재진입,PLL 상실,최초 오류 보존. 정상 모든 읽기는 이제 RD와 ROMSEL을 함께 해제한다.
- 기존039 MCU 생산 코드에서 채집한 GPIO 파형을 이번 FPGA RTL에 다시 입력:448샘플 중 명령/dummy 제외 응답200비트,1880행 통과. MCU가 동일하므로 ARM 재빌드는 하지 않았다.
- 동일 파생 RTL 실제 map/fit/STA/ASM 통과:1465LE/110LAB/44M9K/954register/135physical pins/0virtual/PLL1.
- 내부 최소 여유 setup2.721ns,hold0.131ns,recovery5.619ns,removal1.507ns,pulse5.604ns. 외부38입력831경로·11출력895경로는 미제약 그대로이며 전기 signoff가 아니다.
- RBF223004바이트,BI3165212바이트. 실제 pinned MCU rle_file_getc로223004바이트와 EOF 일치. 기존 encoder의 증명된 마지막FF 중복만 제거하고 원출력 보존.
- 설치·복원9조건:실제039 MCU/FPGA와040 FPGA 바이트 사용. 정상백업/복원·중단복구·알수없는MCU/FPGA·메뉴누락·SD내백업·변경된대상·깨진백업·변경된보존MCU 검사. SD 폴더/base/menu/GBC는 테스트 fixture이며 물리 SD 쓰기는 하지 않았다.

## 전달과 다음 확인

패키지 analysis/local-h1-release-040/NES-H1-RELEASE-040.zip에는 sd-overlay/sd2snes/fpga_nh1.bi3 하나만 있다.
현재039 firmware.stm 유지, 기존039 FPGA는 별도 백업. 기존 NES H1 037.nh1 실행, 화면제목034 유지.
정상1→2→3→1 순환10초→RESET→재진입→GBC 순서로 확인한다. 새 로그는 계속 nes-h1-last-039.txt다.
패키지의 기준 그림은 같은 ROM의 실제034 에뮬레이터 캡처 재사용이며 이번 새 에뮬레이터 실행 주장이 아니다.

039 공개/원시 기록241항목은 상태8파일의 사본과 함께 보존한다. GBC152해시,비NES registry,H0 결과,원본frontend와upstream을 유지한다.
이번 변경은 H1 전달 진단에 한정된다. NES 실제 producer/메모리/렌더러 통합,032 코어자원40LAB여유 검토,DMC 정확성 과제는 남아 있다.
